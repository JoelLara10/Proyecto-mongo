import os
import zipfile
from datetime import datetime, date, timedelta
from decimal import Decimal
from bd import get_db_connection
from bson.objectid import ObjectId  # Solo una vez
from bson.decimal128 import Decimal128
from pymongo.errors import PyMongoError
import psutil
import time
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify, current_app, send_from_directory
)
from apscheduler.schedulers.background import BackgroundScheduler
import bcrypt
from fpdf import FPDF

# Blueprints
from estudios import estudios_bp
from templates.administrativo.pacientes.doc_pacientes import pdf
from templates.medico.impresiones import pdf_med

# Importar funciones de backups
from configuracion.automatizacion import automatizacion_tareas
from utils.backups import (
    realizar_backup,
    restaurar_backup,
    list_backups,
    obtener_colecciones_mongo,
    validar_admin,
    limpiar_backups,
    check_db_health,
    job_backup_auto,
    cargar_config_auto,
    guardar_config_auto
)
<<<<<<< HEAD

=======
from bson.objectid import ObjectId
from bson.decimal128 import Decimal128
from pymongo.errors import PyMongoError
from estudios import contar_solicitudes_pendientes 
>>>>>>> 64fa81f (MODULO ESTUDIOS COMPLETO)
# ===============================
# Inicializar Flask
# ===============================
app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'  # ⚠️ usa una clave segura en producción

# ===============================
# Registrar Blueprints
# ===============================
app.register_blueprint(estudios_bp, url_prefix='/estudios')
app.register_blueprint(pdf)
app.register_blueprint(pdf_med)

# ===============================
# Inicializar Scheduler
# ===============================
scheduler = BackgroundScheduler()

# Guardar scheduler en la app (MUY IMPORTANTE)
app.config['SCHEDULER'] = scheduler

# ===============================
# Programar backup automático (solo una vez)
# ===============================
with app.app_context():
    config = cargar_config_auto()
    if config.get('activo', False):
        scheduler.add_job(
            job_backup_auto,
            'interval',
            minutes=config['intervalo'],
            args=[app],
            id='backup_automatico',
            replace_existing=True
        )

# Iniciar scheduler (UNA SOLA VEZ)
scheduler.start()

