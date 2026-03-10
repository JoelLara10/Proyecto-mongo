# configuracion/copias_seguridad.py
from flask import render_template, request, session, flash, redirect, url_for, current_app
from utils.backups import (
    obtener_colecciones_mongo, list_backups, validar_admin,
    realizar_backup, restaurar_backup, limpiar_backups
)


def copias_seguridad():
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Acceso denegado.', 'danger')
        return redirect(url_for('dashboard'))

    colecciones = obtener_colecciones_mongo()
    backups = list_backups()

    # Obtener nombre de archivo para descargar desde la sesión
    download_filename = session.pop('download_backup', None)

    if request.method == 'POST':
        action = request.form.get('action')

        # Solo validar admin para backup (NO para restore)
        if action == 'backup':
            auth_user = request.form.get('auth_user')
            auth_pass = request.form.get('auth_pass')

            if not auth_user or not auth_pass:
                flash('Debes confirmar usuario y contraseña de administrador.', 'danger')
                return redirect(request.url)
            if not validar_admin(auth_user, auth_pass):
                flash('Credenciales inválidas.', 'danger')
                return redirect(request.url)

        if action == 'backup':
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
                    session['download_backup'] = nombre
                    return redirect(url_for('copias_seguridad'))
            except Exception as e:
                flash(f'Error: {str(e)}', 'danger')

        elif action == 'restore':
            archivo = request.form.get('selected_backup')
            if not archivo:
                flash('Selecciona un archivo', 'warning')
                return redirect(request.url)

            try:
                # SIN VALIDACIÓN DE ADMIN para restore
                restaurar_backup(archivo)
                flash('Restauración completada exitosamente', 'success')
            except Exception as e:
                flash(f'Error en restauración: {str(e)}', 'danger')

        return redirect(request.url)

    return render_template(
        'configuracion/copias/copias_seguridad.html',
        colecciones=colecciones,
        backups=backups,
        download_filename=download_filename
    )


def download_backup(filename):
    from flask import send_from_directory
    import os
    carpeta = os.path.join(current_app.root_path, 'configuracion', 'copias')
    return send_from_directory(carpeta, filename, as_attachment=True)