from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from templates.administrativo.pacientes.doc_pacientes import pdf
from templates.medico.impresiones import pdf_med
import pymysql
import bcrypt
from flask import request, make_response
from fpdf import FPDF
from decimal import Decimal
from datetime import datetime, timedelta
from datetime import datetime, date
import pymysql.cursors
from estudios import estudios_bp


app = Flask(__name__)
app.register_blueprint(estudios_bp, url_prefix='/estudios')
app.register_blueprint(pdf)
app.register_blueprint(pdf_med)
app.secret_key = 'tu_clave_secreta_aqui'  # Cambia esto por algo seguro

# Configuración de MySQL
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASS = ''
DB_NAME = 'ineo_db'


def get_db_connection():
    return pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, db=DB_NAME,
                           cursorclass=pymysql.cursors.DictCursor)

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
# ============================       INICIO       ====================================
# ====================================================================================


@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and bcrypt.checkpw(password, user['password'].encode('utf-8')):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Login exitoso!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos.', 'error')

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    role = session['role']
    menu_options = []

    # Contar solicitudes pendientes
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    
    # Contar solicitudes pendientes de laboratorio (id_examen únicos)
    cursor.execute("""
        SELECT COUNT(DISTINCT id_examen) as count 
        FROM examenes_laboratorio 
        WHERE LOWER(estado) = 'pendiente'
    """)
    lab_pendientes = cursor.fetchone()['count']
    
    # Contar solicitudes pendientes de gabinete (id_examen únicos)
    cursor.execute("""
        SELECT COUNT(DISTINCT id_examen) as count 
        FROM examenes_gabinete_det 
        WHERE UPPER(estado) = 'PENDIENTE'
    """)
    gab_pendientes = cursor.fetchone()['count']
    
    total_pendientes = lab_pendientes + gab_pendientes
    cursor.close()
    conn.close()

    if role == 'admin':
        menu_options = [
            {'name': 'Administrativo', 'url': url_for('administrativo')},
            {'name': 'Médico', 'url': url_for('medico')},
            {'name': 'Estudios', 'url': url_for('estudios.estudios_home')},
            {'name': 'Configuración', 'url': url_for('menu_configuracion')}
        ]

    return render_template('dashboard.html', 
                         role=role, 
                         menu_options=menu_options,
                         lab_pendientes=lab_pendientes,
                         gab_pendientes=gab_pendientes,
                         total_pendientes=total_pendientes)


# ====================================================================================
# ========================       ADMINISTRATIVO       ================================
# ====================================================================================

@app.route('/admin/administrativo')
def administrativo():
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))

    usuario = {
        'username': session['username'],
        'img_perfil': 'default_profile.jpg'  # Placeholder
    }
    img_sistema = 'logo.jpg'  # Placeholder

    return render_template('administrativo/administrativo.html', usuario=usuario, img_sistema=img_sistema)


@app.route('/admin/gestion_pacientes')
def gestion_pacientes():
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Query para hospitalizados (ajusta filtros según área)
    cursor.execute("""
                   SELECT p.Id_exp,
                          p.papell,
                          p.sapell,
                          p.nom_pac,
                          p.fecnac,
                          p.tel,
                          a.id_atencion,
                          a.area,
                          a.fecha_ing,
                          c.numero AS num_cama
                   FROM pacientes p
                            JOIN atencion a ON p.Id_exp = a.Id_exp
                            LEFT JOIN camas c ON a.id_cama = c.id_cama
                   WHERE a.area = 'Hospitalizado' AND a.status = 'ABIERTA'
                   """)
    hospitalized = cursor.fetchall()
    for p in hospitalized:
        p['edad'] = calcular_edad(p['fecnac'])

    # Queries similares para urgencias y ambulatorios
    cursor.execute("""
                   SELECT p.Id_exp,
                          p.papell,
                          p.sapell,
                          p.nom_pac,
                          p.fecnac,
                          p.tel,
                          a.id_atencion,
                          a.area,
                          a.fecha_ing,
                          c.numero AS num_cama
                   FROM pacientes p
                            JOIN atencion a ON p.Id_exp = a.Id_exp
                            LEFT JOIN camas c ON a.id_cama = c.id_cama
                   WHERE a.area = 'Urgencias' AND a.status = 'ABIERTA'
                   """)
    urgencias = cursor.fetchall()
    for p in urgencias:
        p['edad'] = calcular_edad(p['fecnac'])

    cursor.execute("""
                   SELECT p.Id_exp,
                          p.papell,
                          p.sapell,
                          p.nom_pac,
                          p.fecnac,
                          p.tel,
                          a.id_atencion,
                          a.area,
                          a.fecha_ing,
                          c.numero AS num_cama
                   FROM pacientes p
                            JOIN atencion a ON p.Id_exp = a.Id_exp
                            LEFT JOIN camas c ON a.id_cama = c.id_cama
                   WHERE a.area = 'Ambulatorio' AND a.status = 'ABIERTA'
                   """)
    ambulatorios = cursor.fetchall()
    for p in ambulatorios:
        p['edad'] = calcular_edad(p['fecnac'])

    cursor.close()
    conn.close()

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

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)  # Usa DictCursor para resultados como diccionarios

    # ================= GET =================
    cursor.execute("""
        SELECT id_cama, numero
        FROM camas
        WHERE ocupada = 0
    """)
    camas = cursor.fetchall()

    cursor.execute("""
        SELECT id, username
        FROM users
        WHERE role = 'medico'
    """)
    medicos = cursor.fetchall()

    if request.method == 'POST':
        try:
            # ---------- PACIENTE ----------
            curp = request.form['curp']
            papell = request.form['papell']
            sapell = request.form['sapell']
            nom_pac = request.form['nom_pac']
            fecnac = request.form['fecnac']
            tel = request.form['tel']
            alergias = request.form.get('alergias', '')

            # ---------- ATENCIÓN ----------
            area = request.form['area']
            id_cama = request.form.get('id_cama') or None
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
            medicos_list = [m for m in medicos_list if m]  # Filtrar no vacíos

            # ===== INSERT PACIENTE =====
            cursor.execute("""
                INSERT INTO pacientes (curp, papell, sapell, nom_pac, fecnac, tel)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (curp, papell, sapell, nom_pac, fecnac, tel))

            id_exp = cursor.lastrowid

            # ===== INSERT ATENCION =====
            cursor.execute("""
                INSERT INTO atencion (Id_exp, area, id_cama, motivo, especialidad, alergias)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (id_exp, area, id_cama, motivo, especialidad, alergias))

            id_atencion = cursor.lastrowid

            # ===== INSERT MÉDICOS =====
            for id_medico in medicos_list:
                cursor.execute("""
                    INSERT INTO atencion_medicos (id_atencion, id_medico)
                    VALUES (%s, %s)
                """, (id_atencion, id_medico))

            # ===== MARCAR CAMA OCUPADA =====
            if id_cama:
                cursor.execute("""
                    UPDATE camas
                    SET ocupada = 1
                    WHERE id_cama = %s
                """, (id_cama,))

            # ===== INSERT FAMILIAR =====
            cursor.execute("""
                INSERT INTO familiares (Id_exp, nombre, parentesco, telefono)
                VALUES (%s, %s, %s, %s)
            """, (id_exp, fam_nombre, fam_parentesco, fam_tel))

            conn.commit()
            flash('Paciente registrado correctamente.', 'success')
            return redirect(url_for('gestion_pacientes'))

        except Exception as e:
            conn.rollback()
            flash(f'Error al registrar paciente: {e}', 'error')

        finally:
            cursor.close()
            conn.close()

    return render_template('administrativo/pacientes/nuevo_paciente.html', camas=camas, medicos=medicos)


