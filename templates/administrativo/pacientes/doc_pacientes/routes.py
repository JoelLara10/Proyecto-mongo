from flask import Blueprint, make_response
from fpdf import FPDF
from bd import get_db_connection
from datetime import datetime
from bson import ObjectId

pdf = Blueprint('pdf', __name__)


# ===============================
# HOJA INICIAL
# ===============================
@pdf.route('/pdf/hoja-inicial/<int:id_exp>/<int:id_atencion>')
def hoja_inicial(id_exp, id_atencion):
    try:
        db = get_db_connection()

        # ===============================
        # OBTENER DATOS DE MONGODB
        # ===============================

        # 1. Obtener atención
        atencion = db['atencion'].find_one({"id_atencion": id_atencion}) or {}

        # 2. Obtener paciente
        paciente = db['pacientes'].find_one({"Id_exp": id_exp}) or {}

        # 3. Obtener médico(s) de atencion_medicos
        medicos_asignados = list(db['atencion_medicos'].find({"id_atencion": id_atencion}))
        medico = {}
        if medicos_asignados:
            # Tomar el primer médico asignado
            id_medico = medicos_asignados[0].get('id_medico')
            if id_medico:
                medico = db['users'].find_one({"id": id_medico}) or {}

        # ===============================
        # GENERAR PDF
        # ===============================
        pdf_doc = FPDF('P', 'mm', 'Letter')
        pdf_doc.set_auto_page_break(True, 25)
        pdf_doc.add_page()

        # Título
        pdf_doc.set_font('Arial', 'B', 16)
        pdf_doc.cell(0, 10, 'HOJA INICIAL', ln=True, align='C')

        # Fecha
        pdf_doc.set_font('Arial', '', 10)
        fecha = atencion.get('fecha_ing')
        if fecha:
            if isinstance(fecha, str):
                try:
                    fecha = datetime.strptime(fecha.split('T')[0], '%Y-%m-%d')
                except:
                    fecha = datetime.now()
            fecha_str = fecha.strftime('%d/%m/%Y %H:%M')
        else:
            fecha_str = ''
        pdf_doc.cell(0, 6, f'Fecha de ingreso: {fecha_str}', ln=True, align='R')
        pdf_doc.ln(4)

        # Datos del Paciente
        pdf_doc.set_font('Arial', 'B', 11)
        pdf_doc.cell(0, 8, 'Datos del Paciente', ln=True)

        pdf_doc.set_font('Arial', '', 10)
        pdf_doc.cell(
            0, 7,
            f"Paciente: {paciente.get('papell', '')} {paciente.get('sapell', '')} {paciente.get('nom_pac', '')}",
            ln=True
        )
        pdf_doc.cell(0, 7, f"Teléfono: {paciente.get('tel', 'No especificado')}", ln=True)

        # Datos de Atención
        pdf_doc.ln(3)
        pdf_doc.set_font('Arial', 'B', 11)
        pdf_doc.cell(0, 8, 'Datos de Atención', ln=True)

        pdf_doc.set_font('Arial', '', 10)
        pdf_doc.cell(0, 7, f"Área: {atencion.get('area', '')}", ln=True)
        pdf_doc.multi_cell(0, 7, f"Motivo de atención:\n{atencion.get('motivo', '')}")
        pdf_doc.multi_cell(0, 7, f"Alergias:\n{atencion.get('alergias', 'No especificado')}")

        # Médico
        pdf_doc.ln(20)
        pdf_doc.set_font('Arial', 'B', 10)
        pdf_doc.cell(
            0, 6,
            f"Médico: {medico.get('papell', '')} ({medico.get('username', '')})",
            ln=True, align='C'
        )

        response = make_response(pdf_doc.output(dest='S').encode('latin-1'))
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'inline; filename=hoja_inicial.pdf'
        return response

    except Exception as e:
        print(f"Error generando hoja inicial: {e}")
        return f"Error: {e}", 500


