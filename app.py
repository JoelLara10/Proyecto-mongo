from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from templates.administrativo.pacientes.doc_pacientes import pdf
import pymysql
import bcrypt
from datetime import datetime, date
import pymysql.cursors
import os
import zipfile
from datetime import datetime
from flask import render_template, flash



app = Flask(__name__)
app.register_blueprint(pdf)
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

    if role == 'admin':
        menu_options = [
            {'name': 'Administrativo', 'url': url_for('administrativo')},
            {'name': 'Médico', 'url': url_for('medico')},
            {'name': 'Estudios', 'url': '#'},
            {'name': 'Configuración', 'url': url_for('menu_configuracion')},
        ]

    return render_template('dashboard.html', role=role, menu_options=menu_options)


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
# ============================       CONFIGURACION      ===============================
# ====================================================================================



# -------------------- MENÚ CONFIGURACIÓN --------------------
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


# -------------------- MENÚ CAMAS --------------------
@app.route('/configuracion/menu_camas')
def menu_camas():
    if 'user_id' not in session:
        flash('Debes iniciar sesión', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM camas ORDER BY numero ASC")
    camas = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'configuracion/camas/menu_camas.html',
        camas=camas
    )


# -------------------- ALTA DE CAMAS --------------------
@app.route('/configuracion/alta_camas', methods=['GET', 'POST'])
def alta_camas():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            num_cama = request.form['num_cama']
            estatus = request.form['estatus']
            area = request.form['tipo']
            tipo_habitacion = request.form['hab']
            piso = request.form['piso']
            seccion = request.form['seccion']

            conn = get_db_connection()
            cursor = conn.cursor()

            # Validar duplicados
            cursor.execute(
                "SELECT id_cama FROM camas WHERE numero = %s",
                (num_cama,)
            )
            if cursor.fetchone():
                flash('Ya existe una cama con ese número.', 'warning')
                return redirect(url_for('alta_camas'))

            cursor.execute("""
                INSERT INTO camas
                (numero, estatus, area, tipo_habitacion, piso, seccion, ocupada)
                VALUES (%s, %s, %s, %s, %s, %s, 0)
            """, (
                num_cama,
                estatus,
                area,
                tipo_habitacion,
                piso,
                seccion
            ))

            conn.commit()
            cursor.close()
            conn.close()

            flash('Cama registrada correctamente ✅', 'success')
            return redirect(url_for('menu_camas'))

        except Exception as e:
            flash(f'Error al registrar cama: {e}', 'error')

    return render_template(
        'configuracion/camas/alta_camas.html'
    )


# -------------------- COPIAS DE SEGURIDAD --------------------
@app.route('/configuracion/copias')
def copias_seguridad():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('dashboard'))

    # Ruta base real del proyecto
    ruta_proyecto = current_app.root_path

    # Carpeta copias dentro de configuracion
    carpeta_copias = os.path.join(
        ruta_proyecto,
        'configuracion',
        'copias'
    )
    os.makedirs(carpeta_copias, exist_ok=True)

    fecha = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    nombre_zip = f'respaldo_{fecha}.zip'
    ruta_zip = os.path.join(carpeta_copias, nombre_zip)

    with zipfile.ZipFile(ruta_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for carpeta, _, archivos in os.walk(ruta_proyecto):

            # Excluir copias y entorno virtual
            if 'copias' in carpeta or 'venv' in carpeta:
                continue

            for archivo in archivos:
                ruta_completa = os.path.join(carpeta, archivo)
                ruta_relativa = os.path.relpath(
                    ruta_completa,
                    ruta_proyecto
                )
                zipf.write(ruta_completa, ruta_relativa)

    flash('Copia de seguridad creada correctamente 🛡️', 'success')

    return render_template(
        'configuracion/copias/copias_seguridad.html',
        archivo=nombre_zip
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
        INNER JOIN atencion a ON p.Id_exp = a.Id_exp
        WHERE a.id_atencion = %s
    """, (id_atencion,))
    paciente = cursor.fetchone()

    if not paciente:
        flash('Paciente no encontrado.', 'error')
        return redirect(url_for('dashboard'))

    # ================= LABORATORIO =================
    cursor.execute("""
        SELECT el.id_examen, 
               GROUP_CONCAT(c.nombre SEPARATOR ', ') AS estudios,
               u.papell AS medico,
               el.observaciones, 
               el.fecha
        FROM examenes_laboratorio el
        JOIN examenes_laboratorio_det eld ON el.id_examen = eld.id_examen
        JOIN catalogo_examenes_laboratorio c ON eld.id_catalogo = c.id_catalogo
        JOIN users u ON el.id_medico = u.id
        WHERE el.id_atencion = %s
        GROUP BY el.id_examen
        ORDER BY el.id_examen DESC
    """, (id_atencion,))
    laboratorio = cursor.fetchall()

    # ================= GABINETE =================
    cursor.execute("""
                   SELECT eg.id_examen,
                          eg.fecha,
                          eg.observaciones,
                          eg.id_atencion,
                          u.papell                                       AS medico,
                          GROUP_CONCAT(egd.nombre_examen SEPARATOR ', ') AS estudios
                   FROM examenes_gabinete eg
                            JOIN examenes_gabinete_det egd
                                 ON eg.id_examen = egd.id_examen
                            JOIN users u
                                 ON eg.id_medico = u.id
                   WHERE eg.id_atencion = %s
                   GROUP BY eg.id_examen
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


@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada.', 'info')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)