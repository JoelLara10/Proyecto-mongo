"""
Script para generar datos masivos de prueba para análisis clínicos
Ejecutar: python generate_mock_data.py
"""

from pymongo import MongoClient
from datetime import datetime, timedelta
import random
import uuid
from bson import ObjectId

# Configuración de conexión
MONGO_URI = "mongodb+srv://db_user:FRX5F6562LJtGgV0@cluster0.1zrjfmk.mongodb.net/?appName=Cluster0"  # Cambia según tu configuración
DB_NAME = "ineo_db2"  # Cambia según tu base de datos

# Conectar a MongoDB
client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# ==================== CONFIGURACIÓN ====================
NUM_PACIENTES = 200
NUM_ATENCIONES_POR_PACIENTE = (1, 8)  # Mínimo 1, máximo 8 atenciones por paciente
NUM_EXAMENES_POR_ATENCION = (1, 10)   # Mínimo 1, máximo 10 exámenes por atención

# Rangos para predicción de diabetes
GLUCOSA_RANGO = (70, 200)      # Normal < 100, Prediabético 100-125, Diabético > 126
HBA1C_RANGO = (4.5, 9.0)       # Normal < 5.7, Prediabético 5.7-6.4, Diabético > 6.5
COLESTEROL_RANGO = (150, 300)   # Normal < 200, Alto > 200

# Rangos para signos vitales
FC_RANGO = (50, 120)    # Frecuencia cardíaca (normal 60-100)
FR_RANGO = (10, 25)     # Frecuencia respiratoria (normal 12-20)
TEMP_RANGO = (35.5, 38.5)  # Temperatura (normal 36.1-37.2)
SPO2_RANGO = (85, 100)  # Saturación O2 (normal 95-100)

# Listas de datos
AREAS = ["Hospitalizado", "Urgencias", "Ambulatorio", "UCI", "Consultorio Externo"]
ESPECIALIDADES = ["Medicina General", "Cardiología", "Pediatría", "Traumatología", 
                  "Ginecología", "Oftalmología", "Neurología", "Psiquiatría"]

# Catálogo de exámenes (basado en tus datos reales)
CATALOGO_EXAMENES = [
    {"id_catalogo": 1, "nombre": "Agudeza visual", "tipo": "GABINETE", "precio": 150},
    {"id_catalogo": 2, "nombre": "Refracción", "tipo": "GABINETE", "precio": 200},
    {"id_catalogo": 3, "nombre": "Tonometría", "tipo": "GABINETE", "precio": 180},
    {"id_catalogo": 4, "nombre": "Biomicroscopía", "tipo": "GABINETE", "precio": 250},
    {"id_catalogo": 5, "nombre": "Fondo de ojo", "tipo": "GABINETE", "precio": 300},
    {"id_catalogo": 6, "nombre": "Campimetría", "tipo": "GABINETE", "precio": 220},
    {"id_catalogo": 7, "nombre": "OCT de mácula", "tipo": "GABINETE", "precio": 400},
    {"id_catalogo": 8, "nombre": "OCT de nervio óptico", "tipo": "GABINETE", "precio": 350},
    {"id_catalogo": 9, "nombre": "Paquimetría", "tipo": "GABINETE", "precio": 160},
    {"id_catalogo": 10, "nombre": "Topografía corneal", "tipo": "GABINETE", "precio": 280},
    {"id_catalogo": 11, "nombre": "Ultrasonido ocular", "tipo": "GABINETE", "precio": 320},
    {"id_catalogo": 12, "nombre": "Angiografía fluoresceínica", "tipo": "GABINETE", "precio": 450},
    {"id_catalogo": 13, "nombre": "Retinografía", "tipo": "GABINETE", "precio": 240},
    {"id_catalogo": 14, "nombre": "Gonioscopía", "tipo": "GABINETE", "precio": 190},
    {"id_catalogo": 15, "nombre": "Queratometría", "tipo": "GABINETE", "precio": 170},
    {"id_catalogo": 16, "nombre": "Biometría Hemática", "tipo": "LABORATORIO", "precio": 80},
    {"id_catalogo": 17, "nombre": "Química Sanguínea", "tipo": "LABORATORIO", "precio": 120},
    {"id_catalogo": 18, "nombre": "Glucosa", "tipo": "LABORATORIO", "precio": 50},
    {"id_catalogo": 19, "nombre": "Urea", "tipo": "LABORATORIO", "precio": 60},
    {"id_catalogo": 20, "nombre": "Creatinina", "tipo": "LABORATORIO", "precio": 70},
    {"id_catalogo": 21, "nombre": "Perfil Lipídico", "tipo": "LABORATORIO", "precio": 150},
    {"id_catalogo": 22, "nombre": "Examen General de Orina", "tipo": "LABORATORIO", "precio": 90},
    {"id_catalogo": 23, "nombre": "Tiempo de Protrombina", "tipo": "LABORATORIO", "precio": 100},
    {"id_catalogo": 24, "nombre": "Grupo y RH", "tipo": "LABORATORIO", "precio": 110},
    {"id_catalogo": 25, "nombre": "Hemoglobina Glicosilada", "tipo": "LABORATORIO", "precio": 130},
]

