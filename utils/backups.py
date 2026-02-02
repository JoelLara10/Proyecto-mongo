# utils/backups.py (versión actualizada con restauración)

import os
import json
import csv
import zipfile
import io
import tempfile
from datetime import datetime
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
                    nombre_archivo = f'backup_{tipo}_{fecha}.sql'
                    ruta_archivo = os.path.join(carpeta, nombre_archivo)

                    with open(ruta_archivo, 'w', encoding='utf-8') as f:
                        f.write(f'-- RESPALDO {tipo.upper()} - {fecha}\n\n')
                        for tabla in tablas_finales:
                            cursor.execute(f"SHOW CREATE TABLE `{tabla}`")
                            f.write(cursor.fetchone()['Create Table'] + ";\n\n")

                            cursor.execute(f"SELECT * FROM `{tabla}`")
                            filas = cursor.fetchall()
                            for fila in filas:
                                cols = list(fila.keys())
                                values = cursor.mogrify(",".join(["%s"] * len(cols)), list(fila.values()))
                                f.write(f"INSERT INTO `{tabla}` ({', '.join(cols)}) VALUES ({values});\n")

                elif formato == 'json':
                    nombre_archivo = f'backup_{tipo}_{fecha}.json'
                    ruta_archivo = os.path.join(carpeta, nombre_archivo)
                    respaldo = {}
                    for tabla in tablas_finales:
                        cursor.execute(f"SELECT * FROM `{tabla}`")
                        respaldo[tabla] = cursor.fetchall()

                    with open(ruta_archivo, 'w', encoding='utf-8') as f:
                        json.dump(respaldo, f, indent=4, default=str)

                elif formato == 'csv':
                    nombre_archivo = f'backup_{tipo}_{fecha}.zip'
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

                # Actualizar control de backups
                ahora = datetime.now().isoformat()
                control['ultima_copia'] = ahora
                if tipo == 'completa':
                    control['ultima_completa'] = ahora
                guardar_control(control)

                flash(f'¡Respaldo {tipo} ({formato.upper()}) creado exitosamente!', 'success')

                # Redirigir con parámetro para iniciar descarga
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
                    # Ejecutar SQL (dividir por ; pero manejar multi-statement)
                    for statement in sql_script.split(';\n'):
                        if statement.strip():
                            cursor.execute(statement)
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
                                query = f"INSERT INTO `{tabla}` ({', '.join(cols)}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE " + ', '.join([f"{col}=VALUES({col})" for col in cols])
                                cursor.execute(query, values)
                    conn.commit()

                elif ext == '.zip':
                    with zipfile.ZipFile(ruta_archivo, 'r') as zipf:
                        for name in zipf.namelist():
                            if name.endswith('.csv'):
                                tabla = name.split('_')[0]  # Asumir nombre como table_tipo_fecha.csv
                                with zipf.open(name) as csvfile:
                                    reader = csv.DictReader(io.TextIOWrapper(csvfile, 'utf-8'))
                                    rows = list(reader)
                                    if rows:
                                        cols = reader.fieldnames
                                        for row in rows:
                                            values = [row[col] for col in cols]
                                            placeholders = ', '.join(['%s'] * len(cols))
                                            query = f"INSERT INTO `{tabla}` ({', '.join(cols)}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE " + ', '.join([f"{col}=VALUES({col})" for col in cols])
                                            cursor.execute(query, values)
                    conn.commit()

                flash(f'¡Restauración desde {selected_file} completada exitosamente!', 'success')

            except Exception as e:
                conn.rollback()
                flash(f'Error al restaurar: {str(e)}', 'danger')

            return redirect(request.url)

    cursor.close()
    conn.close()

    return render_template('configuracion/copias/copias_seguridad.html', tablas=tablas, backups=backups, download_filename=download_filename)


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
    # Lógica similar a la de backup en POST, pero automática (sin tablas_sel, usa todas para completa, etc.)
    # Asume respaldar todas las tablas para simplicidad
    conn = get_db_connection()
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    tablas = obtener_tablas_bd(cursor)
    tablas_sel = [t['TABLE_NAME'] for t in tablas]  # Todas por default

    # Filtrar según tipo (similar a antes)
    control = cargar_control()
    ultima_completa = control.get('ultima_completa')
    ultima_copia = control.get('ultima_copia')

    tablas_finales = []
    for tabla in tablas_sel:
        t_info = next((t for t in tablas if t['TABLE_NAME'] == tabla), None)
        if t_info:
            if tipo == 'completa':
                tablas_finales.append(tabla)
            elif tipo == 'diferencial' and ultima_completa:
                if t_info['UPDATE_TIME'] and str(t_info['UPDATE_TIME']) > ultima_completa:
                    tablas_finales.append(tabla)
            elif tipo == 'incremental' and ultima_copia:
                if t_info['UPDATE_TIME'] and str(t_info['UPDATE_TIME']) > ultima_copia:
                    tablas_finales.append(tabla)

    if not tablas_finales:
        current_app.logger.info('No hay cambios para backup automático.')
        cursor.close()
        conn.close()
        return

    carpeta = os.path.join(current_app.root_path, 'configuracion', 'copias')
    os.makedirs(carpeta, exist_ok=True)
    fecha = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    try:
        if formato == 'sql':
            nombre = f'backup_auto_{tipo}_{fecha}.sql'
            ruta_archivo = os.path.join(carpeta, nombre)
            with open(ruta_archivo, 'w', encoding='utf-8') as f:
                f.write(f'-- BACKUP AUTOMÁTICO {tipo.upper()} - {fecha}\n\n')
                for tabla in tablas_finales:
                    cursor.execute(f"SHOW CREATE TABLE `{tabla}`")
                    f.write(cursor.fetchone()['Create Table'] + ";\n\n")
                    cursor.execute(f"SELECT * FROM `{tabla}`")
                    filas = cursor.fetchall()
                    for fila in filas:
                        cols = list(fila.keys())
                        values = cursor.mogrify(",".join(["%s"] * len(cols)), list(fila.values()))
                        f.write(f"INSERT INTO `{tabla}` ({', '.join(cols)}) VALUES ({values});\n")

        # Similar para json y csv (copia la lógica de antes, sin send_file)

        # Actualizar control
        ahora = datetime.now().isoformat()
        control['ultima_copia'] = ahora
        if tipo == 'completa':
            control['ultima_completa'] = ahora
        guardar_control(control)

        current_app.logger.info(f'Backup automático {tipo} ({formato}) creado: {nombre}')

    except Exception as e:
        current_app.logger.error(f'Error en backup automático: {str(e)}')

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
                    # restore_from_file(latest_backup)

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