# ===============================
# HOJA FRONTAL
# ===============================
@pdf.route('/pdf/hoja-frontal/<int:id_exp>/<int:id_atencion>')
def hoja_frontal(id_exp, id_atencion):
    try:
        db = get_db_connection()

        # Obtener datos
        atencion = db['atencion'].find_one({"id_atencion": id_atencion}) or {}
        paciente = db['pacientes'].find_one({"Id_exp": id_exp}) or {}

        # Obtener médico
        medicos_asignados = list(db['atencion_medicos'].find({"id_atencion": id_atencion}))
        medico = {}
        if medicos_asignados:
            id_medico = medicos_asignados[0].get('id_medico')
            if id_medico:
                medico = db['users'].find_one({"id": id_medico}) or {}

        # Generar PDF
        pdf_doc = FPDF('P', 'mm', 'Letter')
        pdf_doc.set_auto_page_break(True, 25)
        pdf_doc.add_page()

        # Título
        pdf_doc.set_font('Arial', 'B', 16)
        pdf_doc.cell(0, 10, 'HOJA FRONTAL', ln=True, align='C')

        # Fecha
        pdf_doc.set_font('Arial', '', 10)
        fecha = atencion.get('fecha_ing')
        if fecha:
            if isinstance(fecha, str):
                try:
                    fecha = datetime.strptime(fecha.split('T')[0], '%Y-%m-%d')
                except:
                    fecha = datetime.now()
            fecha_str = fecha.strftime('%d/%m/%Y %H:%M')
        else:
            fecha_str = ''
        pdf_doc.cell(0, 6, f'Fecha de ingreso: {fecha_str}', ln=True, align='R')
        pdf_doc.ln(4)

        # Datos Paciente
        pdf_doc.set_font('Arial', 'B', 11)
        pdf_doc.cell(0, 8, 'Datos del Paciente', ln=True)

        pdf_doc.set_font('Arial', '', 10)
        pdf_doc.cell(
            0, 7,
            f"Paciente: {id_exp} - {paciente.get('papell', '')} {paciente.get('sapell', '')} {paciente.get('nom_pac', '')}",
            ln=True
        )
        pdf_doc.cell(0, 7, f"Teléfono: {paciente.get('tel', 'No especificado')}", ln=True)

        # Edad
        fecnac = paciente.get('fecnac')
        if fecnac:
            if isinstance(fecnac, str):
                try:
                    fecnac = datetime.strptime(fecnac.split('T')[0], '%Y-%m-%d')
                except:
                    fecnac = None
            if fecnac:
                edad = datetime.now().year - fecnac.year
                pdf_doc.cell(0, 7, f"Edad: {edad} años", ln=True)

        pdf_doc.ln(3)

        # Datos Atención
        pdf_doc.set_font('Arial', 'B', 11)
        pdf_doc.cell(0, 8, 'Datos de Atención', ln=True)

        pdf_doc.set_font('Arial', '', 10)
        pdf_doc.cell(0, 7, f"Área: {atencion.get('area', '')}", ln=True)
        pdf_doc.cell(0, 7, f"Especialidad: {atencion.get('especialidad', 'No especificada')}", ln=True)
        pdf_doc.multi_cell(0, 7, f"Motivo de atención:\n{atencion.get('motivo', '')}")
        pdf_doc.multi_cell(0, 7, f"Alergias:\n{atencion.get('alergias', 'No especificado')}")

        # Médico
        pdf_doc.ln(15)
        pdf_doc.set_font('Arial', 'B', 10)
        pdf_doc.cell(
            0, 6,
            f"Médico tratante: {medico.get('papell', '')} ({medico.get('username', '')})",
            ln=True, align='C'
        )

        response = make_response(pdf_doc.output(dest='S').encode('latin-1'))
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'inline; filename=hoja_frontal.pdf'
        return response

    except Exception as e:
        print(f"Error generando hoja frontal: {e}")
        return f"Error: {e}", 500


