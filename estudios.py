from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from bd import get_db_connection
from werkzeug.utils import secure_filename
from datetime import datetime
import os

# =========================
# CONFIGURACIÓN
# =========================
UPLOAD_FOLDER_GAB = 'static/resultados/gabinete'
UPLOAD_FOLDER_LAB = 'static/resultados/laboratorio'

os.makedirs(UPLOAD_FOLDER_GAB, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_LAB, exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def contar_solicitudes_pendientes():
    """Función auxiliar para contar solicitudes pendientes (id_examen únicos)"""
    db = get_db_connection()
    examenes_laboratorio = db['examenes_laboratorio']
    lab_pendientes = examenes_laboratorio.count_documents({"estado": {"$regex": "^pendiente$", "$options": "i"}})
    
    examenes_gabinete_det = db['examenes_gabinete_det']
    gab_pendientes = examenes_gabinete_det.count_documents({"estado": {"$regex": "^PENDIENTE$"}})
    
    total_pendientes = lab_pendientes + gab_pendientes
    
    return lab_pendientes, gab_pendientes, total_pendientes
#------------------------------------------------------------------------------------------------------------
estudios_bp = Blueprint('estudios', __name__)

def obtener_rol_usuario():
    if 'user_id' not in session:
        return None

    db = get_db_connection()
    users = db['users']
    user = users.find_one({"id": int(session['user_id'])}, {"role": 1})
    return user['role'] if user else None


# =========================
# HOME / LISTADOS
# =========================
@estudios_bp.route('/')
def estudios_home():
    vista = request.args.get('vista')
    solicitudes = []

    # =========================
    # CONTAR SOLICITUDES PENDIENTES
    # =========================
    lab_pendientes, gab_pendientes, total_pendientes = contar_solicitudes_pendientes()

    # -------- LABORATORIO PENDIENTES --------
    if vista == 'solicitudes_laboratorio':
        db = get_db_connection()
        pipeline = [
            {"$match": {"estado": {"$regex": "^pendiente$", "$options": "i"}}},
            {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
            {"$unwind": "$atencion"},
            {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
            {"$unwind": "$paciente"},
            {"$lookup": {"from": "camas", "localField": "atencion.id_cama", "foreignField": "id_cama", "as": "cama"}},
            {"$unwind": {"path": "$cama", "preserveNullAndEmptyArrays": True}},
            {"$lookup": {"from": "users", "localField": "id_medico", "foreignField": "id", "as": "user"}},
            {"$unwind": "$user"},
            {"$lookup": {"from": "examenes_laboratorio_det", "localField": "id_examen", "foreignField": "id_examen", "as": "det"}},
            {"$unwind": "$det"},
            {"$lookup": {"from": "catalogo_examenes_laboratorio", "localField": "det.id_catalogo", "foreignField": "id_catalogo", "as": "cat"}},
            {"$unwind": "$cat"},
            {"$group": {
                "_id": "$id_examen",
                "fecha": {"$first": "$fecha"},
                "paciente": {"$first": {"$concat": ["$paciente.nom_pac", " ", "$paciente.papell", " ", "$paciente.sapell"]}},
                "medico": {"$first": "$user.papell"},
                "habitacion": {"$first": "$cama.numero"},
                "estudios": {"$push": "$cat.nombre"}
            }},
            {"$project": {
                "id_examen": "$_id",
                "fecha": 1,
                "paciente": 1,
                "medico": 1,
                "habitacion": 1,
                "estudios": {"$reduce": {"input": "$estudios", "initialValue": "", "in": {"$concat": ["$$value", {"$cond": [{"$eq": ["$$value", ""]}, "", ", "]}, "$$this"]}}}
            }},
            {"$sort": {"fecha": -1}}
        ]
        solicitudes = list(db['examenes_laboratorio'].aggregate(pipeline))

    # -------- LABORATORIO REALIZADOS --------
    if vista == 'resultados_laboratorio':
        db = get_db_connection()
        pipeline = [
            {"$match": {"estado": {"$regex": "^realizado$", "$options": "i"}}},
            {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
            {"$unwind": "$atencion"},
            {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
            {"$unwind": "$paciente"},
            {"$lookup": {"from": "camas", "localField": "atencion.id_cama", "foreignField": "id_cama", "as": "cama"}},
            {"$unwind": {"path": "$cama", "preserveNullAndEmptyArrays": True}},
            {"$lookup": {"from": "users", "localField": "id_medico", "foreignField": "id", "as": "user"}},
            {"$unwind": "$user"},
            {"$lookup": {"from": "examenes_laboratorio_det", "localField": "id_examen", "foreignField": "id_examen", "as": "det"}},
            {"$unwind": "$det"},
            {"$lookup": {"from": "catalogo_examenes_laboratorio", "localField": "det.id_catalogo", "foreignField": "id_catalogo", "as": "cat"}},
            {"$unwind": "$cat"},
            {"$group": {
                "_id": "$id_examen",
                "fecha": {"$first": "$fecha"},
                "fecha_realizado": {"$first": "$fecha_realizado"},
                "paciente": {"$first": {"$concat": ["$paciente.nom_pac", " ", "$paciente.papell", " ", "$paciente.sapell"]}},
                "medico": {"$first": "$user.papell"},
                "habitacion": {"$first": "$cama.numero"},
                "estudios": {"$push": "$cat.nombre"}
            }},
            {"$project": {
                "id_examen": "$_id",
                "fecha": 1,
                "fecha_realizado": 1,
                "paciente": 1,
                "medico": 1,
                "habitacion": 1,
                "estudios": {"$reduce": {"input": "$estudios", "initialValue": "", "in": {"$concat": ["$$value", {"$cond": [{"$eq": ["$$value", ""]}, "", ", "]}, "$$this"]}}}
            }},
            {"$sort": {"fecha_realizado": -1}}
        ]
        solicitudes = list(db['examenes_laboratorio'].aggregate(pipeline))

    # -------- GABINETE PENDIENTES --------
    if vista == 'solicitudes_gabinete':
        db = get_db_connection()
        pipeline = [
            {"$lookup": {"from": "examenes_gabinete_det", "localField": "id_examen", "foreignField": "id_examen", "as": "det"}},
            {"$unwind": "$det"},
            {"$match": {"det.estado": {"$regex": "^PENDIENTE$"}}},
            {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
            {"$unwind": "$atencion"},
            {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
            {"$unwind": "$paciente"},
            {"$lookup": {"from": "camas", "localField": "atencion.id_cama", "foreignField": "id_cama", "as": "cama"}},
            {"$unwind": {"path": "$cama", "preserveNullAndEmptyArrays": True}},
            {"$lookup": {"from": "users", "localField": "id_medico", "foreignField": "id", "as": "user"}},
            {"$unwind": "$user"},
            {"$group": {
                "_id": "$id_examen",
                "fecha": {"$first": "$fecha"},
                "paciente": {"$first": {"$concat": ["$paciente.papell", " ", "$paciente.sapell", " ", "$paciente.nom_pac"]}},
                "medico": {"$first": "$user.papell"},
                "habitacion": {"$first": "$cama.numero"},
                "estudios": {"$push": "$det.nombre_examen"}
            }},
            {"$project": {
                "id_examen": "$_id",
                "fecha": 1,
                "paciente": 1,
                "medico": 1,
                "habitacion": 1,
                "estudios": {"$reduce": {"input": "$estudios", "initialValue": "", "in": {"$concat": ["$$value", {"$cond": [{"$eq": ["$$value", ""]}, "", ", "]}, "$$this"]}}}
            }},
            {"$sort": {"fecha": -1}}
        ]
        solicitudes = list(db['examenes_gabinete'].aggregate(pipeline))

    # ---------------- GABINETE REALIZADOS ----------------
    if vista == 'resultados_gabinete':
        db = get_db_connection()
        pipeline = [
            {"$lookup": {"from": "examenes_gabinete_det", "localField": "id_examen", "foreignField": "id_examen", "as": "det"}},
            {"$unwind": "$det"},
            {"$match": {"det.estado": {"$regex": "^REALIZADO$"}}},
            {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
            {"$unwind": "$atencion"},
            {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
            {"$unwind": "$paciente"},
            {"$lookup": {"from": "camas", "localField": "atencion.id_cama", "foreignField": "id_cama", "as": "cama"}},
            {"$unwind": {"path": "$cama", "preserveNullAndEmptyArrays": True}},
            {"$lookup": {"from": "users", "localField": "id_medico", "foreignField": "id", "as": "user"}},
            {"$unwind": "$user"},
            {"$group": {
                "_id": "$id_examen",
                "fecha": {"$first": "$fecha"},
                "fecha_realizado": {"$first": "$det.fecha_realizado"},
                "paciente": {"$first": {"$concat": ["$paciente.papell", " ", "$paciente.sapell", " ", "$paciente.nom_pac"]}},
                "medico": {"$first": "$user.papell"},
                "habitacion": {"$first": "$cama.numero"},
                "estudios": {"$push": "$det.nombre_examen"}
            }},
            {"$project": {
                "id_examen": "$_id",
                "fecha": 1,
                "fecha_realizado": 1,
                "paciente": 1,
                "medico": 1,
                "habitacion": 1,
                "estudios": {"$reduce": {"input": "$estudios", "initialValue": "", "in": {"$concat": ["$$value", {"$cond": [{"$eq": ["$$value", ""]}, "", ", "]}, "$$this"]}}}
            }},
            {"$sort": {"fecha_realizado": -1}}
        ]
        solicitudes = list(db['examenes_gabinete'].aggregate(pipeline))

    return render_template(
        'estudios/index.html',
        vista=vista,
        solicitudes=solicitudes,
        lab_pendientes=lab_pendientes,
        gab_pendientes=gab_pendientes,
        total_pendientes=total_pendientes
    )

# =========================
# SUBIR RESULTADOS GABINETE
# =========================
@estudios_bp.route('/subir_resultado_gabinete/<int:id_examen>', methods=['GET', 'POST'])
def subir_resultado_gabinete(id_examen):
    db = get_db_connection()

    pipeline = [
        {"$match": {"id_examen": id_examen}},
        {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
        {"$unwind": "$atencion"},
        {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$lookup": {"from": "camas", "localField": "atencion.id_cama", "foreignField": "id_cama", "as": "cama"}},
        {"$unwind": {"path": "$cama", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "examenes_gabinete_det", "localField": "id_examen", "foreignField": "id_examen", "as": "det"}},
        {"$unwind": "$det"},
        {"$group": {
            "_id": "$id_examen",
            "paciente": {"$first": {"$concat": ["$paciente.papell", " ", "$paciente.sapell", " ", "$paciente.nom_pac"]}},
            "habitacion": {"$first": "$cama.numero"},
            "estudios": {"$push": "$det.nombre_examen"}
        }},
        {"$project": {
            "id_examen": "$_id",
            "paciente": 1,
            "habitacion": 1,
            "estudios": {"$reduce": {"input": "$estudios", "initialValue": "", "in": {"$concat": ["$$value", {"$cond": [{"$eq": ["$$value", ""]}, "", ", "]}, "$$this"]}}}
        }}
    ]
    solicitud = list(db['examenes_gabinete'].aggregate(pipeline))[0] if list(db['examenes_gabinete'].aggregate(pipeline)) else None

    if request.method == 'POST':
        observaciones = request.form.get('observaciones', '')
        files = request.files.getlist('archivos')

        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER_GAB, filename))

                db['examenes_gabinete_det'].update_many({"id_examen": id_examen}, {"$set": {
                    "archivo_resultado": filename,
                    "observaciones": observaciones,
                    "fecha_realizado": datetime.now(),
                    "estado": 'REALIZADO'
                }})

        flash('Resultados de gabinete subidos correctamente', 'success')
        return redirect(url_for('estudios.estudios_home', vista='solicitudes_gabinete'))
    # Obtener conteo de solicitudes pendientes
    lab_pendientes, gab_pendientes, total_pendientes = contar_solicitudes_pendientes()
        

    return render_template(
        'estudios/index.html',
        vista='subir_resultado_gabinete',
        solicitud=solicitud,
        lab_pendientes=lab_pendientes,
        gab_pendientes=gab_pendientes,
        total_pendientes=total_pendientes
    )

# =========================
# SUBIR RESULTADOS LABORATORIO
# =========================
@estudios_bp.route('/subir_resultado_laboratorio/<int:id_examen>', methods=['GET', 'POST'])
def subir_resultado_laboratorio(id_examen):
    db = get_db_connection()

    pipeline = [
        {"$match": {"id_examen": id_examen}},
        {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
        {"$unwind": "$atencion"},
        {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$lookup": {"from": "camas", "localField": "atencion.id_cama", "foreignField": "id_cama", "as": "cama"}},
        {"$unwind": {"path": "$cama", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "examenes_laboratorio_det", "localField": "id_examen", "foreignField": "id_examen", "as": "det"}},
        {"$unwind": "$det"},
        {"$lookup": {"from": "catalogo_examenes_laboratorio", "localField": "det.id_catalogo", "foreignField": "id_catalogo", "as": "cat"}},
        {"$unwind": "$cat"},
        {"$group": {
            "_id": "$id_examen",
            "paciente": {"$first": {"$concat": ["$paciente.nom_pac", " ", "$paciente.papell", " ", "$paciente.sapell"]}},
            "habitacion": {"$first": "$cama.numero"},
            "estudios": {"$push": "$cat.nombre"}
        }},
        {"$project": {
            "id_examen": "$_id",
            "paciente": 1,
            "habitacion": 1,
            "estudios": {"$reduce": {"input": "$estudios", "initialValue": "", "in": {"$concat": ["$$value", {"$cond": [{"$eq": ["$$value", ""]}, "", ", "]}, "$$this"]}}}
        }}
    ]
    solicitud = list(db['examenes_laboratorio'].aggregate(pipeline))[0] if list(db['examenes_laboratorio'].aggregate(pipeline)) else None

    if request.method == 'POST':
        observaciones = request.form.get('observaciones', '')
        files = request.files.getlist('archivos')

        nombres_archivos = []

        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER_LAB, filename))
                nombres_archivos.append(filename)

        db['examenes_laboratorio'].update_one({"id_examen": id_examen}, {"$set": {
            "archivo_resultado": ','.join(nombres_archivos),
            "observaciones": observaciones,
            "fecha_realizado": datetime.now(),
            "estado": 'realizado'
        }})

        flash('Resultados de laboratorio subidos correctamente', 'success')
        return redirect(url_for('estudios.estudios_home', vista='solicitudes_laboratorio'))
    # Obtener conteo de solicitudes pendientes
    lab_pendientes, gab_pendientes, total_pendientes = contar_solicitudes_pendientes()

    return render_template(
        'estudios/index.html',
        vista='subir_resultado_laboratorio',
        solicitud=solicitud,
        lab_pendientes=lab_pendientes,
        gab_pendientes=gab_pendientes,
        total_pendientes=total_pendientes
    )



# =========================
# EDITAR RESULTADOS LABORATORIO
# =========================
@estudios_bp.route('/editar_resultado_laboratorio/<int:id_examen>', methods=['GET', 'POST'])
def editar_resultado_laboratorio(id_examen):
    db = get_db_connection()

    # 1) Información general del estudio
    pipeline = [
        {"$match": {"id_examen": id_examen}},
        {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
        {"$unwind": "$atencion"},
        {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$lookup": {"from": "camas", "localField": "atencion.id_cama", "foreignField": "id_cama", "as": "cama"}},
        {"$unwind": {"path": "$cama", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "id_examen": 1,
            "paciente": {"$concat": ["$paciente.nom_pac", " ", "$paciente.papell", " ", "$paciente.sapell"]},
            "habitacion": "$cama.numero",
            "archivo_resultado": 1,
            "observaciones": 1
        }}
    ]
    solicitud = list(db['examenes_laboratorio'].aggregate(pipeline))[0] if list(db['examenes_laboratorio'].aggregate(pipeline)) else None

    # Si no existe
    if not solicitud:
        flash('Solicitud no encontrada', 'danger')
        return redirect(url_for('estudios.estudios_home', vista='resultados_laboratorio'))

    paciente = solicitud.get('paciente')
    habitacion = solicitud.get('habitacion')
    archivo_resultado = solicitud.get('archivo_resultado') or ''
    observaciones = solicitud.get('observaciones') or ''

    # Convertir archivos a lista (nombres)
    archivos = []
    if archivo_resultado:
        # quitar espacios innecesarios
        archivos = [a.strip() for a in archivo_resultado.split(',') if a.strip()]

    # POST -> procesar eliminación / subida de nuevos archivos y actualizar DB
    if request.method == 'POST':
        # 1) Archivos a eliminar (checkboxes)
        eliminar = request.form.getlist('eliminar_archivos')  # lista de nombres
        # 2) Nuevos archivos a subir
        nuevos = request.files.getlist('archivos')

        # --- eliminar físicamente los archivos marcados (si existen) ---
        if eliminar:
            for nombre in eliminar:
                # quitar del listado actual
                if nombre in archivos:
                    archivos.remove(nombre)

                # intentar borrar archivos en la carpeta de uploads que terminen con el nombre eliminado
                try:
                    for f in os.listdir(UPLOAD_FOLDER_LAB):
                        # comparamos por igualdad o por que termine con el nombre (por si guardaste con prefijo)
                        if f == nombre or f.endswith('_' + nombre) or f.endswith(nombre):
                            ruta_borrar = os.path.join(UPLOAD_FOLDER_LAB, f)
                            if os.path.isfile(ruta_borrar):
                                try:
                                    os.remove(ruta_borrar)
                                except Exception:
                                    # no detener por error en borrado físico
                                    pass
                except FileNotFoundError:
                    # la carpeta puede no existir; no rompemos la ejecución
                    pass

        # --- procesar subida de nuevos archivos ---
        nuevos_guardados = []
        if nuevos:
            # asegurar carpeta
            os.makedirs(UPLOAD_FOLDER_LAB, exist_ok=True)

            for file in nuevos:
                if file and allowed_file(file.filename):
                    # validar tamaño sin leer todo el archivo en memoria
                    file_stream = file.stream
                    # mover al final y medir
                    try:
                        file_stream.seek(0, os.SEEK_END)
                        size = file_stream.tell()
                        file_stream.seek(0)
                    except Exception:
                        # si no se puede medir, permitimos (fallback)
                        size = 0

                    if size and size > MAX_FILE_SIZE:
                        flash(f'Archivo {file.filename} demasiado grande (máx 25MB).', 'danger')
                        return redirect(request.url)

                    filename_secure = secure_filename(file.filename)

                    # Para evitar colisiones en disco guardamos con prefijo de timestamp,
                    # pero guardamos en DB el nombre original (o si prefieres guardar el prefijado, cámbialo aqui)
                    ts = datetime.now().strftime('%Y%m%d%H%M%S%f')
                    nombre_guardado_en_disco = f"{id_examen}_{ts}_{filename_secure}"
                    ruta_guardado = os.path.join(UPLOAD_FOLDER_LAB, nombre_guardado_en_disco)
                    try:
                        file.save(ruta_guardado)
                    except Exception as e:
                        flash(f'Error al guardar {file.filename}: {str(e)}', 'danger')
                        return redirect(request.url)

                    # Añadimos el nombre **visible** que guardaremos en la BD.
                    # Si prefieres almacenar el nombre con prefijo (nombre_guardado_en_disco), cámbialo por esa variable.
                    nuevos_guardados.append(filename_secure)
                else:
                    # formato no permitido o filename vacío
                    if file and file.filename:
                        flash(f'Formato no permitido para {file.filename}', 'danger')
                        return redirect(request.url)

        # Unir archivos restantes + nuevos
        archivos_finales = archivos + nuevos_guardados

        # Actualizar DB: archivo_resultado, fecha_realizado y estado
        ahora = datetime.now()
        archivos_db = ','.join(archivos_finales)

        db['examenes_laboratorio'].update_one({"id_examen": id_examen}, {"$set": {
            "archivo_resultado": archivos_db,
            "fecha_realizado": ahora,
            "estado": 'realizado'
        }})

        flash('Cambios guardados correctamente', 'success')
        return redirect(url_for('estudios.estudios_home', vista='resultados_laboratorio'))

    # GET -> renderizar la vista de edición
    # Obtener conteo de solicitudes pendientes
    lab_pendientes, gab_pendientes, total_pendientes = contar_solicitudes_pendientes()

    # preparar 'solicitud' como dict para la plantilla (consistencia)
    solicitud_para_template = {
        'id_examen': id_examen,
        'paciente': paciente,
        'habitacion': habitacion,
        'observaciones': observaciones
    }

    return render_template(
        'estudios/index.html',
        vista='editar_resultado_laboratorio',
        solicitud=solicitud_para_template,
        archivos=archivos,
        lab_pendientes=lab_pendientes,
        gab_pendientes=gab_pendientes,
        total_pendientes=total_pendientes
    )



# =========================
# EDITAR RESULTADOS GABINETE
# =========================
@estudios_bp.route('/editar_resultado_gabinete/<int:id_examen>', methods=['GET', 'POST'])
def editar_resultado_gabinete(id_examen):
    db = get_db_connection()

    # 1) Información general del estudio con datos de examenes_gabinete_det
    # Obtener solo UN registro por id_examen ya que los archivos son los mismos
    pipeline = [
        {"$match": {"id_examen": id_examen}},
        {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
        {"$unwind": "$atencion"},
        {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$lookup": {"from": "camas", "localField": "atencion.id_cama", "foreignField": "id_cama", "as": "cama"}},
        {"$unwind": {"path": "$cama", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "examenes_gabinete_det", "localField": "id_examen", "foreignField": "id_examen", "as": "det"}},
        {"$unwind": "$det"},
        {"$group": {
            "_id": "$id_examen",
            "paciente": {"$first": {"$concat": ["$paciente.nom_pac", " ", "$paciente.papell", " ", "$paciente.sapell"]}},
            "habitacion": {"$first": "$cama.numero"},
            "observaciones": {"$max": "$det.observaciones"},
            "archivo_resultado": {"$max": "$det.archivo_resultado"}
        }},
        {"$project": {
            "id_examen": "$_id",
            "paciente": 1,
            "habitacion": 1,
            "observaciones": 1,
            "archivo_resultado": 1
        }},
        {"$limit": 1}
    ]
    solicitud = list(db['examenes_gabinete'].aggregate(pipeline))[0] if list(db['examenes_gabinete'].aggregate(pipeline)) else None

    # Si no existe
    if not solicitud:
        flash('Solicitud no encontrada', 'danger')
        return redirect(url_for('estudios.estudios_home', vista='resultados_gabinete'))

    paciente = solicitud.get('paciente')
    habitacion = solicitud.get('habitacion')
    archivo_resultado = solicitud.get('archivo_resultado') or ''
    observaciones = solicitud.get('observaciones') or ''

    # Convertir archivos a lista (nombres)
    archivos = []
    if archivo_resultado:
        # quitar espacios innecesarios y dividir por comas
        archivos = [a.strip() for a in archivo_resultado.split(',') if a.strip()]

    # POST -> procesar eliminación / subida de nuevos archivos y actualizar DB
    if request.method == 'POST':
        # 1) Obtener observaciones del formulario
        nuevas_observaciones = request.form.get('observaciones', '').strip()
        
        # 2) Archivos a eliminar (checkboxes)
        eliminar = request.form.getlist('eliminar_archivos')  # lista de nombres
        # 3) Nuevos archivos a subir
        nuevos = request.files.getlist('archivos')

        # --- eliminar físicamente los archivos marcados (si existen) ---
        if eliminar:
            for nombre in eliminar:
                # quitar del listado actual
                if nombre in archivos:
                    archivos.remove(nombre)

                # intentar borrar archivos en la carpeta de uploads que terminen con el nombre eliminado
                try:
                    for f in os.listdir(UPLOAD_FOLDER_GAB):
                        # comparamos por igualdad o por que termine con el nombre (por si guardaste con prefijo)
                        if f == nombre or f.endswith('_' + nombre) or f.endswith(nombre):
                            ruta_borrar = os.path.join(UPLOAD_FOLDER_GAB, f)
                            if os.path.isfile(ruta_borrar):
                                try:
                                    os.remove(ruta_borrar)
                                except Exception:
                                    # no detener por error en borrado físico
                                    pass
                except FileNotFoundError:
                    # la carpeta puede no existir; no rompemos la ejecución
                    pass

        # --- procesar subida de nuevos archivos ---
        nuevos_guardados = []
        if nuevos:
            # asegurar carpeta
            os.makedirs(UPLOAD_FOLDER_GAB, exist_ok=True)

            for file in nuevos:
                if file and allowed_file(file.filename):
                    # validar tamaño sin leer todo el archivo en memoria
                    file_stream = file.stream
                    # mover al final y medir
                    try:
                        file_stream.seek(0, os.SEEK_END)
                        size = file_stream.tell()
                        file_stream.seek(0)
                    except Exception:
                        # si no se puede medir, permitimos (fallback)
                        size = 0

                    if size and size > MAX_FILE_SIZE:
                        flash(f'Archivo {file.filename} demasiado grande (máx 25MB).', 'danger')
                        return redirect(request.url)

                    filename_secure = secure_filename(file.filename)

                    # Para evitar colisiones en disco guardamos con prefijo de timestamp,
                    # pero guardamos en DB el nombre original
                    ts = datetime.now().strftime('%Y%m%d%H%M%S%f')
                    nombre_guardado_en_disco = f"{id_examen}_{ts}_{filename_secure}"
                    ruta_guardado = os.path.join(UPLOAD_FOLDER_GAB, nombre_guardado_en_disco)
                    try:
                        file.save(ruta_guardado)
                    except Exception as e:
                        flash(f'Error al guardar {file.filename}: {str(e)}', 'danger')
                        return redirect(request.url)

                    # Añadimos el nombre **visible** que guardaremos en la BD.
                    nuevos_guardados.append(filename_secure)
                else:
                    # formato no permitido o filename vacío
                    if file and file.filename:
                        flash(f'Formato no permitido para {file.filename}', 'danger')
                        return redirect(request.url)

        # Unir archivos restantes + nuevos
        archivos_finales = archivos + nuevos_guardados

        # Actualizar DB: archivo_resultado, fecha_realizado, estado y observaciones en TODOS los registros de examenes_gabinete_det para este id_examen
        ahora = datetime.now()
        archivos_db = ','.join(archivos_finales)

        db['examenes_gabinete_det'].update_many({"id_examen": id_examen}, {"$set": {
            "archivo_resultado": archivos_db,
            "fecha_realizado": ahora,
            "estado": 'REALIZADO',
            "observaciones": nuevas_observaciones
        }})

        flash('Cambios guardados correctamente', 'success')
        return redirect(url_for('estudios.estudios_home', vista='resultados_gabinete'))

    # GET -> renderizar la vista de edición
    # Obtener conteo de solicitudes pendientes
    lab_pendientes, gab_pendientes, total_pendientes = contar_solicitudes_pendientes()

    # preparar 'solicitud' como dict para la plantilla (consistencia)
    solicitud_para_template = {
        'id_examen': id_examen,
        'paciente': paciente,
        'habitacion': habitacion,
        'observaciones': observaciones
    }

    return render_template(
        'estudios/index.html',
        vista='editar_resultado_gabinete',
        solicitud=solicitud_para_template,
        archivos=archivos,
        lab_pendientes=lab_pendientes,
        gab_pendientes=gab_pendientes,
        total_pendientes=total_pendientes
    )



# =========================
# VISTA PREVIA RESULTADOS LABORATORIO
# =========================
@estudios_bp.route('/ver_resultado_laboratorio/<int:id_examen>')
def ver_resultado_laboratorio(id_examen):
    db = get_db_connection()

    pipeline = [
        {"$match": {"id_examen": id_examen}},
        {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
        {"$unwind": "$atencion"},
        {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$project": {
            "id_examen": 1,
            "paciente": {"$concat": ["$paciente.nom_pac", " ", "$paciente.papell", " ", "$paciente.sapell"]},
            "archivo_resultado": 1
        }}
    ]
    row = list(db['examenes_laboratorio'].aggregate(pipeline))[0] if list(db['examenes_laboratorio'].aggregate(pipeline)) else None

    # Rol del usuario
    rol = obtener_rol_usuario()

    # Contadores
    lab_pendientes, gab_pendientes, total_pendientes = contar_solicitudes_pendientes()

    if not row:
        flash('Resultados no encontrados', 'danger')
        return redirect(url_for('estudios.estudios_home', vista='resultados_laboratorio'))

    archivos = []
    if row['archivo_resultado']:
        archivos = [a.strip() for a in row['archivo_resultado'].split(',') if a.strip()]

    return render_template(
        'estudios/index.html',
        vista='ver_resultado_laboratorio',
        paciente=row['paciente'],
        archivos=archivos,
        rol=rol,  # 🔥 CLAVE
        lab_pendientes=lab_pendientes,
        gab_pendientes=gab_pendientes,
        total_pendientes=total_pendientes
    )


# =========================
# VISTA PREVIA RESULTADOS GABINETE
# =========================
@estudios_bp.route('/ver_resultado_gabinete/<int:id_examen>')
def ver_resultado_gabinete(id_examen):
    db = get_db_connection()

    rows = list(db['examenes_gabinete_det'].find({"id_examen": id_examen, "estado": "REALIZADO"}, {"archivo_resultado": 1}))

    # Rol del usuario
    rol = obtener_rol_usuario()

    # Contadores
    lab_pendientes, gab_pendientes, total_pendientes = contar_solicitudes_pendientes()

    archivos = []

    for row in rows:
        if row.get('archivo_resultado'):
            for nombre in row['archivo_resultado'].split(','):
                nombre = nombre.strip()
                if nombre:
                    archivos.append({
                        'nombre': nombre,
                        'url': url_for(
                            'static',
                            filename=f'resultados/gabinete/{nombre}'
                        ),
                        'tipo': nombre.split('.')[-1].lower()
                    })

    return render_template(
        'estudios/index.html',
        vista='ver_resultado_gabinete',
        archivos=archivos,
        rol=rol,  # 🔥 CLAVE
        lab_pendientes=lab_pendientes,
        gab_pendientes=gab_pendientes,
        total_pendientes=total_pendientes
    )


# =========================
# ELIMINAR RESULTADO GABINETE
# =========================
@estudios_bp.route('/eliminar_resultado_gabinete/<int:id_examen>')
def eliminar_resultado_gabinete(id_examen):
    db = get_db_connection()

    # 1) Obtener archivos asociados
    rows = list(db['examenes_gabinete_det'].find({"id_examen": id_examen}, {"archivo_resultado": 1}))

    # 2) Eliminar archivos físicos
    try:
        for row in rows:
            archivo = row.get('archivo_resultado')
            if archivo:
                ruta = os.path.join(UPLOAD_FOLDER_GAB, archivo)
                if os.path.exists(ruta):
                    try:
                        os.remove(ruta)
                    except Exception:
                        pass
    except Exception:
        pass

    # 3) Eliminar detalles
    db['examenes_gabinete_det'].delete_many({"id_examen": id_examen})

    # 4) Eliminar encabezado
    db['examenes_gabinete'].delete_one({"id_examen": id_examen})

    flash('Solicitud de gabinete eliminada correctamente', 'success')
    return redirect(url_for('estudios.estudios_home', vista='resultados_gabinete'))

# =========================
# ELIMINAR RESULTADO LABORATORIO
# =========================
@estudios_bp.route('/eliminar_resultado_laboratorio/<int:id_examen>')
def eliminar_resultado_laboratorio(id_examen):
    db = get_db_connection()
    
    # 1) Obtener archivo asociado si existe
    resultado = db['examenes_laboratorio'].find_one({"id_examen": id_examen}, {"archivo_resultado": 1})
    
    # 2) Eliminar archivo físico si existe
    if resultado and 'archivo_resultado' in resultado and resultado['archivo_resultado']:
        try:
            ruta = os.path.join(UPLOAD_FOLDER_LAB, resultado['archivo_resultado'])
            if os.path.exists(ruta):
                os.remove(ruta)
        except Exception as e:
            print(f"Error al eliminar archivo: {e}")
            # Continuar con la eliminación de la base de datos aunque falle el archivo
    
    # 3) Eliminar detalles primero (debido a la relación de clave foránea)
    db['examenes_laboratorio_det'].delete_many({"id_examen": id_examen})
    
    # 4) Eliminar encabezado
    db['examenes_laboratorio'].delete_one({"id_examen": id_examen})
    
    flash('Solicitud de laboratorio eliminada correctamente', 'success')
    return redirect(url_for('estudios.estudios_home', vista='resultados_laboratorio'))