def get_next_sequence(name):
    db = get_db_connection()
    counters = db['counters']
    result = counters.find_one_and_update(
        {"_id": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    return result['seq']

def registrar_log_global(accion):
    if 'username' not in session:
        return
    try:
        db = get_db_connection()
        logs = db['logs']
        logs.insert_one({
            "usuario": session['username'],
            "accion": accion,
            "fecha": datetime.now()
        })
    except Exception as e:
        print("Error al registrar log:", e)

def calcular_edad(fecha_nacimiento):
    hoy = date.today()
    return hoy.year - fecha_nacimiento.year - (
        (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day)
    )

# Filtro personalizado para strftime
@app.template_filter('strftime')
def _jinja2_filter_datetime(date, fmt='%d/%m/%Y'):
    if isinstance(date, str):
        # Asume formato de entrada si es string (ajusta según tu DB)
        date = datetime.strptime(date, '%Y-%m-%d') if len(date) == 10 else datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
    return date.strftime(fmt)

# ====================================================================================
# ============================ INICIO ====================================
# ====================================================================================
# ===============================
# REGISTRO GLOBAL DE ACCIONES
# ===============================
@app.after_request
def registrar_acciones(response):
    if 'username' not in session:
        return response
    rutas_ignoradas = [
        '/static',
        '/favicon.ico',
        '/dashboard',
        '/configuracion',
        '/logs/ultimo'
    ]
    if any(request.path.startswith(r) for r in rutas_ignoradas):
        return response
    accion = f"{request.method} {request.path}"
    registrar_log_global(accion)
    return response

# ===============================
# OBTENER ÚLTIMO LOG
# ===============================
@app.route('/logs/ultimo')
def ultimo_log():
    if 'username' not in session:
        return {"nuevo": False}
    db = get_db_connection()
    logs = db['logs']
    log = logs.find_one(sort=[("fecha", -1)])
    if not log:
        return {"nuevo": False}
    return {
        "usuario": log['usuario'],
        "accion": log['accion'],
        "fecha": log['fecha'].strftime('%Y-%m-%d %H:%M:%S')
    }

# ===============================
# INDEX
# ===============================
@app.route('/')
def index():
    return redirect(url_for('login'))

# ===============================
# COPIAS DE SEGURIDAD
# ===============================
@app.route('/configuracion/copias', methods=['GET', 'POST'])
def copias_seguridad():
    """Vista para copias de seguridad - IMPLEMENTACIÓN DIRECTA"""
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard'))

    # Importar aquí para evitar circular imports
    from utils.backups import obtener_colecciones_mongo, list_backups, validar_admin, realizar_backup, restaurar_backup, \
        limpiar_backups

    colecciones = obtener_colecciones_mongo()
    backups = list_backups()

    # Usar sesión en lugar de request.args para evitar descargas múltiples
    download_filename = session.pop('download_backup', None)

    if request.method == 'POST':
        action = request.form.get('action')

        # ===== SOLO BACKUP requiere autenticación =====
        if action == 'backup':
            auth_user = request.form.get('auth_user')
            auth_pass = request.form.get('auth_pass')

            if not auth_user or not auth_pass:
                flash('Debes confirmar usuario y contraseña de administrador.', 'danger')
                return redirect(request.url)
            if not validar_admin(auth_user, auth_pass):
                flash('Credenciales inválidas.', 'danger')
                return redirect(request.url)

            tipo = request.form.get('tipo', 'completa')
            formato = request.form.get('formato', 'json')
            colecciones_sel = request.form.getlist('colecciones')

            if tipo == 'completa' and not colecciones_sel:
                colecciones_sel = colecciones

            if not colecciones_sel:
                flash('Selecciona al menos una colección.', 'warning')
                return redirect(request.url)

            try:
                nombre = realizar_backup(tipo, formato, colecciones_sel, False)
                if nombre:
                    flash(f'Backup {tipo} creado', 'success')
                    limpiar_backups(4)
                    # Guardar en sesión para descarga
                    session['download_backup'] = nombre
                    return redirect(url_for('copias_seguridad'))
                else:
                    flash('No se pudo crear el backup (sin cambios para modo diferencial/incremental)', 'warning')
            except Exception as e:
                flash(f'Error en backup: {str(e)}', 'danger')

        # ===== RESTORE NO requiere autenticación =====
        elif action == 'restore':
            archivo = request.form.get('selected_backup')
            if not archivo:
                flash('Selecciona un archivo para restaurar', 'warning')
                return redirect(request.url)

            try:
                restaurar_backup(archivo)
                flash(f'Restauración desde {archivo} completada exitosamente', 'success')
            except Exception as e:
                flash(f'Error en restauración: {str(e)}', 'danger')

        return redirect(request.url)

    return render_template(
        'configuracion/copias/copias_seguridad.html',
        colecciones=colecciones,
        backups=backups,
        download_filename=download_filename
    )

@app.route('/configuracion/copias/download/<filename>')
def download_backup(filename):
    carpeta = os.path.join(current_app.root_path, 'configuracion', 'copias')
    return send_from_directory(carpeta, filename, as_attachment=True)

# ===============================
# AUTOMATIZACIÓN
# ===============================
@app.route('/configuracion/automatizacion', methods=['GET', 'POST'])
def automatizacion_tareas_route():
    return automatizacion_tareas()

# ===============================
# LOGIN
# ===============================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')

        db = get_db_connection()
        users_coll = db['users']

        user = users_coll.find_one({"username": username})

        if user and bcrypt.checkpw(password, user['password']):
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Login exitoso!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos.', 'danger')

    return render_template('login.html')
# ===============================
# DASHBOARD
# ===============================
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    role = session['role']
    lab_pendientes, gab_pendientes, total_pendientes = contar_solicitudes_pendientes()
    menu_options = []
    # ===============================
    # CONTAR SOLICITUDES PENDIENTES
    # ===============================
    db = get_db_connection()
    examenes_laboratorio = db['examenes_laboratorio']
    lab_pendientes = examenes_laboratorio.count_documents({"estado": {"$regex": "^pendiente$", "$options": "i"}})
    examenes_gabinete_det = db['examenes_gabinete_det']
    gab_pendientes = examenes_gabinete_det.count_documents({"estado": "PENDIENTE"})
    total_pendientes = lab_pendientes + gab_pendientes
    # ===============================
    # MENÚ SEGÚN ROL
    # ===============================
    if role == 'admin':
        menu_options = [
            {'name': 'Administrativo', 'url': url_for('administrativo')},
            {'name': 'Médico', 'url': url_for('medico')},
            {'name': 'Estudios', 'url': url_for('estudios.estudios_home')},
            {'name': 'Configuración', 'url': url_for('menu_configuracion')},
            {'name': 'Rendimiento', 'url': url_for('rendimiento')}
        ]
    elif role == 'medico':
        menu_options = [
            {'name': 'Módulo Médico', 'url': url_for('medico')},
            {'name': 'Resultados de Estudios', 'url': url_for('estudios.estudios_home')}
        ]
    elif role == 'administrativo':
        menu_options = [
            {'name': 'Administrativo', 'url': url_for('administrativo')}
        ]
    elif role == 'enfermero':
        menu_options = [
            {'name': 'Signos Vitales', 'url': url_for('dashboard')} # cambia si tienes ruta propia
        ]
    elif role == 'estudios':
        menu_options = [
        {'name': 'Módulo Estudios', 'url': url_for('estudios.estudios_home')}
    ]
    # ===============================
    # RENDER
    # ===============================
    return render_template(
        'dashboard.html',
        role=role,
        menu_options=menu_options,
        lab_pendientes=lab_pendientes,
        gab_pendientes=gab_pendientes,
        total_pendientes=total_pendientes
    )

# ====================================================================================
# ======================== ADMINISTRATIVO ================================
# ====================================================================================
@app.route('/admin/administrativo')
def administrativo():
    if 'user_id' not in session:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    usuario = {
        'username': session['username'],
        'img_perfil': 'default_profile.jpg' # Placeholder
    }
    img_sistema = 'logo.jpg' # Placeholder
    return render_template('administrativo/administrativo.html', usuario=usuario, img_sistema=img_sistema)

@app.route('/admin/gestion_pacientes')
def gestion_pacientes():
    if 'user_id' not in session:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    db = get_db_connection()
    atencion_coll = db['atencion']
    # Hospitalized
    pipeline_hosp = [
        {"$match": {"area": "Hospitalizado", "status": "ABIERTA"}},
        {"$lookup": {"from": "pacientes", "localField": "Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$lookup": {"from": "camas", "localField": "id_cama", "foreignField": "id_cama", "as": "cama"}},
        {"$unwind": {"path": "$cama", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "Id_exp": "$paciente.Id_exp",
            "papell": "$paciente.papell",
            "sapell": "$paciente.sapell",
            "nom_pac": "$paciente.nom_pac",
            "fecnac": "$paciente.fecnac",
            "tel": "$paciente.tel",
            "id_atencion": 1,
            "area": 1,
            "fecha_ing": 1,
            "num_cama": "$cama.numero"
        }}
    ]
    hospitalized = list(atencion_coll.aggregate(pipeline_hosp))
    for p in hospitalized:
        p['edad'] = calcular_edad(p['fecnac']) if 'fecnac' in p else 0
    # Urgencias
    pipeline_urg = [
        {"$match": {"area": "Urgencias", "status": "ABIERTA"}},
        {"$lookup": {"from": "pacientes", "localField": "Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$lookup": {"from": "camas", "localField": "id_cama", "foreignField": "id_cama", "as": "cama"}},
        {"$unwind": {"path": "$cama", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "Id_exp": "$paciente.Id_exp",
            "papell": "$paciente.papell",
            "sapell": "$paciente.sapell",
            "nom_pac": "$paciente.nom_pac",
            "fecnac": "$paciente.fecnac",
            "tel": "$paciente.tel",
            "id_atencion": 1,
            "area": 1,
            "fecha_ing": 1,
            "num_cama": "$cama.numero"
        }}
    ]
    urgencias = list(atencion_coll.aggregate(pipeline_urg))
    for p in urgencias:
        p['edad'] = calcular_edad(p['fecnac']) if 'fecnac' in p else 0
    # Ambulatorios
    pipeline_amb = [
        {"$match": {"area": "Ambulatorio", "status": "ABIERTA"}},
        {"$lookup": {"from": "pacientes", "localField": "Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$lookup": {"from": "camas", "localField": "id_cama", "foreignField": "id_cama", "as": "cama"}},
        {"$unwind": {"path": "$cama", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "Id_exp": "$paciente.Id_exp",
            "papell": "$paciente.papell",
            "sapell": "$paciente.sapell",
            "nom_pac": "$paciente.nom_pac",
            "fecnac": "$paciente.fecnac",
            "tel": "$paciente.tel",
            "id_atencion": 1,
            "area": 1,
            "fecha_ing": 1,
            "num_cama": "$cama.numero"
        }}
    ]
    ambulatorios = list(atencion_coll.aggregate(pipeline_amb))
    for p in ambulatorios:
        p['edad'] = calcular_edad(p['fecnac']) if 'fecnac' in p else 0
    return render_template('administrativo/pacientes/gestion_pacientes.html',
                           hospitalized=hospitalized,
                           urgencias=urgencias,
                           ambulatorios=ambulatorios,
                           role=session['role'],
                           usuario={'id_usua': session['user_id'], 'id_rol': session['role']})

@app.route('/admin/nuevo_paciente', methods=['GET', 'POST'])
def nuevo_paciente():
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    db = get_db_connection()
    camas_coll = db['camas']
    users_coll = db['users']
    camas = list(camas_coll.find({"ocupada": 0}, {"id_cama": 1, "numero": 1}))
    medicos = list(users_coll.find({"role": "medico"}, {"_id": 1, "username": 1}))
    if request.method == 'POST':
        try:
            # ---------- PACIENTE ----------
            curp = request.form['curp']
            papell = request.form['papell']
            sapell = request.form['sapell']
            nom_pac = request.form['nom_pac']
            fecnac = datetime.strptime(request.form['fecnac'], '%Y-%m-%d')
            tel = request.form['tel']
            alergias = request.form.get('alergias', '')
            # ---------- ATENCIÓN ----------
            area = request.form['area']
            id_cama = int(request.form.get('id_cama')) if request.form.get('id_cama') else None
            motivo = request.form['motivo']
            especialidad = request.form['especialidad']
            # ---------- FAMILIAR ----------
            fam_nombre = request.form['fam_nombre']
            fam_parentesco = request.form['fam_parentesco']
            fam_tel = request.form['fam_tel']
            # ---------- MÉDICOS ----------
            medicos_list = [
                request.form.get('medico1'),
                request.form.get('medico2'),
                request.form.get('medico3'),
                request.form.get('medico4'),
                request.form.get('medico5')
            ]
            medicos_list = [int(m) for m in medicos_list if m] # Filtrar no vacíos, assume id int
            # ===== INSERT PACIENTE =====
            pacientes_coll = db['pacientes']
            id_exp = get_next_sequence('pacientes_Id_exp')
            pacientes_coll.insert_one({
                "Id_exp": id_exp,
                "curp": curp,
                "papell": papell,
                "sapell": sapell,
                "nom_pac": nom_pac,
                "fecnac": fecnac,
                "tel": tel
            })
            # ===== INSERT ATENCION =====
            atencion_coll = db['atencion']
            id_atencion = get_next_sequence('atencion_id_atencion')
            atencion_coll.insert_one({
                "id_atencion": id_atencion,
                "Id_exp": id_exp,
                "area": area,
                "id_cama": id_cama,
                "motivo": motivo,
                "especialidad": especialidad,
                "alergias": alergias,
                "fecha_ing": datetime.now(),
                "status": "ABIERTA"
            })
            # ===== INSERT MÉDICOS =====
            atencion_medicos_coll = db['atencion_medicos']
            for id_medico in medicos_list:
                atencion_medicos_coll.insert_one({
                    "id_atencion": id_atencion,
                    "id_medico": id_medico
                })
            # ===== MARCAR CAMA OCUPADA =====
            if id_cama:
                camas_coll.update_one({"id_cama": id_cama}, {"$set": {"ocupada": 1}})
            # ===== INSERT FAMILIAR =====
            familiares_coll = db['familiares']
            familiares_coll.insert_one({
                "Id_exp": id_exp,
                "nombre": fam_nombre,
                "parentesco": fam_parentesco,
                "telefono": fam_tel
            })
            flash('Paciente registrado correctamente.', 'success')
            return redirect(url_for('gestion_pacientes'))
        except Exception as e:
            flash(f'Error al registrar paciente: {e}', 'error')
    return render_template('administrativo/pacientes/nuevo_paciente.html', camas=camas, medicos=medicos)

@app.route('/admin/editar_paciente/<int:id_exp>', methods=['GET', 'POST'])
def editar_paciente(id_exp):
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    db = get_db_connection()
    camas_coll = db['camas']
    users_coll = db['users']
    pacientes_coll = db['pacientes']
    atencion_coll = db['atencion']
    atencion_medicos_coll = db['atencion_medicos']
    familiares_coll = db['familiares']
    # ===== DATOS PARA SELECTS =====
    camas = list(camas_coll.find({"$or": [{"ocupada": 0}, {"id_cama": {"$in": list(atencion_coll.find({"Id_exp": id_exp}, {"id_cama": 1}))}} ]}, {"id_cama": 1, "numero": 1}))
    medicos = list(users_coll.find({"role": "medico"}, {"_id": 1, "username": 1}))
    # ===== GET =====
    pipeline = [
        {"$match": {"Id_exp": id_exp}},
        {"$lookup": {"from": "atencion", "localField": "Id_exp", "foreignField": "Id_exp", "as": "atencion"}},
        {"$unwind": "$atencion"},
        {"$project": {
            "_id": 0,
            "curp": 1,
            "papell": 1,
            "sapell": 1,
            "nom_pac": 1,
            "fecnac": 1,
            "tel": 1,
            "area": "$atencion.area",
            "id_cama": "$atencion.id_cama",
            "motivo": "$atencion.motivo",
            "especialidad": "$atencion.especialidad",
            "alergias": "$atencion.alergias"
        }}
    ]
    paciente = list(pacientes_coll.aggregate(pipeline))[0] if list(pacientes_coll.aggregate(pipeline)) else None
    medicos_asignados = [m['id_medico'] for m in atencion_medicos_coll.find({"id_atencion": paciente['atencion']['id_atencion']})]
    familiar = familiares_coll.find_one({"Id_exp": id_exp})
    if request.method == 'POST':
        try:
            # ===== PACIENTE =====
            pacientes_coll.update_one({"Id_exp": id_exp}, {"$set": {
                "curp": request.form['curp'],
                "papell": request.form['papell'],
                "sapell": request.form['sapell'],
                "nom_pac": request.form['nom_pac'],
                "fecnac": datetime.strptime(request.form['fecnac'], '%Y-%m-%d'),
                "tel": request.form['tel']
            }})
            # ===== ATENCION =====
            atencion_coll.update_one({"Id_exp": id_exp}, {"$set": {
                "area": request.form['area'],
                "id_cama": int(request.form.get('id_cama')) if request.form.get('id_cama') else None,
                "motivo": request.form['motivo'],
                "especialidad": request.form['especialidad'],
                "alergias": request.form.get('alergias', '')
            }})
            # ===== MÉDICOS =====
            atencion_medicos_coll.delete_many({"id_atencion": paciente['atencion']['id_atencion']})
            for m in ['medico1','medico2','medico3','medico4','medico5']:
                if request.form.get(m):
                    atencion_medicos_coll.insert_one({
                        "id_atencion": paciente['atencion']['id_atencion'],
                        "id_medico": int(request.form[m])
                    })
            # ===== FAMILIAR =====
            familiares_coll.update_one({"Id_exp": id_exp}, {"$set": {
                "nombre": request.form['fam_nombre'],
                "parentesco": request.form['fam_parentesco'],
                "telefono": request.form['fam_tel']
            }})
            flash('Paciente actualizado correctamente.', 'success')
            return redirect(url_for('gestion_pacientes'))
        except Exception as e:
            flash(f'Error al actualizar: {e}', 'error')
    return render_template(
        'administrativo/pacientes/editar_paciente.html',
        paciente=paciente,
        camas=camas,
        medicos=medicos,
        medicos_asignados=medicos_asignados,
        familiar=familiar
    )

@app.route('/admin/documentos_pacientes')
def documentos_pacientes():
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    db = get_db_connection()
    pipeline = [
        {"$lookup": {"from": "atencion", "localField": "Id_exp", "foreignField": "Id_exp", "as": "atencion"}},
        {"$unwind": "$atencion"},
        {"$project": {
            "Id_exp": 1,
            "papell": 1,
            "sapell": 1,
            "nom_pac": 1,
            "id_atencion": "$atencion.id_atencion",
            "fecha_ing": "$atencion.fecha_ing"
        }},
        {"$sort": {"atencion.fecha_ing": -1}}
    ]
    pacientes = list(db['pacientes'].aggregate(pipeline))
    return render_template(
        'administrativo/pacientes/doc_pacientes/documentos_pacientes.html',
        pacientes=pacientes
    )

@app.route('/buscar-paciente')
def buscar_paciente():
    q = request.args.get('q', '')
    db = get_db_connection()
    pacientes = db['pacientes']
    regex = {"$regex": f".*{q}.*", "$options": "i"}
    query = {"$or": [{"curp": regex}, {"nom_pac": regex}, {"papell": regex}]}
    results = list(pacientes.find(query, {"Id_exp": 1, "curp": 1, "papell": 1, "sapell": 1, "nom_pac": 1, "fecnac": 1, "tel": 1}).limit(5))
    for p in results:
        if p.get("fecnac"):
            p["fecnac"] = p["fecnac"].strftime('%Y-%m-%d')
        p['_id'] = str(p['_id']) # if needed
    return jsonify(results)

@app.route('/expedientes')
def ver_expedientes():
    db = get_db_connection()
    pipeline = [
        {"$lookup": {"from": "pacientes", "localField": "id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
        {"$unwind": "$atencion"},
        {"$lookup": {"from": "users", "localField": "usuario_alta", "foreignField": "id", "as": "user"}},
        {"$unwind": {"path": "$user", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "id_expediente": 1,
            "Id_exp": "$paciente.Id_exp",
            "paciente": {"$concat": ["$paciente.papell", " ", "$paciente.sapell", " ", "$paciente.nom_pac"]},
            "area": "$atencion.area",
            "fecha_ing": "$atencion.fecha_ing",
            "fecha_alta": 1,
            "usuario_alta": "$user.username",
            "id_atencion": "$atencion.id_atencion"
        }},
        {"$sort": {"fecha_alta": -1}}
    ]
    expedientes = list(db['expedientes'].aggregate(pipeline))
    return render_template(
        'administrativo/pacientes/exped/expedientes.html',
        expedientes=expedientes
    )

@app.route('/expediente/<int:id_atencion>/<int:id_exp>', methods=['GET', 'POST'])
def expediente(id_atencion, id_exp):
    db = get_db_connection()
    atencion_coll = db['atencion']
    pac = atencion_coll.find_one({"id_atencion": id_atencion}, {
        "Id_exp": 1, "papell": 1, "sapell": 1, "nom_pac": 1, "area": 1, "fecha_ing": 1, "status": 1
    })
    cuenta_coll = db['cuenta_paciente']
    cuenta = list(cuenta_coll.find({"id_atencion": id_atencion}, {"fecha": 1, "descripcion": 1, "cantidad": 1, "precio": 1, "subtotal": 1}))
    total_pipeline = [
        {"$match": {"id_atencion": id_atencion}},
        {"$group": {"_id": None, "total": {"$sum": "$subtotal"}}}
    ]
    total_result = list(cuenta_coll.aggregate(total_pipeline))
    total = total_result[0]['total'] if total_result else 0
    # ===== CERRAR CUENTA =====
    if request.method == 'POST' and pac['status'] == 'ABIERTA':
        atencion_coll.update_one({"id_atencion": id_atencion}, {"$set": {"status": "CERRADA"}})
        expedientes_coll = db['expedientes']
        expedientes_coll.insert_one({
            "id_exp": id_exp,
            "id_atencion": id_atencion,
            "fecha_alta": datetime.now(),
            "usuario_alta": ObjectId(session['user_id'])
        })
        return redirect(url_for('expediente', id_atencion=id_atencion, id_exp=id_exp))
    return render_template(
        'administrativo/pacientes/cuenta_pac/expediente.html',
        pac=pac,
        cuenta=cuenta,
        total=total
    )

# ====================================================================================
# ============================ MÉDICO ====================================
# ====================================================================================
@app.route('/medico/medico')
def medico():
    if 'user_id' not in session or session['role'] not in ['admin', 'medico']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    db = get_db_connection()
    users_coll = db['users']
    user_data = users_coll.find_one({"_id": ObjectId(session['user_id'])}, {"_id": 1, "papell": 1, "img_perfil": 1})
    usuario = {
        'id_usua': str(user_data['_id']),
        'papell': user_data.get('papell') or session['username'],
        'img_perfil': user_data.get('img_perfil')
    }
    logo = {'img_base': 'logo.jpg'} # placeholder
    # -------------------------------------------------
    # 1. CONSULTA EXTERNA → área = 'Ambulatorio' (sin cama física)
    # -------------------------------------------------
    pipeline_consulta = [
        {"$match": {"area": "Ambulatorio", "status": "ABIERTA"}},
        {"$lookup": {"from": "pacientes", "localField": "Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$project": {
            "id_atencion": 1,
            "num_cama": {"$concat": ["Consulta ", {"$toString": "$id_atencion"}]},
            "estatus": "OCUPADA",
            "nom_pac": "$paciente.nom_pac",
            "papell": "$paciente.papell",
            "sapell": "$paciente.sapell",
            "Id_exp": "$paciente.Id_exp"
        }},
        {"$sort": {"fecha_ing": -1}}
    ]
    beds_consulta = list(db['atencion'].aggregate(pipeline_consulta))
    # -------------------------------------------------
    # 2. PREPARACIÓN → área = 'Urgencias'
    # -------------------------------------------------
    pipeline_preparacion = [
        {"$match": {"area": "Urgencias"}},
        {"$lookup": {"from": "atencion", "localField": "id_cama", "foreignField": "id_cama", "as": "atencion", "pipeline": [{"$match": {"status": "ABIERTA"}}]}},
        {"$unwind": {"path": "$atencion", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": {"path": "$paciente", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "id_cama": 1,
            "id_atencion": "$atencion.id_atencion",
            "num_cama": "$numero",
            "estatus": {"$cond": [{"$ifNull": ["$atencion.id_atencion", False]}, "OCUPADA", "LIBRE"]},
            "nom_pac": "$paciente.nom_pac",
            "papell": "$paciente.papell",
            "sapell": "$paciente.sapell",
            "Id_exp": "$paciente.Id_exp"
        }},
        {"$sort": {"numero": 1}}
    ]
    beds_preparacion = list(db['camas'].aggregate(pipeline_preparacion))
    # -------------------------------------------------
    # 3. RECUPERACIÓN → área = 'Hospitalizado'
    # -------------------------------------------------
    pipeline_recuperacion = [
        {"$match": {"area": "Hospitalizado"}},
        {"$lookup": {"from": "atencion", "localField": "id_cama", "foreignField": "id_cama", "as": "atencion", "pipeline": [{"$match": {"status": "ABIERTA"}}]}},
        {"$unwind": {"path": "$atencion", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": {"path": "$paciente", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "id_cama": 1,
            "id_atencion": "$atencion.id_atencion",
            "num_cama": "$numero",
            "estatus": {"$cond": [{"$ifNull": ["$atencion.id_atencion", False]}, "OCUPADA", "LIBRE"]},
            "nom_pac": "$paciente.nom_pac",
            "papell": "$paciente.papell",
            "sapell": "$paciente.sapell",
            "Id_exp": "$paciente.Id_exp"
        }},
        {"$sort": {"numero": 1}}
    ]
    beds_recuperacion = list(db['camas'].aggregate(pipeline_recuperacion))
    # -------------------------------------------------
    # Asignar hasta 5 médicos a cada cama ocupada
    # -------------------------------------------------
    def asignar_medicos(beds):
        atencion_medicos_coll = db['atencion_medicos']
        for bed in beds:
            bed['id_usua'] = bed['id_usua2'] = bed['id_usua3'] = bed['id_usua4'] = bed['id_usua5'] = None
            if bed.get('id_atencion'):
                medicos = list(atencion_medicos_coll.find({"id_atencion": bed['id_atencion']}, {"id_medico": 1}).sort("_id", 1).limit(5))
                for i, m in enumerate(medicos):
                    bed[f'id_usua{"" if i==0 else i+1}'] = m['id_medico']
        return beds
    beds_consulta = asignar_medicos(beds_consulta)
    beds_preparacion = asignar_medicos(beds_preparacion)
    beds_recuperacion = asignar_medicos(beds_recuperacion)
    return render_template(
        'medico/medico.html',
        usuario=usuario,
        logo=logo,
        beds_consulta=beds_consulta,
        beds_preparacion=beds_preparacion,
        beds_recuperacion=beds_recuperacion
    )

# Ruta para vista de paciente seleccionado
@app.route('/medico/paciente/<int:id_atencion>/<int:Id_exp>')
def paciente(id_atencion, Id_exp):
    if 'user_id' not in session or session['role'] not in ['admin', 'medico']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    db = get_db_connection()
    users_coll = db['users']
    user_data = users_coll.find_one({"_id": ObjectId(session['user_id'])}, {"papell": 1})
    usuario = {
        'id_usua': session['user_id'],
        'papell': user_data.get('papell', '')  # Use .get() with a default value
    }
    # Datos del paciente
    pipeline = [
        {"$match": {"Id_exp": Id_exp}},
        {"$lookup": {"from": "atencion", "localField": "Id_exp", "foreignField": "Id_exp", "as": "atencion"}},
        {"$unwind": "$atencion"},
        {"$match": {"atencion.id_atencion": id_atencion}},
        {"$project": {
            "Id_exp": 1,
            "papell": 1,
            "sapell": 1,
            "nom_pac": 1,
            "fecnac": 1,
            "area": "$atencion.area",
            "motivo_atn": {"$ifNull": ["$atencion.motivo", ""]},  # Default to empty string if missing
            "alergias": {"$ifNull": ["$atencion.alergias", ""]},
            "fecha": "$atencion.fecha_ing"
        }}
    ]
    paciente = list(db['pacientes'].aggregate(pipeline))[0] if list(db['pacientes'].aggregate(pipeline)) else None
    if paciente and 'fecnac' in paciente:
        paciente['edad'] = calcular_edad(paciente['fecnac'])
    # Familiar
    familiar = db['familiares'].find_one({"Id_exp": Id_exp})
    # Médicos
    pipeline_med = [
        {"$match": {"id_atencion": id_atencion}},
        {"$lookup": {"from": "users", "localField": "id_medico", "foreignField": "_id", "as": "user"}},
        {"$unwind": "$user"},
        {"$project": {"doctor": "$user.username"}}
    ]
    medicos = list(db['atencion_medicos'].aggregate(pipeline_med))
    diagnostico = paciente['motivo_atn'] if paciente else ''
    # Cama
    cama = db['camas'].find_one({"id_cama": paciente.get('atencion', {}).get('id_cama')}, {"num_cama": "$numero", "tipo": "$area"}) or {'num_cama': 'Sin Cama', 'tipo': ''}
    return render_template(
        'medico/paciente.html',
        paciente=paciente,
        familiar=familiar,
        medicos=medicos,
        diagnostico=diagnostico,
        cama=cama,
        usuario=usuario,
        id_atencion=id_atencion,
        Id_exp=Id_exp
    )

@app.route('/medico/historia_clinica/<int:id_atencion>/<int:id_exp>',
           methods=['GET', 'POST'])
def historia_clinica(id_atencion, id_exp):
    db = get_db_connection()
    pacientes_coll = db['pacientes']
    historia_coll = db['historia_clinica']
    paciente = pacientes_coll.find_one({"Id_exp": id_exp})
    if request.method == 'POST':
        motivo = request.form['motivo_consulta']
        sinto = ",".join(request.form.getlist('sintomatologia[]'))
        sinto_otro = request.form['sintomatologia_otros']
        heredo = ",".join(request.form.getlist('heredo[]'))
        heredo_otro = request.form['heredo_otros']
        nopat = ",".join(request.form.getlist('nopat[]'))
        nopat_otro = request.form['nopat_otros']
        pat_enf = request.form['pat_enfermedades']
        pat_med = request.form['pat_medicamentos']
        pat_ale = request.form['pat_alergias']
        pat_ocu = request.form['pat_oculares']
        pat_cir = request.form['pat_cirugias']
        historia_coll.insert_one({
            "Id_exp": id_exp,
            "motivo_consulta": motivo,
            "sintomatologia": sinto,
            "sintomatologia_otros": sinto_otro,
            "heredo": heredo,
            "heredo_otros": heredo_otro,
            "nopat": nopat,
            "nopat_otros": nopat_otro,
            "pat_enfermedades": pat_enf,
            "pat_medicamentos": pat_med,
            "pat_alergias": pat_ale,
            "pat_oculares": pat_ocu,
            "pat_cirugias": pat_cir
        })
        flash('Historia clínica guardada correctamente', 'success')
        return redirect(
            url_for(
                'historia_clinica',
                id_atencion=id_atencion,
                id_exp=id_exp
            )
        )
    return render_template(
        'medico/forms/historia_clinica.html',
        paciente=paciente,
        id_atencion=id_atencion,
        Id_exp=id_exp
    )

@app.route('/medico/examenes-gabinete/<int:id_atencion>', methods=['GET'])
def examenes_gabinete(id_atencion):
    if 'user_id' not in session or session['role'] not in ['admin', 'medico']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    db = get_db_connection()
    pipeline = [
        {"$match": {"id_atencion": id_atencion}},
        {"$lookup": {"from": "pacientes", "localField": "Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$project": {"Id_exp": "$paciente.Id_exp", "papell": "$paciente.papell", "sapell": "$paciente.sapell", "nom_pac": "$paciente.nom_pac"}}
    ]
    paciente = list(db['atencion'].aggregate(pipeline))[0] if list(db['atencion'].aggregate(pipeline)) else None
    examenes = list(db['catalogo_examenes'].find({"tipo": "GABINETE"}, {"id_catalogo": 1, "nombre": 1}).sort("nombre", 1))
    return render_template(
        'medico/forms/examenes_gabinete.html',
        id_atencion=id_atencion,
        paciente=paciente,
        examenes=examenes
    )
@app.route('/medico/examenes-gabinete/guardar', methods=['POST'])
def guardar_examenes_gabinete():
    if 'user_id' not in session:
        flash('Sesión no válida.', 'error')
        return redirect(url_for('dashboard'))
    id_atencion = int(request.form.get('id_atencion'))
    observaciones = request.form.get('otros')
    examenes_ids = request.form.getlist('examenes[]')
    examenes_ids = [int(e) for e in examenes_ids]
    if not examenes_ids:
        flash('Debe seleccionar al menos un examen.', 'warning')
        return redirect(url_for('examenes_gabinete', id_atencion=id_atencion))
    db = get_db_connection()
    # 1️⃣ Insertar encabezado (usando colección unificada 'examenes')
    examenes_coll = db['examenes']
    id_examen = get_next_sequence('examenes_id_examen')
    examenes_coll.insert_one({
        "id_examen": id_examen,
        "id_atencion": id_atencion,
        "id_medico": ObjectId(session['user_id']),
        "observaciones": observaciones,
        "fecha": datetime.now()
    })
    # 2️⃣ Insertar detalle (usando colección unificada 'examenes_det', con id_catalogo)
    examenes_det_coll = db['examenes_det']
    catalogo_coll = db['catalogo_examenes']
    for id_catalogo in examenes_ids:
        examen = catalogo_coll.find_one({"id_catalogo": id_catalogo}, {"nombre": 1})
        examenes_det_coll.insert_one({
            "id_examen": id_examen,
            "id_catalogo": id_catalogo,
            "nombre_examen": examen.get('nombre', ''),  # Denormalizar nombre para simplicidad
            "estado": "PENDIENTE"
        })
    flash('Exámenes de gabinete guardados correctamente.', 'success')
    return redirect(
        url_for(
            'examenes_gabinete',
            id_atencion=id_atencion
        )
    )

@app.route('/medico/examenes-laboratorio/<int:id_atencion>', methods=['GET'])
def examenes_laboratorio(id_atencion):
    if 'user_id' not in session or session['role'] not in ['admin', 'medico']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    db = get_db_connection()
    # Paciente completo
    pipeline = [
        {"$match": {"id_atencion": id_atencion}},
        {"$lookup": {"from": "pacientes", "localField": "Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$project": {
            "Id_exp": "$paciente.Id_exp",
            "nom_pac": "$paciente.nom_pac",
            "papell": "$paciente.papell",
            "sapell": "$paciente.sapell"
        }}
    ]
    paciente = list(db['atencion'].aggregate(pipeline))[0] if list(db['atencion'].aggregate(pipeline)) else None
    # Catálogo de exámenes (filtrado por tipo LABORATORIO)
    examenes = list(db['catalogo_examenes'].find({"tipo": "LABORATORIO"}, {"id_catalogo": 1, "nombre": 1}).sort("nombre", 1))
    return render_template(
        'medico/forms/examenes_laboratorio.html',
        id_atencion=id_atencion,
        paciente=paciente,
        Id_exp=paciente['Id_exp'],
        examenes=examenes
    )

@app.route('/medico/examenes-laboratorio/guardar', methods=['POST'])
def guardar_examenes_laboratorio():
    if 'user_id' not in session:
        flash('Sesión no válida.', 'error')
        return redirect(url_for('dashboard'))
    id_atencion = int(request.form.get('id_atencion'))
    Id_exp = int(request.form.get('Id_exp'))
    observaciones = request.form.get('otros')
    examenes = request.form.getlist('examenes[]')
    examenes = [int(e) for e in examenes]
    if not examenes:
        flash('Debe seleccionar al menos un examen.', 'warning')
        return redirect(url_for('examenes_laboratorio', id_atencion=id_atencion))
    db = get_db_connection()
    # Encabezado (usando colección unificada 'examenes')
    examenes_coll = db['examenes']
    id_examen = get_next_sequence('examenes_id_examen')
    examenes_coll.insert_one({
        "id_examen": id_examen,
        "id_atencion": id_atencion,
        "id_medico": ObjectId(session['user_id']),
        "observaciones": observaciones,
        "fecha": datetime.now()
    })
    # Detalle (usando colección unificada 'examenes_det', con id_catalogo)
    examenes_det_coll = db['examenes_det']
    catalogo_coll = db['catalogo_examenes']
    for id_catalogo in examenes:
        examen = catalogo_coll.find_one({"id_catalogo": id_catalogo}, {"nombre": 1})
        examenes_det_coll.insert_one({
            "id_examen": id_examen,
            "id_catalogo": id_catalogo,
            "nombre_examen": examen.get('nombre', ''),  # Denormalizar nombre para simplicidad
            "estado": "PENDIENTE"
        })
    flash('Exámenes de laboratorio enviados correctamente.', 'success')
    return redirect(
        url_for(
            'examenes_laboratorio',
            id_atencion=id_atencion
        )
    )


@app.route('/medico/resultados-estudios/<int:id_atencion>')
def resultados_estudios(id_atencion):
    if 'user_id' not in session:
        flash('Sesión no válida.', 'error')
        return redirect(url_for('dashboard'))
    db = get_db_connection()

    # ================= PACIENTE =================
    pipeline = [
        {"$match": {"id_atencion": id_atencion}},
        {"$lookup": {"from": "pacientes", "localField": "Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$project": {
            "Id_exp": "$paciente.Id_exp",
            "papell": "$paciente.papell",
            "sapell": "$paciente.sapell",
            "nom_pac": "$paciente.nom_pac",
            "area": 1,
            "fecha_ing": 1
        }}
    ]
    paciente_list = list(db['atencion'].aggregate(pipeline))
    paciente = paciente_list[0] if paciente_list else None

    if not paciente:
        flash('Paciente no encontrado.', 'error')
        return redirect(url_for('dashboard'))

    # ================= LABORATORIO =================
    pipeline_lab = [
        {"$match": {"id_atencion": id_atencion}},
        {"$lookup": {"from": "examenes_det", "localField": "id_examen", "foreignField": "id_examen", "as": "det"}},
        {"$unwind": "$det"},
        {"$lookup": {"from": "catalogo_examenes", "localField": "det.id_catalogo", "foreignField": "id_catalogo",
                     "as": "cat"}},
        {"$unwind": "$cat"},
        {"$match": {"cat.tipo": "LABORATORIO"}},
        {"$lookup": {"from": "users", "localField": "id_medico", "foreignField": "_id", "as": "user"}},
        {"$unwind": "$user"},
        {"$group": {
            "_id": "$id_examen",
            "id_examen": {"$first": "$id_examen"},  # 👈 AGREGAR ESTO
            "fecha": {"$first": "$fecha"},
            "observaciones": {"$first": "$observaciones"},
            "medico": {"$first": {"$concat": ["$user.pnombre", " ", "$user.papell"]}},
            "estudios": {"$push": "$cat.nombre"},
            "detalles": {"$push": {
                "nombre": "$cat.nombre",
                "estado": "$det.estado",
                "resultado": "$det.resultado",
                "fecha_realizado": "$det.fecha_realizado"
            }}
        }},
        {"$sort": {"fecha": -1}}
    ]
    laboratorio = list(db['examenes'].aggregate(pipeline_lab))

    # ================= GABINETE =================
    pipeline_gab = [
        {"$match": {"id_atencion": id_atencion}},
        {"$lookup": {"from": "examenes_det", "localField": "id_examen", "foreignField": "id_examen", "as": "det"}},
        {"$unwind": "$det"},
        {"$lookup": {"from": "catalogo_examenes", "localField": "det.id_catalogo", "foreignField": "id_catalogo",
                     "as": "cat"}},
        {"$unwind": "$cat"},
        {"$match": {"cat.tipo": "GABINETE"}},
        {"$lookup": {"from": "users", "localField": "id_medico", "foreignField": "_id", "as": "user"}},
        {"$unwind": "$user"},
        {"$group": {
            "_id": "$id_examen",
            "id_examen": {"$first": "$id_examen"},  # 👈 AGREGAR ESTO
            "fecha": {"$first": "$fecha"},
            "observaciones": {"$first": "$observaciones"},
            "medico": {"$first": {"$concat": ["$user.pnombre", " ", "$user.papell"]}},
            "estudios": {"$push": "$cat.nombre"},
            "detalles": {"$push": {
                "nombre": "$cat.nombre",
                "estado": "$det.estado",
                "archivo": "$det.archivo_resultado",
                "fecha_realizado": "$det.fecha_realizado"
            }}
        }},
        {"$sort": {"fecha": -1}}
    ]
    gabinete = list(db['examenes'].aggregate(pipeline_gab))

    return render_template(
        'medico/res_estudios/resultados_estudios.html',
        paciente=paciente,
        id_atencion=id_atencion,
        laboratorio=laboratorio,
        gabinete=gabinete
    )


@app.route('/medico/resultados-laboratorio/<int:id_examen>')
def ver_resultado_laboratorio(id_examen):
    if 'user_id' not in session:
        flash('Sesión no válida.', 'error')
        return redirect(url_for('dashboard'))

    db = get_db_connection()

    # Obtener encabezado y paciente
    pipeline_enc = [
        {"$match": {"id_examen": id_examen}},
        {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
        {"$unwind": "$atencion"},
        {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$lookup": {"from": "users", "localField": "id_medico", "foreignField": "_id", "as": "user"}},
        {"$unwind": "$user"},
        {"$project": {
            "fecha": 1,
            "observaciones": 1,
            "id_atencion": "$atencion.id_atencion",
            "Id_exp": "$paciente.Id_exp",
            "papell": "$paciente.papell",
            "sapell": "$paciente.sapell",
            "nom_pac": "$paciente.nom_pac",
            "medico": {"$concat": ["$user.pnombre", " ", "$user.papell"]}
        }}
    ]

    encabezado_list = list(db['examenes'].aggregate(pipeline_enc))
    if not encabezado_list:
        flash('Resultado no encontrado.', 'error')
        return redirect(url_for('dashboard'))

    encabezado = encabezado_list[0]

    # Crear objeto paciente para el template
    paciente = {
        'Id_exp': encabezado['Id_exp'],
        'papell': encabezado['papell'],
        'sapell': encabezado['sapell'],
        'nom_pac': encabezado['nom_pac']
    }

    # Obtener detalles de laboratorio
    pipeline_det = [
        {"$match": {"id_examen": id_examen}},
        {"$lookup": {"from": "catalogo_examenes", "localField": "id_catalogo", "foreignField": "id_catalogo",
                     "as": "cat"}},
        {"$unwind": "$cat"},
        {"$match": {"cat.tipo": "LABORATORIO"}},
        {"$project": {
            "nombre": "$cat.nombre",
            "estado": 1,
            "resultado": 1,
            "fecha_realizado": 1,
            "observaciones": 1
        }}
    ]

    detalles = list(db['examenes_det'].aggregate(pipeline_det))

    return render_template(
        'medico/res_estudios/ver_resultado_laboratorio.html',
        encabezado=encabezado,
        paciente=paciente,  # 👈 AGREGAR ESTO
        detalles=detalles,
        id_atencion=encabezado['id_atencion']
    )


@app.route('/medico/gabinete/ver/<int:id_examen>')
def ver_resultado_gabinete(id_examen):
    if 'user_id' not in session:
        flash('Sesión no válida', 'error')
        return redirect(url_for('dashboard'))

    db = get_db_connection()

    # Obtener encabezado y paciente
    pipeline_enc = [
        {"$match": {"id_examen": id_examen}},
        {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
        {"$unwind": "$atencion"},
        {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$lookup": {"from": "users", "localField": "id_medico", "foreignField": "_id", "as": "user"}},
        {"$unwind": "$user"},
        {"$project": {
            "fecha": 1,
            "observaciones": 1,
            "id_atencion": "$atencion.id_atencion",
            "Id_exp": "$paciente.Id_exp",
            "papell": "$paciente.papell",
            "sapell": "$paciente.sapell",
            "nom_pac": "$paciente.nom_pac",
            "medico": {"$concat": ["$user.pnombre", " ", "$user.papell"]}
        }}
    ]

    encabezado_list = list(db['examenes'].aggregate(pipeline_enc))
    if not encabezado_list:
        flash('Resultado no encontrado.', 'error')
        return redirect(url_for('dashboard'))

    encabezado = encabezado_list[0]

    # Crear objeto paciente para el template
    paciente = {
        'Id_exp': encabezado['Id_exp'],
        'papell': encabezado['papell'],
        'sapell': encabezado['sapell'],
        'nom_pac': encabezado['nom_pac']
    }

    # Obtener detalles de gabinete
    pipeline_det = [
        {"$match": {"id_examen": id_examen}},
        {"$lookup": {"from": "catalogo_examenes", "localField": "id_catalogo", "foreignField": "id_catalogo",
                     "as": "cat"}},
        {"$unwind": "$cat"},
        {"$match": {"cat.tipo": "GABINETE"}},
        {"$project": {
            "nombre": "$cat.nombre",
            "estado": 1,
            "archivo_resultado": 1,
            "fecha_realizado": 1,
            "observaciones": 1
        }}
    ]

    detalles = list(db['examenes_det'].aggregate(pipeline_det))

    return render_template(
        'medico/res_estudios/ver_resultado_gabinete.html',
        encabezado=encabezado,
        paciente=paciente,  # 👈 AGREGAR ESTO
        detalles=detalles,
        id_atencion=encabezado['id_atencion']
    )

# ==================== GESTIÓN DE CUENTAS ====================
@app.route('/admin/presupuestos', methods=['GET', 'POST'])
def presupuestos():
    if 'user_id' not in session:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    db = get_db_connection()
    # ⚠️ Temporal
    id_pac = 1
    nombre = 'PRUEBA'
    IVA = Decimal('1.16')
    # ======================
    # INSERTAR SERVICIO
    # ======================
    if request.method == 'POST' and 'btnserv' in request.form:
        serv_id = request.form.get('serv')
        cantidad = int(request.form.get('cantidad'))
        serv = db['cat_servicios'].find_one({"id_serv": int(serv_id)}, {"serv_desc": 1})
        if serv:
            db['presupuesto'].insert_one({
                "fecha": datetime.now(),
                "id_pac": id_pac,
                "nombre": nombre,
                "id_serv": serv_id,
                "servicio": serv['serv_desc'],
                "cantidad": cantidad
            })
        return redirect(url_for('presupuestos'))
    # ======================
    # INSERTAR MEDICAMENTO
    # ======================
    if request.method == 'POST' and 'btnmed' in request.form:
        item_id = request.form.get('med')
        cantidad = int(request.form.get('cantidad'))
        item = db['item'].find_one({"item_id": int(item_id)}, {"item_code": 1, "item_name": 1})
        if item:
            db['presupuesto'].insert_one({
                "fecha": datetime.now(),
                "id_pac": id_pac,
                "nombre": nombre,
                "id_serv": item['item_code'],
                "servicio": item['item_name'],
                "cantidad": cantidad
            })
        return redirect(url_for('presupuestos'))
    # ======================
    # SELECTS PARA FORMULARIOS
    # ======================
    servicios = list(db['cat_servicios'].find({"serv_activo": "SI"}, {"id_serv": 1, "serv_desc": 1, "serv_costo": 1}))
    items = list(db['item'].find({}, {"item_id": 1, "item_code": 1, "item_name": 1, "item_price": 1}))
    # ======================
    # TABLA PRESUPUESTO - SERVICIOS
    # ======================
    pipeline_serv = [
        {"$match": {"id_pac": id_pac}},
        {"$lookup": {"from": "cat_servicios", "localField": "id_serv", "foreignField": "id_serv", "as": "cat"}},
        {"$unwind": "$cat"},
        {"$project": {
            "fecha": 1,
            "id_pac": 1,
            "nombre": 1,
            "id_serv": 1,
            "servicio": 1,
            "cantidad": 1,
            "serv_costo": "$cat.serv_costo"
        }}
    ]
    lista_serv = list(db['presupuesto'].aggregate(pipeline_serv))
    for p in lista_serv:
        costo = Decimal(str(p['serv_costo']))
        cantidad = Decimal(str(p['cantidad']))
        p['subtotal'] = costo * cantidad
        p['total'] = p['subtotal'] * IVA
    # ======================
    # TABLA PRESUPUESTO - ITEMS
    # ======================
    pipeline_items = [
        {"$match": {"id_pac": id_pac}},
        {"$lookup": {"from": "item", "localField": "id_serv", "foreignField": "item_code", "as": "it"}},
        {"$unwind": "$it"},
        {"$project": {
            "fecha": 1,
            "id_pac": 1,
            "nombre": 1,
            "id_serv": 1,
            "servicio": 1,
            "cantidad": 1,
            "item_price": "$it.item_price"
        }}
    ]
    lista_items = list(db['presupuesto'].aggregate(pipeline_items))
    for p in lista_items:
        precio = Decimal(str(p['item_price']))
        cantidad = Decimal(str(p['cantidad']))
        p['subtotal'] = precio * cantidad
        p['total'] = p['subtotal'] * IVA
    return render_template(
        'administrativo/gestion_cuentas/presupuestos.html',
        servicios=servicios,
        items=items,
        lista_serv=lista_serv,
        lista_items=lista_items,
        IVA=IVA
    )

@app.route('/admin/presupuestos/eliminar/<int:id_presupuesto>', methods=['POST'])
def eliminar_presupuesto(id_presupuesto):
    if 'user_id' not in session:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    db = get_db_connection()
    db['presupuesto'].delete_one({"id_presupuesto": id_presupuesto})
    flash('Registro eliminado correctamente', 'success')
    return redirect(url_for('presupuestos'))

@app.route('/admin/corte_caja')
def corte_caja():
    if 'user_id' not in session:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    return render_template('administrativo/gestion_cuentas/corte_caja.html')

@app.route('/corte_caja/pdf', methods=['POST'])
def corte_caja_pdf():
    fecha_inicio = datetime.strptime(request.form['fecha_inicio'], "%Y-%m-%d")
    fecha_fin = datetime.strptime(request.form['fecha_fin'], "%Y-%m-%d") + timedelta(days=1)
    db = get_db_connection()
    pdf = FPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    # =============================
    # ENCABEZADO
    # =============================
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(43, 45, 127)
    pdf.cell(0, 10, 'REPORTE CORTE DE CAJA', border=1, ln=1, align='C')
    pdf.ln(5)
    pdf.set_font('Arial', '', 10)
    pdf.cell(
        0, 8,
        f"Periodo del {fecha_inicio.strftime('%Y-%m-%d')} al {request.form['fecha_fin']}",
        ln=1
    )
    # =============================
    # TABLA
    # =============================
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 9)
    headers = ['#', 'Fecha', 'Paciente', 'Monto', 'Tipo', 'Metodo']
    widths = [8, 25, 80, 20, 15, 30]
    for h, w in zip(headers, widths):
        pdf.cell(w, 8, h, 1)
    pdf.ln()
    pdf.set_font('Arial', '', 8)
    total_efectivo = 0
    contador = 1
    pipeline = [
        {"$match": {"fecha": {"$gte": fecha_inicio, "$lt": fecha_fin}, "tipo_pago": {"$nin": ['DESCUENTO','ASEGURADORA']}}},
        {"$lookup": {"from": "pago_serv", "localField": "id_pac", "foreignField": "id_pac", "as": "pago"}},
        {"$unwind": "$pago"},
        {"$project": {"nombre": "$pago.nombre", "fecha": 1, "deposito": 1, "tipo_pago": 1}},
        {"$sort": {"nombre": 1}}
    ]
    rows = list(db['depositos_pserv'].aggregate(pipeline))
    for r in rows:
        pdf.cell(8, 8, str(contador), 1)
        pdf.cell(25, 8, r['fecha'].strftime('%Y-%m-%d'), 1)
        pdf.cell(80, 8, r['nombre'], 1)
        pdf.cell(20, 8, f"${float(r['deposito']):.2f}", 1)
        pdf.cell(15, 8, 'SERV', 1)
        pdf.cell(30, 8, r['tipo_pago'], 1)
        pdf.ln()
        total_efectivo += float(r['deposito'])
        contador += 1
    # =============================
    # TOTAL
    # =============================
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(0, 10, f"TOTAL EFECTIVO: ${total_efectivo:,.2f}", 1, ln=1)
    response = make_response(pdf.output(dest='S').encode('latin-1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=corte_caja.pdf'
    return response

@app.route('/corte_caja/excel')
def corte_caja_excel():
    # Consulta
    # Generar Excel
    return "Generar Excel"

@app.route('/medico/imprimir/<int:id_atencion>')
def imprimir_documentos(id_atencion):
    db = get_db_connection()
    pipeline = [
        {"$match": {"id_atencion": id_atencion}},
        {"$lookup": {"from": "pacientes", "localField": "Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$project": {"Id_exp": "$paciente.Id_exp", "papell": "$paciente.papell", "sapell": "$paciente.sapell", "nom_pac": "$paciente.nom_pac"}}
    ]
    paciente = list(db['atencion'].aggregate(pipeline))[0] if list(db['atencion'].aggregate(pipeline)) else None
    return render_template(
        'medico/impresiones/imprimir_documentos.html',
        paciente=paciente,
        id_atencion=id_atencion
    )


@app.route('/medico/imprimir/signos/<int:id_atencion>')
def imprimir_signos_vitales(id_atencion):
    db = get_db_connection()

    # Obtener información del paciente
    pipeline_paciente = [
        {"$match": {"id_atencion": id_atencion}},
        {"$lookup": {"from": "pacientes", "localField": "Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$project": {
            "Id_exp": "$paciente.Id_exp",
            "papell": "$paciente.papell",
            "sapell": "$paciente.sapell",
            "nom_pac": "$paciente.nom_pac"
        }}
    ]
    paciente_result = list(db['atencion'].aggregate(pipeline_paciente))
    paciente = paciente_result[0] if paciente_result else None

    # Obtener signos vitales con TODOS los campos necesarios
    signos = list(db['signos_vitales'].find(
        {"id_atencion": id_atencion}
    ).sort("fecha_registro", -1))

    # Convertir ObjectId a string para cada signo (si es necesario)
    for signo in signos:
        signo['_id'] = str(signo['_id'])

    return render_template(
        'medico/impresiones/signos_vitales.html',
        paciente=paciente,
        signos=signos,
        id_atencion=id_atencion
    )

@app.route('/medico/imprimir/notas/<int:id_atencion>')
def imprimir_notas_medicas(id_atencion):
    db = get_db_connection()
    pipeline = [
        {"$match": {"id_atencion": id_atencion}},
        {"$lookup": {"from": "pacientes", "localField": "Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$project": {"Id_exp": "$paciente.Id_exp", "papell": "$paciente.papell", "sapell": "$paciente.sapell", "nom_pac": "$paciente.nom_pac"}}
    ]
    paciente = list(db['atencion'].aggregate(pipeline))[0] if list(db['atencion'].aggregate(pipeline)) else None
    notas = list(db['notas_medicas'].find({"id_atencion": id_atencion}).sort("fecha_registro", -1))
    return render_template(
        'medico/impresiones/notas_medicas.html',
        paciente=paciente,
        notas=notas,
        id_atencion=id_atencion
    )

@app.route('/medico/imprimir/diagnostico/<int:id_atencion>')
def imprimir_diagnostico(id_atencion):
    db = get_db_connection()
    pipeline = [
        {"$match": {"id_atencion": id_atencion}},
        {"$lookup": {"from": "pacientes", "localField": "Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$project": {"Id_exp": "$paciente.Id_exp", "papell": "$paciente.papell", "sapell": "$paciente.sapell", "nom_pac": "$paciente.nom_pac"}}
    ]
    paciente = list(db['atencion'].aggregate(pipeline))[0] if list(db['atencion'].aggregate(pipeline)) else None
    diagnosticos = list(db['diagnosticos'].find({"id_atencion": id_atencion}).sort("fecha_registro", -1))
    return render_template(
        'medico/impresiones/diagnostico.html',
        paciente=paciente,
        diagnosticos=diagnosticos,
        id_atencion=id_atencion
    )


@app.route('/medico/imprimir/recetas/<int:id_atencion>')
def imprimir_recetas(id_atencion):
    db = get_db_connection()

    # Obtener paciente
    pipeline_pac = [
        {"$match": {"id_atencion": id_atencion}},
        {"$lookup": {"from": "pacientes", "localField": "Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$project": {
            "Id_exp": "$paciente.Id_exp",
            "papell": "$paciente.papell",
            "sapell": "$paciente.sapell",
            "nom_pac": "$paciente.nom_pac"
        }}
    ]
    paciente_list = list(db['atencion'].aggregate(pipeline_pac))
    paciente = paciente_list[0] if paciente_list else None

    # Obtener recetas (cada documento es una receta con array de medicamentos)
    recetas = list(db['recetas'].find(
        {"id_atencion": id_atencion}
    ).sort("fecha_registro", -1))

    return render_template(
        'medico/impresiones/recetas.html',
        paciente=paciente,
        recetas=recetas,  # Ahora recetas es una lista de documentos con id_receta
        id_atencion=id_atencion
    )


@app.route('/medico/imprimir/laboratorio/<int:id_atencion>')
def imprimir_laboratorio(id_atencion):
    db = get_db_connection()

    # Obtener paciente
    pipeline_pac = [
        {"$match": {"id_atencion": id_atencion}},
        {"$lookup": {"from": "pacientes", "localField": "Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$project": {
            "Id_exp": "$paciente.Id_exp",
            "papell": "$paciente.papell",
            "sapell": "$paciente.sapell",
            "nom_pac": "$paciente.nom_pac"
        }}
    ]
    paciente_list = list(db['atencion'].aggregate(pipeline_pac))
    paciente = paciente_list[0] if paciente_list else None

    # Obtener exámenes de laboratorio
    pipeline_examenes = [
        {"$match": {"id_atencion": id_atencion}},
        {"$lookup": {
            "from": "examenes_det",
            "localField": "id_examen",
            "foreignField": "id_examen",
            "as": "detalles"
        }},
        {"$unwind": "$detalles"},
        {"$lookup": {
            "from": "catalogo_examenes",
            "localField": "detalles.id_catalogo",
            "foreignField": "id_catalogo",
            "as": "catalogo"
        }},
        {"$unwind": "$catalogo"},
        {"$match": {"catalogo.tipo": "LABORATORIO"}},
        {"$group": {
            "_id": "$id_examen",
            "id_examen": {"$first": "$id_examen"},  # 👈 IMPORTANTE: incluir id_examen explícitamente
            "fecha": {"$first": "$fecha"},
            "observaciones": {"$first": "$observaciones"},
            "examenes": {
                "$push": {
                    "nombre": "$catalogo.nombre",
                    "estado": "$detalles.estado",
                    "resultado": "$detalles.resultado"
                }
            },
            "estados": {"$push": "$detalles.estado"}
        }},
        {"$addFields": {
            "estado": {  # 👈 Estado general del grupo
                "$cond": [
                    {"$in": ["PENDIENTE", "$estados"]},
                    "PENDIENTE",
                    {
                        "$cond": [
                            {"$in": ["CANCELADO", "$estados"]},
                            "CANCELADO",
                            "REALIZADO"
                        ]
                    }
                ]
            }
        }},
        {"$project": {
            "id_examen": 1,  # 👈 Asegurar que id_examen está en el resultado
            "fecha": 1,
            "estado": 1,
            "observaciones": 1,
            "examenes": 1
        }},
        {"$sort": {"fecha": -1}}
    ]

    examenes = list(db['examenes'].aggregate(pipeline_examenes))

    return render_template(
        'medico/impresiones/examenes_laboratorio.html',
        paciente=paciente,
        examenes=examenes,
        id_atencion=id_atencion
    )


@app.route('/medico/imprimir/gabinete/<int:id_atencion>')
def imprimir_gabinete(id_atencion):
    db = get_db_connection()

    # Obtener paciente
    pipeline_pac = [
        {"$match": {"id_atencion": id_atencion}},
        {"$lookup": {"from": "pacientes", "localField": "Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$project": {
            "Id_exp": "$paciente.Id_exp",
            "papell": "$paciente.papell",
            "sapell": "$paciente.sapell",
            "nom_pac": "$paciente.nom_pac"
        }}
    ]
    paciente_list = list(db['atencion'].aggregate(pipeline_pac))
    paciente = paciente_list[0] if paciente_list else None

    # Obtener exámenes de gabinete
    pipeline_examenes = [
        {"$match": {"id_atencion": id_atencion}},
        {"$lookup": {
            "from": "examenes_det",
            "localField": "id_examen",
            "foreignField": "id_examen",
            "as": "detalles"
        }},
        {"$unwind": "$detalles"},
        {"$lookup": {
            "from": "catalogo_examenes",
            "localField": "detalles.id_catalogo",
            "foreignField": "id_catalogo",
            "as": "catalogo"
        }},
        {"$unwind": "$catalogo"},
        {"$match": {"catalogo.tipo": "GABINETE"}},
        {"$group": {
            "_id": "$id_examen",
            "id_examen": {"$first": "$id_examen"},
            "fecha": {"$first": "$fecha"},
            "observaciones": {"$first": "$observaciones"},
            "examenes": {
                "$push": {
                    "nombre": "$catalogo.nombre",
                    "estado": "$detalles.estado",
                    "archivo": "$detalles.archivo_resultado"
                }
            },
            "estados": {"$push": "$detalles.estado"}
        }},
        {"$addFields": {
            "estado_general": {  # 👈 Cambiar de "estado" a "estado_general"
                "$cond": [
                    {"$in": ["PENDIENTE", "$estados"]},
                    "PENDIENTE",
                    {
                        "$cond": [
                            {"$in": ["CANCELADO", "$estados"]},
                            "CANCELADO",
                            "REALIZADO"
                        ]
                    }
                ]
            }
        }},
        {"$project": {
            "id_examen": 1,
            "fecha": 1,
            "estado_general": 1,  # 👈 Asegurar que se llama estado_general
            "observaciones": 1,
            "examenes": 1
        }},
        {"$sort": {"fecha": -1}}
    ]

    examenes = list(db['examenes'].aggregate(pipeline_examenes))

    # DEBUG: Imprimir para verificar (opcional)
    print("Exámenes encontrados:", len(examenes))
    for e in examenes:
        print(f"ID: {e.get('id_examen')}, Estado: {e.get('estado_general')}")

    return render_template(
        'medico/impresiones/examenes_gabinete.html',
        paciente=paciente,
        examenes=examenes,
        id_atencion=id_atencion
    )

@app.route('/medico/signos-vitales/<int:id_atencion>', methods=['GET', 'POST'])
def signos_vitales(id_atencion):
    if 'user_id' not in session:
        flash('Sesión no válida', 'error')
        return redirect(url_for('dashboard'))
    db = get_db_connection()
    # ========= PACIENTE =========
    pipeline = [
        {"$match": {"id_atencion": id_atencion}},
        {"$lookup": {"from": "pacientes", "localField": "Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$project": {"paciente": 1}}
    ]
    paciente = list(db['atencion'].aggregate(pipeline))[0]['paciente'] if list(db['atencion'].aggregate(pipeline)) else None
    if not paciente:
        flash('Paciente no encontrado', 'error')
        return redirect(url_for('dashboard'))
    # ========= POST =========
    if request.method == 'POST':
        db['signos_vitales'].insert_one({
            "id_signos": get_next_sequence('signos_vitales_id'),  # AGREGAR ESTO
            "id_atencion": id_atencion,
            "ta": request.form.get('ta'),
            "fc": request.form.get('fc'),
            "fr": request.form.get('fr'),
            "temp": request.form.get('temp'),
            "spo2": request.form.get('spo2'),
            "peso": request.form.get('peso'),
            "talla": request.form.get('talla'),
            "fecha_registro": datetime.now()
        })
        flash('Signos vitales registrados correctamente', 'success')
        return redirect(url_for('signos_vitales', id_atencion=id_atencion))
    return render_template(
        'medico/forms/signos_vitales.html',
        paciente=paciente,
        id_atencion=id_atencion
    )

@app.route('/medico/nota-medica/<int:id_atencion>', methods=['GET', 'POST'])
def nota_medica(id_atencion):
    if 'user_id' not in session:
        flash('Sesión no válida', 'error')
        return redirect(url_for('dashboard'))
    db = get_db_connection()
    if request.method == 'POST':
        db['notas_medicas'].insert_one({
            "id_nota": get_next_sequence('notas_medicas_id'),  # AGREGAR ESTO
            "id_atencion": id_atencion,
            "subjetivo": request.form['subjetivo'],
            "objetivo": request.form['objetivo'],
            "analisis": request.form['analisis'],
            "plan": request.form['plan'],
            "id_medico": ObjectId(session['user_id']),
            "fecha_registro": datetime.now()
        })
        flash('Nota médica registrada correctamente', 'success')
        return redirect(url_for('nota_medica', id_atencion=id_atencion))
    pipeline = [
        {"$match": {"id_atencion": id_atencion}},
        {"$lookup": {"from": "pacientes", "localField": "Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$project": {"paciente": 1}}
    ]
    paciente = list(db['atencion'].aggregate(pipeline))[0]['paciente'] if list(db['atencion'].aggregate(pipeline)) else None
    notas = list(db['notas_medicas'].find({"id_atencion": id_atencion}).sort("fecha_registro", -1))
    return render_template(
        'medico/forms/nota_medica.html',
        paciente=paciente,
        notas=notas,
        id_atencion=id_atencion
    )

@app.route('/medico/diagnostico/<int:id_atencion>', methods=['GET', 'POST'])
def diagnostico(id_atencion):
    if 'user_id' not in session:
        flash('Sesión no válida', 'error')
        return redirect(url_for('dashboard'))
    db = get_db_connection()
    atencion_coll = db['atencion']
    atencion = atencion_coll.find_one({"id_atencion": id_atencion}, {"status": 1})
    if not atencion:
        flash('Atención no encontrada', 'danger')
        return redirect(url_for('dashboard'))
    # ===== POST =====
    if request.method == 'POST':
        diagnostico_principal = request.form['diagnostico_principal']
        secundarios = request.form.get('diagnosticos_secundarios')
        observaciones = request.form.get('observaciones')
        diag_coll = db['diagnosticos']

        if diag_coll.find_one({"id_atencion": id_atencion}):
            diag_coll.update_one({"id_atencion": id_atencion}, {"$set": {
                "diagnostico_principal": diagnostico_principal,
                "diagnosticos_secundarios": secundarios,
                "observaciones": observaciones
            }})
        else:
            diag_coll.insert_one({
                "id_diagnostico": get_next_sequence('diagnosticos_id'),  # AGREGAR ESTO
                "id_atencion": id_atencion,
                "diagnostico_principal": diagnostico_principal,
                "diagnosticos_secundarios": secundarios,
                "observaciones": observaciones,
                "fecha_registro": datetime.now()
            })
        flash('Diagnóstico guardado correctamente', 'success')
        return redirect(url_for('diagnostico', id_atencion=id_atencion))
    # ===== GET =====
    diagnostico = db['diagnosticos'].find_one({"id_atencion": id_atencion})
    pipeline = [
        {"$match": {"id_atencion": id_atencion}},
        {"$lookup": {"from": "pacientes", "localField": "Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$project": {"paciente": 1}}
    ]
    paciente = list(atencion_coll.aggregate(pipeline))[0]['paciente'] if list(atencion_coll.aggregate(pipeline)) else None
    return render_template(
        'medico/forms/diagnostico.html',
        diagnostico=diagnostico,
        paciente=paciente,
        id_atencion=id_atencion,
        status_atencion=atencion['status']
    )


@app.route('/medico/receta/<int:id_atencion>', methods=['GET', 'POST'])
def receta_medica(id_atencion):
    if 'user_id' not in session:
        flash('Sesión no válida', 'error')
        return redirect(url_for('dashboard'))
    db = get_db_connection()

    if request.method == 'POST':
        medicamentos = request.form.getlist('medicamento[]')
        dosis = request.form.getlist('dosis[]')
        frecuencia = request.form.getlist('frecuencia[]')
        duracion = request.form.getlist('duracion[]')
        indicaciones = request.form.getlist('indicaciones[]')

        # Crear UN SOLO documento con TODOS los medicamentos
        recetas_coll = db['recetas']

        # Construir el array de medicamentos
        medicamentos_array = []
        for i in range(len(medicamentos)):
            if medicamentos[i].strip():  # Solo si no está vacío
                medicamentos_array.append({
                    "medicamento": medicamentos[i],
                    "dosis": dosis[i] if i < len(dosis) else "",
                    "frecuencia": frecuencia[i] if i < len(frecuencia) else "",
                    "duracion": duracion[i] if i < len(duracion) else "",
                    "indicaciones": indicaciones[i] if i < len(indicaciones) else ""
                })

        if medicamentos_array:
            recetas_coll.insert_one({
                "id_receta": get_next_sequence('recetas_id'),
                "id_atencion": id_atencion,
                "medicamentos": medicamentos_array,  # Array de medicamentos
                "id_medico": ObjectId(session['user_id']),
                "fecha_registro": datetime.now()
            })
            flash('Receta guardada correctamente', 'success')
        else:
            flash('No se ingresaron medicamentos', 'error')

        return redirect(url_for('receta_medica', id_atencion=id_atencion))

    # GET: Obtener paciente y recetas
    pipeline = [
        {"$match": {"id_atencion": id_atencion}},
        {"$lookup": {"from": "pacientes", "localField": "Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$project": {"paciente": 1}}
    ]
    paciente = list(db['atencion'].aggregate(pipeline))
    paciente = paciente[0]['paciente'] if paciente else None

    # Obtener recetas (ahora cada una es un documento con array de medicamentos)
    recetas = list(db['recetas'].find(
        {"id_atencion": id_atencion}
    ).sort("fecha_registro", -1))

    return render_template(
        'medico/forms/receta.html',
        paciente=paciente,
        recetas=recetas,
        id_atencion=id_atencion
    )

@app.route('/medico/diagnostico/historial/<int:id_atencion>')
def historial_diagnostico(id_atencion):
    if 'user_id' not in session:
        flash('Sesión no válida', 'error')
        return redirect(url_for('dashboard'))
    db = get_db_connection()
    # ================= HISTORIAL =================
    pipeline = [
        {"$match": {"id_atencion": id_atencion}},
        {"$lookup": {"from": "users", "localField": "id_medico", "foreignField": "id", "as": "user"}},
        {"$unwind": "$user"},
        {"$project": {
            "diagnostico_principal": 1,
            "diagnosticos_secundarios": 1,
            "observaciones": 1,
            "fecha_registro": 1,
            "medico_papell": "$user.papell"
        }},
        {"$sort": {"fecha_registro": -1}}
    ]
    historial = list(db['diagnosticos_historial'].aggregate(pipeline))
    # ================= PACIENTE =================
    pipeline_pac = [
        {"$match": {"id_atencion": id_atencion}},
        {"$lookup": {"from": "pacientes", "localField": "Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$project": {"paciente": 1}}
    ]
    paciente = list(db['atencion'].aggregate(pipeline_pac))[0]['paciente'] if list(db['atencion'].aggregate(pipeline_pac)) else None
    return render_template(
        'medico/forms/historial_diagnostico.html',
        historial=historial,
        paciente=paciente,
        id_atencion=id_atencion
    )

# ====================================================================================
# ============================ CONFIGURACION ===============================
# ====================================================================================
# ==================== MENÚ CONFIGURACION ====================
@app.route('/configuracion/configuracion')
def menu_configuracion():
    if 'user_id' not in session:
        flash('Debes iniciar sesión', 'error')
        return redirect(url_for('login'))
    usuario = {
        'username': session.get('username'),
        'role': session.get('role')
    }
    return render_template(
        'configuracion/menu_configuracion.html',
        usuario=usuario
    )

# ==================== MENÚ CAMAS ====================
@app.route('/configuracion/menu_camas')
def menu_camas():
    if 'user_id' not in session:
        flash('Debes iniciar sesión', 'error')
        return redirect(url_for('login'))
    db = get_db_connection()
    camas = list(db['camas'].find().sort("numero", 1))
    return render_template(
        'configuracion/camas/menu_camas.html',
        camas=camas
    )

# ==================== ALTA DE CAMAS ====================
@app.route('/configuracion/alta_camas', methods=['GET', 'POST'])
def alta_camas():
    if 'user_id' not in session:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        numero = request.form['numero']
        area = request.form['area']
        tipo_habitacion = request.form.get('tipo_habitacion')
        piso = request.form.get('piso')
        seccion = request.form.get('seccion')
        ocupada = int(request.form.get('ocupada', 0)) # 0 o 1
        try:
            db = get_db_connection()
            camas_coll = db['camas']
            # Validar duplicado
            if camas_coll.find_one({"numero": numero}):
                flash('Ya existe una cama con ese número.', 'warning')
                return redirect(url_for('alta_camas'))
            # Insertar todos los campos
            id_cama = get_next_sequence('camas_id_cama')
            camas_coll.insert_one({
                "id_cama": id_cama,
                "numero": numero,
                "area": area,
                "tipo_habitacion": tipo_habitacion,
                "piso": piso,
                "seccion": seccion,
                "ocupada": ocupada
            })
            flash('Cama registrada correctamente', 'success')
            return redirect(url_for('menu_camas'))
        except Exception as e:
            flash(f'Error al registrar cama: {e}', 'error')
    return render_template('configuracion/camas/alta_camas.html')

# ==================== EDITAR CAMA ====================
@app.route('/configuracion/editar_cama/<int:id>', methods=['GET', 'POST'])
def editar_cama(id):
    if 'user_id' not in session:
        flash('Debes iniciar sesión', 'error')
        return redirect(url_for('login'))
    db = get_db_connection()
    camas_coll = db['camas']
    if request.method == 'POST':
        estatus = request.form['estatus']
        area = request.form['area']
        tipo_habitacion = request.form['tipo_habitacion']
        piso = request.form.get('piso')
        seccion = request.form.get('seccion')
        ocupada = int(request.form.get('ocupada', 0))
        try:
            camas_coll.update_one({"id_cama": id}, {"$set": {
                "estatus": estatus,
                "area": area,
                "tipo_habitacion": tipo_habitacion,
                "piso": piso,
                "seccion": seccion,
                "ocupada": ocupada
            }})
            flash('Cama actualizada correctamente', 'success')
            return redirect(url_for('menu_camas'))
        except Exception as e:
            flash(f'Error al actualizar cama: {e}', 'error')
    # GET → mostrar datos actuales
    cama = camas_coll.find_one({"id_cama": id})
    if not cama:
        flash('Cama no encontrada', 'error')
        return redirect(url_for('menu_camas'))
    return render_template('configuracion/camas/editar_cama.html', cama=cama)

# ==================== ELIMINAR CAMA ====================
@app.route('/configuracion/eliminar_cama/<int:id>', methods=['POST'])
def eliminar_cama(id):
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "No autorizado"}), 403
    try:
        db = get_db_connection()
        db['camas'].delete_one({"id_cama": id})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ====================================================================================
# ============================ PERSONAL ====================================
# ====================================================================================
@app.route('/configuracion/personal')
def alta_usuarios():
    db = get_db_connection()
    personal = list(db['users'].find({}, {"id": 1, "username": 1, "role": 1}).sort("id", -1))
    roles = ['admin', 'medico', 'enfermero', 'administrativo']
    return render_template(
        'configuracion/personal/alta_usuario.html',
        personal=personal,
        roles=roles
    )

# ====================================================================================
# ============================ INSERTAR USUARIO ===============================
# ====================================================================================
@app.route('/configuracion/personal/insertar', methods=['POST'])
def insertar_usuario():
    db = get_db_connection()
    users_coll = db['users']

    try:
        username = request.form['username'].strip()
        password = request.form['password']
        role = request.form['role']

        # Validar usuario duplicado
        if users_coll.find_one({"username": username}):
            flash('El usuario ya existe', 'danger')
            return redirect(url_for('alta_usuarios'))

        # Hashear contraseña (GUARDAR COMO BYTES)
        pw_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        )

        # Insertar usuario
        users_coll.insert_one({
            "username": username,
            "password": pw_hash,   # bytes
            "role": role
        })

        # Log global
        registrar_log_global(
            f"Creó un nuevo usuario: {username}"
        )

        flash('Usuario creado correctamente', 'success')
        return redirect(url_for('alta_usuarios'))

    except Exception as e:
        flash(f'Error al crear usuario: {e}', 'danger')
        return redirect(url_for('alta_usuarios'))
# ====================================================================================
# ============================ EDITAR USUARIO ===============================
# ====================================================================================
@app.route('/configuracion/personal/editar/<int:user_id>', methods=['GET', 'POST'])
def editar_usuario(user_id):
    db = get_db_connection()
    users_coll = db['users']
    usuario = users_coll.find_one({"id": user_id}, {"id": 1, "username": 1, "role": 1})
    if not usuario:
        flash('Usuario no encontrado', 'danger')
        return redirect(url_for('alta_usuarios'))
    roles = ['admin', 'medico', 'enfermero', 'administrativo']
    if request.method == 'POST':
        try:
            users_coll.update_one({"id": user_id}, {"$set": {
                "username": request.form['username'],
                "role": request.form['role']
            }})
            flash('Usuario actualizado correctamente', 'success')
            return redirect(url_for('alta_usuarios'))
        except Exception as e:
            flash(f'Error al actualizar usuario: {e}', 'danger')
            return redirect(url_for('alta_usuarios'))
    return render_template(
        'configuracion/personal/editar_usuario.html',
        usuario=usuario,
        roles=roles
    )

# ====================================================================================
# ============================ MOSTRAR USUARIO ===============================
# ====================================================================================
@app.route('/configuracion/personal/mostrar/<int:user_id>')
def mostrar_usuario(user_id):
    db = get_db_connection()
    usuario = db['users'].find_one({"id": user_id}, {"username": 1, "role": 1})
    if not usuario:
        flash('Usuario no encontrado', 'danger')
        return redirect(url_for('alta_usuarios'))
    return render_template(
        'configuracion/personal/mostrar_usuario.html',
        usuario=usuario
    )

@app.route('/configuracion/diagnostico')
def listar_diagnosticos():
    db = get_db_connection()
    diagnosticos = list(db['cat_diag'].find({}, {"id_diag": 1, "diag": 1, "id_cie10": 1}).sort("id_diag", -1))
    return render_template(
        'configuracion/diagnostico/cat_diagnostico.html',
        diagnosticos=diagnosticos
    )

# ============================ INSERTAR DIAGNÓSTICO ============================
@app.route('/configuracion/diagnostico/insertar', methods=['POST'])
def insertar_diagnostico():
    diag = request.form.get('diag')
    id_cie10 = request.form.get('id_cie10')
    if diag and id_cie10:
        db = get_db_connection()
        cat_diag_coll = db['cat_diag']
        id_diag = get_next_sequence('cat_diag_id_diag')
        cat_diag_coll.insert_one({
            "id_diag": id_diag,
            "diag": diag,
            "id_cie10": id_cie10
        })
        flash('Diagnóstico registrado correctamente', 'success')
    else:
        flash('Todos los campos son obligatorios', 'danger')
    return redirect(url_for('listar_diagnosticos'))

# ============================ EDITAR DIAGNÓSTICO ============================
@app.route('/configuracion/diagnostico/editar/<int:id>', methods=['GET', 'POST'])
def editar_diagnostico(id):
    db = get_db_connection()
    cat_diag_coll = db['cat_diag']
    if request.method == 'POST':
        diag = request.form['diag']
        id_cie10 = request.form['id_cie10']
        cat_diag_coll.update_one({"id_diag": id}, {"$set": {
            "diag": diag,
            "id_cie10": id_cie10
        }})
        flash('Diagnóstico actualizado correctamente', 'info')
        return redirect(url_for('listar_diagnosticos'))
    diagnostico = cat_diag_coll.find_one({"id_diag": id})
    return render_template(
        'configuracion/diagnostico/edit_diagnostico.html',
        diagnostico=diagnostico
    )

# ============================ ELIMINAR DIAGNÓSTICO ============================
@app.route('/configuracion/diagnostico/eliminar/<int:id>')
def eliminar_diagnostico(id):
    db = get_db_connection()
    db['cat_diag'].delete_one({"id_diag": id})
    flash('Diagnóstico eliminado correctamente', 'warning')
    return redirect(url_for('listar_diagnosticos'))

# ====================================================================================
# ============================ SERVICIOS ====================================
# ====================================================================================
@app.route('/configuracion/servicios')
def cat_servicios():
    db = get_db_connection()
    pipeline = [
        {"$lookup": {"from": "service_type", "localField": "tipo", "foreignField": "ser_type_id", "as": "t"}},
        {"$unwind": {"path": "$t", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "serv_cve": 1,
            "serv_desc": 1,
            "serv_costo": 1,
            "serv_costo2": 1,
            "serv_costo3": 1,
            "serv_costo4": 1,
            "serv_costo5": 1,
            "serv_costo6": 1,
            "serv_costo7": 1,
            "serv_costo8": 1,
            "serv_umed": 1,
            "serv_activo": 1,
            "tipo": 1,
            "proveedor": 1,
            "grupo": 1,
            "codigo_sat": 1,
            "c_cveuni": 1,
            "c_nombre": 1,
            "iva": 1,
            "tip_insumo": "$t.ser_type_desc"
        }},
        {"$sort": {"id_serv": -1}}
    ]
    servicios = list(db['cat_servicios'].aggregate(pipeline))
    tipos = list(db['service_type'].find())
    proveedores = list(db['proveedores'].find())
    return render_template(
        'configuracion/servicios/cat_servicios.html',
        servicios=servicios,
        tipos=tipos,
        proveedores=proveedores
    )

# ==================== EDITAR SERVICIOS ====================
@app.route('/configuracion/servicios/editar/<int:id>', methods=['GET', 'POST'])
def editar_servicio(id):
    db = get_db_connection()
    cat_servicios_coll = db['cat_servicios']
    # ===================== POST (GUARDAR CAMBIOS) =====================
    if request.method == 'POST':
        data = request.form
        cat_servicios_coll.update_one({"id_serv": id}, {"$set": {
            "serv_cve": data['clave'],
            "serv_desc": data['descripcion'],
            "serv_costo": data['costo'],
            "serv_costo2": data.get('costo2', 0),
            "serv_costo3": data.get('costo3', 0),
            "serv_costo4": data.get('costo4', 0),
            "serv_costo5": data.get('costo5', 0),
            "serv_costo6": data.get('costo6', 0),
            "serv_costo7": data.get('costo7', 0),
            "serv_costo8": data.get('costo8', 0),
            "serv_umed": data['med'],
            "tipo": data['tipo'],
            "proveedor": data['proveedor'],
            "grupo": data['grupo'],
            "codigo_sat": data['codigo_sat'],
            "c_cveuni": data['c_cveuni'],
            "c_nombre": 'SERVICIO',
            "iva": 0.16
        }})
        flash('Servicio actualizado correctamente', 'success')
        return redirect(url_for('cat_servicios'))
    # ===================== GET (CARGAR FORM) =====================
    pipeline = [
        {"$match": {"id_serv": id}},
        {"$lookup": {"from": "service_type", "localField": "tipo", "foreignField": "ser_type_id", "as": "t"}},
        {"$unwind": {"path": "$t", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "proveedores", "localField": "proveedor", "foreignField": "id_prov", "as": "p"}},
        {"$unwind": {"path": "$p", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "serv_cve": 1,
            "serv_desc": 1,
            "serv_costo": 1,
            "serv_costo2": 1,
            "serv_costo3": 1,
            "serv_costo4": 1,
            "serv_costo5": 1,
            "serv_costo6": 1,
            "serv_costo7": 1,
            "serv_costo8": 1,
            "serv_umed": 1,
            "serv_activo": 1,
            "tipo": 1,
            "proveedor": 1,
            "grupo": 1,
            "codigo_sat": 1,
            "c_cveuni": 1,
            "c_nombre": 1,
            "iva": 1,
            "ser_type_desc": "$t.ser_type_desc",
            "nom_prov": "$p.nom_prov"
        }}
    ]
    servicio = list(cat_servicios_coll.aggregate(pipeline))[0] if list(cat_servicios_coll.aggregate(pipeline)) else None
    tipos = list(db['service_type'].find())
    proveedores = list(db['proveedores'].find())
    if not servicio:
        flash('Servicio no encontrado', 'danger')
        return redirect(url_for('cat_servicios'))
    return render_template(
        'configuracion/servicios/edit_servicios.html',
        servicio=servicio,
        tipos=tipos,
        proveedores=proveedores
    )

# ==================== INSERTAR SERVICIO ====================
@app.route('/insertar_servicio', methods=['POST'])
def insertar_servicio():
    if request.method == 'POST':
        data = request.form
        # ──────────────────────────────────────────────────────────────
        # 1. Extraer todos los campos del formulario
        # ──────────────────────────────────────────────────────────────
        serv_cve = data.get('serv_cve')
        serv_desc = data.get('serv_desc')
        serv_costo = data.get('serv_costo')
        serv_costo2 = data.get('serv_costo2')
        serv_costo3 = data.get('serv_costo3')
        serv_costo4 = data.get('serv_costo4')
        serv_costo5 = data.get('serv_costo5')
        serv_costo6 = data.get('serv_costo6')
        serv_costo7 = data.get('serv_costo7')
        serv_costo8 = data.get('serv_costo8')
        serv_umed = data.get('serv_umed')
        serv_tipo = data.get('serv_tipo') # ← este es el ID del tipo
        proveedor = data.get('proveedor')
        grupo = data.get('grupo')
        codigo_sat = data.get('codigo_sat')
        c_cveuni = data.get('c_cveuni')
        c_nombre = data.get('c_nombre')
        tasa_iva = data.get('iva') # cambia el nombre si tu input se llama diferente
        db = get_db_connection()
        # ──────────────────────────────────────────────────────────────
        # 2. Obtener la descripción del tipo de servicio
        # ──────────────────────────────────────────────────────────────
        tipo = db['service_type'].find_one({"ser_type_id": int(serv_tipo)}, {"ser_type_desc": 1})
        tip_insumo = tipo['ser_type_desc'] if tipo else ''
        # ──────────────────────────────────────────────────────────────
        # 3. Insertar el servicio
        # ──────────────────────────────────────────────────────────────
        id_serv = get_next_sequence('cat_servicios_id_serv')
        db['cat_servicios'].insert_one({
            "id_serv": id_serv,
            "serv_cve": serv_cve,
            "serv_desc": serv_desc,
            "serv_costo": serv_costo,
            "serv_costo2": serv_costo2,
            "serv_costo3": serv_costo3,
            "serv_costo4": serv_costo4,
            "serv_costo5": serv_costo5,
            "serv_costo6": serv_costo6,
            "serv_costo7": serv_costo7,
            "serv_costo8": serv_costo8,
            "serv_umed": serv_umed,
            "serv_activo": 'SI',
            "tipo": serv_tipo,
            "tip_insumo": tip_insumo,
            "proveedor": proveedor,
            "grupo": grupo,
            "codigo_sat": codigo_sat,
            "c_cveuni": c_cveuni,
            "c_nombre": c_nombre,
            "iva": tasa_iva
        })
        flash('Servicio registrado correctamente', 'success')
        return redirect(url_for('cat_servicios'))
    # Por si acaso llega por GET (no debería)
    flash('Método no permitido', 'danger')
    return redirect(url_for('cat_servicios'))

# ==================== GESTIÓN DE CUENTAS (ACTIVOS) ====================
@app.route('/admin/cuenta_pacientes')
def cuenta_pacientes():
    if 'user_id' not in session:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    db = get_db_connection()
    # 1) Intento con anticipos (si tienes tabla depositos_atencion con id_atencion,monto)
    # Si no existe, cae al query sin anticipos y pone 0.
    pipeline_con_anticipos = [
        {"$match": {"status": "ABIERTA"}},
        {"$lookup": {"from": "pacientes", "localField": "Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$lookup": {"from": "camas", "localField": "id_cama", "foreignField": "id_cama", "as": "cama"}},
        {"$unwind": {"path": "$cama", "preserveNullAndEmptyArrays": True}},
        {"$lookup": {"from": "atencion_medicos", "localField": "id_atencion", "foreignField": "id_atencion", "as": "medicos"}},
        {"$lookup": {"from": "users", "localField": "medicos.id_medico", "foreignField": "id", "as": "users"}},
        {"$addFields": {
            "medico": {"$arrayElemAt": ["$users.username", 0]},
            "subtotal": {"$ifNull": [{"$sum": "$cuenta_paciente.subtotal"}, 0]},
            "anticipos": {"$ifNull": [{"$sum": "$depositos_atencion.monto"}, 0]}
        }},
        {"$project": {
            "id_atencion": 1,
            "Id_exp": 1,
            "especialidad": 1,
            "fecha_ing": 1,
            "area": 1,
            "num_cama": {"$ifNull": ["$cama.numero", 'Sin cama']},
            "paciente": {"$concat": ["$paciente.papell", " ", "$paciente.sapell", " ", "$paciente.nom_pac"]},
            "medico": 1,
            "subtotal": 1,
            "anticipos": 1
        }},
        {"$sort": {"fecha_ing": -1}}
    ]
    rows = list(db['atencion'].aggregate(pipeline_con_anticipos))
    # 2) Cálculos (IVA 16%)
    for r in rows:
        sub = Decimal(str(r.get('subtotal', 0) or 0))
        iva = (sub * Decimal('0.16'))
        total = sub + iva
        r['iva'] = iva
        r['total'] = total
        r['anticipos'] = Decimal(str(r.get('anticipos', 0) or 0))
        # Si médico es None
        if not r.get('medico'):
            r['medico'] = 'Sin médico'
    return render_template(
        'administrativo/gestion_cuentas/cuenta_pacientes.html',
        cuentas=rows
    )

# (Opcional) PDF simple de cuenta: si no tienes aún tu ruta PDF, aquí dejo un placeholder.
# Puedes cambiar la lógica y el formato a tu gusto.
@app.route('/admin/cuenta_pdf/<int:id_atencion>')
def cuenta_pdf(id_atencion):
    if 'user_id' not in session:
        flash('Sesión no válida.', 'error')
        return redirect(url_for('login'))
    db = get_db_connection()
    pipeline = [
        {"$match": {"id_atencion": id_atencion}},
        {"$lookup": {"from": "pacientes", "localField": "Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$project": {
            "id_atencion": 1,
            "Id_exp": 1,
            "fecha_ing": 1,
            "paciente": {"$concat": ["$paciente.papell", " ", "$paciente.sapell", " ", "$paciente.nom_pac"]}
        }}
    ]
    header = list(db['atencion'].aggregate(pipeline))[0] if list(db['atencion'].aggregate(pipeline)) else None
    items = list(db['cuenta_paciente'].find({"id_atencion": id_atencion}, {"fecha": 1, "descripcion": 1, "cantidad": 1, "precio": 1, "subtotal": 1}).sort("fecha", 1))
    total_pipeline = [
        {"$match": {"id_atencion": id_atencion}},
        {"$group": {"_id": None, "subtotal": {"$sum": "$subtotal"}}}
    ]
    sub_result = list(db['cuenta_paciente'].aggregate(total_pipeline))
    sub = Decimal(str(sub_result[0]['subtotal'])) if sub_result else Decimal('0')
    iva = sub * Decimal('0.16')
    total = sub + iva
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "CUENTA DEL PACIENTE", ln=1, align="C")
    pdf.ln(3)
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, f"Atencion: {header['id_atencion']} Expediente: {header['Id_exp']}", ln=1)
    pdf.cell(0, 6, f"Paciente: {header['paciente']}", ln=1)
    pdf.cell(0, 6, f"Fecha ingreso: {header['fecha_ing'].strftime('%Y-%m-%d')}", ln=1)
    pdf.ln(4)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(25, 7, "Fecha", 1)
    pdf.cell(90, 7, "Descripcion", 1)
    pdf.cell(15, 7, "Cant", 1, align="C")
    pdf.cell(25, 7, "Subtotal", 1, align="R")
    pdf.ln()
    pdf.set_font("Arial", "", 8)
    for it in items:
        pdf.cell(25, 7, it['fecha'].strftime('%Y-%m-%d'), 1)
        pdf.cell(90, 7, str(it['descripcion'])[:45], 1)
        pdf.cell(15, 7, str(it['cantidad']), 1, align="C")
        pdf.cell(25, 7, f"${float(it['subtotal']):.2f}", 1, align="R")
        pdf.ln()
    pdf.ln(3)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 7, f"SUBTOTAL: ${float(sub):.2f}", ln=1, align="R")
    pdf.cell(0, 7, f"IVA (16%): ${float(iva):.2f}", ln=1, align="R")
    pdf.cell(0, 7, f"TOTAL: ${float(total):.2f}", ln=1, align="R")
    response = make_response(pdf.output(dest='S').encode('latin-1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=cuenta_paciente.pdf'
    return response

# ==================== CENSO ====================
@app.route('/admin/censo')
def censo():
    if 'user_id' not in session:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    db = get_db_connection()
    def obtener_camas_por_area(area_camas, area_atencion=None):
        """
        area_camas: valor en tabla camas.area (Urgencias/Hospitalizado)
        area_atencion: valor en tabla atencion.area (Ambulatorio/Urgencias/Hospitalizado)
        """
        filas = []
        # 1) Ambulatorio (sin cama física)
        if area_atencion == 'Ambulatorio':
            pipeline = [
                {"$match": {"area": "Ambulatorio", "status": "ABIERTA"}},
                {"$lookup": {"from": "pacientes", "localField": "Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
                {"$unwind": "$paciente"},
                {"$lookup": {"from": "atencion_medicos", "localField": "id_atencion", "foreignField": "id_atencion", "as": "medicos"}},
                {"$lookup": {"from": "users", "localField": "medicos.id_medico", "foreignField": "id", "as": "users"}},
                {"$project": {
                    "id_atencion": 1,
                    "num_cama": {"$concat": ["Consulta ", {"$toString": "$id_atencion"}]},
                    "fecha_ing": 1,
                    "motivo_ingreso": "$motivo",
                    "status": 1,
                    "alergias": 1,
                    "Id_exp": "$paciente.Id_exp",
                    "fecnac": "$paciente.fecnac",
                    "papell": "$paciente.papell",
                    "sapell": "$paciente.sapell",
                    "nom_pac": "$paciente.nom_pac",
                    "medico_tratante": {"$arrayElemAt": ["$users.username", 0]}
                }},
                {"$sort": {"fecha_ing": -1}}
            ]
            filas = list(db['atencion'].aggregate(pipeline))
            for f in filas:
                f['estatus'] = 'OCUPADA'
                f['fecha'] = f.get('fecha_ing')
                f['motivo_recepcion'] = f.get('motivo_ingreso', '') or ''
                f['alta_med'] = 'NO' # no existe en tu BD
                f['paciente_nombre'] = f"{f.get('papell','')} {f.get('sapell','')} {f.get('nom_pac','')}".strip()
                f['edad_txt'] = calcular_edad(f['fecnac']) if f.get('fecnac') else ''
                f['medico_txt'] = f.get('medico_tratante') or ''
            return filas
        # 2) Con cama física (Urgencias/Hospitalizado)
        pipeline = [
            {"$match": {"area": area_camas}},
            {"$lookup": {"from": "atencion", "localField": "id_cama", "foreignField": "id_cama", "as": "atencion"}},
            {"$unwind": {"path": "$atencion", "preserveNullAndEmptyArrays": True}},
            {"$match": {"$or": [{"atencion.status": "ABIERTA"}, {"atencion": {"$exists": False}}]}},
            {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
            {"$unwind": {"path": "$paciente", "preserveNullAndEmptyArrays": True}},
            {"$lookup": {"from": "atencion_medicos", "localField": "atencion.id_atencion", "foreignField": "id_atencion", "as": "medicos"}},
            {"$lookup": {"from": "users", "localField": "medicos.id_medico", "foreignField": "id", "as": "users"}},
            {"$project": {
                "id_cama": 1,
                "numero": 1,
                "ocupada": 1,
                "area_cama": "$area",
                "id_atencion": "$atencion.id_atencion",
                "fecha_ing": "$atencion.fecha_ing",
                "motivo_ing": "$atencion.motivo",
                "status": "$atencion.status",
                "Id_exp": "$paciente.Id_exp",
                "fecnac": "$paciente.fecnac",
                "papell": "$paciente.papell",
                "sapell": "$paciente.sapell",
                "nom_pac": "$paciente.nom_pac",
                "medico_tratante": {"$arrayElemAt": ["$users.username", 0]}
            }},
            {"$sort": {"numero": 1}}
        ]
        filas = list(db['camas'].aggregate(pipeline))
        for f in filas:
            if not f.get('id_atencion'):
                # Cama libre (o mantenimiento si ocupada=1 sin atención abierta)
                f['fecha'] = None
                f['motivo_recepcion'] = ''
                f['Id_exp'] = ''
                f['paciente_nombre'] = ''
                f['edad_txt'] = ''
                f['medico_txt'] = ''
                f['alta_med'] = ''
                if int(f.get('ocupada') or 0) == 1:
                    f['estatus'] = 'MANTENIMIENTO'
                else:
                    f['estatus'] = 'LIBRE'
            else:
                # Cama ocupada con atención abierta
                f['fecha'] = f.get('fecha_ing')
                f['motivo_recepcion'] = f.get('motivo_ing', '') or ''
                f['paciente_nombre'] = f"{f.get('papell','')} {f.get('sapell','')} {f.get('nom_pac','')}".strip()
                f['edad_txt'] = calcular_edad(f['fecnac']) if f.get('fecnac') else ''
                f['medico_txt'] = f.get('medico_tratante') or ''
                f['alta_med'] = 'NO'
                f['estatus'] = 'OCUPADA'
        return filas
    # Secciones
    consulta = obtener_camas_por_area(area_camas='Urgencias', area_atencion='Ambulatorio') # CONSULTA
    preparacion = obtener_camas_por_area(area_camas='Urgencias') # PREPARACIÓN
    recuperacion = obtener_camas_por_area(area_camas='Hospitalizado') # RECUPERACIÓN
    return render_template(
        'administrativo/censo/censo.html',
        consulta=consulta,
        preparacion=preparacion,
        recuperacion=recuperacion
    )

@app.route('/admin/censo/imprimir')
def imprimir_censo():
    if 'user_id' not in session:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    db = get_db_connection()
    # ========= HELPERS =========
    def fmt_fecha(x):
        if not x:
            return ""
        try:
            return x.strftime("%d/%m/%Y")
        except Exception:
            return ""
    def calc_estancia(fecha_ing):
        if not fecha_ing:
            return ""
        dias = (datetime.now() - fecha_ing).days
        return f"{dias}d" if dias >= 0 else ""
    def obtener_area_con_camas(area_camas):
        pipeline = [
            {"$match": {"area": area_camas}},
            {"$lookup": {"from": "atencion", "localField": "id_cama", "foreignField": "id_cama", "as": "atencion"}},
            {"$unwind": {"path": "$atencion", "preserveNullAndEmptyArrays": True}},
            {"$match": {"$or": [{"atencion.status": "ABIERTA"}, {"atencion": {"$exists": False}}]}},
            {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
            {"$unwind": {"path": "$paciente", "preserveNullAndEmptyArrays": True}},
            {"$lookup": {"from": "atencion_medicos", "localField": "atencion.id_atencion", "foreignField": "id_atencion", "as": "medicos"}},
            {"$lookup": {"from": "users", "localField": "medicos.id_medico", "foreignField": "id", "as": "users"}},
            {"$project": {
                "num_cama": "$numero",
                "ocupada": 1,
                "fecha_ing": "$atencion.fecha_ing",
                "motivo": "$atencion.motivo",
                "alergias": "$atencion.alergias",
                "Id_exp": "$paciente.Id_exp",
                "fecnac": "$paciente.fecnac",
                "papell": "$paciente.papell",
                "sapell": "$paciente.sapell",
                "nom_pac": "$paciente.nom_pac",
                "medico_tratante": {"$arrayElemAt": ["$users.username", 0]}
            }},
            {"$sort": {"numero": 1}}
        ]
        rows = list(db['camas'].aggregate(pipeline))
        # estatus: OCUPADA / LIBRE / MANTENIMIENTO (ocupada=1 pero sin atención)
        for r in rows:
            if not r.get("id_atencion"):
                r["estatus"] = "MANTENIMIENTO" if int(r.get("ocupada") or 0) == 1 else "LIBRE"
            else:
                r["estatus"] = "OCUPADA"
        return rows
    def obtener_consulta():
        pipeline = [
            {"$match": {"area": 'Ambulatorio', "status": "ABIERTA"}},
            {"$lookup": {"from": "pacientes", "localField": "Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
            {"$unwind": "$paciente"},
            {"$lookup": {"from": "atencion_medicos", "localField": "id_atencion", "foreignField": "id_atencion", "as": "medicos"}},
            {"$lookup": {"from": "users", "localField": "medicos.id_medico", "foreignField": "id", "as": "users"}},
            {"$project": {
                "id_atencion": 1,
                "fecha_ing": 1,
                "motivo": 1,
                "alergias": 1,
                "Id_exp": "$paciente.Id_exp",
                "fecnac": "$paciente.fecnac",
                "papell": "$paciente.papell",
                "sapell": "$paciente.sapell",
                "nom_pac": "$paciente.nom_pac",
                "medico_tratante": {"$arrayElemAt": ["$users.username", 0]}
            }},
            {"$sort": {"fecha_ing": -1}}
        ]
        rows = list(db['atencion'].aggregate(pipeline))
        for r in rows:
            r["num_cama"] = f"Consulta {r['id_atencion']}"
            r["estatus"] = "OCUPADA"
        return rows
    hosp = obtener_area_con_camas("Hospitalizado")
    urg = obtener_area_con_camas("Urgencias")
    cons = obtener_consulta()
    # ========= PDF =========
    class PDF(FPDF):
        def header(self):
            self.set_text_color(43, 45, 127)
            self.set_font("Arial", "B", 12)
            self.cell(0, 8, "CENSO DIARIO DE PACIENTES", 0, 1, "C")
            self.set_font("Arial", "", 9)
            self.cell(0, 6, "FECHA: " + datetime.now().strftime("%d/%m/%Y %I:%M %p"), 0, 1, "R")
            self.ln(2)
        def footer(self):
            self.set_y(-15)
            self.set_font("Arial", "B", 8)
            self.cell(0, 8, f"Página {self.page_no()}/{{nb}}", 0, 0, "C")
            self.cell(0, 8, "CMSI-013", 0, 0, "R")
    pdf = PDF("L", "mm", "legal")
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_margins(10, 10, 10)
    pdf.set_auto_page_break(True, 20)
    pdf.set_draw_color(43, 45, 180)
    pdf.set_text_color(43, 45, 127)
    def encabezado_tabla(titulo):
        pdf.set_font("Arial", "B", 9)
        pdf.cell(0, 6, titulo, 1, 1, "C")
        pdf.set_font("Arial", "B", 6)
        pdf.cell(12, 6, "#", 1, 0, "C")
        pdf.cell(18, 6, "F.ING", 1, 0, "C")
        pdf.cell(78, 6, "PACIENTE", 1, 0, "C")
        pdf.cell(16, 6, "F.NAC", 1, 0, "C")
        pdf.cell(10, 6, "EDAD", 1, 0, "C")
        pdf.cell(14, 6, "FOLIO", 1, 0, "C")
        pdf.cell(12, 6, "DEIH", 1, 0, "C")
        pdf.cell(92, 6, "DIAGNOSTICO", 1, 0, "C")
        pdf.cell(50, 6, "ALERGIAS", 1, 0, "C")
        pdf.cell(38, 6, "MEDICO", 1, 1, "C")
    def fila_vacia(num):
        pdf.set_font("Arial", "", 6)
        pdf.cell(12, 6, str(num), 1, 0, "C")
        pdf.cell(18, 6, "", 1, 0)
        pdf.cell(78, 6, "", 1, 0)
        pdf.cell(16, 6, "", 1, 0)
        pdf.cell(10, 6, "", 1, 0)
        pdf.cell(14, 6, "", 1, 0)
        pdf.cell(12, 6, "", 1, 0)
        pdf.cell(92, 6, "", 1, 0)
        pdf.cell(50, 6, "", 1, 0)
        pdf.cell(38, 6, "", 1, 1)
    def fila_mantenimiento(num):
        pdf.set_font("Arial", "B", 6)
        pdf.cell(12, 6, str(num), 1, 0, "C")
        pdf.set_font("Arial", "", 6)
        pdf.cell(18, 6, "", 1, 0)
        pdf.cell(78, 6, "", 1, 0)
        pdf.cell(16, 6, "", 1, 0)
        pdf.cell(10, 6, "", 1, 0)
        pdf.cell(14, 6, "", 1, 0)
        pdf.cell(12, 6, "", 1, 0)
        pdf.cell(92, 6, "", 1, 0)
        pdf.cell(50, 6, "", 1, 0)
        pdf.set_text_color(255, 0, 2)
        pdf.set_font("Arial", "B", 6)
        pdf.cell(38, 6, "NO DISPONIBLE", 1, 1, "C")
        pdf.set_text_color(43, 45, 127)
    def fila(row):
        num = row.get("num_cama", "")
        fecha_ing = fmt_fecha(row.get("fecha_ing"))
        fecnac = fmt_fecha(row.get("fecnac"))
        edad = ""
        if row.get("fecnac"):
            try:
                edad = str(calcular_edad(row["fecnac"]))
            except Exception:
                edad = ""
        folio = str(row.get("Id_exp") or "")
        deih = calc_estancia(row.get("fecha_ing"))
        paciente = f"{row.get('papell','')} {row.get('sapell','')} {row.get('nom_pac','')}".strip()
        diag = str(row.get("motivo") or "")
        alergias = str(row.get("alergias") or "")
        medico = str(row.get("medico_tratante") or "")
        pdf.set_font("Arial", "", 6)
        pdf.cell(12, 6, str(num), 1, 0, "C")
        pdf.cell(18, 6, fecha_ing, 1, 0)
        pdf.cell(78, 6, paciente[:55], 1, 0)
        pdf.cell(16, 6, fecnac, 1, 0, "C")
        pdf.cell(10, 6, edad, 1, 0, "C")
        pdf.cell(14, 6, folio, 1, 0, "C")
        pdf.cell(12, 6, deih, 1, 0, "C")
        pdf.cell(92, 6, diag[:70], 1, 0)
        pdf.set_text_color(255, 0, 2)
        pdf.set_font("Arial", "B", 6)
        pdf.cell(50, 6, alergias[:35], 1, 0)
        pdf.set_text_color(43, 45, 127)
        pdf.set_font("Arial", "", 6)
        pdf.cell(38, 6, medico[:25], 1, 1)
    # ========= SECCIONES =========
    encabezado_tabla("HOSPITALIZACIÓN")
    for r in hosp:
        if r["estatus"] == "MANTENIMIENTO":
            fila_mantenimiento(r.get("num_cama"))
        elif r["estatus"] == "LIBRE":
            fila_vacia(r.get("num_cama"))
        else:
            fila(r)
    pdf.ln(3)
    encabezado_tabla("URGENCIAS")
    for r in urg:
        if r["estatus"] == "MANTENIMIENTO":
            fila_mantenimiento(r.get("num_cama"))
        elif r["estatus"] == "LIBRE":
            fila_vacia(r.get("num_cama"))
        else:
            fila(r)
    pdf.ln(3)
    encabezado_tabla("CONSULTA")
    for r in cons:
        fila(r)
    # ========= RESPUESTA =========
    pdf_bytes = pdf.output(dest="S").encode("latin-1")
    response = make_response(pdf_bytes)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "inline; filename=censo_diario.pdf"
    return response

# ====================================================================================
# ============================ RENDIMIENTO ====================================
# ====================================================================================
@app.route('/api/logs_recientes')
def logs_recientes():
    db = get_db_connection()
    logs = list(db['users'].find({}, {"id": 1, "username": 1, "role": 1, "created_at": 1}).sort("id", -1))
    return jsonify(logs)

# ====================================================================================
@app.route('/rendimiento')
def rendimiento():
    import psutil
    # ----- Sistema -----
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    disco = psutil.disk_usage('/').percent
    # ----- Usuarios -----
    db = get_db_connection()
    usuarios = list(db['users'].find({}, {"id": 1, "username": 1, "role": 1, "created_at": 1}).sort("id", -1))
    # ----- Logs recientes -----
    logs = list(db['logs'].find({}, {"usuario": 1, "accion": 1, "fecha": 1}).sort("fecha", -1).limit(10))
    return render_template(
        'rendimiento/rendimiento.html',
        cpu=cpu,
        ram=ram,
        disco=disco,
        usuarios=usuarios,
        logs=logs
    )

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)