from flask import Blueprint, redirect, url_for, request, flash
from bd import get_db_connection

expediente = Blueprint('expediente', __name__)

@expediente.route('/cerrar-cuenta/<int:id_atencion>', methods=['POST'])
def cerrar_cuenta(id_atencion):
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE atencion
        SET status = 'CERRADA'
        WHERE id_atencion = %s
    """, (id_atencion,))

    conn.commit()
    conn.close()

    flash('La cuenta fue cerrada correctamente', 'success')
    return redirect(url_for('expediente.ver_expediente', id_atencion=id_atencion))