# estudios.py - Versión final con correcciones de joins y manejo de archivos
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from bd import get_db_connection
from werkzeug.utils import secure_filename
from datetime import datetime
from bson.objectid import ObjectId
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

def obtener_ids_catalogo_por_tipo(tipo):
    """Devuelve lista de id_catalogo cuyo tipo coincida (insensible a mayúsc/minúsc)."""
    db = get_db_connection()
    catalogo = db['catalogo_examenes']
    docs = catalogo.find({"tipo": {"$regex": f"^{tipo}$", "$options": "i"}}, {"id_catalogo": 1})
    return [doc['id_catalogo'] for doc in docs]

def contar_solicitudes_pendientes():
    """Cuenta solicitudes pendientes (id_examen únicos) por tipo usando el catálogo."""
    db = get_db_connection()
    examenes_det = db['examenes_det']

    lab_ids = obtener_ids_catalogo_por_tipo("LABORATORIO")
    gab_ids = obtener_ids_catalogo_por_tipo("GABINETE")

    pipeline_lab = [
        {"$match": {"id_catalogo": {"$in": lab_ids}, "estado": {"$regex": "^PENDIENTE$", "$options": "i"}}},
        {"$group": {"_id": "$id_examen"}},
        {"$count": "count"}
    ]
    lab_res = list(examenes_det.aggregate(pipeline_lab))
    lab_pendientes = lab_res[0]['count'] if lab_res else 0

    pipeline_gab = [
        {"$match": {"id_catalogo": {"$in": gab_ids}, "estado": {"$regex": "^PENDIENTE$", "$options": "i"}}},
        {"$group": {"_id": "$id_examen"}},
        {"$count": "count"}
    ]
    gab_res = list(examenes_det.aggregate(pipeline_gab))
    gab_pendientes = gab_res[0]['count'] if gab_res else 0

    return lab_pendientes, gab_pendientes, lab_pendientes + gab_pendientes

estudios_bp = Blueprint('estudios', __name__)

def obtener_rol_usuario():
    if 'user_id' not in session:
        return None
    db = get_db_connection()
    users = db['users']
    try:
        user = users.find_one({"_id": ObjectId(session['user_id'])}, {"role": 1})
        return user['role'] if user else None
    except:
        return None

