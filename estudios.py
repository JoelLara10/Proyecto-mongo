from flask import Blueprint, render_template, request, redirect, url_for, flash
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

def contar_solicitudes_pendientes(cursor):
    """Función auxiliar para contar solicitudes pendientes (id_examen únicos)"""
    cursor.execute("""
        SELECT COUNT(DISTINCT id_examen) as count 
        FROM examenes_laboratorio 
        WHERE LOWER(estado) = 'pendiente'
    """)
    resultado_lab = cursor.fetchone()
    lab_pendientes = resultado_lab['count'] if isinstance(resultado_lab, dict) else resultado_lab[0]
    
    cursor.execute("""
        SELECT COUNT(DISTINCT id_examen) as count 
        FROM examenes_gabinete_det 
        WHERE UPPER(estado) = 'PENDIENTE'
    """)
    resultado_gab = cursor.fetchone()
    gab_pendientes = resultado_gab['count'] if isinstance(resultado_gab, dict) else resultado_gab[0]
    
    total_pendientes = lab_pendientes + gab_pendientes
    
    return lab_pendientes, gab_pendientes, total_pendientes
#------------------------------------------------------------------------------------------------------------
estudios_bp = Blueprint('estudios', __name__)

# =========================
# HOME / LISTADOS
# =========================
@estudios_bp.route('/')
def estudios_home():
    vista = request.args.get('vista')
    solicitudes = []

    conn = get_db_connection()
    cursor = conn.cursor()
    # =========================
    # CONTAR SOLICITUDES PENDIENTES
    # =========================
    cursor.execute("""
        SELECT COUNT(DISTINCT id_examen) as count 
        FROM examenes_laboratorio 
        WHERE LOWER(estado) = 'pendiente'
    """)
    resultado_lab = cursor.fetchone()
    lab_pendientes = resultado_lab['count'] if isinstance(resultado_lab, dict) else resultado_lab[0]
    
    # Contar solicitudes pendientes de gabinete (id_examen únicos)
    cursor.execute("""
        SELECT COUNT(DISTINCT id_examen) as count 
        FROM examenes_gabinete_det 
        WHERE UPPER(estado) = 'PENDIENTE'
    """)
    resultado_gab = cursor.fetchone()
    gab_pendientes = resultado_gab['count'] if isinstance(resultado_gab, dict) else resultado_gab[0]
    
    total_pendientes = lab_pendientes + gab_pendientes

    # -------- LABORATORIO PENDIENTES --------
    if vista == 'solicitudes_laboratorio':
        cursor.execute("""
            SELECT 
                el.id_examen,
                el.fecha,
                CONCAT(p.nom_pac,' ',p.papell,' ',p.sapell) AS paciente,
                u.papell AS medico,
                c.numero AS habitacion,
                GROUP_CONCAT(cel.nombre SEPARATOR ', ') AS estudios
            FROM examenes_laboratorio el
            JOIN atencion a ON el.id_atencion = a.id_atencion
            LEFT JOIN camas c ON a.id_cama = c.id_cama
            JOIN pacientes p ON a.Id_exp = p.Id_exp
            JOIN users u ON el.id_medico = u.id
            LEFT JOIN examenes_laboratorio_det eld ON el.id_examen = eld.id_examen
            LEFT JOIN catalogo_examenes_laboratorio cel ON eld.id_catalogo = cel.id_catalogo
            WHERE LOWER(el.estado) = 'pendiente'
            GROUP BY el.id_examen
            ORDER BY el.fecha DESC
        """)
        solicitudes = cursor.fetchall()

    # -------- LABORATORIO REALIZADOS --------
    if vista == 'resultados_laboratorio':
        cursor.execute("""
            SELECT 
                el.id_examen,
                el.fecha,
                el.fecha_realizado,
                CONCAT(p.nom_pac,' ',p.papell,' ',p.sapell) AS paciente,
                u.papell AS medico,
                c.numero AS habitacion,
                GROUP_CONCAT(cel.nombre SEPARATOR ', ') AS estudios
            FROM examenes_laboratorio el
            JOIN atencion a ON el.id_atencion = a.id_atencion
            LEFT JOIN camas c ON a.id_cama = c.id_cama
            JOIN pacientes p ON a.Id_exp = p.Id_exp
            JOIN users u ON el.id_medico = u.id
            LEFT JOIN examenes_laboratorio_det eld ON el.id_examen = eld.id_examen
            LEFT JOIN catalogo_examenes_laboratorio cel ON eld.id_catalogo = cel.id_catalogo
            WHERE LOWER(el.estado) = 'realizado'
            GROUP BY el.id_examen
            ORDER BY el.fecha_realizado DESC
        """)
        solicitudes = cursor.fetchall()

    # -------- GABINETE PENDIENTES --------
    if vista == 'solicitudes_gabinete':
        cursor.execute("""
            SELECT 
                eg.id_examen,
                eg.fecha,
                CONCAT(p.papell,' ',p.sapell,' ',p.nom_pac) AS paciente,
                u.papell AS medico,
                c.numero AS habitacion,
                GROUP_CONCAT(egd.nombre_examen SEPARATOR ', ') AS estudios
            FROM examenes_gabinete eg
            JOIN atencion a ON eg.id_atencion = a.id_atencion
            LEFT JOIN camas c ON a.id_cama = c.id_cama
            JOIN pacientes p ON a.Id_exp = p.Id_exp
            JOIN users u ON eg.id_medico = u.id
            JOIN examenes_gabinete_det egd ON eg.id_examen = egd.id_examen
            WHERE UPPER(egd.estado) = 'PENDIENTE'
            GROUP BY eg.id_examen
            ORDER BY eg.fecha DESC
        """)
        solicitudes = cursor.fetchall()

    # ---------------- GABINETE REALIZADOS ----------------
    if vista == 'resultados_gabinete':
        cursor.execute("""
            SELECT 
                eg.id_examen,
                eg.fecha,
                egd.fecha_realizado,
                CONCAT(p.papell,' ',p.sapell,' ',p.nom_pac) AS paciente,
                u.papell AS medico,
                c.numero AS habitacion,
                GROUP_CONCAT(egd.nombre_examen SEPARATOR ', ') AS estudios
            FROM examenes_gabinete eg
            JOIN examenes_gabinete_det egd ON eg.id_examen = egd.id_examen
            JOIN atencion a ON eg.id_atencion = a.id_atencion
            LEFT JOIN camas c ON a.id_cama = c.id_cama
            JOIN pacientes p ON a.Id_exp = p.Id_exp
            JOIN users u ON eg.id_medico = u.id
            WHERE UPPER(egd.estado) = 'REALIZADO'
            GROUP BY eg.id_examen
            ORDER BY egd.fecha_realizado DESC
        """)
        solicitudes = cursor.fetchall()

    cursor.close()
    conn.close()

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
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            eg.id_examen,
            CONCAT(p.papell,' ',p.sapell,' ',p.nom_pac) AS paciente,
            c.numero AS habitacion,
            GROUP_CONCAT(egd.nombre_examen SEPARATOR ', ') AS estudios
        FROM examenes_gabinete eg
        JOIN atencion a ON eg.id_atencion = a.id_atencion
        LEFT JOIN camas c ON a.id_cama = c.id_cama
        JOIN pacientes p ON a.Id_exp = p.Id_exp
        JOIN examenes_gabinete_det egd ON eg.id_examen = egd.id_examen
        WHERE eg.id_examen = %s
        GROUP BY eg.id_examen
    """, (id_examen,))
    solicitud = cursor.fetchone()

    if request.method == 'POST':
        observaciones = request.form.get('observaciones', '')
        files = request.files.getlist('archivos')

        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER_GAB, filename))

                cursor.execute("""
                    UPDATE examenes_gabinete_det
                    SET archivo_resultado = %s,
                        observaciones = %s,
                        fecha_realizado = %s,
                        estado = 'REALIZADO'
                    WHERE id_examen = %s
                """, (filename, observaciones, datetime.now(), id_examen))

        conn.commit()
        cursor.close()
        conn.close()

        flash('Resultados de gabinete subidos correctamente', 'success')
        return redirect(url_for('estudios.estudios_home', vista='solicitudes_gabinete'))
    # Obtener conteo de solicitudes pendientes
    lab_pendientes, gab_pendientes, total_pendientes = contar_solicitudes_pendientes(cursor)
        

    cursor.close()
    conn.close()

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
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            el.id_examen,
            CONCAT(p.nom_pac,' ',p.papell,' ',p.sapell) AS paciente,
            c.numero AS habitacion,
            GROUP_CONCAT(cel.nombre SEPARATOR ', ') AS estudios
        FROM examenes_laboratorio el
        JOIN atencion a ON el.id_atencion = a.id_atencion
        LEFT JOIN camas c ON a.id_cama = c.id_cama
        JOIN pacientes p ON a.Id_exp = p.Id_exp
        LEFT JOIN examenes_laboratorio_det eld ON el.id_examen = eld.id_examen
        LEFT JOIN catalogo_examenes_laboratorio cel ON eld.id_catalogo = cel.id_catalogo
        WHERE el.id_examen = %s
        GROUP BY el.id_examen
    """, (id_examen,))
    solicitud = cursor.fetchone()

    if request.method == 'POST':
        observaciones = request.form.get('observaciones', '')
        files = request.files.getlist('archivos')

        nombres_archivos = []

        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER_LAB, filename))
                nombres_archivos.append(filename)

        cursor.execute("""
            UPDATE examenes_laboratorio
            SET archivo_resultado = %s,
                observaciones = %s,
                fecha_realizado = %s,
                estado = 'realizado'
            WHERE id_examen = %s
        """, (
            ','.join(nombres_archivos),
            observaciones,
            datetime.now(),
            id_examen
        ))

        conn.commit()
        cursor.close()
        conn.close()

        flash('Resultados de laboratorio subidos correctamente', 'success')
        return redirect(url_for('estudios.estudios_home', vista='solicitudes_laboratorio'))
    # Obtener conteo de solicitudes pendientes
    lab_pendientes, gab_pendientes, total_pendientes = contar_solicitudes_pendientes(cursor)

    cursor.close()
    conn.close()

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
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1) Información general del estudio
    cursor.execute("""
        SELECT 
            el.id_examen,
            CONCAT(p.nom_pac,' ',p.papell,' ',p.sapell) AS paciente,
            c.numero AS habitacion,
            el.archivo_resultado,
            el.observaciones
        FROM examenes_laboratorio el
        JOIN atencion a ON el.id_atencion = a.id_atencion
        LEFT JOIN camas c ON a.id_cama = c.id_cama
        JOIN pacientes p ON a.Id_exp = p.Id_exp
        WHERE el.id_examen = %s
    """, (id_examen,))

    solicitud = cursor.fetchone()

    # Si no existe
    if not solicitud:
        cursor.close()
        conn.close()
        flash('Solicitud no encontrada', 'danger')
        return redirect(url_for('estudios.estudios_home', vista='resultados_laboratorio'))

    # Extraer los campos sea que 'solicitud' sea dict o tuple
    if isinstance(solicitud, dict):
        paciente = solicitud.get('paciente')
        habitacion = solicitud.get('habitacion')
        archivo_resultado = solicitud.get('archivo_resultado') or ''
        observaciones = solicitud.get('observaciones') or ''
    else:
        # tupla: (id_examen, paciente, habitacion, archivo_resultado, observaciones)
        # defensivamente comprobamos longitud
        try:
            _, paciente, habitacion, archivo_resultado, observaciones = solicitud
            archivo_resultado = archivo_resultado or ''
            observaciones = observaciones or ''
        except Exception:
            # fallback por si la forma es distinta
            paciente = solicitud[1] if len(solicitud) > 1 else ''
            habitacion = solicitud[2] if len(solicitud) > 2 else ''
            archivo_resultado = solicitud[3] if len(solicitud) > 3 else ''
            observaciones = solicitud[4] if len(solicitud) > 4 else ''

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
                        cursor.close()
                        conn.close()
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
                        cursor.close()
                        conn.close()
                        return redirect(request.url)

                    # Añadimos el nombre **visible** que guardaremos en la BD.
                    # Si prefieres almacenar el nombre con prefijo (nombre_guardado_en_disco), cámbialo por esa variable.
                    nuevos_guardados.append(filename_secure)
                else:
                    # formato no permitido o filename vacío
                    if file and file.filename:
                        flash(f'Formato no permitido para {file.filename}', 'danger')
                        cursor.close()
                        conn.close()
                        return redirect(request.url)

        # Unir archivos restantes + nuevos
        archivos_finales = archivos + nuevos_guardados

        # Actualizar DB: archivo_resultado, fecha_realizado y estado
        ahora = datetime.now()
        archivos_db = ','.join(archivos_finales)

        cursor.execute("""
            UPDATE examenes_laboratorio
            SET archivo_resultado = %s,
                fecha_realizado = %s,
                estado = 'realizado'
            WHERE id_examen = %s
        """, (archivos_db, ahora, id_examen))

        conn.commit()
        cursor.close()
        conn.close()

        flash('Cambios guardados correctamente', 'success')
        return redirect(url_for('estudios.estudios_home', vista='resultados_laboratorio'))

    # GET -> renderizar la vista de edición
    # Obtener conteo de solicitudes pendientes
    lab_pendientes, gab_pendientes, total_pendientes = contar_solicitudes_pendientes(cursor)
    cursor.close()
    conn.close()

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
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1) Información general del estudio con datos de examenes_gabinete_det
    # Obtener solo UN registro por id_examen ya que los archivos son los mismos
    cursor.execute("""
        SELECT 
            eg.id_examen,
            CONCAT(p.nom_pac,' ',p.papell,' ',p.sapell) AS paciente,
            c.numero AS habitacion,
            MAX(egd.observaciones) AS observaciones,
            MAX(egd.archivo_resultado) AS archivo_resultado
        FROM examenes_gabinete eg
        JOIN atencion a ON eg.id_atencion = a.id_atencion
        LEFT JOIN camas c ON a.id_cama = c.id_cama
        JOIN pacientes p ON a.Id_exp = p.Id_exp
        JOIN examenes_gabinete_det egd ON eg.id_examen = egd.id_examen
        WHERE eg.id_examen = %s
        GROUP BY eg.id_examen, p.nom_pac, p.papell, p.sapell, c.numero
        LIMIT 1
    """, (id_examen,))

    solicitud = cursor.fetchone()

    # Si no existe
    if not solicitud:
        cursor.close()
        conn.close()
        flash('Solicitud no encontrada', 'danger')
        return redirect(url_for('estudios.estudios_home', vista='resultados_gabinete'))

    # Extraer los campos sea que 'solicitud' sea dict o tuple
    if isinstance(solicitud, dict):
        paciente = solicitud.get('paciente')
        habitacion = solicitud.get('habitacion')
        archivo_resultado = solicitud.get('archivo_resultado') or ''
        observaciones = solicitud.get('observaciones') or ''
    else:
        # tupla: (id_examen, paciente, habitacion, observaciones, archivo_resultado)
        try:
            _, paciente, habitacion, observaciones, archivo_resultado = solicitud
            archivo_resultado = archivo_resultado or ''
            observaciones = observaciones or ''
        except Exception:
            # fallback por si la forma es distinta
            paciente = solicitud[1] if len(solicitud) > 1 else ''
            habitacion = solicitud[2] if len(solicitud) > 2 else ''
            observaciones = solicitud[3] if len(solicitud) > 3 else ''
            archivo_resultado = solicitud[4] if len(solicitud) > 4 else ''

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
                        cursor.close()
                        conn.close()
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
                        cursor.close()
                        conn.close()
                        return redirect(request.url)

                    # Añadimos el nombre **visible** que guardaremos en la BD.
                    nuevos_guardados.append(filename_secure)
                else:
                    # formato no permitido o filename vacío
                    if file and file.filename:
                        flash(f'Formato no permitido para {file.filename}', 'danger')
                        cursor.close()
                        conn.close()
                        return redirect(request.url)

        # Unir archivos restantes + nuevos
        archivos_finales = archivos + nuevos_guardados

        # Actualizar DB: archivo_resultado, fecha_realizado, estado y observaciones en TODOS los registros de examenes_gabinete_det para este id_examen
        ahora = datetime.now()
        archivos_db = ','.join(archivos_finales)

        cursor.execute("""
            UPDATE examenes_gabinete_det
            SET archivo_resultado = %s,
                fecha_realizado = %s,
                estado = 'REALIZADO',
                observaciones = %s
            WHERE id_examen = %s
        """, (archivos_db, ahora, nuevas_observaciones, id_examen))

        conn.commit()
        cursor.close()
        conn.close()

        flash('Cambios guardados correctamente', 'success')
        return redirect(url_for('estudios.estudios_home', vista='resultados_gabinete'))

    # GET -> renderizar la vista de edición
    # Obtener conteo de solicitudes pendientes
    lab_pendientes, gab_pendientes, total_pendientes = contar_solicitudes_pendientes(cursor)
    cursor.close()
    conn.close()

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
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            el.id_examen,
            CONCAT(p.nom_pac,' ',p.papell,' ',p.sapell) AS paciente,
            el.archivo_resultado
        FROM examenes_laboratorio el
        JOIN atencion a ON el.id_atencion = a.id_atencion
        JOIN pacientes p ON a.Id_exp = p.Id_exp
        WHERE el.id_examen = %s
    """, (id_examen,))

    row = cursor.fetchone()
    # Obtener conteo de solicitudes pendientes
    lab_pendientes, gab_pendientes, total_pendientes = contar_solicitudes_pendientes(cursor)
    cursor.close()
    conn.close()

    if not row:
        flash('Resultados no encontrados', 'danger')
        return redirect(url_for('estudios.estudios_home', vista='resultados_laboratorio'))

    # Compatibilidad tuple / dict
    if isinstance(row, dict):
        paciente = row.get('paciente')
        archivos_db = row.get('archivo_resultado') or ''
    else:
        _, paciente, archivos_db = row

    archivos = []
    if archivos_db:
        archivos = [a.strip() for a in archivos_db.split(',') if a.strip()]

    
    

    return render_template(
        'estudios/index.html',
        vista='ver_resultado_laboratorio',
        paciente=paciente,
        archivos=archivos,
        lab_pendientes=lab_pendientes,
        gab_pendientes=gab_pendientes,
        total_pendientes=total_pendientes
    )


# =========================
# VISTA PREVIA RESULTADOS GABINETE
# =========================
@estudios_bp.route('/ver_resultado_gabinete/<int:id_examen>')
def ver_resultado_gabinete(id_examen):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT archivo_resultado
        FROM examenes_gabinete_det
        WHERE id_examen = %s
          AND estado = 'REALIZADO'
    """, (id_examen,))

    row = cursor.fetchone()
    # Obtener conteo de solicitudes pendientes
    lab_pendientes, gab_pendientes, total_pendientes = contar_solicitudes_pendientes(cursor)
    cursor.close()
    conn.close()

    archivos = []

    if row:
        # soporta tuple o dict
        archivo_resultado = (
            row['archivo_resultado']
            if isinstance(row, dict)
            else row[0]
        )

        if archivo_resultado:
            for nombre in archivo_resultado.split(','):
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
        lab_pendientes=lab_pendientes,
        gab_pendientes=gab_pendientes,
        total_pendientes=total_pendientes
    )


