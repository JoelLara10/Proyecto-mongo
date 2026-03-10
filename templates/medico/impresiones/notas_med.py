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


@pdf_med.route('/pdf/receta/<int:id_receta>')
def receta_pdf(id_receta):
    db = get_db_connection()

    # Buscar la receta por su ID
    pipeline = [
        {"$match": {"id_receta": id_receta}},
        {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
        {"$unwind": "$atencion"},
        {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$project": {
            "medicamentos": 1,
            "fecha_registro": 1,
            "papell": "$paciente.papell",
            "sapell": "$paciente.sapell",
            "nom_pac": "$paciente.nom_pac"
        }}
    ]

    recetas = list(db['recetas'].aggregate(pipeline))

    if not recetas:
        return "Receta no encontrada", 404

    receta = recetas[0]

    # Crear PDF
    pdf_doc = FPDF('P', 'mm', 'Letter')
    pdf_doc.set_auto_page_break(True, 20)
    pdf_doc.add_page()

    # Encabezado
    pdf_doc.set_font('Arial', 'B', 16)
    pdf_doc.cell(0, 10, 'RECETA MÉDICA', ln=True, align='C')

    pdf_doc.ln(10)
    pdf_doc.set_font('Arial', '', 11)

    # Datos del paciente
    pdf_doc.cell(0, 7, f"Paciente: {receta['papell']} {receta['sapell']} {receta['nom_pac']}", ln=True)
    pdf_doc.cell(0, 7, f"Fecha: {receta['fecha_registro'].strftime('%d/%m/%Y %H:%M')}", ln=True)

    pdf_doc.ln(10)

    # Línea separadora
    pdf_doc.cell(0, 0, '', 'T', ln=True)
    pdf_doc.ln(5)

    # Lista de medicamentos
    for i, med in enumerate(receta['medicamentos'], 1):
        pdf_doc.set_font('Arial', 'B', 12)
        pdf_doc.cell(0, 8, f"{i}. {med['medicamento']}", ln=True)

        pdf_doc.set_font('Arial', '', 10)
        pdf_doc.cell(0, 6, f"   Dosis: {med['dosis']}", ln=True)
        pdf_doc.cell(0, 6, f"   Frecuencia: {med['frecuencia']}", ln=True)
        pdf_doc.cell(0, 6, f"   Duración: {med['duracion']}", ln=True)

        if med.get('indicaciones'):
            pdf_doc.multi_cell(0, 6, f"   Indicaciones: {med['indicaciones']}")

        pdf_doc.ln(5)

    # Espacio para firma
    pdf_doc.ln(20)
    pdf_doc.cell(0, 7, "__________________________________", ln=True, align='R')
    pdf_doc.set_font('Arial', 'B', 10)
    pdf_doc.cell(0, 7, "Firma del Médico", ln=True, align='R')

    response = make_response(pdf_doc.output(dest='S').encode('latin-1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=receta_{id_receta}.pdf'
    return response


@pdf_med.route('/pdf/laboratorio/<int:id_examen>')
def laboratorio_pdf(id_examen):
    db = get_db_connection()

    # ===============================
    # ENCABEZADO + PACIENTE (desde colecciones unificadas)
    # ===============================
    pipeline_enc = [
        {"$match": {"id_examen": id_examen}},
        {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
        {"$unwind": "$atencion"},
        {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$lookup": {"from": "users", "localField": "id_medico", "foreignField": "_id", "as": "medico"}},
        {"$unwind": {"path": "$medico", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "fecha": 1,
            "observaciones": 1,
            "papell": "$paciente.papell",
            "sapell": "$paciente.sapell",
            "nom_pac": "$paciente.nom_pac",
            "medico_nombre": {"$concat": ["$medico.pnombre", " ", "$medico.papell"]}
        }}
    ]

    encabezado_list = list(db['examenes'].aggregate(pipeline_enc))
    if not encabezado_list:
        return "Examen de laboratorio no encontrado", 404

    encabezado = encabezado_list[0]

    # ===============================
    # DETALLE DE EXÁMENES (desde examenes_det + catálogo)
    # ===============================
    pipeline_det = [
        {"$match": {"id_examen": id_examen}},
        {"$lookup": {
            "from": "catalogo_examenes",
            "localField": "id_catalogo",
            "foreignField": "id_catalogo",
            "as": "cat"
        }},
        {"$unwind": "$cat"},
        {"$match": {"cat.tipo": "LABORATORIO"}},
        {"$project": {
            "nombre": "$cat.nombre",
            "estado": 1,
            "resultado": 1,
            "fecha_realizado": 1,
            "observaciones": 1
        }}
    ]

    detalles = list(db['examenes_det'].aggregate(pipeline_det))

    # PDF
    pdf_doc = FPDF('P', 'mm', 'Letter')
    pdf_doc.set_auto_page_break(True, 20)
    pdf_doc.add_page()

    # Encabezado
    pdf_doc.set_font('Arial', 'B', 16)
    pdf_doc.cell(0, 10, 'SOLICITUD DE EXÁMENES DE LABORATORIO', ln=True, align='C')

    pdf_doc.ln(5)
    pdf_doc.set_font('Arial', '', 11)

    # Datos del paciente
    pdf_doc.cell(0, 7, f"Paciente: {encabezado['papell']} {encabezado['sapell']} {encabezado['nom_pac']}", ln=True)

    fecha = encabezado['fecha'].strftime('%d/%m/%Y %H:%M')
    pdf_doc.cell(0, 7, f"Fecha de solicitud: {fecha}", ln=True)

    if encabezado.get('medico_nombre'):
        pdf_doc.cell(0, 7, f"Médico solicitante: {encabezado['medico_nombre']}", ln=True)

    # Observaciones generales
    if encabezado.get('observaciones'):
        pdf_doc.ln(3)
        pdf_doc.set_font('Arial', 'B', 11)
        pdf_doc.cell(0, 7, 'Observaciones generales:', ln=True)
        pdf_doc.set_font('Arial', '', 10)
        pdf_doc.multi_cell(0, 6, encabezado['observaciones'])

    # Línea separadora
    pdf_doc.ln(5)
    pdf_doc.cell(0, 0, '', 'T', ln=True)
    pdf_doc.ln(5)

    # Detalle de exámenes
    pdf_doc.set_font('Arial', 'B', 12)
    pdf_doc.cell(0, 8, 'Exámenes solicitados:', ln=True)
    pdf_doc.ln(3)

    pdf_doc.set_font('Arial', '', 10)
    for i, det in enumerate(detalles, 1):
        # Nombre del examen
        pdf_doc.set_font('Arial', 'B', 10)
        pdf_doc.cell(0, 6, f"{i}. {det['nombre']}", ln=True)

        # Estado
        pdf_doc.set_font('Arial', '', 10)
        estado = det.get('estado', 'PENDIENTE')
        pdf_doc.cell(0, 5, f"   Estado: {estado}", ln=True)

        # Fecha realizado (si existe)
        if det.get('fecha_realizado'):
            fecha_real = det['fecha_realizado'].strftime('%d/%m/%Y')
            pdf_doc.cell(0, 5, f"   Fecha realizado: {fecha_real}", ln=True)

        # Resultado (si existe)
        if det.get('resultado'):
            pdf_doc.multi_cell(0, 5, f"   Resultado: {det['resultado']}")

        # Observaciones del detalle
        if det.get('observaciones'):
            pdf_doc.multi_cell(0, 5, f"   Observaciones: {det['observaciones']}")

        pdf_doc.ln(3)

    # Espacio para firma
    pdf_doc.ln(10)
    pdf_doc.cell(0, 7, "__________________________________", ln=True, align='R')
    pdf_doc.set_font('Arial', 'B', 10)
    pdf_doc.cell(0, 7, "Firma del Médico", ln=True, align='R')

    response = make_response(pdf_doc.output(dest='S').encode('latin-1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=laboratorio_{id_examen}.pdf'
    return response


@pdf_med.route('/pdf/gabinete/<int:id_examen>')
def gabinete_pdf(id_examen):
    db = get_db_connection()

    # ===============================
    # ENCABEZADO + PACIENTE (desde colecciones unificadas)
    # ===============================
    pipeline_enc = [
        {"$match": {"id_examen": id_examen}},
        {"$lookup": {"from": "atencion", "localField": "id_atencion", "foreignField": "id_atencion", "as": "atencion"}},
        {"$unwind": "$atencion"},
        {"$lookup": {"from": "pacientes", "localField": "atencion.Id_exp", "foreignField": "Id_exp", "as": "paciente"}},
        {"$unwind": "$paciente"},
        {"$lookup": {"from": "users", "localField": "id_medico", "foreignField": "_id", "as": "medico"}},
        {"$unwind": {"path": "$medico", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "fecha": 1,
            "observaciones": 1,
            "papell": "$paciente.papell",
            "sapell": "$paciente.sapell",
            "nom_pac": "$paciente.nom_pac",
            "medico_nombre": {"$concat": ["$medico.pnombre", " ", "$medico.papell"]}
        }}
    ]

    encabezado_list = list(db['examenes'].aggregate(pipeline_enc))
    if not encabezado_list:
        return "Examen de gabinete no encontrado", 404

    encabezado = encabezado_list[0]

    # ===============================
    # DETALLE DE ESTUDIOS (desde examenes_det + catálogo)
    # ===============================
    pipeline_det = [
        {"$match": {"id_examen": id_examen}},
        {"$lookup": {
            "from": "catalogo_examenes",
            "localField": "id_catalogo",
            "foreignField": "id_catalogo",
            "as": "cat"
        }},
        {"$unwind": "$cat"},
        {"$match": {"cat.tipo": "GABINETE"}},
        {"$project": {
            "nombre": "$cat.nombre",
            "estado": 1,
            "fecha_realizado": 1,
            "observaciones": 1,
            "archivo_resultado": 1
        }}
    ]

    detalles = list(db['examenes_det'].aggregate(pipeline_det))

    # PDF
    pdf_doc = FPDF('P', 'mm', 'Letter')
    pdf_doc.set_auto_page_break(True, 20)
    pdf_doc.add_page()

    # Encabezado
    pdf_doc.set_font('Arial', 'B', 16)
    pdf_doc.cell(0, 10, 'SOLICITUD DE EXÁMENES DE GABINETE', ln=True, align='C')

    pdf_doc.ln(5)
    pdf_doc.set_font('Arial', '', 11)

    # Datos del paciente
    pdf_doc.cell(0, 7, f"Paciente: {encabezado['papell']} {encabezado['sapell']} {encabezado['nom_pac']}", ln=True)

    fecha = encabezado['fecha'].strftime('%d/%m/%Y %H:%M')
    pdf_doc.cell(0, 7, f"Fecha de solicitud: {fecha}", ln=True)

    if encabezado.get('medico_nombre'):
        pdf_doc.cell(0, 7, f"Médico solicitante: {encabezado['medico_nombre']}", ln=True)

    # Observaciones generales
    if encabezado.get('observaciones'):
        pdf_doc.ln(3)
        pdf_doc.set_font('Arial', 'B', 11)
        pdf_doc.cell(0, 7, 'Observaciones generales:', ln=True)
        pdf_doc.set_font('Arial', '', 10)
        pdf_doc.multi_cell(0, 6, encabezado['observaciones'])

    # Línea separadora
    pdf_doc.ln(5)
    pdf_doc.cell(0, 0, '', 'T', ln=True)
    pdf_doc.ln(5)

    # Detalle de estudios
    pdf_doc.set_font('Arial', 'B', 12)
    pdf_doc.cell(0, 8, 'Estudios solicitados:', ln=True)
    pdf_doc.ln(3)

    pdf_doc.set_font('Arial', '', 10)
    for i, det in enumerate(detalles, 1):
        # Nombre del estudio
        pdf_doc.set_font('Arial', 'B', 10)
        pdf_doc.cell(0, 6, f"{i}. {det['nombre']}", ln=True)

        # Estado
        pdf_doc.set_font('Arial', '', 10)
        estado = det.get('estado', 'PENDIENTE')
        pdf_doc.cell(0, 5, f"   Estado: {estado}", ln=True)

        # Fecha realizado (si existe)
        if det.get('fecha_realizado'):
            fecha_real = det['fecha_realizado'].strftime('%d/%m/%Y')
            pdf_doc.cell(0, 5, f"   Fecha realizado: {fecha_real}", ln=True)

        # Indicador de archivo (si existe)
        if det.get('archivo_resultado'):
            pdf_doc.cell(0, 5, f"   Archivo resultado: Disponible", ln=True)

        # Observaciones del detalle
        if det.get('observaciones'):
            pdf_doc.multi_cell(0, 5, f"   Observaciones: {det['observaciones']}")

        pdf_doc.ln(3)

    # Espacio para firma
    pdf_doc.ln(10)
    pdf_doc.cell(0, 7, "__________________________________", ln=True, align='R')
    pdf_doc.set_font('Arial', 'B', 10)
    pdf_doc.cell(0, 7, "Firma del Médico", ln=True, align='R')

    response = make_response(pdf_doc.output(dest='S').encode('latin-1'))
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=gabinete_{id_examen}.pdf'
    return response