@app.route('/admin/editar_paciente/<int:id_exp>', methods=['GET', 'POST'])
def editar_paciente(id_exp):
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # ===== DATOS PARA SELECTS =====
    cursor.execute("SELECT id_cama, numero FROM camas WHERE ocupada = 0 OR id_cama = (SELECT id_cama FROM atencion WHERE Id_exp = %s)", (id_exp,))
    camas = cursor.fetchall()

    cursor.execute("SELECT id, username FROM users WHERE role = 'medico'")
    medicos = cursor.fetchall()

    # ===== GET =====
    cursor.execute("""
        SELECT p.*, a.area, a.id_cama, a.motivo, a.especialidad, a.alergias
        FROM pacientes p
        JOIN atencion a ON p.Id_exp = a.Id_exp
        WHERE p.Id_exp = %s
    """, (id_exp,))
    paciente = cursor.fetchone()

    cursor.execute("""
        SELECT id_medico
        FROM atencion_medicos
        WHERE id_atencion = (
            SELECT id_atencion FROM atencion WHERE Id_exp = %s
        )
    """, (id_exp,))
    medicos_asignados = [m['id_medico'] for m in cursor.fetchall()]

    cursor.execute("""
        SELECT * FROM familiares
        WHERE Id_exp = %s
    """, (id_exp,))
    familiar = cursor.fetchone()

    if request.method == 'POST':
        try:
            # ===== PACIENTE =====
            cursor.execute("""
                UPDATE pacientes
                SET curp=%s, papell=%s, sapell=%s, nom_pac=%s, fecnac=%s, tel=%s
                WHERE Id_exp=%s
            """, (
                request.form['curp'],
                request.form['papell'],
                request.form['sapell'],
                request.form['nom_pac'],
                request.form['fecnac'],
                request.form['tel'],
                id_exp
            ))

            # ===== ATENCION =====
            cursor.execute("""
                UPDATE atencion
                SET area=%s, id_cama=%s, motivo=%s, especialidad=%s, alergias=%s
                WHERE Id_exp=%s
            """, (
                request.form['area'],
                request.form.get('id_cama') or None,
                request.form['motivo'],
                request.form['especialidad'],
                request.form.get('alergias', ''),
                id_exp
            ))

            # ===== MÉDICOS =====
            cursor.execute("""
                DELETE FROM atencion_medicos
                WHERE id_atencion = (
                    SELECT id_atencion FROM atencion WHERE Id_exp=%s
                )
            """, (id_exp,))

            cursor.execute("SELECT id_atencion FROM atencion WHERE Id_exp=%s", (id_exp,))
            id_atencion = cursor.fetchone()['id_atencion']

            for m in ['medico1','medico2','medico3','medico4','medico5']:
                if request.form.get(m):
                    cursor.execute("""
                        INSERT INTO atencion_medicos (id_atencion, id_medico)
                        VALUES (%s, %s)
                    """, (id_atencion, request.form[m]))

            # ===== FAMILIAR =====
            cursor.execute("""
                UPDATE familiares
                SET nombre=%s, parentesco=%s, telefono=%s
                WHERE Id_exp=%s
            """, (
                request.form['fam_nombre'],
                request.form['fam_parentesco'],
                request.form['fam_tel'],
                id_exp
            ))

            conn.commit()
            flash('Paciente actualizado correctamente.', 'success')
            return redirect(url_for('gestion_pacientes'))

        except Exception as e:
            conn.rollback()
            flash(f'Error al actualizar: {e}', 'error')

        finally:
            cursor.close()
            conn.close()

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

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute("""
        SELECT p.Id_exp, p.papell, p.sapell, p.nom_pac,
               a.id_atencion, a.fecha_ing
        FROM pacientes p
        JOIN atencion a ON p.Id_exp = a.Id_exp
        ORDER BY a.fecha_ing DESC
    """)

    pacientes = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'administrativo/pacientes/doc_pacientes/documentos_pacientes.html',
        pacientes=pacientes
    )


@app.route('/buscar-paciente')
def buscar_paciente():
    q = request.args.get('q', '')
    conn = get_db_connection()

    # 👇 CLAVE: cursor como diccionario
    cur = conn.cursor()

    cur.execute("""
        SELECT Id_exp, curp, papell, sapell, nom_pac, fecnac, tel
        FROM pacientes
        WHERE curp LIKE %s
           OR nom_pac LIKE %s
           OR papell LIKE %s
        LIMIT 5
    """, (f"%{q}%", f"%{q}%", f"%{q}%"))

    pacientes = cur.fetchall()
    conn.close()

    # 👇 Convertir fecha a string
    for p in pacientes:
        if p["fecnac"]:
            p["fecnac"] = p["fecnac"].strftime('%Y-%m-%d')

    return jsonify(pacientes)

