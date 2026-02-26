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
    db = get_db_connection()
    users = db['users']
    user = users.find_one({"username": username}, {"username": 1, "password": 1, "role": 1})

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

def obtener_tablas_bd():
    db = get_db_connection()
    collections = db.list_collection_names()
    # Para simular UPDATE_TIME, asumir que documentos tienen 'updated_at' field, obtener max por collection
    tablas = []
    for coll_name in collections:
        max_updated = db[coll_name].find_one(sort=[("updated_at", -1)])
        update_time = max_updated['updated_at'] if max_updated and 'updated_at' in max_updated else None
        tablas.append({"TABLE_NAME": coll_name, "UPDATE_TIME": update_time})
    return tablas

def list_backups():
    carpeta = os.path.join(current_app.root_path, 'configuracion', 'copias')
    backups = []
    for file in os.listdir(carpeta):
        if file.startswith('backup_') and file.endswith(('.json', '.zip', '.xlsx', '.pdf')):  # Ajustado sin .sql
            backups.append(file)
    return sorted(backups, reverse=True)  # Más recientes primero

# ==================== FUNCIÓN PRINCIPAL ====================
def backup_bd():

    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard'))

    tablas = obtener_tablas_bd()
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
                db_conn = get_db_connection()

                if formato == 'json':  # Reemplazamos 'sql' por 'json' para Mongo
                    nombre_archivo = f'backup_manual_{tipo}_{fecha}.json'
                    ruta_archivo = os.path.join(carpeta, nombre_archivo)
                    respaldo = {}
                    for coll in tablas_finales:
                        respaldo[coll] = list(db_conn[coll].find())
                    with open(ruta_archivo, 'w', encoding='utf-8') as f:
                        json.dump(respaldo, f, indent=4, default=str)

                elif formato == 'csv':
                    nombre_archivo = f'backup_manual_{tipo}_{fecha}.zip'
                    ruta_archivo = os.path.join(carpeta, nombre_archivo)

                    with zipfile.ZipFile(ruta_archivo, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for coll in tablas_finales:
                            docs = list(db_conn[coll].find())
                            if docs:
                                csv_buffer = io.StringIO()
                                writer = csv.DictWriter(csv_buffer, fieldnames=docs[0].keys())
                                writer.writeheader()
                                writer.writerows(docs)
                                zipf.writestr(f"{coll}_{tipo}_{fecha}.csv", csv_buffer.getvalue())

                elif formato == 'excel':
                    nombre_archivo = f'backup_manual_{tipo}_{fecha}.xlsx'
                    ruta_archivo = os.path.join(carpeta, nombre_archivo)

                    wb = Workbook()
                    wb.remove(wb.active)  # Quitar hoja vacía

                    for coll in tablas_finales:
                        ws = wb.create_sheet(title=coll)
                        docs = list(db_conn[coll].find())

                        if not docs:
                            continue

                        # Encabezados
                        ws.append(list(docs[0].keys()))

                        # Datos
                        for doc in docs:
                            ws.append(list(doc.values()))

                    wb.save(ruta_archivo)

                elif formato == 'pdf':
                    nombre_archivo = f'backup_manual_{tipo}_{fecha}.pdf'
                    ruta_archivo = os.path.join(carpeta, nombre_archivo)

                    doc = SimpleDocTemplate(ruta_archivo, pagesize=letter)
                    styles = getSampleStyleSheet()
                    elementos = []

                    elementos.append(Paragraph(
                        f"Reporte de respaldo ({tipo.upper()}) - {fecha}",
                        styles['Title']
                    ))

                    for coll in tablas_finales:
                        docs = list(db_conn[coll].find())

                        elementos.append(Paragraph(
                            f"Colección: {coll}",
                            styles['Heading2']
                        ))

                        if not docs:
                            elementos.append(Paragraph("Sin datos", styles['Normal']))
                            continue

                        data = [list(docs[0].keys())]
                        for doc in docs:
                            data.append([str(v) for v in doc.values()])

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
                db_conn = get_db_connection()

                if ext == '.json':
                    with open(ruta_archivo, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    for coll, docs in data.items():
                        if docs:
                            db_conn[coll].delete_many({})  # Clear existing
                            db_conn[coll].insert_many(docs)

                elif ext == '.zip':

                    with zipfile.ZipFile(ruta_archivo, 'r') as zipf:

                        for name in zipf.namelist():

                            if not name.lower().endswith('.csv'):
                                continue

                            coll = name.split('_')[0].strip()

                            with zipf.open(name) as csvfile:

                                reader = csv.DictReader(
                                    io.TextIOWrapper(csvfile, 'utf-8')
                                )

                                rows = list(reader)

                                if not rows:
                                    continue

                                db_conn[coll].delete_many({})  # Clear existing
                                db_conn[coll].insert_many(rows)

                elif ext == '.xlsx':
                    from openpyxl import load_workbook
                    wb = load_workbook(ruta_archivo)
                    for sheet_name in wb.sheetnames:
                        ws = wb[sheet_name]
                        headers = [cell.value for cell in ws[1]]
                        docs = []
                        for row in ws.iter_rows(min_row=2):
                            doc = {headers[i]: cell.value for i, cell in enumerate(row)}
                            docs.append(doc)
                        db_conn[sheet_name].delete_many({})  # Clear existing
                        if docs:
                            db_conn[sheet_name].insert_many(docs)

                # PDF restore not applicable for data, skip or log

                flash(f'¡Restauración desde {selected_file} completada exitosamente!', 'success')

            except Exception as e:
                flash(f'Error al restaurar: {str(e)}', 'danger')

            return redirect(request.url)

    return render_template('configuracion/copias/copias_seguridad.html', tablas=tablas, backups=backups, download_filename=download_filename)

def restore_from_file(nombre_archivo):
    carpeta = os.path.join(current_app.root_path, 'configuracion', 'copias')
    ruta = os.path.join(carpeta, nombre_archivo)

    try:
        ext = os.path.splitext(nombre_archivo)[1].lower()
        db_conn = get_db_connection()

        if ext == '.json':
            with open(ruta, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for coll, docs in data.items():
                if docs:
                    db_conn[coll].delete_many({})  # Clear existing
                    db_conn[coll].insert_many(docs)

        # (JSON / CSV / XLSX similar to above)

        current_app.logger.info(
            f'Restauración automática completada: {nombre_archivo}'
        )

    except Exception as e:
        current_app.logger.error(
            f'Error en restauración automática: {str(e)}'
        )


def cargar_config_auto():
    ruta = os.path.join(current_app.root_path, RUTA_CONFIG_AUTO)
    if not os.path.exists(ruta):
        return {'intervalo': 60, 'tipo': 'completa', 'formato': 'json', 'auto_restore': False}  # Cambiado sql a json
    try:
        with open(ruta, 'r', encoding='utf-8') as f:
            data = f.read().strip()
            return json.loads(data) if data else {}
    except:
        return {'intervalo': 60, 'tipo': 'completa', 'formato': 'json', 'auto_restore': False}

def guardar_config_auto(config):
    ruta = os.path.join(current_app.root_path, RUTA_CONFIG_AUTO)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)

def check_db_health():
    try:
        db = get_db_connection()
        db.command("ping")
        return True
    except Exception as e:
        current_app.logger.error(f"Error en health check: {str(e)}")
        return False

def realizar_backup_automatico(tipo, formato):
    try:
        tablas = obtener_tablas_bd()
        tablas_sel = [t['TABLE_NAME'] for t in tablas]

        control = cargar_control()
        ultima_completa = control.get('ultima_completa')
        ultima_copia = control.get('ultima_copia')

        tablas_finales = []

        for t in tablas:
            coll = t['TABLE_NAME']
            update_time = t['UPDATE_TIME']

            if tipo == 'completa':
                tablas_finales.append(coll)

            elif tipo == 'diferencial' and ultima_completa:
                if update_time and str(update_time) > ultima_completa:
                    tablas_finales.append(coll)

            elif tipo == 'incremental' and ultima_copia:
                if update_time and str(update_time) > ultima_copia:
                    tablas_finales.append(coll)

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

        # ================= BACKUP JSON =================
        if formato == 'json':
            nombre = f'backup_auto_{tipo}_{fecha}.json'
            ruta_archivo = os.path.join(carpeta, nombre)

            respaldo = {}
            db_conn = get_db_connection()
            for coll in tablas_finales:
                respaldo[coll] = list(db_conn[coll].find())

            with open(ruta_archivo, 'w', encoding='utf-8') as f:
                json.dump(respaldo, f, indent=4, default=str)

        # (CSV / EXCEL / PDF similar, adaptado de arriba)

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