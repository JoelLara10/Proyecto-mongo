# utils/backups.py (versión actualizada con restauración)

import os
import json
import csv
import zipfile
import io
import tempfile
from datetime import datetime
from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import bcrypt
from flask import (
    render_template, request, session, flash,
    redirect, url_for, current_app, send_from_directory
)
from bd import get_db_connection
import pymysql
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore

RUTA_CONFIG_AUTO = 'configuracion/copias/config_auto.json'

RUTA_CONTROL = 'configuracion/copias/control_backups.json'

def limpiar_backups(max_por_tipo=4):
    carpeta = os.path.join(
        current_app.root_path,
        'configuracion',
        'copias'
    )

    if not os.path.exists(carpeta):
        return

    backups = {}

    for f in os.listdir(carpeta):
        ruta = os.path.join(carpeta, f)

        if not os.path.isfile(ruta) or not f.startswith('backup_'):
            continue

        nombre = os.path.splitext(f)[0]
        partes = nombre.split('_')

        if len(partes) < 3 or partes[0] != 'backup':
            continue

        # === AGRUPACIÓN ROBUSTA ===
        if partes[1] == 'auto':
            tipo = partes[2]
            grupo = f'auto_{tipo}'
        elif partes[1] == 'manual':
            tipo = partes[2]
            grupo = f'manual_{tipo}'
        else:
            # Legacy: backups manuales sin la palabra "manual"
            tipo = partes[1]
            grupo = f'manual_{tipo}'

        backups.setdefault(grupo, []).append(ruta)

    # === LOGGING PARA DIAGNOSTICAR ===
    current_app.logger.info(
        f'Backups encontrados por grupo: { {k: len(v) for k, v in backups.items()} }'
    )

    for grupo, archivos in backups.items():
        current_app.logger.info(f'Procesando grupo {grupo} → {len(archivos)} backups')
        archivos.sort(key=os.path.getmtime, reverse=True)

        for archivo in archivos[max_por_tipo:]:
            try:
                os.remove(archivo)
                current_app.logger.info(
                    f'Backup eliminado ({grupo}): {os.path.basename(archivo)}'
                )
            except Exception as e:
                current_app.logger.error(f'Error eliminando {archivo}: {str(e)}')

def validar_admin(username, password):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    cursor.execute("""
        SELECT username, password, role
        FROM users
        WHERE username = %s
        LIMIT 1
    """, (username,))

    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if not user:
        return False

    # 🔐 bcrypt → convertir a bytes
    password_input = password.encode('utf-8')
    password_hash = user['password'].encode('utf-8')

    # 🔐 Verificar contraseña bcrypt
    if not bcrypt.checkpw(password_input, password_hash):
        return False

    # 🔐 Verificar rol
    if user['role'] != 'admin':
        return False

    return True

def cargar_control():
    ruta = os.path.join(current_app.root_path, RUTA_CONTROL)
    if not os.path.exists(ruta):
        return {}
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            data = f.read().strip()
            return json.loads(data) if data else {}
    except:
        return {}

def guardar_control(data):
    ruta = os.path.join(current_app.root_path, RUTA_CONTROL)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def obtener_tablas_bd(cursor):
    cursor.execute("""
        SELECT TABLE_NAME, UPDATE_TIME 
        FROM information_schema.TABLES 
        WHERE TABLE_SCHEMA = DATABASE()
    """)
    return cursor.fetchall()

def list_backups():
    carpeta = os.path.join(current_app.root_path, 'configuracion', 'copias')
    backups = []
    for file in os.listdir(carpeta):
        if file.startswith('backup_') and file.endswith(('.sql', '.json', '.zip')):
            backups.append(file)
    return sorted(backups, reverse=True)  # Más recientes primero

