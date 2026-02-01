from flask import make_response
from fpdf import FPDF
from bd import get_db_connection
from . import pdf_med
from datetime import datetime
import pymysql.cursors


@pdf_med.route('/pdf/signos-vitales/<int:id_signos>')
def signos_vitales_pdf(id_signos):

    conn = get_db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    cur.execute("""
        SELECT 
            s.ta, s.fc, s.fr, s.temp, s.spo2, s.peso, s.talla, s.fecha_registro,
            p.papell, p.sapell, p.nom_pac
        FROM signos_vitales s
        JOIN atencion a ON a.id_atencion = s.id_atencion
        JOIN pacientes p ON p.Id_exp = a.Id_exp
        WHERE s.id_signos = %s
    """, (id_signos,))

    datos = cur.fetchone()
    conn.close()

    if not datos:
        # Manejar caso de no encontrado, por ejemplo redirigir o error
        return "Signos vitales no encontrados", 404

    pdf_doc = FPDF('P', 'mm', 'Letter')
    pdf_doc.set_auto_page_break(True, 20)
    pdf_doc.add_page()

    pdf_doc.set_font('Arial', 'B', 14)
    pdf_doc.cell(0, 10, 'SIGNOS VITALES', ln=True, align='C')

    pdf_doc.ln(5)
    pdf_doc.set_font('Arial', '', 10)
    pdf_doc.cell(
        0, 7,
        f"Paciente: {datos['papell']} {datos['sapell']} {datos['nom_pac']}",
        ln=True
    )

    fecha = datos['fecha_registro'].strftime('%d/%m/%Y %H:%M')
    pdf_doc.cell(0, 7, f"Fecha: {fecha}", ln=True)

    pdf_doc.ln(4)
    pdf_doc.set_font('Arial', 'B', 10)

    labels = [
        ('TA', datos['ta']),
        ('FC', datos['fc']),
        ('FR', datos['fr']),
        ('Temperatura', datos['temp']),
        ('SpO2', datos['spo2']),
        ('Peso', datos['peso']),
        ('Talla', datos['talla'])
    ]

    for label, value in labels:
        pdf_doc.cell(60, 7, label, border=1)
        pdf_doc.cell(0, 7, str(value), border=1, ln=True)

    response = make_response(pdf_doc.output(dest='S').encode('latin-1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=signos_vitales.pdf'
    return response

@pdf_med.route('/pdf/notas-medicas/<int:id_nota>')
def notas_medicas_pdf(id_nota):

    conn = get_db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    cur.execute("""
        SELECT 
            n.subjetivo, n.objetivo, n.analisis, n.plan, n.fecha_registro,
            p.papell, p.sapell, p.nom_pac
        FROM notas_medicas n
        JOIN atencion a ON a.id_atencion = n.id_atencion
        JOIN pacientes p ON p.Id_exp = a.Id_exp
        WHERE n.id_nota = %s
    """, (id_nota,))

    datos = cur.fetchone()
    conn.close()

    if not datos:
        return "Nota médica no encontrada", 404

    pdf_doc = FPDF('P', 'mm', 'Letter')
    pdf_doc.set_auto_page_break(True, 20)
    pdf_doc.add_page()

    pdf_doc.set_font('Arial', 'B', 14)
    pdf_doc.cell(0, 10, 'NOTA MÉDICA (SOAP)', ln=True, align='C')

    pdf_doc.ln(5)
    pdf_doc.set_font('Arial', '', 10)
    pdf_doc.cell(
        0, 7,
        f"Paciente: {datos['papell']} {datos['sapell']} {datos['nom_pac']}",
        ln=True
    )

    fecha = datos['fecha_registro'].strftime('%d/%m/%Y %H:%M')
    pdf_doc.cell(0, 7, f"Fecha: {fecha}", ln=True)

    pdf_doc.ln(10)
    pdf_doc.set_font('Arial', 'B', 12)
    pdf_doc.cell(0, 8, 'Subjetivo:', ln=True)
    pdf_doc.set_font('Arial', '', 10)
    pdf_doc.multi_cell(0, 7, datos['subjetivo'] or 'No especificado')

    pdf_doc.ln(5)
    pdf_doc.set_font('Arial', 'B', 12)
    pdf_doc.cell(0, 8, 'Objetivo:', ln=True)
    pdf_doc.set_font('Arial', '', 10)
    pdf_doc.multi_cell(0, 7, datos['objetivo'] or 'No especificado')

    pdf_doc.ln(5)
    pdf_doc.set_font('Arial', 'B', 12)
    pdf_doc.cell(0, 8, 'Análisis:', ln=True)
    pdf_doc.set_font('Arial', '', 10)
    pdf_doc.multi_cell(0, 7, datos['analisis'] or 'No especificado')

    pdf_doc.ln(5)
    pdf_doc.set_font('Arial', 'B', 12)
    pdf_doc.cell(0, 8, 'Plan:', ln=True)
    pdf_doc.set_font('Arial', '', 10)
    pdf_doc.multi_cell(0, 7, datos['plan'] or 'No especificado')

    response = make_response(pdf_doc.output(dest='S').encode('latin-1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=nota_medica.pdf'
    return response

@pdf_med.route('/pdf/diagnostico/<int:id_diagnostico>')
def diagnostico_pdf(id_diagnostico):

    conn = get_db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    cur.execute("""
        SELECT 
            d.diagnostico_principal,
            d.diagnosticos_secundarios,
            d.observaciones,
            d.fecha_registro,
            p.papell,
            p.sapell,
            p.nom_pac
        FROM diagnosticos d
        JOIN atencion a ON a.id_atencion = d.id_atencion
        JOIN pacientes p ON p.Id_exp = a.Id_exp
        WHERE d.id_diagnostico = %s
    """, (id_diagnostico,))

    datos = cur.fetchone()
    conn.close()

    if not datos:
        return "Diagnóstico no encontrado", 404

    # ===============================
    # PDF
    # ===============================
    pdf_doc = FPDF('P', 'mm', 'Letter')
    pdf_doc.set_auto_page_break(True, 20)
    pdf_doc.add_page()

    pdf_doc.set_font('Arial', 'B', 14)
    pdf_doc.cell(0, 10, 'DIAGNÓSTICO MÉDICO', ln=True, align='C')

    pdf_doc.ln(5)
    pdf_doc.set_font('Arial', '', 10)
    pdf_doc.cell(
        0, 7,
        f"Paciente: {datos['papell']} {datos['sapell']} {datos['nom_pac']}",
        ln=True
    )

    fecha = datos['fecha_registro'].strftime('%d/%m/%Y %H:%M')
    pdf_doc.cell(0, 7, f"Fecha: {fecha}", ln=True)

    # ===============================
    # CONTENIDO
    # ===============================
    pdf_doc.ln(10)
    pdf_doc.set_font('Arial', 'B', 12)
    pdf_doc.cell(0, 8, 'Diagnóstico principal:', ln=True)
    pdf_doc.set_font('Arial', '', 10)
    pdf_doc.multi_cell(0, 7, datos['diagnostico_principal'])

    pdf_doc.ln(5)
    pdf_doc.set_font('Arial', 'B', 12)
    pdf_doc.cell(0, 8, 'Diagnósticos secundarios:', ln=True)
    pdf_doc.set_font('Arial', '', 10)
    pdf_doc.multi_cell(
        0, 7,
        datos['diagnosticos_secundarios'] or 'No especificado'
    )

    pdf_doc.ln(5)
    pdf_doc.set_font('Arial', 'B', 12)
    pdf_doc.cell(0, 8, 'Observaciones:', ln=True)
    pdf_doc.set_font('Arial', '', 10)
    pdf_doc.multi_cell(
        0, 7,
        datos['observaciones'] or 'No especificado'
    )

    response = make_response(pdf_doc.output(dest='S').encode('latin-1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=diagnostico.pdf'
    return response


@pdf_med.route('/pdf/receta/<int:id_atencion>/<fecha>')
def receta_pdf(id_atencion, fecha):

    conn = get_db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    cur.execute("""
        SELECT 
            r.medicamento,
            r.dosis,
            r.frecuencia,
            r.duracion,
            r.indicaciones,
            r.fecha_registro,
            p.papell,
            p.sapell,
            p.nom_pac
        FROM recetas r
        JOIN atencion a ON a.id_atencion = r.id_atencion
        JOIN pacientes p ON p.Id_exp = a.Id_exp
        WHERE r.id_atencion = %s
          AND r.fecha_registro = %s
    """, (id_atencion, fecha))

    recetas = cur.fetchall()
    conn.close()

    if not recetas:
        return "Receta no encontrada", 404

    paciente = recetas[0]

    pdf_doc = FPDF('P', 'mm', 'Letter')
    pdf_doc.set_auto_page_break(True, 20)
    pdf_doc.add_page()

    pdf_doc.set_font('Arial', 'B', 14)
    pdf_doc.cell(0, 10, 'RECETA MÉDICA', ln=True, align='C')

    pdf_doc.ln(5)
    pdf_doc.set_font('Arial', '', 10)
    pdf_doc.cell(
        0, 7,
        f"Paciente: {paciente['papell']} {paciente['sapell']} {paciente['nom_pac']}",
        ln=True
    )

    fecha_txt = paciente['fecha_registro'].strftime('%d/%m/%Y %H:%M')
    pdf_doc.cell(0, 7, f"Fecha: {fecha_txt}", ln=True)

    pdf_doc.ln(10)

    # LISTA DE MEDICAMENTOS
    for i, r in enumerate(recetas, 1):
        pdf_doc.set_font('Arial', 'B', 11)
        pdf_doc.cell(0, 8, f"Medicamento {i}", ln=True)

        pdf_doc.set_font('Arial', '', 10)
        pdf_doc.multi_cell(0, 7, f"Nombre: {r['medicamento']}")
        pdf_doc.multi_cell(0, 7, f"Dosis: {r['dosis']}")
        pdf_doc.multi_cell(0, 7, f"Frecuencia: {r['frecuencia']}")
        pdf_doc.multi_cell(0, 7, f"Duración: {r['duracion']}")
        pdf_doc.multi_cell(
            0, 7,
            f"Indicaciones: {r['indicaciones'] or 'No especificado'}"
        )
        pdf_doc.ln(4)

    response = make_response(pdf_doc.output(dest='S').encode('latin-1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=receta_medica.pdf'
    return response


@pdf_med.route('/pdf/laboratorio/<int:id_examen>')
def laboratorio_pdf(id_examen):

    conn = get_db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # ENCABEZADO + PACIENTE
    cur.execute("""
        SELECT 
            el.fecha,
            el.estado,
            el.observaciones,
            p.papell,
            p.sapell,
            p.nom_pac
        FROM examenes_laboratorio el
        JOIN atencion a ON a.id_atencion = el.id_atencion
        JOIN pacientes p ON p.Id_exp = a.Id_exp
        WHERE el.id_examen = %s
    """, (id_examen,))
    encabezado = cur.fetchone()

    # DETALLE DE EXÁMENES
    cur.execute("""
        SELECT c.nombre
        FROM examenes_laboratorio_det d
        JOIN catalogo_examenes_laboratorio c
            ON c.id_catalogo = d.id_catalogo
        WHERE d.id_examen = %s
    """, (id_examen,))
    detalles = cur.fetchall()

    conn.close()

    if not encabezado:
        return "Examen no encontrado", 404

    # PDF
    pdf_doc = FPDF('P', 'mm', 'Letter')
    pdf_doc.set_auto_page_break(True, 20)
    pdf_doc.add_page()

    pdf_doc.set_font('Arial', 'B', 14)
    pdf_doc.cell(0, 10, 'SOLICITUD DE EXÁMENES DE LABORATORIO', ln=True, align='C')

    pdf_doc.ln(5)
    pdf_doc.set_font('Arial', '', 10)
    pdf_doc.cell(
        0, 7,
        f"Paciente: {encabezado['papell']} {encabezado['sapell']} {encabezado['nom_pac']}",
        ln=True
    )

    fecha = encabezado['fecha'].strftime('%d/%m/%Y %H:%M')
    pdf_doc.cell(0, 7, f"Fecha: {fecha}", ln=True)
    pdf_doc.cell(0, 7, f"Estado: {encabezado['estado'].capitalize()}", ln=True)

    pdf_doc.ln(10)
    pdf_doc.set_font('Arial', 'B', 12)
    pdf_doc.cell(0, 8, 'Exámenes solicitados:', ln=True)

    pdf_doc.set_font('Arial', '', 10)
    for i, d in enumerate(detalles, 1):
        pdf_doc.cell(0, 7, f"{i}. {d['nombre']}", ln=True)

    if encabezado['observaciones']:
        pdf_doc.ln(5)
        pdf_doc.set_font('Arial', 'B', 11)
        pdf_doc.cell(0, 8, 'Observaciones:', ln=True)
        pdf_doc.set_font('Arial', '', 10)
        pdf_doc.multi_cell(0, 7, encabezado['observaciones'])

    response = make_response(pdf_doc.output(dest='S').encode('latin-1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=examenes_laboratorio.pdf'
    return response


@pdf_med.route('/pdf/gabinete/<int:id_examen>')
def gabinete_pdf(id_examen):

    conn = get_db_connection()
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # ENCABEZADO + PACIENTE
    cur.execute("""
        SELECT 
            eg.fecha,
            eg.observaciones,
            p.papell,
            p.sapell,
            p.nom_pac
        FROM examenes_gabinete eg
        JOIN atencion a ON a.id_atencion = eg.id_atencion
        JOIN pacientes p ON p.Id_exp = a.Id_exp
        WHERE eg.id_examen = %s
    """, (id_examen,))
    encabezado = cur.fetchone()

    # DETALLE DE ESTUDIOS
    cur.execute("""
        SELECT 
            nombre_examen,
            estado,
            fecha_realizado,
            observaciones
        FROM examenes_gabinete_det
        WHERE id_examen = %s
    """, (id_examen,))
    detalles = cur.fetchall()

    conn.close()

    if not encabezado:
        return "Examen de gabinete no encontrado", 404

    # PDF
    pdf_doc = FPDF('P', 'mm', 'Letter')
    pdf_doc.set_auto_page_break(True, 20)
    pdf_doc.add_page()

    pdf_doc.set_font('Arial', 'B', 14)
    pdf_doc.cell(0, 10, 'SOLICITUD DE EXÁMENES DE GABINETE', ln=True, align='C')

    pdf_doc.ln(5)
    pdf_doc.set_font('Arial', '', 10)
    pdf_doc.cell(
        0, 7,
        f"Paciente: {encabezado['papell']} {encabezado['sapell']} {encabezado['nom_pac']}",
        ln=True
    )

    fecha = encabezado['fecha'].strftime('%d/%m/%Y %H:%M')
    pdf_doc.cell(0, 7, f"Fecha: {fecha}", ln=True)

    if encabezado['observaciones']:
        pdf_doc.ln(3)
        pdf_doc.multi_cell(0, 7, f"Observaciones generales:\n{encabezado['observaciones']}")

    pdf_doc.ln(8)
    pdf_doc.set_font('Arial', 'B', 12)
    pdf_doc.cell(0, 8, 'Estudios solicitados:', ln=True)

    pdf_doc.set_font('Arial', '', 10)
    for i, d in enumerate(detalles, 1):
        estado = d['estado']
        fecha_realizado = (
            d['fecha_realizado'].strftime('%d/%m/%Y')
            if d['fecha_realizado'] else 'No especificado'
        )

        pdf_doc.multi_cell(
            0, 7,
            f"{i}. {d['nombre_examen']}\n"
            f"   Estado: {estado}\n"
            f"   Fecha realizado: {fecha_realizado}\n"
            f"   Observaciones: {d['observaciones'] or 'No especificado'}"
        )
        pdf_doc.ln(2)

    response = make_response(pdf_doc.output(dest='S').encode('latin-1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=examenes_gabinete.pdf'
    return response
