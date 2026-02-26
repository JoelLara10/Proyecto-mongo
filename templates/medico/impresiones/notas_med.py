from flask import make_response
from fpdf import FPDF
from bd import get_db_connection
from . import pdf_med
from datetime import datetime


@pdf_med.route('/pdf/signos-vitales/<int:id_signos>')
def signos_vitales_pdf(id_signos):

    db = get_db_connection()

    pipeline = [
        {"$match": {"id_signos": id_signos}},
        {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
        {"$unwind": "$atencion"},
        {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$project": {
            "ta": 1,
            "fc": 1,
            "fr": 1,
            "temp": 1,
            "spo2": 1,
            "peso": 1,
            "talla": 1,
            "fecha_registro": 1,
            "papell": "$paciente.papell",
            "sapell": "$paciente.sapell",
            "nom_pac": "$paciente.nom_pac"
        }}
    ]
    datos = list(db['signos_vitales'].aggregate(pipeline))[0] if list(db['signos_vitales'].aggregate(pipeline)) else None

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

    db = get_db_connection()

    pipeline = [
        {"$match": {"id_nota": id_nota}},
        {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
        {"$unwind": "$atencion"},
        {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$project": {
            "subjetivo": 1,
            "objetivo": 1,
            "analisis": 1,
            "plan": 1,
            "fecha_registro": 1,
            "papell": "$paciente.papell",
            "sapell": "$paciente.sapell",
            "nom_pac": "$paciente.nom_pac"
        }}
    ]
    datos = list(db['notas_medicas'].aggregate(pipeline))[0] if list(db['notas_medicas'].aggregate(pipeline)) else None

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

    db = get_db_connection()

    pipeline = [
        {"$match": {"id_diagnostico": id_diagnostico}},
        {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
        {"$unwind": "$atencion"},
        {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$project": {
            "diagnostico_principal": 1,
            "diagnosticos_secundarios": 1,
            "observaciones": 1,
            "fecha_registro": 1,
            "papell": "$paciente.papell",
            "sapell": "$paciente.sapell",
            "nom_pac": "$paciente.nom_pac"
        }}
    ]
    datos = list(db['diagnosticos'].aggregate(pipeline))[0] if list(db['diagnosticos'].aggregate(pipeline)) else None

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

    db = get_db_connection()

    fecha_dt = datetime.strptime(fecha, '%Y-%m-%d %H:%M:%S') if len(fecha) > 10 else datetime.strptime(fecha, '%Y-%m-%d')

    pipeline = [
        {"$match": {"id_atencion": id_atencion, "fecha_registro": fecha_dt}},
        {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
        {"$unwind": "$atencion"},
        {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$project": {
            "medicamento": 1,
            "dosis": 1,
            "frecuencia": 1,
            "duracion": 1,
            "indicaciones": 1,
            "fecha_registro": 1,
            "papell": "$paciente.papell",
            "sapell": "$paciente.sapell",
            "nom_pac": "$paciente.nom_pac"
        }}
    ]
    recetas = list(db['recetas'].aggregate(pipeline))

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
        pdf_doc.ln(2)

    response = make_response(pdf_doc.output(dest='S').encode('latin-1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=receta_medica.pdf'
    return response


@pdf_med.route('/pdf/laboratorio/<int:id_examen>')
def laboratorio_pdf(id_examen):

    db = get_db_connection()

    # ===============================
    # ENCABEZADO + PACIENTE
    # ===============================
    pipeline_enc = [
        {"$match": {"id_examen": id_examen}},
        {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
        {"$unwind": "$atencion"},
        {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$project": {
            "fecha": 1,
            "estado": 1,
            "fecha_realizado": 1,
            "observaciones": 1,
            "papell": "$paciente.papell",
            "sapell": "$paciente.sapell",
            "nom_pac": "$paciente.nom_pac"
        }}
    ]
    encabezado = list(db['examenes_laboratorio'].aggregate(pipeline_enc))[0] if list(db['examenes_laboratorio'].aggregate(pipeline_enc)) else None

    # ===============================
    # DETALLE DE EXÁMENES
    # ===============================
    pipeline_det = [
        {"$match": {"id_examen": id_examen}},
        {"$lookup": {"from": "catalogo_examenes_laboratorio", "localField": "id_catalogo", "foreignField": "id_catalogo", "as": "cat"}},
        {"$unwind": "$cat"},
        {"$project": {"nombre": "$cat.nombre"}}
    ]
    detalles = list(db['examenes_laboratorio_det'].aggregate(pipeline_det))

    if not encabezado:
        return "Examen de laboratorio no encontrado", 404

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

    fecha_realizado = (
        encabezado['fecha_realizado'].strftime('%d/%m/%Y')
        if encabezado.get('fecha_realizado') else 'No especificado'
    )
    pdf_doc.cell(0, 7, f"Fecha realizado: {fecha_realizado}", ln=True)

    # OBSERVACIONES GENERALES
    if encabezado['observaciones']:
        pdf_doc.ln(3)
        pdf_doc.multi_cell(
            0, 7,
            f"Observaciones generales:\n{encabezado['observaciones']}"
        )

    # DETALLE
    pdf_doc.ln(8)
    pdf_doc.set_font('Arial', 'B', 12)
    pdf_doc.cell(0, 8, 'Exámenes solicitados:', ln=True)

    pdf_doc.set_font('Arial', '', 10)
    for i, d in enumerate(detalles, 1):
        pdf_doc.multi_cell(
            0, 7,
            f"{i}. {d['nombre']}\n"
            f"   Estado: {encabezado['estado'].capitalize()}\n"
            f"   Fecha realizado: {fecha_realizado}"
        )
        pdf_doc.ln(2)

    # RESPUESTA
    response = make_response(pdf_doc.output(dest='S').encode('latin-1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=examenes_laboratorio.pdf'
    return response



@pdf_med.route('/pdf/gabinete/<int:id_examen>')
def gabinete_pdf(id_examen):

    db = get_db_connection()

    # ENCABEZADO + PACIENTE
    pipeline_enc = [
        {"$match": {"id_examen": id_examen}},
        {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
        {"$unwind": "$atencion"},
        {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$project": {
            "fecha": 1,
            "observaciones": 1,
            "papell": "$paciente.papell",
            "sapell": "$paciente.sapell",
            "nom_pac": "$paciente.nom_pac"
        }}
    ]
    encabezado = list(db['examenes_gabinete'].aggregate(pipeline_enc))[0] if list(db['examenes_gabinete'].aggregate(pipeline_enc)) else None

    # DETALLE DE ESTUDIOS
    detalles = list(db['examenes_gabinete_det'].find({"id_examen": id_examen}, {"nombre_examen": 1, "estado": 1, "fecha_realizado": 1, "observaciones": 1}))

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
            if d.get('fecha_realizado') else 'No especificado'
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