def generar_curp():
    """Generar CURP aleatoria"""
    consonantes = "BCDFGHJKLMNPQRSTVWXYZ"
    vocales = "AEIOU"
    return f"{random.choice(consonantes)}{random.choice(vocales)}{random.choice(consonantes)}{random.randint(10,99)}{random.randint(10,99)}{random.choice(consonantes)}{random.choice(vocales)}{random.randint(0,9)}{random.randint(0,9)}{random.choice(consonantes)}{random.choice(vocales)}{random.randint(0,9)}"

def generar_telefono():
    """Generar teléfono mexicano"""
    return f"722{random.randint(1000000, 9999999)}"

def generar_fecha_nacimiento():
    """Generar fecha de nacimiento (18-90 años)"""
    anos_atras = random.randint(18, 90)
    fecha = datetime.now() - timedelta(days=anos_atras * 365)
    return fecha.replace(hour=0, minute=0, second=0, microsecond=0)

def generar_fecha_ingreso(fecha_nacimiento):
    """Generar fecha de ingreso (últimos 2 años)"""
    dias_atras = random.randint(0, 730)
    return datetime.now() - timedelta(days=dias_atras)

def generar_valor_glucosa():
    """Generar valor de glucosa con tendencia a diabetes en algunos casos"""
    if random.random() < 0.15:  # 15% de riesgo alto
        return random.randint(127, 200)
    elif random.random() < 0.25:  # 25% de riesgo medio
        return random.randint(100, 126)
    else:
        return random.randint(70, 99)

def generar_valor_hba1c():
    """Generar valor de HbA1c con tendencia a diabetes"""
    if random.random() < 0.15:
        return round(random.uniform(6.6, 9.0), 1)
    elif random.random() < 0.25:
        return round(random.uniform(5.7, 6.5), 1)
    else:
        return round(random.uniform(4.5, 5.6), 1)

def generar_valor_colesterol():
    """Generar valor de colesterol"""
    if random.random() < 0.20:
        return random.randint(201, 300)
    else:
        return random.randint(150, 200)

def generar_signos_vitales():
    """Generar signos vitales (algunos anómalos intencionalmente)"""
    # 20% de probabilidad de generar valores anómalos
    if random.random() < 0.20:
        return {
            "ta": f"{random.randint(130, 180)}/{random.randint(90, 110)}",
            "fc": random.choice([random.randint(40, 59), random.randint(101, 130)]),
            "fr": random.choice([random.randint(8, 11), random.randint(21, 30)]),
            "temp": round(random.choice([random.uniform(35.0, 36.0), random.uniform(37.3, 39.0)]), 1),
            "spo2": random.randint(85, 94),
            "peso": round(random.uniform(50, 120), 1),
            "talla": round(random.uniform(1.50, 1.90), 2)
        }
    else:
        return {
            "ta": f"{random.randint(100, 130)}/{random.randint(60, 85)}",
            "fc": random.randint(60, 100),
            "fr": random.randint(12, 20),
            "temp": round(random.uniform(36.1, 37.2), 1),
            "spo2": random.randint(95, 100),
            "peso": round(random.uniform(50, 120), 1),
            "talla": round(random.uniform(1.50, 1.90), 2)
        }