@app.route('/expedientes')
def ver_expedientes():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            e.id_expediente,
            p.Id_exp,
            CONCAT(p.papell, ' ', p.sapell, ' ', p.nom_pac) AS paciente,
            a.area,
            a.fecha_ing,
            e.fecha_alta,
            u.username AS usuario_alta,
            a.id_atencion
        FROM expedientes e
        JOIN pacientes p ON e.id_exp = p.Id_exp
        JOIN atencion a ON e.id_atencion = a.id_atencion
        LEFT JOIN users u ON e.usuario_alta = u.id
        ORDER BY e.fecha_alta DESC;
    """)

    expedientes = cur.fetchall()
    conn.close()

    return render_template(
        'administrativo/pacientes/exped/expedientes.html',
        expedientes=expedientes
    )


@app.route('/expediente/<int:id_atencion>/<int:id_exp>', methods=['GET', 'POST'])
def expediente(id_atencion, id_exp):
    conn = get_db_connection()
    cur = conn.cursor()

    # ===== DATOS PACIENTE + ATENCIÓN =====
    cur.execute("""
        SELECT p.Id_exp, p.papell, p.sapell, p.nom_pac,
               a.id_atencion, a.area, a.fecha_ing, a.status
        FROM pacientes p
        JOIN atencion a ON a.Id_exp = p.Id_exp
        WHERE a.id_atencion = %s
    """, (id_atencion,))
    pac = cur.fetchone()

    # ===== CUENTA =====
    cur.execute("""
        SELECT fecha, descripcion, cantidad, precio, subtotal
        FROM cuenta_paciente
        WHERE id_atencion = %s
    """, (id_atencion,))
    cuenta = cur.fetchall()

    cur.execute("""
        SELECT IFNULL(SUM(subtotal),0) AS total
        FROM cuenta_paciente
        WHERE id_atencion = %s
    """, (id_atencion,))
    total = cur.fetchone()['total']

    # ===== CERRAR CUENTA =====
    if request.method == 'POST' and pac['status'] == 'ABIERTA':
        cur.execute("""
            UPDATE atencion
            SET status = 'CERRADA'
            WHERE id_atencion = %s
        """, (id_atencion,))

        cur.execute("""
            INSERT INTO expedientes (id_exp, id_atencion, fecha_alta, usuario_alta)
            VALUES (%s, %s, NOW(), %s)
        """, (id_exp, id_atencion, session['user_id']))

        conn.commit()
        conn.close()
        return redirect(url_for('expediente', id_atencion=id_atencion, id_exp=id_exp))

    conn.close()

    return render_template(
        'administrativo/pacientes/cuenta_pac/expediente.html',
        pac=pac,
        cuenta=cuenta,
        total=total
    )


# ====================================================================================
# ============================       MÉDICO       ====================================
# ====================================================================================


@app.route('/medico/medico')
def medico():
    if 'user_id' not in session or session['role'] not in ['admin', 'medico']:
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Usuario actual
    cursor.execute("SELECT id, papell, img_perfil FROM users WHERE id = %s", (session['user_id'],))
    user_data = cursor.fetchone()
    usuario = {
        'id_usua': user_data['id'],
        'papell': user_data['papell'] or session['username'],
        'img_perfil': user_data['img_perfil']
    }

    logo = {'img_base': 'logo.jpg'}  # placeholder, cambia si tienes tabla de logo

    # -------------------------------------------------
    # 1. CONSULTA EXTERNA → área = 'Ambulatorio' (sin cama física)
    # -------------------------------------------------
    cursor.execute("""
        SELECT 
            a.id_atencion,
            CONCAT('Consulta ', a.id_atencion) AS num_cama,
            'OCUPADA' AS estatus,
            p.nom_pac,
            p.papell,
            p.sapell,
            a.Id_exp
        FROM atencion a
        JOIN pacientes p ON a.Id_exp = p.Id_exp
        WHERE a.area = 'Ambulatorio' AND a.status = 'ABIERTA'
        ORDER BY a.fecha_ing DESC
    """)
    beds_consulta = cursor.fetchall()

    # -------------------------------------------------
    # 2. PREPARACIÓN → área = 'Urgencias'
    # -------------------------------------------------
    cursor.execute("""
        SELECT 
            c.id_cama,
            COALESCE(a.id_atencion, NULL) AS id_atencion,
            c.numero AS num_cama,
            IF(a.id_atencion IS NULL, 'LIBRE', 'OCUPADA') AS estatus,
            p.nom_pac,
            p.papell,
            p.sapell,
            a.Id_exp
        FROM camas c
        LEFT JOIN atencion a ON c.id_cama = a.id_cama AND a.status = 'ABIERTA'
        LEFT JOIN pacientes p ON a.Id_exp = p.Id_exp
        WHERE c.area = 'Urgencias'
        ORDER BY c.numero ASC
    """)
    beds_preparacion = cursor.fetchall()

    # -------------------------------------------------
    # 3. RECUPERACIÓN → área = 'Hospitalizado'
    # -------------------------------------------------
    cursor.execute("""
        SELECT 
            c.id_cama,
            COALESCE(a.id_atencion, NULL) AS id_atencion,
            c.numero AS num_cama,
            IF(a.id_atencion IS NULL, 'LIBRE', 'OCUPADA') AS estatus,
            p.nom_pac,
            p.papell,
            p.sapell,
            a.Id_exp
        FROM camas c
        LEFT JOIN atencion a ON c.id_cama = a.id_cama AND a.status = 'ABIERTA'
        LEFT JOIN pacientes p ON a.Id_exp = p.Id_exp
        WHERE c.area = 'Hospitalizado'
        ORDER BY c.numero ASC
    """)
    beds_recuperacion = cursor.fetchall()

    # -------------------------------------------------
    # Asignar hasta 5 médicos a cada cama ocupada
    # -------------------------------------------------
    def asignar_medicos(beds):
        for bed in beds:
            bed['id_usua'] = bed['id_usua2'] = bed['id_usua3'] = bed['id_usua4'] = bed['id_usua5'] = None
            if bed['id_atencion']:
                cursor.execute("""
                    SELECT id_medico 
                    FROM atencion_medicos 
                    WHERE id_atencion = %s 
                    ORDER BY id LIMIT 5
                """, (bed['id_atencion'],))
                medicos = cursor.fetchall()
                for i, m in enumerate(medicos):
                    bed[f'id_usua{"" if i==0 else i+1}'] = m['id_medico']
        return beds

    beds_consulta = asignar_medicos(beds_consulta)
    beds_preparacion = asignar_medicos(beds_preparacion)
    beds_recuperacion = asignar_medicos(beds_recuperacion)

    cursor.close()
    conn.close()

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

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Usuario logueado
    cursor.execute(
        "SELECT id, papell FROM users WHERE id = %s",
        (session['user_id'],)
    )
    user_data = cursor.fetchone()

    usuario = {
        'id_usua': user_data['id'],
        'papell': user_data['papell']
    }

    # Datos del paciente
    cursor.execute("""
        SELECT 
            p.Id_exp, p.papell, p.sapell, p.nom_pac, p.fecnac,
            a.area, a.motivo AS motivo_atn, a.alergias,
            a.fecha_ing AS fecha
        FROM pacientes p
        JOIN atencion a ON p.Id_exp = a.Id_exp
        WHERE a.id_atencion = %s AND p.Id_exp = %s
    """, (id_atencion, Id_exp))
    paciente = cursor.fetchone()

    if paciente and paciente['fecnac']:
        paciente['edad'] = calcular_edad(paciente['fecnac'])

    # Familiar
    cursor.execute("""
        SELECT nombre, parentesco, telefono
        FROM familiares
        WHERE Id_exp = %s
        LIMIT 1
    """, (Id_exp,))
    familiar = cursor.fetchone()

    # Médicos
    cursor.execute("""
        SELECT u.username AS doctor
        FROM atencion_medicos am
        JOIN users u ON am.id_medico = u.id
        WHERE am.id_atencion = %s
    """, (id_atencion,))
    medicos = cursor.fetchall()

    diagnostico = paciente['motivo_atn'] if paciente else ''

    # Cama
    cursor.execute("""
        SELECT numero AS num_cama, area AS tipo
        FROM camas
        WHERE id_cama = (
            SELECT id_cama FROM atencion WHERE id_atencion = %s
        )
    """, (id_atencion,))
    cama = cursor.fetchone() or {'num_cama': 'Sin Cama', 'tipo': ''}

    cursor.close()
    conn.close()

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

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute(
        "SELECT * FROM pacientes WHERE Id_exp = %s",
        (id_exp,)
    )
    paciente = cursor.fetchone()

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

        cursor.execute("""
            INSERT INTO historia_clinica
            (Id_exp, motivo_consulta, sintomatologia, sintomatologia_otros,
             heredo, heredo_otros, nopat, nopat_otros,
             pat_enfermedades, pat_medicamentos, pat_alergias,
             pat_oculares, pat_cirugias)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            id_exp, motivo, sinto, sinto_otro,
            heredo, heredo_otro, nopat, nopat_otro,
            pat_enf, pat_med, pat_ale, pat_ocu, pat_cir
        ))

        conn.commit()
        flash('Historia clínica guardada correctamente', 'success')

        cursor.close()
        conn.close()

        return redirect(
            url_for(
                'historia_clinica',
                id_atencion=id_atencion,
                id_exp=id_exp
            )
        )

    cursor.close()
    conn.close()

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

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Paciente
    cursor.execute("""
        SELECT p.Id_exp, p.papell, p.sapell, p.nom_pac
        FROM pacientes p
        JOIN atencion a ON p.Id_exp = a.Id_exp
        WHERE a.id_atencion = %s
    """, (id_atencion,))
    paciente = cursor.fetchone()

    # Catálogo de exámenes
    cursor.execute("""
        SELECT id_catalogo, nombre
        FROM catalogo_examenes_gabinete
        ORDER BY nombre
    """)
    examenes = cursor.fetchall()

    cursor.close()
    conn.close()

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

    id_atencion = request.form.get('id_atencion')
    observaciones = request.form.get('otros')
    examenes_ids = request.form.getlist('examenes[]')

    if not examenes_ids:
        flash('Debe seleccionar al menos un examen.', 'warning')
        return redirect(url_for('examenes_gabinete', id_atencion=id_atencion))

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # 1️⃣ Insertar encabezado
    cursor.execute("""
        INSERT INTO examenes_gabinete (id_atencion, id_medico, observaciones)
        VALUES (%s, %s, %s)
    """, (id_atencion, session['user_id'], observaciones))

    id_examen = cursor.lastrowid

    # 2️⃣ Insertar detalle (nombre del examen)
    for id_catalogo in examenes_ids:
        cursor.execute("""
            SELECT nombre
            FROM catalogo_examenes_gabinete
            WHERE id_catalogo = %s
        """, (id_catalogo,))
        examen = cursor.fetchone()

        cursor.execute("""
            INSERT INTO examenes_gabinete_det (id_examen, nombre_examen)
            VALUES (%s, %s)
        """, (id_examen, examen['nombre']))

    conn.commit()
    cursor.close()
    conn.close()

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

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # Paciente completo
    cursor.execute("""
        SELECT 
            p.Id_exp,
            p.nom_pac,
            p.papell,
            p.sapell
        FROM atencion a
        JOIN pacientes p ON a.Id_exp = p.Id_exp
        WHERE a.id_atencion = %s
    """, (id_atencion,))
    paciente = cursor.fetchone()

    # Catálogo de exámenes
    cursor.execute("""
        SELECT id_catalogo, nombre
        FROM catalogo_examenes_laboratorio
        ORDER BY nombre
    """)
    examenes = cursor.fetchall()

    cursor.close()
    conn.close()

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

    id_atencion = request.form.get('id_atencion')
    Id_exp = request.form.get('Id_exp')
    observaciones = request.form.get('otros')
    examenes = request.form.getlist('examenes[]')

    if not examenes:
        flash('Debe seleccionar al menos un examen.', 'warning')
        return redirect(url_for('examenes_laboratorio', id_atencion=id_atencion))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Encabezado
    cursor.execute("""
        INSERT INTO examenes_laboratorio
        (id_atencion, id_medico, observaciones)
        VALUES (%s, %s, %s)
    """, (id_atencion, session['user_id'], observaciones))

    id_examen = cursor.lastrowid

    # Detalle
    for id_catalogo in examenes:
        cursor.execute("""
            INSERT INTO examenes_laboratorio_det
            (id_examen, id_catalogo)
            VALUES (%s, %s)
        """, (id_examen, id_catalogo))

    conn.commit()
    cursor.close()
    conn.close()

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

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # ================= PACIENTE =================
    cursor.execute("""
        SELECT p.Id_exp, p.papell, p.sapell, p.nom_pac,
               a.area, a.fecha_ing
        FROM pacientes p
        JOIN atencion a ON p.Id_exp = a.Id_exp
        WHERE a.id_atencion = %s
    """, (id_atencion,))
    paciente = cursor.fetchone()

    if not paciente:
        flash('Paciente no encontrado.', 'error')
        return redirect(url_for('dashboard'))

    # ================= LABORATORIO (SOLO REALIZADOS) =================
    cursor.execute("""
        SELECT 
            el.id_examen,
            GROUP_CONCAT(c.nombre SEPARATOR ', ') AS estudios,
            u.papell AS medico,
            el.observaciones,
            el.fecha
        FROM examenes_laboratorio el
        JOIN examenes_laboratorio_det eld 
            ON el.id_examen = eld.id_examen
        JOIN catalogo_examenes_laboratorio c 
            ON eld.id_catalogo = c.id_catalogo
        JOIN users u 
            ON el.id_medico = u.id
        WHERE el.id_atencion = %s
          AND (
              el.estado = 'realizado'
              OR el.archivo_resultado IS NOT NULL
              OR el.fecha_realizado IS NOT NULL
          )
        GROUP BY el.id_examen
        ORDER BY el.fecha DESC
    """, (id_atencion,))
    laboratorio = cursor.fetchall()

    # ================= GABINETE (SOLO REALIZADOS) =================
    cursor.execute("""
        SELECT 
            eg.id_examen,
            eg.fecha,
            eg.observaciones,
            u.papell AS medico,
            GROUP_CONCAT(egd.nombre_examen SEPARATOR ', ') AS estudios
        FROM examenes_gabinete eg
        JOIN examenes_gabinete_det egd 
            ON eg.id_examen = egd.id_examen
        JOIN users u 
            ON eg.id_medico = u.id
        WHERE eg.id_atencion = %s
          AND (
              egd.estado = 'REALIZADO'
              OR egd.archivo_resultado IS NOT NULL
          )
        GROUP BY eg.id_examen
        ORDER BY eg.fecha DESC
    """, (id_atencion,))
    gabinete = cursor.fetchall()

    cursor.close()
    conn.close()

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

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # ================= RESULTADO LABORATORIO =================
    cursor.execute("""
        SELECT el.id_examen,
               el.fecha,
               el.observaciones,
               a.id_atencion,
               p.Id_exp, p.papell, p.sapell, p.nom_pac,
               u.papell AS medico,
               GROUP_CONCAT(c.nombre SEPARATOR ', ') AS estudios
        FROM examenes_laboratorio el
        JOIN examenes_laboratorio_det eld ON el.id_examen = eld.id_examen
        JOIN catalogo_examenes_laboratorio c ON eld.id_catalogo = c.id_catalogo
        JOIN atencion a ON el.id_atencion = a.id_atencion
        JOIN pacientes p ON a.Id_exp = p.Id_exp
        JOIN users u ON el.id_medico = u.id
        WHERE el.id_examen = %s
        GROUP BY el.id_examen
    """, (id_examen,))

    resultado = cursor.fetchone()

    cursor.close()
    conn.close()

    if not resultado:
        flash('Resultado no encontrado.', 'error')
        return redirect(url_for('dashboard'))

    return render_template(
        'medico/res_estudios/ver_resultado_laboratorio.html',
        resultado=resultado,
        id_atencion=resultado['id_atencion'],
        paciente={
            'Id_exp': resultado['Id_exp'],
            'nom_pac': resultado['nom_pac'],
            'papell': resultado['papell'],
            'sapell': resultado['sapell']
        }
    )