# ===============================
# CONTRATO DE SERVICIOS
# ===============================
@pdf.route('/pdf/contrato-servicios/<int:id_exp>/<int:id_atencion>')
def contrato_servicios(id_exp, id_atencion):
    try:
        db = get_db_connection()

        # Obtener datos
        paciente = db['pacientes'].find_one({"Id_exp": id_exp}) or {}
        atencion = db['atencion'].find_one({"id_atencion": id_atencion}) or {}

        # Obtener médico
        medicos_asignados = list(db['atencion_medicos'].find({"id_atencion": id_atencion}))
        medico = {}
        if medicos_asignados:
            id_medico = medicos_asignados[0].get('id_medico')
            if id_medico:
                medico = db['users'].find_one({"id": id_medico}) or {}

        # Generar PDF
        pdf = FPDF('P', 'mm', 'Letter')
        pdf.set_auto_page_break(True, 30)
        pdf.add_page()

        # Encabezado
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'CONTRATO DE PRESTACIÓN DE SERVICIOS HOSPITALARIOS', ln=True, align='C')

        # Fecha
        pdf.set_font('Arial', '', 10)
        fecha = atencion.get('fecha_ing')
        if fecha:
            if isinstance(fecha, str):
                try:
                    fecha = datetime.strptime(fecha.split('T')[0], '%Y-%m-%d')
                except:
                    fecha = datetime.now()
            fecha_str = fecha.strftime('%d/%m/%Y %H:%M')
        else:
            fecha_str = ''
        pdf.cell(0, 6, f'Fecha: {fecha_str}', ln=True, align='R')
        pdf.ln(4)

        # Datos Paciente
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(0, 8, 'Datos del Paciente', ln=True)

        pdf.set_font('Arial', '', 10)
        pdf.cell(
            0, 7,
            f"Paciente: {id_exp} - {paciente.get('papell', '')} {paciente.get('sapell', '')} {paciente.get('nom_pac', '')}",
            ln=True
        )
        pdf.cell(0, 7, f"Teléfono: {paciente.get('tel', 'No especificado')}", ln=True)

        # Edad
        fecnac = paciente.get('fecnac')
        if fecnac:
            if isinstance(fecnac, str):
                try:
                    fecnac = datetime.strptime(fecnac.split('T')[0], '%Y-%m-%d')
                except:
                    fecnac = None
            if fecnac:
                edad = datetime.now().year - fecnac.year
                pdf.cell(0, 7, f"Edad: {edad} años", ln=True)

        pdf.ln(4)

        # Cláusulas
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'CLÁUSULAS', ln=True, align='C')
        pdf.ln(2)

        pdf.set_font('Arial', '', 9)

        pdf.multi_cell(0, 6,
                       'PRIMERA.- El INSTITUTO DE ENFERMEDADES OCULARES se obliga, a solicitud del PACIENTE, '
                       'a proporcionarle los servicios hospitalarios necesarios conforme a indicaciones médicas.'
                       )
        pdf.ln(1)

        pdf.multi_cell(0, 6,
                       'SEGUNDA.- El PACIENTE se obliga a cubrir el importe total de los servicios médicos, '
                       'hospitalarios, medicamentos, estudios y cualquier otro cargo derivado de su atención.'
                       )
        pdf.ln(1)

        pdf.multi_cell(0, 6,
                       'TERCERA.- El PACIENTE acepta que los pagos deberán cubrirse conforme se generen los cargos, '
                       'liquidando el total al momento del alta médica.'
                       )
        pdf.ln(1)

        pdf.multi_cell(0, 6,
                       'CUARTA.- El PACIENTE se compromete a respetar el reglamento interno del Instituto, '
                       'liberándolo de cualquier responsabilidad ajena al acto médico.'
                       )
        pdf.ln(1)

        pdf.multi_cell(0, 6,
                       f'QUINTA.- El PACIENTE autoriza al Médico tratante {medico.get("papell", "")} '
                       'para llevar a cabo los procedimientos médicos y/o quirúrgicos que considere necesarios.'
                       )
        pdf.ln(1)

        pdf.multi_cell(0, 6,
                       'SEXTA.- En caso de que el PACIENTE no pueda firmar el presente contrato, '
                       'podrá hacerlo la persona responsable que lo acompañe.'
                       )

        # Firmas
        pdf.ln(10)
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 6, f'Metepec, México a {datetime.now().strftime("%d/%m/%Y")}', ln=True, align='C')
        pdf.ln(8)

        pdf.set_font('Arial', 'B', 10)
        pdf.cell(95, 6, 'PACIENTE', 0, 0, 'C')
        pdf.cell(95, 6, 'INSTITUTO', 0, 1, 'C')

        pdf.set_font('Arial', '', 10)
        pdf.cell(
            95, 6,
            f"{paciente.get('papell', '')} {paciente.get('sapell', '')} {paciente.get('nom_pac', '')}",
            0, 0, 'C'
        )
        pdf.cell(95, 6, 'INSTITUTO DE ENFERMEDADES OCULARES', 0, 1, 'C')

        pdf.ln(4)
        pdf.cell(95, 6, '_____________________________', 0, 0, 'C')
        pdf.cell(95, 6, '_____________________________', 0, 1, 'C')
        pdf.cell(95, 6, 'NOMBRE Y FIRMA', 0, 0, 'C')
        pdf.cell(95, 6, 'NOMBRE Y FIRMA', 0, 1, 'C')

        response = make_response(pdf.output(dest='S').encode('latin-1'))
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'inline; filename=contrato_servicios.pdf'
        return response

    except Exception as e:
        print(f"Error generando contrato: {e}")
        return f"Error: {e}", 500