def generar_camas():
    """Generar camas si no existen o agregar más"""
    print("\n🛏️ Generando camas...")
    
    # Obtener el máximo id_cama existente
    max_cama = db.camas.find_one(sort=[("id_cama", -1)])
    start_id = max_cama["id_cama"] + 1 if max_cama else 1
    
    areas = ["Hospitalizado", "Urgencias", "UCI", "Ambulatorio", "Consultorio Externo"]
    camas = []
    id_cama = start_id
    
    for area in areas:
        num_camas = 30 if area == "Hospitalizado" else 20 if area == "Urgencias" else 10
        for i in range(num_camas):
            # Verificar si ya existe una cama con este número en esta área
            existing = db.camas.find_one({"area": area, "numero": str(id_cama)})
            if not existing:
                camas.append({
                    "id_cama": id_cama,
                    "numero": str(id_cama),
                    "area": area,
                    "tipo_habitacion": random.choice(["Individual", "Compartida"]),
                    "piso": str(random.randint(1, 3)),
                    "seccion": random.choice(["A", "B", "C", "D"]),
                    "ocupada": random.choice([0, 1])
                })
            id_cama += 1
    
    if camas:
        try:
            db.camas.insert_many(camas, ordered=False)
            print(f"✅ Creadas {len(camas)} nuevas camas")
        except Exception as e:
            print(f"⚠️ Algunas camas ya existían: {e}")
    else:
        print("✅ No se necesitan nuevas camas")

def limpiar_datos_existentes():
    """Opcional: Limpiar datos existentes antes de generar nuevos"""
    respuesta = input("¿Deseas limpiar los datos existentes? (s/n): ")
    if respuesta.lower() == 's':
        colecciones = ["pacientes", "atencion", "examenes", "examenes_det", 
                      "signos_vitales", "cuenta_paciente", "familiares", 
                      "diagnosticos", "notas_medicas"]
        
        for col in colecciones:
            try:
                resultado = db[col].delete_many({})
                print(f"🗑️ Limpiados {resultado.deleted_count} registros de {col}")
            except Exception as e:
                print(f"⚠️ Error limpiando {col}: {e}")
        
        # Reiniciar contadores
        db.counters.update_one(
            {"_id": "pacientes_Id_exp"}, 
            {"$set": {"seq": 0}}, 
            upsert=True
        )
        db.counters.update_one(
            {"_id": "atencion_id_atencion"}, 
            {"$set": {"seq": 0}}, 
            upsert=True
        )
        db.counters.update_one(
            {"_id": "examenes_id_examen"}, 
            {"$set": {"seq": 0}}, 
            upsert=True
        )
        print("✅ Contadores reiniciados")

def obtener_siguiente_id(coleccion, id_field):
    """Obtener siguiente ID secuencial"""
    counter = db.counters.find_one_and_update(
        {"_id": coleccion},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True
    )
    return counter["seq"]

def generar_pacientes(n):
    """Generar n pacientes"""
    print(f"\n👥 Generando {n} pacientes...")
    pacientes = []
    
    # Obtener el máximo Id_exp existente
    max_exp = db.pacientes.find_one(sort=[("Id_exp", -1)])
    start_id = max_exp["Id_exp"] + 1 if max_exp else 1
    
    for i in range(n):
        fecha_nac = generar_fecha_nacimiento()
        paciente = {
            "Id_exp": start_id + i,
            "curp": generar_curp(),
            "papell": random.choice(["García", "Martínez", "López", "Hernández", "Pérez"]),
            "sapell": random.choice(["Rodríguez", "González", "Sánchez", "Ramírez", "Flores"]),
            "nom_pac": random.choice(["Juan", "María", "Carlos", "Ana", "Luis", "Laura", "José", "Carmen"]),
            "fecnac": fecha_nac.isoformat(),
            "tel": generar_telefono()
        }
        pacientes.append(paciente)
    
    if pacientes:
        db.pacientes.insert_many(pacientes)
        print(f"✅ Generados {len(pacientes)} pacientes")
    
    return pacientes

