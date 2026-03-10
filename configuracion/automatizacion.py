# configuracion/automatizacion.py
from flask import render_template, request, session, flash, redirect, url_for, current_app
from utils.backups import cargar_config_auto, guardar_config_auto, job_backup_auto


def automatizacion_tareas():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard'))

    config = cargar_config_auto()

    if request.method == 'POST':
        config['tipo'] = request.form.get('tipo', 'completa')
        config['formato'] = request.form.get('formato', 'json')
        config['intervalo'] = int(request.form.get('intervalo', 60))
        config['auto_restore'] = request.form.get('auto_restore') == 'on'
        config['activo'] = request.form.get('activo') == 'on'

        guardar_config_auto(config)

        scheduler = current_app.config.get('SCHEDULER')
        if scheduler:
            # Eliminar jobs existentes
            try:
                scheduler.remove_job('backup_automatico')
            except:
                pass

            if config['activo']:
                scheduler.add_job(
                    job_backup_auto,
                    'interval',
                    minutes=config['intervalo'],
                    args=[current_app._get_current_object()],
                    id='backup_automatico',
                    replace_existing=True
                )
                flash('Configuración guardada y tarea programada.', 'success')
            else:
                flash('Configuración guardada. Tareas desactivadas.', 'info')
        else:
            flash('Error: Scheduler no disponible', 'danger')

    return render_template(
        'configuracion/automatizacion/automatizacion_tareas.html',
        config=config
    )