# =========================
# HOME / LISTADOS
# =========================
@estudios_bp.route('/')
def estudios_home():
    vista = request.args.get('vista')
    solicitudes = []

    lab_pendientes, gab_pendientes, total_pendientes = contar_solicitudes_pendientes()
    db = get_db_connection()

    lab_ids = obtener_ids_catalogo_por_tipo("LABORATORIO")
    gab_ids = obtener_ids_catalogo_por_tipo("GABINETE")

    # -------- LABORATORIO PENDIENTES --------
    if vista == 'solicitudes_laboratorio':
        pipeline = [
            {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
            {"$unwind": "$atencion"},
            {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
            {"$unwind": "$paciente"},
            {"$lookup": {"from": "camas", "localField": "atencion.id_cama", "foreignField": "id_cama", "as": "cama"}},
            {"$unwind": {"path": "$cama", "preserveNullAndEmptyArrays": True}},
            {"$lookup": {"from": "users", "localField": "id_medico", "foreignField": "_id", "as": "user"}},  # 👈 CORREGIDO
            {"$unwind": "$user"},
            {"$lookup": {"from": "examenes_det", "localField": "id_examen", "foreignField": "id_examen", "as": "det"}},
            {"$unwind": "$det"},
            {"$match": {"det.id_catalogo": {"$in": lab_ids}, "det.estado": {"$regex": "^PENDIENTE$", "$options": "i"}}},
            {"$lookup": {"from": "catalogo_examenes", "localField": "det.id_catalogo", "foreignField": "id_catalogo", "as": "cat"}},
            {"$unwind": "$cat"},
            {"$group": {
                "_id": "$id_examen",
                "fecha": {"$first": "$fecha"},
                "paciente": {"$first": {"$concat": ["$paciente.nom_pac", " ", "$paciente.papell", " ", "$paciente.sapell"]}},
                "medico": {"$first": {"$concat": ["$user.nombre", " ", "$user.papell"]}},
                "habitacion": {"$first": "$cama.numero"},
                "estudios": {"$push": "$cat.nombre"}
            }},
            {"$project": {
                "id_examen": "$_id",
                "fecha": 1,
                "paciente": 1,
                "medico": 1,
                "habitacion": 1,
                "estudios": {
                    "$reduce": {
                        "input": "$estudios",
                        "initialValue": "",
                        "in": {"$concat": ["$$value", {"$cond": [{"$eq": ["$$value", ""]}, "", ", "]}, "$$this"]}
                    }
                }
            }},
            {"$sort": {"fecha": -1}}
        ]
        solicitudes = list(db['examenes'].aggregate(pipeline))

    # -------- LABORATORIO REALIZADOS --------
    elif vista == 'resultados_laboratorio':
        pipeline = [
            {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
            {"$unwind": "$atencion"},
            {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
            {"$unwind": "$paciente"},
            {"$lookup": {"from": "camas", "localField": "atencion.id_cama", "foreignField": "id_cama", "as": "cama"}},
            {"$unwind": {"path": "$cama", "preserveNullAndEmptyArrays": True}},
            {"$lookup": {"from": "users", "localField": "id_medico", "foreignField": "_id", "as": "user"}},
            {"$unwind": "$user"},
            {"$lookup": {"from": "examenes_det", "localField": "id_examen", "foreignField": "id_examen", "as": "det"}},
            {"$unwind": "$det"},
            {"$match": {"det.id_catalogo": {"$in": lab_ids}, "det.estado": {"$regex": "^REALIZADO$", "$options": "i"}}},
            {"$lookup": {"from": "catalogo_examenes", "localField": "det.id_catalogo", "foreignField": "id_catalogo", "as": "cat"}},
            {"$unwind": "$cat"},
            {"$group": {
                "_id": "$id_examen",
                "fecha": {"$first": "$fecha"},
                "fecha_realizado": {"$first": "$det.fecha_realizado"},
                "paciente": {"$first": {"$concat": ["$paciente.nom_pac", " ", "$paciente.papell", " ", "$paciente.sapell"]}},
                "medico": {"$first": {"$concat": ["$user.nombre", " ", "$user.papell"]}},
                "habitacion": {"$first": "$cama.numero"},
                "estudios": {"$push": "$cat.nombre"}
            }},
            # 👇 IMPORTANTE: proyectar _id como id_examen y formatear estudios como string
            {"$project": {
                "id_examen": "$_id",
                "fecha": 1,
                "fecha_realizado": 1,
                "paciente": 1,
                "medico": 1,
                "habitacion": 1,
                "estudios": {
                    "$reduce": {
                        "input": "$estudios",
                        "initialValue": "",
                        "in": {"$concat": ["$$value", {"$cond": [{"$eq": ["$$value", ""]}, "", ", "]}, "$$this"]}
                    }
                }
            }},
            {"$sort": {"fecha_realizado": -1}}
        ]
        solicitudes = list(db['examenes'].aggregate(pipeline))
    

    # -------- GABINETE PENDIENTES --------
    elif vista == 'solicitudes_gabinete':
        pipeline = [
            {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
            {"$unwind": "$atencion"},
            {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
            {"$unwind": "$paciente"},
            {"$lookup": {"from": "camas", "localField": "atencion.id_cama", "foreignField": "id_cama", "as": "cama"}},
            {"$unwind": {"path": "$cama", "preserveNullAndEmptyArrays": True}},
            {"$lookup": {"from": "users", "localField": "id_medico", "foreignField": "_id", "as": "user"}},  # 👈 CORREGIDO
            {"$unwind": "$user"},
            {"$lookup": {"from": "examenes_det", "localField": "id_examen", "foreignField": "id_examen", "as": "det"}},
            {"$unwind": "$det"},
            {"$match": {"det.id_catalogo": {"$in": gab_ids}, "det.estado": {"$regex": "^PENDIENTE$", "$options": "i"}}},
            {"$lookup": {"from": "catalogo_examenes", "localField": "det.id_catalogo", "foreignField": "id_catalogo", "as": "cat"}},
            {"$unwind": "$cat"},
            {"$group": {
                "_id": "$id_examen",
                "fecha": {"$first": "$fecha"},
                "paciente": {"$first": {"$concat": ["$paciente.nom_pac", " ", "$paciente.papell", " ", "$paciente.sapell"]}},
                "medico": {"$first": {"$concat": ["$user.nombre", " ", "$user.papell"]}},
                "habitacion": {"$first": "$cama.numero"},
                "estudios": {"$push": "$cat.nombre"}
            }},
            {"$project": {
                "id_examen": "$_id",
                "fecha": 1,
                "paciente": 1,
                "medico": 1,
                "habitacion": 1,
                "estudios": {
                    "$reduce": {
                        "input": "$estudios",
                        "initialValue": "",
                        "in": {"$concat": ["$$value", {"$cond": [{"$eq": ["$$value", ""]}, "", ", "]}, "$$this"]}
                    }
                }
            }},
            {"$sort": {"fecha": -1}}
        ]
        solicitudes = list(db['examenes'].aggregate(pipeline))

    # -------- GABINETE REALIZADOS --------
    elif vista == 'resultados_gabinete':
        pipeline = [
            {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
            {"$unwind": "$atencion"},
            {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
            {"$unwind": "$paciente"},
            {"$lookup": {"from": "camas", "localField": "atencion.id_cama", "foreignField": "id_cama", "as": "cama"}},
            {"$unwind": {"path": "$cama", "preserveNullAndEmptyArrays": True}},
            {"$lookup": {"from": "users", "localField": "id_medico", "foreignField": "_id", "as": "user"}},
            {"$unwind": "$user"},
            {"$lookup": {"from": "examenes_det", "localField": "id_examen", "foreignField": "id_examen", "as": "det"}},
            {"$unwind": "$det"},
            {"$match": {"det.id_catalogo": {"$in": gab_ids}, "det.estado": {"$regex": "^REALIZADO$", "$options": "i"}}},
            {"$lookup": {"from": "catalogo_examenes", "localField": "det.id_catalogo", "foreignField": "id_catalogo", "as": "cat"}},
            {"$unwind": "$cat"},
            {"$group": {
                "_id": "$id_examen",
                "fecha": {"$first": "$fecha"},
                "fecha_realizado": {"$first": "$det.fecha_realizado"},
                "paciente": {"$first": {"$concat": ["$paciente.nom_pac", " ", "$paciente.papell", " ", "$paciente.sapell"]}},
                "medico": {"$first": {"$concat": ["$user.nombre", " ", "$user.papell"]}},
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
                "estudios": {
                    "$reduce": {
                        "input": "$estudios",
                        "initialValue": "",
                        "in": {"$concat": ["$$value", {"$cond": [{"$eq": ["$$value", ""]}, "", ", "]}, "$$this"]}
                    }
                }
            }},
            {"$sort": {"fecha_realizado": -1}}
        ]
        solicitudes = list(db['examenes'].aggregate(pipeline))

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
    gab_ids = obtener_ids_catalogo_por_tipo("GABINETE")

    pipeline = [
        {"$match": {"id_examen": id_examen}},
        {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
        {"$unwind": "$atencion"},
        {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$lookup": {"from": "camas", "localField": "atencion.id_cama", "foreignField": "id_cama", "as": "cama"}},
        {"$unwind": {"path": "$cama", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "examenes_det", "localField": "id_examen", "foreignField": "id_examen", "as": "det"}},
        {"$unwind": "$det"},
        {"$match": {"det.id_catalogo": {"$in": gab_ids}}},
        {"$lookup": {"from": "catalogo_examenes", "localField": "det.id_catalogo", "foreignField": "id_catalogo", "as": "cat"}},
        {"$unwind": "$cat"},
        {"$group": {
            "_id": "$id_examen",
            "paciente": {"$first": {"$concat": ["$paciente.papell", " ", "$paciente.sapell", " ", "$paciente.nom_pac"]}},
            "habitacion": {"$first": "$cama.numero"},
            "estudios": {"$push": "$cat.nombre"}
        }},
        {"$project": {
            "id_examen": "$_id",
            "paciente": 1,
            "habitacion": 1,
            "estudios": {
                "$reduce": {
                    "input": "$estudios",
                    "initialValue": "",
                    "in": {"$concat": ["$$value", {"$cond": [{"$eq": ["$$value", ""]}, "", ", "]}, "$$this"]}
                }
            }
        }}
    ]
    res = list(db['examenes'].aggregate(pipeline))
    solicitud = res[0] if res else None

    if request.method == 'POST':
        observaciones = request.form.get('observaciones', '')
        files = request.files.getlist('archivos')
        nombres_guardados = []

        for file in files:
            if file and allowed_file(file.filename):
                filename_secure = secure_filename(file.filename)
                ts = datetime.now().strftime('%Y%m%d%H%M%S%f')
                nombre_guardado = f"{id_examen}_{ts}_{filename_secure}"
                file.save(os.path.join(UPLOAD_FOLDER_GAB, nombre_guardado))
                nombres_guardados.append(nombre_guardado)

        archivos_db = ','.join(nombres_guardados) if nombres_guardados else ''

        db['examenes_det'].update_many(
            {"id_examen": id_examen, "id_catalogo": {"$in": gab_ids}},
            {"$set": {
                "archivo_resultado": archivos_db,
                "observaciones": observaciones,
                "fecha_realizado": datetime.now(),
                "estado": 'REALIZADO'
                
            }}
        )

        flash('Resultados de gabinete subidos correctamente', 'success')
        return redirect(url_for('estudios.estudios_home', vista='solicitudes_gabinete'))

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
    lab_ids = obtener_ids_catalogo_por_tipo("LABORATORIO")

    pipeline = [
        {"$match": {"id_examen": id_examen}},
        {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
        {"$unwind": "$atencion"},
        {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$lookup": {"from": "camas", "localField": "atencion.id_cama", "foreignField": "id_cama", "as": "cama"}},
        {"$unwind": {"path": "$cama", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "examenes_det", "localField": "id_examen", "foreignField": "id_examen", "as": "det"}},
        {"$unwind": "$det"},
        {"$match": {"det.id_catalogo": {"$in": lab_ids}}},
        {"$lookup": {"from": "catalogo_examenes", "localField": "det.id_catalogo", "foreignField": "id_catalogo", "as": "cat"}},
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
            "estudios": {
                "$reduce": {
                    "input": "$estudios",
                    "initialValue": "",
                    "in": {"$concat": ["$$value", {"$cond": [{"$eq": ["$$value", ""]}, "", ", "]}, "$$this"]}
                }
            }
        }}
    ]
    res = list(db['examenes'].aggregate(pipeline))
    solicitud = res[0] if res else None

    if request.method == 'POST':
        observaciones = request.form.get('observaciones', '')
        files = request.files.getlist('archivos')
        nombres_guardados = []

        for file in files:
            if file and allowed_file(file.filename):
                filename_secure = secure_filename(file.filename)
                ts = datetime.now().strftime('%Y%m%d%H%M%S%f')
                nombre_guardado = f"{id_examen}_{ts}_{filename_secure}"
                file.save(os.path.join(UPLOAD_FOLDER_LAB, nombre_guardado))
                nombres_guardados.append(nombre_guardado)

        archivos_db = ','.join(nombres_guardados) if nombres_guardados else ''

        db['examenes_det'].update_many(
            {"id_examen": id_examen, "id_catalogo": {"$in": lab_ids}},
            {"$set": {
                "archivo_resultado": archivos_db,
                "observaciones": observaciones,
                "fecha_realizado": datetime.now(),
                "estado": 'REALIZADO'
            }}
        )

        flash('Resultados de laboratorio subidos correctamente', 'success')
        return redirect(url_for('estudios.estudios_home', vista='solicitudes_laboratorio'))

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
    lab_ids = obtener_ids_catalogo_por_tipo("LABORATORIO")

    pipeline = [
        {"$match": {"id_examen": id_examen}},
        {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
        {"$unwind": "$atencion"},
        {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$lookup": {"from": "camas", "localField": "atencion.id_cama", "foreignField": "id_cama", "as": "cama"}},
        {"$unwind": {"path": "$cama", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "examenes_det", "localField": "id_examen", "foreignField": "id_examen", "as": "dets"}},
        {"$project": {
            "id_examen": 1,
            "paciente": {"$concat": ["$paciente.nom_pac", " ", "$paciente.papell", " ", "$paciente.sapell"]},
            "habitacion": "$cama.numero",
            "archivo_resultado": {
                "$reduce": {
                    "input": {
                        "$filter": {
                            "input": "$dets",
                            "as": "d",
                            "cond": {"$in": ["$$d.id_catalogo", lab_ids]}
                        }
                    },
                    "initialValue": "",
                    "in": {
                        "$concat": [
                            "$$value",
                            {"$cond": [{"$eq": ["$$value", ""]}, "", ","]},
                            {"$ifNull": ["$$this.archivo_resultado", ""]}
                        ]
                    }
                }
            },
            "observaciones": {
                "$arrayElemAt": [
                    {
                        "$filter": {
                            "input": {
                                "$map": {
                                    "input": {
                                        "$filter": {
                                            "input": "$dets",
                                            "as": "d",
                                            "cond": {"$in": ["$$d.id_catalogo", lab_ids]}
                                        }
                                    },
                                    "as": "d",
                                    "in": {"$ifNull": ["$$d.observaciones", ""]}
                                }
                            },
                            "as": "obs",
                            "cond": {"$ne": ["$$obs", ""]}
                        }
                    },
                    0
                ]
            }
        }}
    ]
    rows = list(db['examenes'].aggregate(pipeline))
    solicitud = rows[0] if rows else None

    if not solicitud:
        flash('Solicitud no encontrada', 'danger')
        return redirect(url_for('estudios.estudios_home', vista='resultados_laboratorio'))

    paciente = solicitud.get('paciente')
    habitacion = solicitud.get('habitacion')
    archivo_resultado = solicitud.get('archivo_resultado') or ''
    observaciones = solicitud.get('observaciones') or ''

    # Eliminar duplicados y vacíos, manteniendo orden (usando dict.fromkeys)
    archivos_raw = [a.strip() for a in archivo_resultado.split(',') if a.strip()]
    archivos = list(dict.fromkeys(archivos_raw))  # elimina duplicados preservando orden

    if request.method == 'POST':
        eliminar = request.form.getlist('eliminar_archivos')
        nuevos = request.files.getlist('archivos')
        nuevas_observaciones = request.form.get('observaciones', '').strip()

        # Eliminar archivos marcados
        if eliminar:
            for nombre in eliminar:
                # Eliminar de la lista archivos
                if nombre in archivos:
                    archivos.remove(nombre)
                # Eliminar físico
                ruta = os.path.join(UPLOAD_FOLDER_LAB, nombre)
                if os.path.exists(ruta):
                    try:
                        os.remove(ruta)
                    except:
                        pass

        # Subir nuevos archivos
        nuevos_guardados = []
        if nuevos:
            for file in nuevos:
                if file and allowed_file(file.filename):
                    file.stream.seek(0, os.SEEK_END)
                    size = file.stream.tell()
                    file.stream.seek(0)
                    if size > MAX_FILE_SIZE:
                        flash(f'Archivo {file.filename} demasiado grande (máx 25MB).', 'danger')
                        return redirect(request.url)

                    filename_secure = secure_filename(file.filename)
                    ts = datetime.now().strftime('%Y%m%d%H%M%S%f')
                    nombre_guardado = f"{id_examen}_{ts}_{filename_secure}"
                    file.save(os.path.join(UPLOAD_FOLDER_LAB, nombre_guardado))
                    nuevos_guardados.append(nombre_guardado)
                elif file.filename:
                    flash(f'Formato no permitido para {file.filename}', 'danger')
                    return redirect(request.url)

        # Combinar archivos existentes (ya sin duplicados) con nuevos
        archivos_finales = archivos + nuevos_guardados
        # Eliminar posibles duplicados (por si acaso) y mantener orden
        archivos_finales = list(dict.fromkeys(archivos_finales))

        archivos_db = ','.join(archivos_finales)

        db['examenes_det'].update_many(
            {"id_examen": id_examen, "id_catalogo": {"$in": lab_ids}},
            {"$set": {
                "archivo_resultado": archivos_db,
                "fecha_realizado": datetime.now(),
                "estado": 'REALIZADO',
                "observaciones": nuevas_observaciones
            }}
        )

        flash('Cambios guardados correctamente', 'success')
        return redirect(url_for('estudios.estudios_home', vista='resultados_laboratorio'))

    lab_pendientes, gab_pendientes, total_pendientes = contar_solicitudes_pendientes()
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
        archivos=archivos,  # lista sin duplicados
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
    gab_ids = obtener_ids_catalogo_por_tipo("GABINETE")

    pipeline = [
        {"$match": {"id_examen": id_examen}},
        {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
        {"$unwind": "$atencion"},
        {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$lookup": {"from": "camas", "localField": "atencion.id_cama", "foreignField": "id_cama", "as": "cama"}},
        {"$unwind": {"path": "$cama", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "examenes_det", "localField": "id_examen", "foreignField": "id_examen", "as": "dets"}},
        {"$project": {
            "id_examen": 1,
            "paciente": {"$concat": ["$paciente.nom_pac", " ", "$paciente.papell", " ", "$paciente.sapell"]},
            "habitacion": "$cama.numero",
            "archivo_resultado": {
                "$reduce": {
                    "input": {
                        "$filter": {
                            "input": "$dets",
                            "as": "d",
                            "cond": {"$in": ["$$d.id_catalogo", gab_ids]}
                        }
                    },
                    "initialValue": "",
                    "in": {
                        "$concat": [
                            "$$value",
                            {"$cond": [{"$eq": ["$$value", ""]}, "", ","]},
                            {"$ifNull": ["$$this.archivo_resultado", ""]}
                        ]
                    }
                }
            },
            "observaciones": {
                "$arrayElemAt": [
                    {
                        "$filter": {
                            "input": {
                                "$map": {
                                    "input": {
                                        "$filter": {
                                            "input": "$dets",
                                            "as": "d",
                                            "cond": {"$in": ["$$d.id_catalogo", gab_ids]}
                                        }
                                    },
                                    "as": "d",
                                    "in": {"$ifNull": ["$$d.observaciones", ""]}
                                }
                            },
                            "as": "obs",
                            "cond": {"$ne": ["$$obs", ""]}
                        }
                    },
                    0
                ]
            }
        }}
    ]
    rows = list(db['examenes'].aggregate(pipeline))
    solicitud = rows[0] if rows else None

    if not solicitud:
        flash('Solicitud no encontrada', 'danger')
        return redirect(url_for('estudios.estudios_home', vista='resultados_gabinete'))

    paciente = solicitud.get('paciente')
    habitacion = solicitud.get('habitacion')
    archivo_resultado = solicitud.get('archivo_resultado') or ''
    observaciones = solicitud.get('observaciones') or ''

    # Eliminar duplicados manteniendo orden
    archivos = [a.strip() for a in archivo_resultado.split(',') if a.strip()]
    archivos = list(dict.fromkeys(archivos))  # 👈 Elimina duplicados

    if request.method == 'POST':
        eliminar = request.form.getlist('eliminar_archivos')
        nuevos = request.files.getlist('archivos')
        nuevas_observaciones = request.form.get('observaciones', '').strip()

        if eliminar:
            for nombre in eliminar:
                if nombre in archivos:
                    archivos.remove(nombre)
                ruta = os.path.join(UPLOAD_FOLDER_GAB, nombre)
                if os.path.exists(ruta):
                    try:
                        os.remove(ruta)
                    except:
                        pass

        nuevos_guardados = []
        if nuevos:
            for file in nuevos:
                if file and allowed_file(file.filename):
                    file.stream.seek(0, os.SEEK_END)
                    size = file.stream.tell()
                    file.stream.seek(0)
                    if size > MAX_FILE_SIZE:
                        flash(f'Archivo {file.filename} demasiado grande (máx 25MB).', 'danger')
                        return redirect(request.url)

                    filename_secure = secure_filename(file.filename)
                    ts = datetime.now().strftime('%Y%m%d%H%M%S%f')
                    nombre_guardado = f"{id_examen}_{ts}_{filename_secure}"
                    file.save(os.path.join(UPLOAD_FOLDER_GAB, nombre_guardado))
                    nuevos_guardados.append(nombre_guardado)
                elif file.filename:
                    flash(f'Formato no permitido para {file.filename}', 'danger')
                    return redirect(request.url)

        archivos_finales = archivos + nuevos_guardados
        # Eliminar duplicados nuevamente antes de guardar
        archivos_finales = list(dict.fromkeys(archivos_finales))
        archivos_db = ','.join(archivos_finales)

        db['examenes_det'].update_many(
            {"id_examen": id_examen, "id_catalogo": {"$in": gab_ids}},
            {"$set": {
                "archivo_resultado": archivos_db,
                "fecha_realizado": datetime.now(),
                "estado": 'REALIZADO',
                "observaciones": nuevas_observaciones
            }}
        )

        flash('Cambios guardados correctamente', 'success')
        return redirect(url_for('estudios.estudios_home', vista='resultados_gabinete'))

    lab_pendientes, gab_pendientes, total_pendientes = contar_solicitudes_pendientes()
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
    lab_ids = obtener_ids_catalogo_por_tipo("LABORATORIO")

    # Obtener paciente
    pipeline = [
        {"$match": {"id_examen": id_examen}},
        {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
        {"$unwind": "$atencion"},
        {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$project": {
            "paciente": {"$concat": ["$paciente.nom_pac", " ", "$paciente.papell", " ", "$paciente.sapell"]}
        }}
    ]
    rows = list(db['examenes'].aggregate(pipeline))
    row = rows[0] if rows else None

    if not row:
        flash('Resultados no encontrados', 'danger')
        return redirect(url_for('estudios.estudios_home', vista='resultados_laboratorio'))

    # Obtener archivos de detalles LABORATORIO realizados
    dets = db['examenes_det'].find({
        "id_examen": id_examen,
        "id_catalogo": {"$in": lab_ids},
        "estado": {"$regex": "^REALIZADO$", "$options": "i"}
    }, {"archivo_resultado": 1})

    archivos_dict = {}
    for d in dets:
        ar = d.get('archivo_resultado')
        if ar:
            for nombre in ar.split(','):
                nombre = nombre.strip()
                if nombre and nombre not in archivos_dict:
                    archivos_dict[nombre] = {
                        'nombre': nombre,
                        'url': url_for('static', filename=f'resultados/laboratorio/{nombre}'),
                        'tipo': nombre.split('.')[-1].lower()
                    }
    archivos = list(archivos_dict.values())

    rol = obtener_rol_usuario()
    lab_pendientes, gab_pendientes, total_pendientes = contar_solicitudes_pendientes()
    return render_template(
        'estudios/index.html',
        vista='ver_resultado_laboratorio',
        paciente=row['paciente'],
        archivos=archivos,
        rol=rol,
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
    gab_ids = obtener_ids_catalogo_por_tipo("GABINETE")

    dets = db['examenes_det'].find({
        "id_examen": id_examen,
        "id_catalogo": {"$in": gab_ids},
        "estado": {"$regex": "^REALIZADO$", "$options": "i"}
    }, {"archivo_resultado": 1})

    archivos_dict = {}
    for d in dets:
        ar = d.get('archivo_resultado')
        if ar:
            for nombre in ar.split(','):
                nombre = nombre.strip()
                if nombre and nombre not in archivos_dict:
                    archivos_dict[nombre] = {
                        'nombre': nombre,
                        'url': url_for('static', filename=f'resultados/gabinete/{nombre}'),
                        'tipo': nombre.split('.')[-1].lower()
                    }
    archivos = list(archivos_dict.values())

    rol = obtener_rol_usuario()
    lab_pendientes, gab_pendientes, total_pendientes = contar_solicitudes_pendientes()
    return render_template(
        'estudios/index.html',
        vista='ver_resultado_gabinete',
        archivos=archivos,
        rol=rol,
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
    gab_ids = obtener_ids_catalogo_por_tipo("GABINETE")

    rows = list(db['examenes_det'].find(
        {"id_examen": id_examen, "id_catalogo": {"$in": gab_ids}},
        {"archivo_resultado": 1}
    ))

    for row in rows:
        archivo = row.get('archivo_resultado')
        if archivo:
            for nombre in archivo.split(','):
                nombre = nombre.strip()
                if nombre:
                    ruta = os.path.join(UPLOAD_FOLDER_GAB, nombre)
                    if os.path.exists(ruta):
                        try:
                            os.remove(ruta)
                        except:
                            pass

    db['examenes_det'].delete_many({"id_examen": id_examen, "id_catalogo": {"$in": gab_ids}})

    restantes = db['examenes_det'].count_documents({"id_examen": id_examen})
    if restantes == 0:
        db['examenes'].delete_one({"id_examen": id_examen})

    flash('Solicitud de gabinete eliminada correctamente', 'success')
    return redirect(url_for('estudios.estudios_home', vista='resultados_gabinete'))

# =========================
# ELIMINAR RESULTADO LABORATORIO
# =========================
@estudios_bp.route('/eliminar_resultado_laboratorio/<int:id_examen>')
def eliminar_resultado_laboratorio(id_examen):
    db = get_db_connection()
    lab_ids = obtener_ids_catalogo_por_tipo("LABORATORIO")

    rows = list(db['examenes_det'].find(
        {"id_examen": id_examen, "id_catalogo": {"$in": lab_ids}},
        {"archivo_resultado": 1}
    ))

    for row in rows:
        archivo = row.get('archivo_resultado')
        if archivo:
            for nombre in archivo.split(','):
                nombre = nombre.strip()
                if nombre:
                    ruta = os.path.join(UPLOAD_FOLDER_LAB, nombre)
                    if os.path.exists(ruta):
                        try:
                            os.remove(ruta)
                        except:
                            pass

    db['examenes_det'].delete_many({"id_examen": id_examen, "id_catalogo": {"$in": lab_ids}})

    restantes = db['examenes_det'].count_documents({"id_examen": id_examen})
    if restantes == 0:
        db['examenes'].delete_one({"id_examen": id_examen})

    flash('Solicitud de laboratorio eliminada correctamente', 'success')
    return redirect(url_for('estudios.estudios_home', vista='resultados_laboratorio'))


# =========================
# NOTIFICACIONES EN DASHBOARD
# =========================
from flask import jsonify

@estudios_bp.route('/api/pendientes', methods=['GET'])
def api_pendientes():
    lab_pendientes, gab_pendientes, total_pendientes = contar_solicitudes_pendientes()
    return jsonify({
        'lab_pendientes': lab_pendientes,
        'gab_pendientes': gab_pendientes,
        'total_pendientes': total_pendientes
    })