# ==================== FUNCIÓN PRINCIPAL ====================
def backup_bd():

    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    tablas = obtener_tablas_bd(cursor)
    backups = list_backups()

    download_filename = request.args.get('download')  # Para mostrar descarga después de POST

    if request.method == 'POST':
        action = request.form.get('action')

        # 🔐 Validación de administrador
        auth_user = request.form.get('auth_user')
        auth_pass = request.form.get('auth_pass')

        if action in ['backup', 'restore']:
            if not auth_user or not auth_pass:
                flash('Debes confirmar usuario y contraseña de administrador.', 'danger')
                return redirect(request.url)

            if not validar_admin(auth_user, auth_pass):
                flash('Credenciales inválidas o usuario sin permisos de administrador.', 'danger')
                return redirect(request.url)

        if action == 'backup':
            tipo = request.form.get('tipo')
            formato = request.form.get('formato')
            tablas_sel = request.form.getlist('tablas')

            # Si es Completa y no seleccionó tablas → respaldar TODAS
            if tipo == 'completa' and not tablas_sel:
                tablas_sel = [t['TABLE_NAME'] for t in tablas]

            if not tablas_sel:
                flash('Debes seleccionar al menos una tabla.', 'warning')
                return redirect(request.url)

            # Filtrar tablas según tipo (completa / diferencial / incremental)
            control = cargar_control()
            ultima_completa = control.get('ultima_completa')
            ultima_copia = control.get('ultima_copia')

            tablas_finales = []
            for tabla in tablas_sel:
                t_info = next((t for t in tablas if t['TABLE_NAME'] == tabla), None)
                if not t_info:
                    continue

                if tipo == 'completa':
                    tablas_finales.append(tabla)
                elif tipo == 'diferencial' and ultima_completa:
                    if t_info['UPDATE_TIME'] and str(t_info['UPDATE_TIME']) > ultima_completa:
                        tablas_finales.append(tabla)
                elif tipo == 'incremental' and ultima_copia:
                    if t_info['UPDATE_TIME'] and str(t_info['UPDATE_TIME']) > ultima_copia:
                        tablas_finales.append(tabla)

            if not tablas_finales:
                flash('No hay cambios para respaldar en modo diferencial/incremental.', 'warning')
                return redirect(request.url)

            # Ruta de guardado
            carpeta = os.path.join(current_app.root_path, 'configuracion', 'copias')
            os.makedirs(carpeta, exist_ok=True)
            fecha = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

            nombre_archivo = None
            try:
                if formato == 'sql':
                    # Ejemplo para SQL (haz lo mismo en json, csv/zip, excel, pdf)
                    nombre_archivo = f'backup_manual_{tipo}_{fecha}.sql'
                    ruta_archivo = os.path.join(carpeta, nombre_archivo)

                    with open(ruta_archivo, 'w', encoding='utf-8') as f:
                        f.write("-- Backup generado por la aplicación\n")
                        f.write("SET FOREIGN_KEY_CHECKS=0;\n\n")

                        # 1️⃣ Crear tablas
                        for tabla in tablas_finales:
                            f.write(f"DROP TABLE IF EXISTS `{tabla}`;\n")
                            cursor.execute(f"SHOW CREATE TABLE `{tabla}`")
                            create_sql = cursor.fetchone()['Create Table']
                            f.write(create_sql + ";\n\n")

                        # 2️⃣ Insertar datos
                        for tabla in tablas_finales:
                            cursor.execute(f"SELECT * FROM `{tabla}`")
                            filas = cursor.fetchall()
                            if not filas:
                                continue

                            columnas = filas[0].keys()
                            columnas_sql = ", ".join([f"`{c}`" for c in columnas])

                            for fila in filas:
                                valores = []
                                for v in fila.values():
                                    if v is None:
                                        valores.append("NULL")
                                    else:
                                        valores.append(pymysql.converters.escape_item(v, conn))
                                valores_sql = ", ".join(valores)
                                f.write(
                                    f"INSERT INTO `{tabla}` ({columnas_sql}) VALUES ({valores_sql});\n"
                                )
                            f.write("\n")

                        f.write("SET FOREIGN_KEY_CHECKS=1;\n")


                elif formato == 'json':
                    # Ejemplo para SQL (haz lo mismo en json, csv/zip, excel, pdf)
                    nombre_archivo = f'backup_manual_{tipo}_{fecha}.json'
                    ruta_archivo = os.path.join(carpeta, nombre_archivo)
                    respaldo = {}
                    for tabla in tablas_finales:
                        cursor.execute(f"SELECT * FROM `{tabla}`")
                        respaldo[tabla] = cursor.fetchall()

                    with open(ruta_archivo, 'w', encoding='utf-8') as f:
                        json.dump(respaldo, f, indent=4, default=str)

                elif formato == 'csv':
                    # Ejemplo para SQL (haz lo mismo en json, csv/zip, excel, pdf)
                    nombre_archivo = f'backup_manual_{tipo}_{fecha}.zip'
                    ruta_archivo = os.path.join(carpeta, nombre_archivo)

                    with zipfile.ZipFile(ruta_archivo, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for tabla in tablas_finales:
                            cursor.execute(f"SELECT * FROM `{tabla}`")
                            filas = cursor.fetchall()
                            if filas:
                                csv_buffer = io.StringIO()
                                writer = csv.DictWriter(csv_buffer, fieldnames=filas[0].keys())
                                writer.writeheader()
                                writer.writerows(filas)
                                zipf.writestr(f"{tabla}_{tipo}_{fecha}.csv", csv_buffer.getvalue())

                elif formato == 'excel':
                    # Ejemplo para SQL (haz lo mismo en json, csv/zip, excel, pdf)
                    nombre_archivo = f'backup_manual_{tipo}_{fecha}.xlsx'
                    ruta_archivo = os.path.join(carpeta, nombre_archivo)

                    wb = Workbook()
                    wb.remove(wb.active)  # Quitar hoja vacía

                    for tabla in tablas_finales:
                        ws = wb.create_sheet(title=tabla)
                        cursor.execute(f"SELECT * FROM `{tabla}`")
                        filas = cursor.fetchall()

                        if not filas:
                            continue

                        # Encabezados
                        ws.append(list(filas[0].keys()))

                        # Datos
                        for fila in filas:
                            ws.append(list(fila.values()))

                    wb.save(ruta_archivo)

                elif formato == 'pdf':
                    # Ejemplo para SQL (haz lo mismo en json, csv/zip, excel, pdf)
                    nombre_archivo = f'backup_manual_{tipo}_{fecha}.pdf'
                    ruta_archivo = os.path.join(carpeta, nombre_archivo)

                    doc = SimpleDocTemplate(ruta_archivo, pagesize=letter)
                    styles = getSampleStyleSheet()
                    elementos = []

                    elementos.append(Paragraph(
                        f"Reporte de respaldo ({tipo.upper()}) - {fecha}",
                        styles['Title']
                    ))

                    for tabla in tablas_finales:
                        cursor.execute(f"SELECT * FROM `{tabla}`")
                        filas = cursor.fetchall()

                        elementos.append(Paragraph(
                            f"Tabla: {tabla}",
                            styles['Heading2']
                        ))

                        if not filas:
                            elementos.append(Paragraph("Sin datos", styles['Normal']))
                            continue

                        data = [list(filas[0].keys())]
                        for fila in filas:
                            data.append([str(v) for v in fila.values()])

                        # Ancho disponible de la hoja
                        page_width, page_height = letter
                        margen = 40
                        ancho_disponible = page_width - (margen * 2)

                        num_columnas = len(data[0])
                        ancho_columnas = ancho_disponible / num_columnas

                        tabla_pdf = Table(
                            data,
                            colWidths=[ancho_columnas] * num_columnas,
                            repeatRows=1  # Repetir encabezado en cada página
                        )

                        tabla_pdf.setStyle(TableStyle([
                            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('FONTSIZE', (0, 0), (-1, -1), 8),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                            ('TOPPADDING', (0, 0), (-1, -1), 4),
                        ]))

                        elementos.append(tabla_pdf)

                    doc.build(elementos)

                # Actualizar control de backups
                ahora = datetime.now().isoformat()
                control['ultima_copia'] = ahora
                if tipo == 'completa':
                    control['ultima_completa'] = ahora
                guardar_control(control)

                flash(f'¡Respaldo {tipo} ({formato.upper()}) creado exitosamente!', 'success')

                # Redirigir con parámetro para iniciar descarga
                limpiar_backups(max_por_tipo=4)
                return redirect(url_for('copias_seguridad', download=nombre_archivo))

            except Exception as e:
                flash(f'Error al generar el respaldo: {str(e)}', 'danger')
                return redirect(request.url)

        elif action == 'restore':
            selected_file = request.form.get('selected_backup')
            if not selected_file:
                flash('Selecciona un archivo de respaldo para restaurar.', 'warning')
                return redirect(request.url)

            carpeta = os.path.join(current_app.root_path, 'configuracion', 'copias')
            ruta_archivo = os.path.join(carpeta, selected_file)

            if not os.path.exists(ruta_archivo):
                flash('El archivo seleccionado no existe.', 'danger')
                return redirect(request.url)

            try:
                ext = os.path.splitext(selected_file)[1].lower()

                if ext == '.sql':
                    with open(ruta_archivo, 'r', encoding='utf-8') as f:
                        sql_script = f.read()

                    for statement in sql_script.split(';'):
                        stmt = statement.strip()
                        if stmt:
                            cursor.execute(stmt)

                    conn.commit()


                elif ext == '.json':
                    with open(ruta_archivo, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    for tabla, rows in data.items():
                        if rows:
                            cols = list(rows[0].keys())
                            for row in rows:
                                values = [row[col] for col in cols]
                                placeholders = ', '.join(['%s'] * len(cols))
                                query = f"""
                                INSERT IGNORE INTO `{tabla}` ({', '.join(cols)})
                                VALUES ({placeholders})
                                """
                                cursor.execute(query, values)

                    conn.commit()



                elif ext == '.zip':

                    filas_insertadas = 0

                    with zipfile.ZipFile(ruta_archivo, 'r') as zipf:

                        for name in zipf.namelist():

                            if not name.lower().endswith('.csv'):
                                continue

                            tabla = name.split('_')[0].strip()

                            # Verificar tabla

                            cursor.execute("""

                                           SELECT 1

                                           FROM information_schema.tables

                                           WHERE table_schema = DATABASE()

                                             AND table_name = %s LIMIT 1

                                           """, (tabla,))

                            if cursor.fetchone() is None:
                                raise Exception(

                                    f"La tabla '{tabla}' no existe. "

                                    f"Restaura primero un respaldo SQL."

                                )

                            with zipf.open(name) as csvfile:

                                reader = csv.DictReader(

                                    io.TextIOWrapper(csvfile, 'utf-8')

                                )

                                rows = list(reader)

                                if not rows:
                                    continue

                                columnas = reader.fieldnames

                                columnas_sql = ", ".join([f"`{c}`" for c in columnas])

                                placeholders = ", ".join(["%s"] * len(columnas))

                                query = f"""

                                    INSERT IGNORE INTO `{tabla}` ({columnas_sql})

                                    VALUES ({placeholders})

                                """

                                for row in rows:
                                    values = [

                                        row[c] if row[c] != '' else None

                                        for c in columnas

                                    ]

                                    cursor.execute(query, values)

                                    filas_insertadas += cursor.rowcount

                    if filas_insertadas == 0:
                        raise Exception(

                            "No se insertaron registros. "

                            "Posibles causas: claves foráneas, duplicados o datos inválidos."

                        )

                    conn.commit()

                flash(f'¡Restauración desde {selected_file} completada exitosamente!', 'success')

            except Exception as e:
                conn.rollback()
                flash(f'Error al restaurar: {str(e)}', 'danger')

            return redirect(request.url)

    cursor.close()
    conn.close()

    return render_template('configuracion/copias/copias_seguridad.html', tablas=tablas, backups=backups, download_filename=download_filename)

def restore_from_file(nombre_archivo):
    conn = get_db_connection()
    cursor = conn.cursor()
    carpeta = os.path.join(current_app.root_path, 'configuracion', 'copias')
    ruta = os.path.join(carpeta, nombre_archivo)

    try:
        ext = os.path.splitext(nombre_archivo)[1].lower()

        if ext == '.sql':
            with open(ruta, 'r', encoding='utf-8') as f:
                sql_script = f.read()

            for statement in sql_script.split(';'):
                stmt = statement.strip()
                if stmt:
                    cursor.execute(stmt)

            conn.commit()

        # (JSON / CSV podrías agregar después)

        current_app.logger.info(
            f'Restauración automática completada: {nombre_archivo}'
        )

    except Exception as e:
        conn.rollback()
        current_app.logger.error(
            f'Error en restauración automática: {str(e)}'
        )

    finally:
        cursor.close()
        conn.close()


def cargar_config_auto():
    ruta = os.path.join(current_app.root_path, RUTA_CONFIG_AUTO)
    if not os.path.exists(ruta):
        return {'intervalo': 60, 'tipo': 'completa', 'formato': 'sql', 'auto_restore': False}
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            data = f.read().strip()
            return json.loads(data) if data else {}
    except:
        return {'intervalo': 60, 'tipo': 'completa', 'formato': 'sql', 'auto_restore': False}

def guardar_config_auto(config):
    ruta = os.path.join(current_app.root_path, RUTA_CONFIG_AUTO)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)

def check_db_health():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        current_app.logger.error(f"Error en health check: {str(e)}")
        return False

def realizar_backup_automatico(tipo, formato):
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    try:
        tablas = obtener_tablas_bd(cursor)
        tablas_sel = [t['TABLE_NAME'] for t in tablas]

        control = cargar_control()
        ultima_completa = control.get('ultima_completa')
        ultima_copia = control.get('ultima_copia')

        tablas_finales = []

        for t in tablas:
            tabla = t['TABLE_NAME']
            update_time = t['UPDATE_TIME']

            if tipo == 'completa':
                tablas_finales.append(tabla)

            elif tipo == 'diferencial' and ultima_completa:
                if update_time and str(update_time) > ultima_completa:
                    tablas_finales.append(tabla)

            elif tipo == 'incremental' and ultima_copia:
                if update_time and str(update_time) > ultima_copia:
                    tablas_finales.append(tabla)

        if not tablas_finales:
            current_app.logger.info(
                'No hay cambios para backup automático.'
            )
            return

        carpeta = os.path.join(
            current_app.root_path,
            'configuracion',
            'copias'
        )
        os.makedirs(carpeta, exist_ok=True)

        fecha = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

        # ================= BACKUP SQL =================
        if formato == 'sql':
            nombre = f'backup_auto_{tipo}_{fecha}.sql'
            ruta_archivo = os.path.join(carpeta, nombre)

            with open(ruta_archivo, 'w', encoding='utf-8') as f:
                f.write(f'-- BACKUP AUTOMÁTICO {tipo.upper()} - {fecha}\n')
                f.write('SET FOREIGN_KEY_CHECKS=0;\n\n')

                # Crear tablas
                for tabla in tablas_finales:
                    f.write(f'DROP TABLE IF EXISTS `{tabla}`;\n')
                    cursor.execute(f"SHOW CREATE TABLE `{tabla}`")
                    f.write(cursor.fetchone()['Create Table'] + ";\n\n")

                # Insertar datos
                for tabla in tablas_finales:
                    cursor.execute(f"SELECT * FROM `{tabla}`")
                    filas = cursor.fetchall()

                    if not filas:
                        continue

                    columnas = filas[0].keys()
                    columnas_sql = ", ".join(
                        [f"`{c}`" for c in columnas]
                    )

                    for fila in filas:
                        valores = []
                        for v in fila.values():
                            if v is None:
                                valores.append("NULL")
                            else:
                                valores.append(
                                    pymysql.converters.escape_item(v, conn)
                                )

                        valores_sql = ", ".join(valores)

                        f.write(
                            f"INSERT INTO `{tabla}` "
                            f"({columnas_sql}) "
                            f"VALUES ({valores_sql});\n"
                        )

                    f.write("\n")

                f.write('SET FOREIGN_KEY_CHECKS=1;\n')

        # (JSON / CSV puedes reutilizar lo mismo que ya tienes)

        # ================= CONTROL =================
        ahora = datetime.now().isoformat()
        control['ultima_copia'] = ahora

        if tipo == 'completa':
            control['ultima_completa'] = ahora

        # Backup creado correctamente
        guardar_control(control)

        current_app.logger.info(
            f'Backup automático {tipo} ({formato}) creado: {nombre}'
        )

        # 🔥 LIMPIAR BACKUPS
        limpiar_backups(max_por_tipo=4)


    except Exception as e:
        current_app.logger.error(
            f'Error en backup automático: {str(e)}'
        )

    finally:
        cursor.close()
        conn.close()

def job_backup_auto(app):
    with app.app_context():
        config = cargar_config_auto()

        if config.get('auto_restore', False):
            if not check_db_health():
                backups = list_backups()
                if backups:
                    latest_backup = backups[0]
                    current_app.logger.info(
                        f'Restaurando desde {latest_backup} debido a error en BD.'
                    )
                    restore_from_file(latest_backup)

        realizar_backup_automatico(config['tipo'], config['formato'])

def automatizacion_tareas():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard'))

    config = cargar_config_auto()

    if request.method == 'POST':
        config['tipo'] = request.form.get('tipo')
        config['formato'] = request.form.get('formato')
        config['intervalo'] = int(request.form.get('intervalo', 60))
        config['auto_restore'] = request.form.get('auto_restore') == 'on'

        guardar_config_auto(config)

        scheduler = current_app.config['SCHEDULER']
        scheduler.remove_all_jobs()

        trigger = IntervalTrigger(minutes=config['intervalo'])

        scheduler.add_job(
            job_backup_auto,
            trigger=trigger,
            args=[current_app._get_current_object()],
            id='backup_automatico',
            replace_existing=True
        )

        flash('Configuración guardada y tarea programada exitosamente.', 'success')

    return render_template(
        'configuracion/automatizacion/automatizacion_tareas.html',
        config=config
    )