@app.route('/medico/gabinete/ver/<int:id_examen>')
def ver_resultado_gabinete(id_examen):

    if 'user_id' not in session:
        flash('Sesión no válida', 'error')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
                   SELECT eg.id_examen,
                          eg.fecha,
                          eg.observaciones,
                          a.id_atencion,
                          p.Id_exp,
                          p.nom_pac,
                          p.papell,
                          p.sapell
                   FROM examenes_gabinete eg
                            JOIN atencion a ON eg.id_atencion = a.id_atencion
                            JOIN pacientes p ON a.Id_exp = p.Id_exp
                   WHERE eg.id_examen = %s
                   """, (id_examen,))

    encabezado = cursor.fetchone()

    cursor.execute("""
                   SELECT nombre_examen,
                          estado,
                          fecha_realizado,
                          archivo_resultado,
                          observaciones
                   FROM examenes_gabinete_det
                   WHERE id_examen = %s
                   """, (id_examen,))

    detalles = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'medico/res_estudios/ver_resultado_gabinete.html',
        encabezado=encabezado,
        detalles=detalles,
        id_atencion=encabezado['id_atencion'],
        paciente={
            'Id_exp': encabezado['Id_exp'],
            'nom_pac': encabezado['nom_pac'],
            'papell': encabezado['papell'],
            'sapell': encabezado['sapell']
        }
    )
# ==================== GESTIÓN DE CUENTAS ====================



@app.route('/admin/presupuestos', methods=['GET', 'POST'])
def presupuestos():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

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

        cursor.execute(
            "SELECT serv_desc FROM cat_servicios WHERE id_serv = %s",
            (serv_id,)
        )
        serv = cursor.fetchone()

        if serv:
            cursor.execute("""
                INSERT INTO presupuesto
                (fecha, id_pac, nombre, id_serv, servicio, cantidad)
                VALUES (NOW(), %s, %s, %s, %s, %s)
            """, (id_pac, nombre, serv_id, serv['serv_desc'], cantidad))
            conn.commit()

        return redirect(url_for('presupuestos'))

    # ======================
    # INSERTAR MEDICAMENTO
    # ======================
    if request.method == 'POST' and 'btnmed' in request.form:
        item_id = request.form.get('med')
        cantidad = int(request.form.get('cantidad'))

        cursor.execute(
            "SELECT item_code, item_name FROM item WHERE item_id = %s",
            (item_id,)
        )
        item = cursor.fetchone()

        if item:
            cursor.execute("""
                INSERT INTO presupuesto
                (fecha, id_pac, nombre, id_serv, servicio, cantidad)
                VALUES (NOW(), %s, %s, %s, %s, %s)
            """, (id_pac, nombre, item['item_code'], item['item_name'], cantidad))
            conn.commit()

        return redirect(url_for('presupuestos'))

    # ======================
    # SELECTS PARA FORMULARIOS
    # ======================
    cursor.execute("""
        SELECT id_serv, serv_desc, serv_costo
        FROM cat_servicios
        WHERE serv_activo = 'SI'
    """)
    servicios = cursor.fetchall()

    cursor.execute("""
        SELECT item_id, item_code, item_name, item_price
        FROM item
    """)
    items = cursor.fetchall()

    # ======================
    # TABLA PRESUPUESTO - SERVICIOS
    # ======================
    cursor.execute("""
        SELECT p.*, c.serv_costo
        FROM presupuesto p
        JOIN cat_servicios c ON c.id_serv = p.id_serv
        WHERE p.id_pac = %s
    """, (id_pac,))
    lista_serv = cursor.fetchall()

    for p in lista_serv:
        costo = Decimal(p['serv_costo'])
        cantidad = Decimal(p['cantidad'])
        p['subtotal'] = costo * cantidad
        p['total'] = p['subtotal'] * IVA

    # ======================
    # TABLA PRESUPUESTO - ITEMS
    # ======================
    cursor.execute("""
        SELECT p.*, i.item_price
        FROM presupuesto p
        JOIN item i ON i.item_code = p.id_serv
        WHERE p.id_pac = %s
    """, (id_pac,))
    lista_items = cursor.fetchall()

    for p in lista_items:
        precio = Decimal(p['item_price'])
        cantidad = Decimal(p['cantidad'])
        p['subtotal'] = precio * cantidad
        p['total'] = p['subtotal'] * IVA

    conn.close()

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
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM presupuesto WHERE id_presupuesto = %s",
        (id_presupuesto,)
    )

    conn.commit()
    conn.close()

    flash('Registro eliminado correctamente', 'success')
    return redirect(url_for('presupuestos'))



@app.route('/admin/corte_caja')
def corte_caja():
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('administrativo/gestion_cuentas/corte_caja.html')

@app.route('/corte_caja/pdf', methods=['POST'])
def corte_caja_pdf():

    fecha_inicio = request.form['fecha_inicio']
    fecha_fin = request.form['fecha_fin']

    # Sumar 1 día a fecha final
    fecha_fin_real = (
        datetime.strptime(fecha_fin, "%Y-%m-%d") + timedelta(days=1)
    ).strftime("%Y-%m-%d")

    conexion = get_db_connection()

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
        f"Periodo del {fecha_inicio} al {fecha_fin}",
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

    with conexion.cursor() as cursor:
        sql = """
        SELECT p.nombre, m.fecha, m.deposito, m.tipo_pago
        FROM pago_serv p
        JOIN depositos_pserv m ON p.id_pac = m.id_pac
        WHERE m.fecha BETWEEN %s AND %s
          AND m.tipo_pago NOT IN ('DESCUENTO','ASEGURADORA')
        ORDER BY p.nombre
        """
        cursor.execute(sql, (fecha_inicio, fecha_fin_real))
        rows = cursor.fetchall()

        for r in rows:
            pdf.cell(8, 8, str(contador), 1)
            pdf.cell(25, 8, str(r['fecha']), 1)
            pdf.cell(80, 8, r['nombre'], 1)
            pdf.cell(20, 8, f"${float(r['deposito']):.2f}", 1)
            pdf.cell(15, 8, 'SERV', 1)
            pdf.cell(30, 8, r['tipo_pago'], 1)
            pdf.ln()

            total_efectivo += float(r['deposito'])
            contador += 1

    conexion.close()

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
    # Consulta SQL
    # Generar Excel
    return "Generar Excel"

@app.route('/medico/imprimir/<int:id_atencion>')
def imprimir_documentos(id_atencion):

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute("""
        SELECT 
            p.Id_exp,
            p.papell,
            p.sapell,
            p.nom_pac
        FROM pacientes p
        JOIN atencion a ON a.Id_exp = p.Id_exp
        WHERE a.id_atencion = %s
    """, (id_atencion,))

    paciente = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        'medico/impresiones/imprimir_documentos.html',
        paciente=paciente,
        id_atencion=id_atencion
    )


@app.route('/medico/imprimir/signos/<int:id_atencion>')
def imprimir_signos_vitales(id_atencion):

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # PACIENTE
    cursor.execute("""
        SELECT 
            p.Id_exp,
            p.papell,
            p.sapell,
            p.nom_pac
        FROM pacientes p
        JOIN atencion a ON a.Id_exp = p.Id_exp
        WHERE a.id_atencion = %s
    """, (id_atencion,))
    paciente = cursor.fetchone()

    # SIGNOS VITALES
    cursor.execute("""
        SELECT *
        FROM signos_vitales
        WHERE id_atencion = %s
        ORDER BY fecha_registro DESC
    """, (id_atencion,))
    signos = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'medico/impresiones/signos_vitales.html',
        paciente=paciente,
        signos=signos,
        id_atencion=id_atencion
    )


@app.route('/medico/imprimir/notas/<int:id_atencion>')
def imprimir_notas_medicas(id_atencion):

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # PACIENTE
    cursor.execute("""
        SELECT 
            p.Id_exp,
            p.papell,
            p.sapell,
            p.nom_pac
        FROM pacientes p
        JOIN atencion a ON a.Id_exp = p.Id_exp
        WHERE a.id_atencion = %s
    """, (id_atencion,))
    paciente = cursor.fetchone()

    # NOTAS MÉDICAS (SOAP)
    cursor.execute("""
        SELECT *
        FROM notas_medicas
        WHERE id_atencion = %s
        ORDER BY fecha_registro DESC
    """, (id_atencion,))
    notas = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'medico/impresiones/notas_medicas.html',
        paciente=paciente,
        notas=notas,
        id_atencion=id_atencion
    )


@app.route('/medico/imprimir/diagnostico/<int:id_atencion>')
def imprimir_diagnostico(id_atencion):

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # ===============================
    # PACIENTE
    # ===============================
    cursor.execute("""
        SELECT 
            p.Id_exp,
            p.papell,
            p.sapell,
            p.nom_pac
        FROM pacientes p
        JOIN atencion a ON a.Id_exp = p.Id_exp
        WHERE a.id_atencion = %s
    """, (id_atencion,))
    paciente = cursor.fetchone()

    # ===============================
    # DIAGNÓSTICOS
    # ===============================
    cursor.execute("""
        SELECT *
        FROM diagnosticos
        WHERE id_atencion = %s
        ORDER BY fecha_registro DESC
    """, (id_atencion,))
    diagnosticos = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'medico/impresiones/diagnostico.html',
        paciente=paciente,
        diagnosticos=diagnosticos,
        id_atencion=id_atencion
    )


@app.route('/medico/imprimir/recetas/<int:id_atencion>')
def imprimir_recetas(id_atencion):

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # PACIENTE
    cursor.execute("""
        SELECT p.Id_exp, p.papell, p.sapell, p.nom_pac
        FROM pacientes p
        JOIN atencion a ON a.Id_exp = p.Id_exp
        WHERE a.id_atencion = %s
    """, (id_atencion,))
    paciente = cursor.fetchone()

    # RECETAS AGRUPADAS POR FECHA
    cursor.execute("""
        SELECT 
            fecha_registro,
            COUNT(*) AS total_meds
        FROM recetas
        WHERE id_atencion = %s
        GROUP BY fecha_registro
        ORDER BY fecha_registro DESC
    """, (id_atencion,))
    recetas = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'medico/impresiones/recetas.html',
        paciente=paciente,
        recetas=recetas,
        id_atencion=id_atencion
    )


@app.route('/medico/imprimir/laboratorio/<int:id_atencion>')
def imprimir_laboratorio(id_atencion):

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # PACIENTE
    cursor.execute("""
        SELECT p.Id_exp, p.papell, p.sapell, p.nom_pac
        FROM pacientes p
        JOIN atencion a ON a.Id_exp = p.Id_exp
        WHERE a.id_atencion = %s
    """, (id_atencion,))
    paciente = cursor.fetchone()

    # SOLICITUDES DE LABORATORIO
    cursor.execute("""
        SELECT *
        FROM examenes_laboratorio
        WHERE id_atencion = %s
        ORDER BY fecha DESC
    """, (id_atencion,))
    examenes = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'medico/impresiones/examenes_laboratorio.html',
        paciente=paciente,
        examenes=examenes,
        id_atencion=id_atencion
    )


@app.route('/medico/imprimir/gabinete/<int:id_atencion>')
def imprimir_gabinete(id_atencion):

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # =========================
    # PACIENTE
    # =========================
    cursor.execute("""
        SELECT p.Id_exp, p.papell, p.sapell, p.nom_pac
        FROM pacientes p
        JOIN atencion a ON a.Id_exp = p.Id_exp
        WHERE a.id_atencion = %s
    """, (id_atencion,))
    paciente = cursor.fetchone()

    # =========================
    # GABINETE + ESTADO GENERAL
    # =========================
    cursor.execute("""
        SELECT 
            eg.id_examen,
            eg.fecha,
            CASE
                WHEN SUM(d.estado = 'CANCELADO') > 0 THEN 'CANCELADO'
                WHEN SUM(d.estado = 'PENDIENTE') > 0 THEN 'PENDIENTE'
                ELSE 'REALIZADO'
            END AS estado_general
        FROM examenes_gabinete eg
        JOIN examenes_gabinete_det d 
            ON d.id_examen = eg.id_examen
        WHERE eg.id_atencion = %s
        GROUP BY eg.id_examen
        ORDER BY eg.fecha DESC
    """, (id_atencion,))
    examenes = cursor.fetchall()

    cursor.close()
    conn.close()

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

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # ========= PACIENTE =========
    cursor.execute("""
        SELECT p.*
        FROM atencion a
        JOIN pacientes p ON a.Id_exp = p.Id_exp
        WHERE a.id_atencion = %s
    """, (id_atencion,))
    paciente = cursor.fetchone()

    if not paciente:
        flash('Paciente no encontrado', 'error')
        return redirect(url_for('dashboard'))

    # ========= POST =========
    if request.method == 'POST':
        cursor.execute("""
            INSERT INTO signos_vitales
            (id_atencion, ta, fc, fr, temp, spo2, peso, talla)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            id_atencion,
            request.form.get('ta'),
            request.form.get('fc'),
            request.form.get('fr'),
            request.form.get('temp'),
            request.form.get('spo2'),
            request.form.get('peso'),
            request.form.get('talla')
        ))

        conn.commit()
        flash('Signos vitales registrados correctamente', 'success')
        return redirect(url_for('signos_vitales', id_atencion=id_atencion))

    cursor.close()
    conn.close()

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

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    if request.method == 'POST':
        cursor.execute("""
            INSERT INTO notas_medicas
            (id_atencion, subjetivo, objetivo, analisis, plan, id_medico)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            id_atencion,
            request.form['subjetivo'],
            request.form['objetivo'],
            request.form['analisis'],
            request.form['plan'],
            session['user_id']
        ))

        conn.commit()
        flash('Nota médica registrada correctamente', 'success')
        return redirect(url_for('nota_medica', id_atencion=id_atencion))

    cursor.execute("""
        SELECT p.*
        FROM atencion a
        JOIN pacientes p ON a.Id_exp = p.Id_exp
        WHERE a.id_atencion = %s
    """, (id_atencion,))
    paciente = cursor.fetchone()

    cursor.execute("""
        SELECT *
        FROM notas_medicas
        WHERE id_atencion = %s
        ORDER BY fecha_registro DESC
    """, (id_atencion,))
    notas = cursor.fetchall()

    cursor.close()
    conn.close()

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

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # ===== ESTADO ATENCIÓN =====
    cursor.execute("""
        SELECT status
        FROM atencion
        WHERE id_atencion = %s
    """, (id_atencion,))
    atencion = cursor.fetchone()

    if not atencion:
        flash('Atención no encontrada', 'danger')
        return redirect(url_for('dashboard'))

    # ===== POST =====
    if request.method == 'POST':

        if atencion['status'] == 'CERRADA':
            flash('La atención está cerrada, no se puede modificar el diagnóstico', 'danger')
            return redirect(url_for('diagnostico', id_atencion=id_atencion))

        diagnostico_principal = request.form['diagnostico_principal']
        secundarios = request.form.get('diagnosticos_secundarios')
        observaciones = request.form.get('observaciones')

        cursor.execute("""
            SELECT id_diagnostico
            FROM diagnosticos
            WHERE id_atencion = %s
        """, (id_atencion,))
        existe = cursor.fetchone()

        if existe:
            cursor.execute("""
                UPDATE diagnosticos
                SET diagnostico_principal=%s,
                    diagnosticos_secundarios=%s,
                    observaciones=%s
                WHERE id_atencion=%s
            """, (diagnostico_principal, secundarios, observaciones, id_atencion))
        else:
            cursor.execute("""
                INSERT INTO diagnosticos
                (id_atencion, diagnostico_principal, diagnosticos_secundarios, observaciones)
                VALUES (%s, %s, %s, %s)
            """, (id_atencion, diagnostico_principal, secundarios, observaciones))

        # ===== HISTORIAL =====
        cursor.execute("""
            INSERT INTO diagnosticos_historial
            (id_atencion, diagnostico_principal, diagnosticos_secundarios, observaciones, id_medico)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            id_atencion,
            diagnostico_principal,
            secundarios,
            observaciones,
            session['user_id']
        ))

        conn.commit()
        flash('Diagnóstico guardado correctamente', 'success')
        return redirect(url_for('diagnostico', id_atencion=id_atencion))

    # ===== GET =====
    cursor.execute("""
        SELECT *
        FROM diagnosticos
        WHERE id_atencion = %s
    """, (id_atencion,))
    diagnostico = cursor.fetchone()

    cursor.execute("""
        SELECT p.*
        FROM atencion a
        JOIN pacientes p ON a.Id_exp = p.Id_exp
        WHERE a.id_atencion = %s
    """, (id_atencion,))
    paciente = cursor.fetchone()

    cursor.close()
    conn.close()

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

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # ================= GUARDAR RECETA =================
    if request.method == 'POST':
        medicamentos = request.form.getlist('medicamento[]')
        dosis = request.form.getlist('dosis[]')
        frecuencia = request.form.getlist('frecuencia[]')
        duracion = request.form.getlist('duracion[]')
        indicaciones = request.form.getlist('indicaciones[]')

        for i in range(len(medicamentos)):
            cursor.execute("""
                           INSERT INTO recetas
                           (id_atencion, medicamento, dosis, frecuencia, duracion, indicaciones, id_medico)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)
                           """, (
                               id_atencion,
                               medicamentos[i],
                               dosis[i],
                               frecuencia[i],
                               duracion[i],
                               indicaciones[i],
                               session['user_id']
                           ))

        conn.commit()
        flash('Receta guardada correctamente', 'success')
        return redirect(url_for('receta_medica', id_atencion=id_atencion))

    # ================= PACIENTE =================
    cursor.execute("""
        SELECT p.*
        FROM atencion a
        JOIN pacientes p ON a.Id_exp = p.Id_exp
        WHERE a.id_atencion = %s
    """, (id_atencion,))
    paciente = cursor.fetchone()

    # ================= RECETAS =================
    cursor.execute("""
        SELECT *
        FROM recetas
        WHERE id_atencion = %s
        ORDER BY fecha_registro DESC
    """, (id_atencion,))
    recetas = cursor.fetchall()

    cursor.close()
    conn.close()

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

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # ================= HISTORIAL =================
    cursor.execute("""
        SELECT dh.*, u.papell AS medico_papell
        FROM diagnosticos_historial dh
        JOIN users u ON dh.id_medico = u.id
        WHERE dh.id_atencion = %s
        ORDER BY dh.fecha_registro DESC
    """, (id_atencion,))
    historial = cursor.fetchall()

    # ================= PACIENTE =================
    cursor.execute("""
        SELECT p.*
        FROM atencion a
        JOIN pacientes p ON a.Id_exp = p.Id_exp
        WHERE a.id_atencion = %s
    """, (id_atencion,))
    paciente = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        'medico/forms/historial_diagnostico.html',
        historial=historial,
        paciente=paciente,
        id_atencion=id_atencion
    )