# ===============================
# CONSENTIMIENTO DATOS PERSONALES
# ===============================
@pdf.route('/pdf/consentimiento-datos/<int:id_exp>/<int:id_atencion>')
def consentimiento_datos(id_exp, id_atencion):
    try:
        db = get_db_connection()

        paciente = db['pacientes'].find_one({"Id_exp": id_exp}) or {}
        atencion = db['atencion'].find_one({"id_atencion": id_atencion}) or {}

        pdf = FPDF('P', 'mm', 'Letter')
        pdf.alias_nb_pages()
        pdf.set_auto_page_break(True, 30)
        pdf.add_page()

        # Encabezado
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 12, 'CARTA DE CONSENTIMIENTO PARA TRATAMIENTO DE DATOS PERSONALES', ln=True, align='C')

        # Fecha
        pdf.set_font('Arial', '', 10)
        fecha = atencion.get('fecha_ing')
        if fecha:
            if isinstance(fecha, str):
                try:
                    fecha = datetime.strptime(fecha.split('T')[0], '%Y-%m-%d')
                except:
                    fecha = datetime.now()
            fecha_str = fecha.strftime('%d/%m/%Y %H:%M')
        else:
            fecha_str = ''
        pdf.cell(0, 6, f'Fecha: {fecha_str}', ln=True, align='R')
        pdf.ln(5)

        # Datos del Paciente
        pdf.set_font('Arial', 'B', 11)
        pdf.set_fill_color(230, 240, 255)
        pdf.cell(0, 8, 'Datos del Paciente:', ln=True, fill=True)

        pdf.set_font('Arial', '', 10)
        pdf.cell(
            0, 7,
            f"Paciente: {paciente.get('papell', '')} {paciente.get('sapell', '')} {paciente.get('nom_pac', '')}",
            ln=True
        )
        pdf.cell(0, 7, f"Teléfono: {paciente.get('tel', 'No especificado')}", ln=True)
        pdf.ln(4)

        # Título
        pdf.set_font('Arial', 'B', 13)
        pdf.set_fill_color(220, 230, 250)
        pdf.cell(0, 8, 'CARTA DE CONSENTIMIENTO', ln=True, align='C', fill=True)
        pdf.ln(2)

        # Texto legal
        pdf.set_font('Arial', '', 9)
        pdf.multi_cell(0, 6,
                       'El (la) que suscribe otorga su consentimiento expreso para que el '
                       'INSTITUTO DE ENFERMEDADES OCULARES recabe, almacene, proteja y trate '
                       'sus datos personales, necesarios para brindarle atención médica.',
                       align='J'
                       )
        pdf.ln(2)

        pdf.multi_cell(0, 6,
                       'Manifiesto que tengo pleno conocimiento del Aviso de Privacidad Integral '
                       'relativo al tratamiento de mis datos personales, así como de los '
                       'mecanismos para ejercer mis derechos ARCO. Asimismo, autorizo que la '
                       'información médica generada sea resguardada en mi Expediente Clínico '
                       'durante el tiempo que la ley establece.',
                       align='J'
                       )

        # Firmas
        pdf.ln(10)
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 6, f"Metepec, México a {datetime.now().strftime('%d/%m/%Y')}", ln=True, align='C')
        pdf.ln(8)

        pdf.set_font('Arial', 'B', 10)
        pdf.cell(95, 6, 'PACIENTE', 0, 0, 'C')
        pdf.cell(95, 6, 'INSTITUTO', 0, 1, 'C')

        pdf.set_font('Arial', '', 10)
        pdf.cell(
            95, 6,
            f"{paciente.get('papell', '')} {paciente.get('sapell', '')} {paciente.get('nom_pac', '')}",
            0, 0, 'C'
        )
        pdf.cell(95, 6, 'INSTITUTO DE ENFERMEDADES OCULARES', 0, 1, 'C')

        pdf.ln(4)
        pdf.cell(95, 6, '_____________________________', 0, 0, 'C')
        pdf.cell(95, 6, '_____________________________', 0, 1, 'C')
        pdf.cell(95, 6, 'NOMBRE Y FIRMA', 0, 0, 'C')
        pdf.cell(95, 6, 'NOMBRE Y FIRMA', 0, 1, 'C')

        response = make_response(pdf.output(dest='S').encode('latin-1'))
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'inline; filename=consentimiento_datos.pdf'
        return response

    except Exception as e:
        print(f"Error generando consentimiento: {e}")
        return f"Error: {e}", 500