# =========================
# ELIMINAR RESULTADO GABINETE
# =========================
@estudios_bp.route('/eliminar_resultado_gabinete/<int:id_examen>')
def eliminar_resultado_gabinete(id_examen):
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1) Obtener archivos asociados
    cursor.execute("""
        SELECT archivo_resultado
        FROM examenes_gabinete_det
        WHERE id_examen = %s
    """, (id_examen,))

    rows = cursor.fetchall()

    # 2) Eliminar archivos físicos
    try:
        for row in rows:
            archivo = row[0]
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
    cursor.execute("""
        DELETE FROM examenes_gabinete_det
        WHERE id_examen = %s
    """, (id_examen,))

    # 4) Eliminar encabezado
    cursor.execute("""
        DELETE FROM examenes_gabinete
        WHERE id_examen = %s
    """, (id_examen,))

    conn.commit()
    cursor.close()
    conn.close()

    flash('Solicitud de gabinete eliminada correctamente', 'success')
    return redirect(url_for('estudios.estudios_home', vista='resultados_gabinete'))

# =========================
# ELIMINAR RESULTADO LABORATORIO
# =========================
@estudios_bp.route('/eliminar_resultado_laboratorio/<int:id_examen>')
def eliminar_resultado_laboratorio(id_examen):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1) Obtener archivo asociado si existe
    cursor.execute("""
        SELECT archivo_resultado 
        FROM examenes_laboratorio 
        WHERE id_examen = %s
    """, (id_examen,))
    
    resultado = cursor.fetchone()
    
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
    cursor.execute("""
        DELETE FROM examenes_laboratorio_det 
        WHERE id_examen = %s
    """, (id_examen,))
    
    # 4) Eliminar encabezado
    cursor.execute("""
        DELETE FROM examenes_laboratorio 
        WHERE id_examen = %s
    """, (id_examen,))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    flash('Solicitud de laboratorio eliminada correctamente', 'success')
    return redirect(url_for('estudios.estudios_home', vista='resultados_laboratorio'))