# ====================================================================================
# ============================       CONFIGURACION      ===============================
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

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM camas ORDER BY numero ASC")
    camas = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template(
        'configuracion/camas/menu_camas.html',
        camas=camas
    )


# ==================== ALTA DE CAMAS ====================
@app.route('/configuracion/alta_camas', methods=['GET', 'POST'])
def alta_camas():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        numero = request.form['numero']
        area = request.form['area']
        tipo_habitacion = request.form.get('tipo_habitacion')
        piso = request.form.get('piso')
        seccion = request.form.get('seccion')
        ocupada = int(request.form.get('ocupada', 0))  # 0 o 1

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Validar duplicado
            cursor.execute("SELECT id_cama FROM camas WHERE numero = %s", (numero,))
            if cursor.fetchone():
                flash('Ya existe una cama con ese número.', 'warning')
                return redirect(url_for('alta_camas'))

            # Insertar todos los campos
            cursor.execute("""
                           INSERT INTO camas (numero, area, tipo_habitacion, piso, seccion, ocupada)
                           VALUES (%s, %s, %s, %s, %s, %s)
                           """, (numero, area, tipo_habitacion, piso, seccion, ocupada))

            conn.commit()
            flash('Cama registrada correctamente', 'success')
            return redirect(url_for('menu_camas'))

        except Exception as e:
            flash(f'Error al registrar cama: {e}', 'error')

        finally:
            cursor.close()
            conn.close()

    return render_template('configuracion/camas/alta_camas.html')


