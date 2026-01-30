from flask import Flask, render_template, request, redirect, url_for, session, flash
import pymysql
import bcrypt
from datetime import datetime, date
import pymysql.cursors
from estudios import estudios_bp

app = Flask(__name__)
app.register_blueprint(estudios_bp, url_prefix='/estudios')
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
            {'name': 'Médico', 'url': '#'},
            {'name': 'Estudios', 'url': url_for('estudios.estudios_home')},
            {'name': 'Configuración', 'url': '#'}
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
                   WHERE a.area = 'Hospitalizado'
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
                   WHERE a.area = 'Urgencias'
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
                   WHERE a.area = 'Ambulatorio'
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


@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada.', 'info')
    return redirect(url_for('login'))


#-------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)