def generar_atenciones(pacientes):
    """Generar atenciones para los pacientes"""
    print(f"\n🏥 Generando atenciones...")
    atenciones = []
    examenes = []
    examenes_det = []
    signos_vitales = []
    cuenta_paciente = []
    
    # Obtener IDs iniciales
    max_atencion = db.atencion.find_one(sort=[("id_atencion", -1)])
    id_atencion = max_atencion["id_atencion"] + 1 if max_atencion else 1
    
    max_examen = db.examenes.find_one(sort=[("id_examen", -1)])
    id_examen = max_examen["id_examen"] + 1 if max_examen else 1
    
    max_signos = db.signos_vitales.find_one(sort=[("id_signos", -1)])
    id_signos = max_signos["id_signos"] + 1 if max_signos else 1
    
    for paciente in pacientes:
        num_atenciones = random.randint(*NUM_ATENCIONES_POR_PACIENTE)
        
        for _ in range(num_atenciones):
            fecha_ing = generar_fecha_ingreso(paciente["fecnac"])
            
            # Crear atención
            atencion = {
                "id_atencion": id_atencion,
                "Id_exp": paciente["Id_exp"],
                "area": random.choice(AREAS),
                "id_cama": random.randint(1, 100),
                "motivo": random.choice(["Consulta general", "Urgencia", "Cirugía", "Revisión", "Dolor"]),
                "especialidad": random.choice(ESPECIALIDADES),
                "alergias": random.choice(["ninguna", "penicilina", "aspirina", "polvo", "ninguna"]),
                "fecha_ing": fecha_ing.isoformat(),
                "status": "ABIERTA"
            }
            atenciones.append(atencion)
            
            # Generar exámenes para esta atención
            num_examenes = random.randint(*NUM_EXAMENES_POR_ATENCION)
            
            for _ in range(num_examenes):
                catalogo = random.choice(CATALOGO_EXAMENES)
                
                # Determinar valores según el tipo de examen
                subtotal = catalogo["precio"]
                
                if catalogo["nombre"] == "Glucosa":
                    subtotal = generar_valor_glucosa()
                elif catalogo["nombre"] == "Hemoglobina Glicosilada":
                    subtotal = generar_valor_hba1c()
                elif catalogo["nombre"] == "Perfil Lipídico":
                    subtotal = generar_valor_colesterol()
                elif catalogo["nombre"] == "Química Sanguínea":
                    subtotal = generar_valor_glucosa()
                
                # Crear examen
                examen = {
                    "id_examen": id_examen,
                    "id_atencion": id_atencion,
                    "id_medico": "69a073bc424067937fe1ad69",
                    "observaciones": random.choice(["", "Urgente", "Requiere seguimiento"]),
                    "fecha": fecha_ing.isoformat(),
                    "subtotal_total": catalogo["precio"]
                }
                examenes.append(examen)
                
                # Crear detalle de examen
                examen_det = {
                    "id_examen": id_examen,
                    "id_catalogo": catalogo["id_catalogo"],
                    "nombre_examen": catalogo["nombre"],
                    "precio": catalogo["precio"],
                    "cantidad": 1,
                    "subtotal": subtotal,
                    "estado": random.choice(["PENDIENTE", "REALIZADO"]),
                    "fecha": fecha_ing.isoformat()
                }
                
                # Si es examen de laboratorio/gabinete con valor numérico, agregar campo de resultado
                if catalogo["nombre"] in ["Glucosa", "Hemoglobina Glicosilada", "Perfil Lipídico", "Química Sanguínea"]:
                    examen_det["resultado"] = subtotal
                    if catalogo["nombre"] == "Glucosa":
                        examen_det["unidad"] = "mg/dL"
                    elif catalogo["nombre"] == "Hemoglobina Glicosilada":
                        examen_det["unidad"] = "%"
                    elif catalogo["nombre"] == "Perfil Lipídico":
                        examen_det["unidad"] = "mg/dL"
                
                examenes_det.append(examen_det)
                
                # Crear cuenta_paciente
                cuenta = {
                    "id_atencion": id_atencion,
                    "Id_exp": paciente["Id_exp"],
                    "fecha": fecha_ing.isoformat(),
                    "descripcion": f"Examen de {catalogo['tipo'].lower()}: {catalogo['nombre']}",
                    "cantidad": 1,
                    "precio": catalogo["precio"],
                    "subtotal": subtotal,
                    "id_examen": id_examen,
                    "tipo": catalogo["tipo"],
                    "estado": random.choice(["PENDIENTE", "PAGADO", "FACTURADO"])
                }
                cuenta_paciente.append(cuenta)
                
                id_examen += 1
            
            # Generar signos vitales (70% de probabilidad)
            if random.random() < 0.7:
                signos = generar_signos_vitales()
                signos.update({
                    "id_signos": id_signos,
                    "id_atencion": id_atencion,
                    "fecha_registro": fecha_ing.isoformat()
                })
                signos_vitales.append(signos)
                id_signos += 1
            
            id_atencion += 1
    
    # Insertar en MongoDB
    if atenciones:
        db.atencion.insert_many(atenciones)
        print(f"✅ Generadas {len(atenciones)} atenciones")
    
    if examenes:
        db.examenes.insert_many(examenes)
        print(f"✅ Generados {len(examenes)} exámenes")
    
    if examenes_det:
        db.examenes_det.insert_many(examenes_det)
        print(f"✅ Generados {len(examenes_det)} detalles de exámenes")
    
    if signos_vitales:
        db.signos_vitales.insert_many(signos_vitales)
        print(f"✅ Generados {len(signos_vitales)} registros de signos vitales")
    
    if cuenta_paciente:
        db.cuenta_paciente.insert_many(cuenta_paciente)
        print(f"✅ Generados {len(cuenta_paciente)} registros en cuenta_paciente")
    
    return atenciones