# ==================== EDITAR CAMA ====================
@app.route('/configuracion/editar_cama/<int:id>', methods=['GET', 'POST'])
def editar_cama(id):
    if 'user_id' not in session:
        flash('Debes iniciar sesión', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)  # <-- CORREGIDO

    if request.method == 'POST':
        estatus = request.form['estatus']
        area = request.form['area']
        tipo_habitacion = request.form['tipo_habitacion']
        piso = request.form.get('piso')
        seccion = request.form.get('seccion')
        ocupada = int(request.form.get('ocupada', 0))

        try:
            cursor.execute("""
                           UPDATE camas
                           SET estatus=%s,
                               area=%s,
                               tipo_habitacion=%s,
                               piso=%s,
                               seccion=%s,
                               ocupada=%s
                           WHERE id_cama = %s
                           """, (estatus, area, tipo_habitacion, piso, seccion, ocupada, id))
            conn.commit()
            flash('Cama actualizada correctamente', 'success')
            return redirect(url_for('menu_camas'))
        except Exception as e:
            flash(f'Error al actualizar cama: {e}', 'error')
        finally:
            cursor.close()
            conn.close()

    # GET → mostrar datos actuales
    cursor.execute("SELECT * FROM camas WHERE id_cama = %s", (id,))
    cama = cursor.fetchone()  # ahora es un diccionario
    cursor.close()
    conn.close()

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
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM camas WHERE id_cama = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ==================== COPIA GENERAL ====================
@app.route('/configuracion/copias')
def copias_seguridad():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))

    ruta_proyecto = current_app.root_path
    carpeta_copias = os.path.join(ruta_proyecto, 'configuracion', 'copias')
    os.makedirs(carpeta_copias, exist_ok=True)

    fecha = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    nombre_zip = f'respaldo_general_{fecha}.zip'
    ruta_zip = os.path.join(carpeta_copias, nombre_zip)

    with zipfile.ZipFile(ruta_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for carpeta, _, archivos in os.walk(ruta_proyecto):
            if 'venv' in carpeta or 'copias' in carpeta:
                continue
            for archivo in archivos:
                ruta_completa = os.path.join(carpeta, archivo)
                ruta_relativa = os.path.relpath(ruta_completa, ruta_proyecto)
                zipf.write(ruta_completa, ruta_relativa)

    flash('Copia de seguridad general creada correctamente', 'success')
    return render_template(
        'configuracion/copias/copias_seguridad.html',
        archivo=nombre_zip
    )


# ==================== COPIA SOLO CAMAS ====================
@app.route('/copias/camas')
def copias_seguridad_camas():
    ruta_proyecto = current_app.root_path
    ruta_camas = os.path.join(ruta_proyecto, 'gestion_camas')

    carpeta_copias = os.path.join(ruta_proyecto, 'configuracion', 'copias')
    os.makedirs(carpeta_copias, exist_ok=True)

    fecha = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    nombre_zip = f'backup_camas_{fecha}.zip'
    ruta_zip = os.path.join(carpeta_copias, nombre_zip)

    with zipfile.ZipFile(ruta_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for carpeta, _, archivos in os.walk(ruta_camas):
            for archivo in archivos:
                ruta_completa = os.path.join(carpeta, archivo)
                ruta_relativa = os.path.relpath(ruta_completa, ruta_camas)
                zipf.write(ruta_completa, ruta_relativa)

    return render_template(
        'configuracion/copias/copias_seguridad.html',
        archivo=nombre_zip
    )


# ==================== COPIA AUTOMATICA ====================
def crear_copia_general():
    ruta_proyecto = current_app.root_path

    carpeta_copias = os.path.join(ruta_proyecto, 'respaldos', 'general')
    os.makedirs(carpeta_copias, exist_ok=True)

    fecha = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    nombre_zip = f'respaldo_general_{fecha}.zip'
    ruta_zip = os.path.join(carpeta_copias, nombre_zip)

    with zipfile.ZipFile(ruta_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for carpeta, _, archivos in os.walk(ruta_proyecto):
            if 'venv' in carpeta or 'respaldos' in carpeta:
                continue
            for archivo in archivos:
                ruta_completa = os.path.join(carpeta, archivo)
                ruta_relativa = os.path.relpath(ruta_completa, ruta_proyecto)
                zipf.write(ruta_completa, ruta_relativa)

    print("✅ Copia automática creada:", ruta_zip)


# ==================== COPIA AUTo ====================
@app.route('/test-backup')
def test_backup():
    crear_copia_general()
    return "Backup creado"


# ====================================================================================
# ============================       PERSONAL       ====================================
# ====================================================================================

@app.route('/configuracion/personal')
def alta_usuarios():
    conexion = get_db_connection()
    cursor = conexion.cursor()

    cursor.execute("""
                   SELECT id,
                          username,
                          role
                   FROM users
                   ORDER BY id DESC
                   """)
    personal = cursor.fetchall()
    cursor.close()
    conexion.close()

    roles = ['admin', 'medico', 'enfermero', 'administrativo']

    return render_template(
        'configuracion/personal/alta_usuario.html',
        personal=personal,
        roles=roles
    )


# ====================================================================================
# ============================     INSERTAR USUARIO     ===============================
# ====================================================================================

@app.route('/configuracion/personal/insertar', methods=['POST'])
def insertar_usuario():
    conexion = get_db_connection()
    cursor = conexion.cursor()

    try:
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']

        # VALIDAR USUARIO DUPLICADO
        cursor.execute(
            "SELECT id FROM users WHERE username = %s",
            (username,)
        )
        if cursor.fetchone():
            flash('El usuario ya existe', 'danger')
            cursor.close()
            conexion.close()
            return redirect(url_for('alta_usuarios'))

        # INSERT USERS
        cursor.execute("""
                       INSERT INTO users (username, password, role)
                       VALUES (%s, %s, %s)
                       """, (username, password, role))

        conexion.commit()
        flash('Usuario creado correctamente', 'success')
        return redirect(url_for('alta_usuarios'))
    except Exception as e:
        conexion.rollback()
        flash(f'Error al crear usuario: {e}', 'danger')
        return redirect(url_for('alta_usuarios'))
    finally:
        cursor.close()
        conexion.close()


# ====================================================================================
# ============================        EDITAR USUARIO     ===============================
# ====================================================================================

@app.route('/configuracion/personal/editar/<int:user_id>', methods=['GET', 'POST'])
def editar_usuario(user_id):
    conexion = get_db_connection()
    cursor = conexion.cursor()

    cursor.execute("""
                   SELECT id,
                          username,
                          role
                   FROM users
                   WHERE id = %s
                   """, (user_id,))
    usuario = cursor.fetchone()

    if not usuario:
        flash('Usuario no encontrado', 'danger')
        cursor.close()
        conexion.close()
        return redirect(url_for('alta_usuarios'))

    roles = ['admin', 'medico', 'enfermero', 'administrativo']

    if request.method == 'POST':
        try:
            cursor.execute("""
                           UPDATE users
                           SET username=%s,
                               role=%s
                           WHERE id = %s
                           """, (
                               request.form['username'],
                               request.form['role'],
                               user_id
                           ))

            conexion.commit()
            flash('Usuario actualizado correctamente', 'success')
            cursor.close()
            conexion.close()
            return redirect(url_for('alta_usuarios'))
        except Exception as e:
            conexion.rollback()
            flash(f'Error al actualizar usuario: {e}', 'danger')
            cursor.close()
            conexion.close()
            return redirect(url_for('alta_usuarios'))

    cursor.close()
    conexion.close()

    return render_template(
        'configuracion/personal/editar_usuario.html',
        usuario=usuario,
        roles=roles
    )


# ====================================================================================
# ============================       MOSTRAR USUARIO     ===============================
# ====================================================================================

@app.route('/configuracion/personal/mostrar/<int:user_id>')
def mostrar_usuario(user_id):
    conexion = get_db_connection()
    cursor = conexion.cursor()

    cursor.execute("""
                   SELECT username,
                          role
                   FROM users
                   WHERE id = %s
                   """, (user_id,))
    usuario = cursor.fetchone()

    cursor.close()
    conexion.close()

    if not usuario:
        flash('Usuario no encontrado', 'danger')
        return redirect(url_for('alta_usuarios'))

    return render_template(
        'configuracion/personal/mostrar_usuario.html',
        usuario=usuario
    )


# ====================================================================================
# ============================       DIAGNOSTICO       ====================================
# ====================================================================================

# ============================ LISTAR DIAGNÓSTICOS ============================
@app.route('/configuracion/diagnostico')
def listar_diagnosticos():
    conexion = get_db_connection()
    cursor = conexion.cursor(pymysql.cursors.DictCursor)

    cursor.execute("""
                   SELECT id_diag, diagnostico, id_cie10
                   FROM cat_diag
                   ORDER BY id_diag DESC
                   """)
    diagnosticos = cursor.fetchall()
    conexion.close()

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
        conexion = get_db_connection()
        cursor = conexion.cursor()

        cursor.execute("""
                       INSERT INTO cat_diag (diagnostico, id_cie10)
                       VALUES (%s, %s)
                       """, (diag, id_cie10))

        conexion.commit()
        conexion.close()

    return redirect(url_for('listar_diagnosticos'))


# ============================ EDITAR DIAGNÓSTICO ============================
@app.route('/configuracion/diagnostico/editar/<int:id>', methods=['GET', 'POST'])
def editar_diagnostico(id):
    conexion = get_db_connection()
    cursor = conexion.cursor(pymysql.cursors.DictCursor)

    if request.method == 'POST':
        diag = request.form['diag']
        id_cie10 = request.form['id_cie10']

        cursor.execute("""
                       UPDATE cat_diag
                       SET diagnostico = %s,
                           id_cie10    = %s
                       WHERE id_diag = %s
                       """, (diag, id_cie10, id))

        conexion.commit()
        conexion.close()
        return redirect(url_for('listar_diagnosticos'))

    cursor.execute("SELECT * FROM cat_diag WHERE id_diag = %s", (id,))
    diagnostico = cursor.fetchone()
    conexion.close()

    return render_template(
        'configuracion/diagnostico/edit_diagnostico.html',
        diagnostico=diagnostico
    )

    # ==================== GESTIÓN DE CUENTAS (ACTIVOS) ====================

@app.route('/admin/cuenta_pacientes')
def cuenta_pacientes():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # 1) Intento con anticipos (si tienes tabla depositos_atencion con id_atencion,monto)
    #    Si no existe, cae al query sin anticipos y pone 0.
    sql_con_anticipos = """
        SELECT
            a.id_atencion,
            a.Id_exp,
            a.especialidad,
            a.fecha_ing,
            a.area,
            COALESCE(c.numero, 'Sin cama') AS num_cama,
            CONCAT(p.papell, ' ', p.sapell, ' ', p.nom_pac) AS paciente,

            (
                SELECT u.username
                FROM atencion_medicos am
                JOIN users u ON u.id = am.id_medico
                WHERE am.id_atencion = a.id_atencion
                ORDER BY am.id ASC
                LIMIT 1
            ) AS medico,

            COALESCE(cp.subtotal, 0) AS subtotal,

            COALESCE(dep.anticipos, 0) AS anticipos
        FROM atencion a
        JOIN pacientes p ON p.Id_exp = a.Id_exp
        LEFT JOIN camas c ON c.id_cama = a.id_cama
        LEFT JOIN (
            SELECT id_atencion, IFNULL(SUM(subtotal), 0) AS subtotal
            FROM cuenta_paciente
            GROUP BY id_atencion
        ) cp ON cp.id_atencion = a.id_atencion
        LEFT JOIN (
            SELECT id_atencion, IFNULL(SUM(monto), 0) AS anticipos
            FROM depositos_atencion
            GROUP BY id_atencion
        ) dep ON dep.id_atencion = a.id_atencion
        WHERE a.status = 'ABIERTA'
        ORDER BY a.fecha_ing DESC
    """

    sql_sin_anticipos = """
        SELECT
            a.id_atencion,
            a.Id_exp,
            a.especialidad,
            a.fecha_ing,
            a.area,
            COALESCE(c.numero, 'Sin cama') AS num_cama,
            CONCAT(p.papell, ' ', p.sapell, ' ', p.nom_pac) AS paciente,

            (
                SELECT u.username
                FROM atencion_medicos am
                JOIN users u ON u.id = am.id_medico
                WHERE am.id_atencion = a.id_atencion
                ORDER BY am.id ASC
                LIMIT 1
            ) AS medico,

            COALESCE(cp.subtotal, 0) AS subtotal
        FROM atencion a
        JOIN pacientes p ON p.Id_exp = a.Id_exp
        LEFT JOIN camas c ON c.id_cama = a.id_cama
        LEFT JOIN (
            SELECT id_atencion, IFNULL(SUM(subtotal), 0) AS subtotal
            FROM cuenta_paciente
            GROUP BY id_atencion
        ) cp ON cp.id_atencion = a.id_atencion
        WHERE a.status = 'ABIERTA'
        ORDER BY a.fecha_ing DESC
    """

    try:
        cursor.execute(sql_con_anticipos)
        rows = cursor.fetchall()
        anticipos_ok = True
    except Exception:
        conn.rollback()
        cursor.execute(sql_sin_anticipos)
        rows = cursor.fetchall()
        anticipos_ok = False

    cursor.close()
    conn.close()

    # 2) Cálculos (IVA 16%)
    for r in rows:
        # asegurar Decimal (subtotal puede venir Decimal/float/int)
        sub = Decimal(str(r.get('subtotal', 0) or 0))
        iva = (sub * Decimal('0.16'))
        total = sub + iva

        r['iva'] = iva
        r['total'] = total

        if not anticipos_ok:
            r['anticipos'] = Decimal('0.00')
        else:
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

    conn = get_db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    cur.execute("""
        SELECT a.id_atencion, a.Id_exp, a.fecha_ing,
               CONCAT(p.papell,' ',p.sapell,' ',p.nom_pac) AS paciente
        FROM atencion a
        JOIN pacientes p ON p.Id_exp = a.Id_exp
        WHERE a.id_atencion = %s
    """, (id_atencion,))
    header = cur.fetchone()

    cur.execute("""
        SELECT fecha, descripcion, cantidad, precio, subtotal
        FROM cuenta_paciente
        WHERE id_atencion = %s
        ORDER BY fecha ASC
    """, (id_atencion,))
    items = cur.fetchall()

    cur.execute("""
        SELECT IFNULL(SUM(subtotal),0) AS subtotal
        FROM cuenta_paciente
        WHERE id_atencion = %s
    """, (id_atencion,))
    sub = Decimal(str(cur.fetchone()['subtotal']))

    cur.close()
    conn.close()

    iva = sub * Decimal('0.16')
    total = sub + iva

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "CUENTA DEL PACIENTE", ln=1, align="C")
    pdf.ln(3)

    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, f"Atencion: {header['id_atencion']}   Expediente: {header['Id_exp']}", ln=1)
    pdf.cell(0, 6, f"Paciente: {header['paciente']}", ln=1)
    pdf.cell(0, 6, f"Fecha ingreso: {header['fecha_ing']}", ln=1)
    pdf.ln(4)

    pdf.set_font("Arial", "B", 9)
    pdf.cell(25, 7, "Fecha", 1)
    pdf.cell(90, 7, "Descripcion", 1)
    pdf.cell(15, 7, "Cant", 1, align="C")
    pdf.cell(25, 7, "Subtotal", 1, align="R")
    pdf.ln()

    pdf.set_font("Arial", "", 8)
    for it in items:
        pdf.cell(25, 7, str(it['fecha']), 1)
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
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    def obtener_camas_por_area(area_camas, area_atencion=None):
        """
        area_camas: valor en tabla camas.area (Urgencias/Hospitalizado)
        area_atencion: valor en tabla atencion.area (Ambulatorio/Urgencias/Hospitalizado)
        """
        filas = []

        # 1) Ambulatorio (sin cama física)
        if area_atencion == 'Ambulatorio':
            cur.execute("""
                SELECT 
                    a.id_atencion,
                    CONCAT('Consulta ', a.id_atencion) AS num_cama,
                    a.fecha_ing,
                    a.motivo AS motivo_ingreso,
                    a.status,
                    a.alergias,
                    p.Id_exp,
                    p.fecnac,
                    p.papell, p.sapell, p.nom_pac,
                    (SELECT u.username
                     FROM atencion_medicos am
                     JOIN users u ON u.id = am.id_medico
                     WHERE am.id_atencion = a.id_atencion
                     ORDER BY am.id ASC
                     LIMIT 1) AS medico_tratante
                FROM atencion a
                JOIN pacientes p ON p.Id_exp = a.Id_exp
                WHERE a.area = 'Ambulatorio' AND a.status = 'ABIERTA'
                ORDER BY a.fecha_ing DESC
            """)
            filas = cur.fetchall()

            for f in filas:
                f['estatus'] = 'OCUPADA'
                f['fecha'] = f.get('fecha_ing')
                f['motivo_recepcion'] = f.get('motivo_ingreso', '') or ''
                f['alta_med'] = 'NO'  # no existe en tu BD
                f['paciente_nombre'] = f"{f.get('papell','')} {f.get('sapell','')} {f.get('nom_pac','')}".strip()
                f['edad_txt'] = calcular_edad(f['fecnac']) if f.get('fecnac') else ''
                f['medico_txt'] = f.get('medico_tratante') or ''

            return filas

        # 2) Con cama física (Urgencias/Hospitalizado)
        cur.execute("""
            SELECT 
                c.id_cama,
                c.numero AS num_cama,
                c.ocupada,
                c.area AS area_cama,

                a.id_atencion,
                a.fecha_ing,
                a.motivo AS motivo_ingreso,
                a.status,

                p.Id_exp,
                p.fecnac,
                p.papell, p.sapell, p.nom_pac,

                (SELECT u.username
                 FROM atencion_medicos am
                 JOIN users u ON u.id = am.id_medico
                 WHERE am.id_atencion = a.id_atencion
                 ORDER BY am.id ASC
                 LIMIT 1) AS medico_tratante
            FROM camas c
            LEFT JOIN atencion a ON a.id_cama = c.id_cama AND a.status = 'ABIERTA'
            LEFT JOIN pacientes p ON p.Id_exp = a.Id_exp
            WHERE c.area = %s
            ORDER BY c.numero ASC
        """, (area_camas,))
        filas = cur.fetchall()

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
                f['motivo_recepcion'] = f.get('motivo_ingreso', '') or ''
                f['paciente_nombre'] = f"{f.get('papell','')} {f.get('sapell','')} {f.get('nom_pac','')}".strip()
                f['edad_txt'] = calcular_edad(f['fecnac']) if f.get('fecnac') else ''
                f['medico_txt'] = f.get('medico_tratante') or ''
                f['alta_med'] = 'NO'
                f['estatus'] = 'OCUPADA'

        return filas

    # Secciones
    consulta = obtener_camas_por_area(area_camas='Urgencias', area_atencion='Ambulatorio')  # CONSULTA
    preparacion = obtener_camas_por_area(area_camas='Urgencias')                           # PREPARACIÓN
    recuperacion = obtener_camas_por_area(area_camas='Hospitalizado')                      # RECUPERACIÓN

    cur.close()
    conn.close()

    return render_template(
        'administrativo/censo/censo.html',
        consulta=consulta,
        preparacion=preparacion,
        recuperacion=recuperacion
    )


@app.route('/admin/censo/imprimir')
def imprimir_censo():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # ========= HELPERS =========
    def fmt_fecha(x):
        if not x:
            return ""
        if isinstance(x, str):
            try:
                if len(x) >= 19:
                    return datetime.strptime(x[:19], "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y")
                return datetime.strptime(x[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
            except Exception:
                return ""
        try:
            return x.strftime("%d/%m/%Y")
        except Exception:
            return ""

    def calc_estancia(fecha_ing):
        if not fecha_ing:
            return ""
        if isinstance(fecha_ing, str):
            try:
                fecha_ing = datetime.strptime(fecha_ing[:19], "%Y-%m-%d %H:%M:%S")
            except Exception:
                try:
                    fecha_ing = datetime.strptime(fecha_ing[:10], "%Y-%m-%d")
                except Exception:
                    return ""
        dias = (datetime.now() - fecha_ing).days
        return f"{dias}d" if dias >= 0 else ""

    def obtener_area_con_camas(area_camas):
        cur.execute("""
            SELECT
                c.numero AS num_cama,
                c.ocupada,
                a.id_atencion,
                a.fecha_ing,
                a.motivo,
                a.alergias,
                p.Id_exp,
                p.fecnac,
                p.papell, p.sapell, p.nom_pac,
                (SELECT u.username
                 FROM atencion_medicos am
                 JOIN users u ON u.id = am.id_medico
                 WHERE am.id_atencion = a.id_atencion
                 ORDER BY am.id ASC
                 LIMIT 1) AS medico_tratante
            FROM camas c
            LEFT JOIN atencion a ON a.id_cama = c.id_cama AND a.status = 'ABIERTA'
            LEFT JOIN pacientes p ON p.Id_exp = a.Id_exp
            WHERE c.area = %s
            ORDER BY c.numero ASC
        """, (area_camas,))
        rows = cur.fetchall()

        # estatus: OCUPADA / LIBRE / MANTENIMIENTO (ocupada=1 pero sin atención)
        for r in rows:
            if not r.get("id_atencion"):
                r["estatus"] = "MANTENIMIENTO" if int(r.get("ocupada") or 0) == 1 else "LIBRE"
            else:
                r["estatus"] = "OCUPADA"
        return rows

    def obtener_consulta():
        cur.execute("""
            SELECT
                a.id_atencion,
                a.fecha_ing,
                a.motivo,
                a.alergias,
                p.Id_exp,
                p.fecnac,
                p.papell, p.sapell, p.nom_pac,
                (SELECT u.username
                 FROM atencion_medicos am
                 JOIN users u ON u.id = am.id_medico
                 WHERE am.id_atencion = a.id_atencion
                 ORDER BY am.id ASC
                 LIMIT 1) AS medico_tratante
            FROM atencion a
            JOIN pacientes p ON p.Id_exp = a.Id_exp
            WHERE a.area = 'Ambulatorio' AND a.status = 'ABIERTA'
            ORDER BY a.fecha_ing DESC
        """)
        rows = cur.fetchall()
        for r in rows:
            r["num_cama"] = f"Consulta {r['id_atencion']}"
            r["estatus"] = "OCUPADA"
        return rows

    hosp = obtener_area_con_camas("Hospitalizado")
    urg = obtener_area_con_camas("Urgencias")
    cons = obtener_consulta()

    cur.close()
    conn.close()

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




@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)