# ===============================
# FICHA DE IDENTIFICACIÓN
# ===============================
@pdf.route('/pdf/ficha-identificacion/<int:id_exp>/<int:id_atencion>')
def ficha_identificacion(id_exp, id_atencion):
    try:
        db = get_db_connection()

        paciente = db['pacientes'].find_one({"Id_exp": id_exp}) or {}
        atencion = db['atencion'].find_one({"id_atencion": id_atencion}) or {}

        # Obtener médico
        medicos_asignados = list(db['atencion_medicos'].find({"id_atencion": id_atencion}))
        medico = {}
        if medicos_asignados:
            id_medico = medicos_asignados[0].get('id_medico')
            if id_medico:
                medico = db['users'].find_one({"id": id_medico}) or {}

        pdf = FPDF('L', 'mm', (210, 135))  # tamaño controlado
        pdf.set_margins(15, 12, 15)
        pdf.set_auto_page_break(True, 15)
        pdf.add_page()

        # Título
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 8, 'TARJETA DE IDENTIFICACIÓN', ln=True, align='C')

        # Fecha
        pdf.set_font('Arial', '', 8)
        fecha = atencion.get('fecha_ing')
        if fecha:
            if isinstance(fecha, str):
                try:
                    fecha = datetime.strptime(fecha.split('T')[0], '%Y-%m-%d')
                except:
                    fecha = datetime.now()
            fecha_str = fecha.strftime('%d/%m/%Y %H:%M')
        else:
            fecha_str = ''
        pdf.cell(0, 5, f'Fecha: {fecha_str}', ln=True, align='R')
        pdf.ln(2)

        # Datos del Paciente
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(0, 6, 'Datos del Paciente', ln=True)

        pdf.set_font('Arial', '', 8)

        # Línea 1
        pdf.cell(12, 5, 'Paciente:', 0, 0)
        pdf.cell(
            60, 5,
            f"{id_exp} - {paciente.get('papell', '')} {paciente.get('sapell', '')} {paciente.get('nom_pac', '')}",
            0, 0
        )
        pdf.cell(18, 5, 'Nacimiento:', 0, 0)
        fecnac = paciente.get('fecnac')
        if fecnac:
            if isinstance(fecnac, str):
                try:
                    fecnac = datetime.strptime(fecnac.split('T')[0], '%Y-%m-%d')
                except:
                    fecnac = None
            if fecnac:
                pdf.cell(40, 5, fecnac.strftime('%d/%m/%Y'), 0, 1)
            else:
                pdf.cell(40, 5, 'No especificado', 0, 1)
        else:
            pdf.cell(40, 5, 'No especificado', 0, 1)

        # Línea 2
        pdf.cell(28, 5, 'CURP:', 0, 0)
        pdf.cell(40, 5, paciente.get('curp', 'No especificado'), 0, 0)
        pdf.cell(18, 5, 'Tel:', 0, 0)
        pdf.cell(0, 5, paciente.get('tel', 'No especificado'), 0, 1)

        # Línea 3
        pdf.cell(15, 5, 'Ingreso:', 0, 0)
        pdf.cell(45, 5, fecha_str, 0, 0)
        pdf.cell(15, 5, 'Médico:', 0, 0)
        pdf.cell(0, 5, medico.get('papell', 'No especificado'), 0, 1)

        # Línea 4
        pdf.cell(25, 5, 'Servicio:', 0, 0)
        pdf.cell(40, 5, atencion.get('area', 'No especificado'), 0, 1)

        # DX
        pdf.cell(12, 5, 'DX:', 0, 0)
        pdf.multi_cell(0, 5, atencion.get('motivo', 'No especificado'))

        # Línea 5 - Alergias
        pdf.cell(18, 5, 'Alergias:', 0, 0)
        pdf.multi_cell(0, 5, atencion.get('alergias', 'No especificado'))

        # Línea 6
        pdf.ln(2)
        pdf.cell(0, 5, 'Riesgo de Caídas: _______________    Riesgo de UPP: _______________', 0, 1)

        response = make_response(pdf.output(dest='S').encode('latin-1'))
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = 'inline; filename=ficha_identificacion.pdf'
        return response

    except Exception as e:
        print(f"Error generando ficha: {e}")
        return f"Error: {e}", 500


# ===============================
# EXPEDIENTE COMPLETO
# ===============================
@pdf.route('/pdf/expediente-completo/<int:id_exp>/<int:id_atencion>')
def expediente_completo(id_exp, id_atencion):
    try:
        # Aquí puedes implementar la lógica para generar un PDF con todo el expediente
        return f"PDF Expediente Completo {id_exp} {id_atencion}"
    except Exception as e:
        return f"Error: {e}", 500