def generar_familiares(pacientes):
    """Generar familiares para algunos pacientes"""
    print(f"\n👪 Generando familiares...")
    familiares = []
    parentescos = ["Padre", "Madre", "Hijo", "Hija", "Esposo", "Esposa", "Hermano", "Hermana"]
    
    for paciente in random.sample(pacientes, min(50, len(pacientes))):
        if random.random() < 0.5:
            familiar = {
                "Id_exp": paciente["Id_exp"],
                "nombre": f"{random.choice(['Juan', 'María', 'Carlos', 'Ana'])} {random.choice(['García', 'Martínez'])}",
                "parentesco": random.choice(parentescos),
                "telefono": generar_telefono()
            }
            familiares.append(familiar)
    
    if familiares:
        db.familiares.insert_many(familiares)
        print(f"✅ Generados {len(familiares)} familiares")

def generar_diagnosticos(atenciones):
    """Generar diagnósticos para algunas atenciones"""
    print(f"\n📋 Generando diagnósticos...")
    diagnosticos = []
    
    diagnosticos_posibles = [
        "Hipertensión esencial",
        "Diabetes mellitus tipo 2",
        "Infección respiratoria aguda",
        "Ojo rojo",
        "Conjuntivitis",
        "Catarata",
        "Glaucoma",
        "Presbicia",
        "Miopía",
        "Hipermetropía"
    ]
    
    max_diagnostico = db.diagnosticos.find_one(sort=[("id_diagnostico", -1)])
    id_diagnostico = max_diagnostico["id_diagnostico"] + 1 if max_diagnostico else 1
    
    for atencion in random.sample(atenciones, min(len(atenciones), len(atenciones) // 2)):
        if random.random() < 0.6:
            diagnostico = {
                "id_diagnostico": id_diagnostico,
                "id_atencion": atencion["id_atencion"],
                "diagnostico_principal": random.choice(diagnosticos_posibles),
                "diagnosticos_secundarios": random.choice(["", random.choice(diagnosticos_posibles)]),
                "observaciones": random.choice(["", "Requiere seguimiento", "Tratamiento indicado"]),
                "fecha_registro": datetime.now().isoformat()
            }
            diagnosticos.append(diagnostico)
            id_diagnostico += 1
    
    if diagnosticos:
        db.diagnosticos.insert_many(diagnosticos)
        print(f"✅ Generados {len(diagnosticos)} diagnósticos")

def generar_notas_medicas(atenciones):
    """Generar notas médicas para algunas atenciones"""
    print(f"\n📝 Generando notas médicas...")
    notas = []
    
    max_nota = db.notas_medicas.find_one(sort=[("id_nota", -1)])
    id_nota = max_nota["id_nota"] + 1 if max_nota else 1
    
    for atencion in random.sample(atenciones, min(len(atenciones), len(atenciones) // 3)):
        if random.random() < 0.5:
            nota = {
                "id_nota": id_nota,
                "id_atencion": atencion["id_atencion"],
                "subjetivo": random.choice(["Paciente refiere dolor", "Paciente estable", "Paciente con mejora"]),
                "objetivo": random.choice(["TA normal", "FC normal", "Signos vitales estables"]),
                "analisis": random.choice(["Mejoría", "Requiere más estudios", "Evolución favorable"]),
                "plan": random.choice(["Seguimiento en 1 semana", "Medicación indicada", "Reposo"]),
                "id_medico": "69a073bc424067937fe1ad69",
                "fecha_registro": datetime.now().isoformat()
            }
            notas.append(nota)
            id_nota += 1
    
    if notas:
        db.notas_medicas.insert_many(notas)
        print(f"✅ Generadas {len(notas)} notas médicas")

def generar_catalogo_examenes():
    """Asegurar que el catálogo de exámenes existe"""
    print(f"\n📚 Verificando catálogo de exámenes...")
    
    existentes = list(db.catalogo_examenes.find())
    
    if len(existentes) < len(CATALOGO_EXAMENES):
        # No limpiar, solo agregar los que faltan
        for examen in CATALOGO_EXAMENES:
            db.catalogo_examenes.update_one(
                {"id_catalogo": examen["id_catalogo"]},
                {"$set": examen},
                upsert=True
            )
        print(f"✅ Catálogo de exámenes actualizado ({len(CATALOGO_EXAMENES)} registros)")
    else:
        print(f"✅ Catálogo de exámenes ya existe ({len(existentes)} registros)")

def mostrar_estadisticas():
    """Mostrar estadísticas finales"""
    print("\n" + "="*50)
    print("📊 ESTADÍSTICAS FINALES")
    print("="*50)
    
    estadisticas = {
        "pacientes": db.pacientes.count_documents({}),
        "atenciones": db.atencion.count_documents({}),
        "examenes": db.examenes.count_documents({}),
        "examenes_det": db.examenes_det.count_documents({}),
        "signos_vitales": db.signos_vitales.count_documents({}),
        "familiares": db.familiares.count_documents({}),
        "diagnosticos": db.diagnosticos.count_documents({}),
        "notas_medicas": db.notas_medicas.count_documents({}),
        "cuenta_paciente": db.cuenta_paciente.count_documents({})
    }
    
    for key, value in estadisticas.items():
        print(f"  📌 {key}: {value}")
    
    print("="*50)
    
    # Mostrar algunos datos de diabetes para verificar
    examenes_diabetes = list(db.examenes_det.find({
        "nombre_examen": {"$in": ["Glucosa", "Hemoglobina Glicosilada", "Perfil Lipídico", "Química Sanguínea"]}
    }).limit(5))
    
    if examenes_diabetes:
        print("\n🩺 Muestra de datos para predicción de diabetes:")
        for ex in examenes_diabetes:
            valor = ex.get('subtotal', ex.get('precio', 'N/A'))
            print(f"  - {ex['nombre_examen']}: {valor}")
    
    # Mostrar algunos signos vitales anómalos
    signos_anomalos = list(db.signos_vitales.find({
        "$or": [
            {"fc": {"$lt": 60}},
            {"fc": {"$gt": 100}},
            {"spo2": {"$lt": 95}}
        ]
    }).limit(5))
    
    if signos_anomalos:
        print(f"\n⚠️ Ejemplo de signos vitales anómalos:")
        for sig in signos_anomalos[:3]:
            print(f"  - FC: {sig.get('fc')}, SPO2: {sig.get('spo2')}")

def main():
    """Función principal"""
    print("\n" + "="*50)
    print("🚀 GENERADOR DE DATOS MASIVOS PARA ANÁLISIS CLÍNICOS")
    print("="*50)
    
    # Opción para limpiar datos existentes
    limpiar_datos_existentes()
    
    # Generar datos
    generar_camas()
    generar_catalogo_examenes()
    pacientes = generar_pacientes(NUM_PACIENTES)
    atenciones = generar_atenciones(pacientes)
    generar_familiares(pacientes)
    generar_diagnosticos(atenciones)
    generar_notas_medicas(atenciones)
    
    # Mostrar estadísticas
    mostrar_estadisticas()
    
    print("\n✅ GENERACIÓN COMPLETADA")
    print("\n💡 Ahora puedes ejecutar los análisis clínicos:")
    print("   python main_clinical_analytics.py")
    print("   o desde el panel administrativo: /admin/clinical-analytics")

if __name__ == "__main__":
    main()