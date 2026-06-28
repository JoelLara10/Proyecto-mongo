# verificar_duplicados.py
from bd import get_db_connection
db = get_db_connection()

# Crear colección si no existe
if 'medications' not in db.list_collection_names():
    db.create_collection('medications')
    print("✅ Colección 'medications' creada")

# Crear índices
db['medications'].create_index([('id_atencion', 1)])
db['medications'].create_index([('fecha_registro', -1)])
db['medications'].create_index([('Id_exp', 1)])

print("✅ Índices creados")

# Inicializar secuencia si no existe
if not db['counters'].find_one({'_id': 'medications_registro_id'}):
    db['counters'].insert_one({'_id': 'medications_registro_id', 'seq': 0})
    print("✅ Secuencia 'medications_registro_id' inicializada")

print("✅ Configuración completada")


""" # crear_coleccion_nursing_notes.py

# Crear colección si no existe
if 'nursing_notes' not in db.list_collection_names():
    db.create_collection('nursing_notes')
    print("✅ Colección 'nursing_notes' creada")

# Crear índices
db['nursing_notes'].create_index([('id_atencion', 1)])
db['nursing_notes'].create_index([('fecha_registro', -1)])
db['nursing_notes'].create_index([('Id_exp', 1)])

print("✅ Índices creados")

# Verificar que el contador existe
if 'counters' not in db.list_collection_names():
    db.create_collection('counters')
    print("✅ Colección 'counters' creada")

# Inicializar secuencia si no existe
if not db['counters'].find_one({'_id': 'nursing_notes_id'}):
    db['counters'].insert_one({'_id': 'nursing_notes_id', 'seq': 0})
    print("✅ Secuencia 'nursing_notes_id' inicializada")

print("✅ Configuración completada") """

""" # 1. Obtener el máximo id_examen actual
max_examen = db['examenes'].find_one(sort=[('id_examen', -1)])
max_id = max_examen['id_examen'] if max_examen else 0
print(f"📊 Máximo id_examen actual: {max_id}")

# 2. Actualizar contador
db['counters'].update_one(
    {'_id': 'examenes_id_examen'},
    {'$set': {'seq': max_id}},
    upsert=True
)
print(f"✅ Contador 'examenes_id_examen' actualizado a {max_id}")

# 3. Verificar el contador
counter = db['counters'].find_one({'_id': 'examenes_id_examen'})
print(f"📊 Contador actual: {counter.get('seq', 0)}")

# 4. Verificar que todos los id_examen en examenes_det existen
ids_examenes = set()
for e in db['examenes'].find({}, {'id_examen': 1}):
    ids_examenes.add(e['id_examen'])

ids_det = set()
for d in db['examenes_det'].find({}, {'id_examen': 1}):
    ids_det.add(d['id_examen'])

ids_huerfanos = ids_det - ids_examenes

if ids_huerfanos:
    print(f"\n⚠️ {len(ids_huerfanos)} IDs huérfanos encontrados en examenes_det:")
    print(f"  {sorted(list(ids_huerfanos))}")
    
    # Opcional: Eliminar o reasignar
    # db['examenes_det'].delete_many({'id_examen': {'$in': list(ids_huerfanos)}})
    # print(f"  Eliminados {result.deleted_count} registros huérfanos")
else:
    print("\n✅ Todos los id_examen en examenes_det existen en examenes") """

""" # 1. Obtener todos los id_examen válidos de examenes
examenes_validos = set()
for e in db['examenes'].find({}, {'id_examen': 1}):
    examenes_validos.add(e['id_examen'])

print(f"📊 IDs válidos en examenes: {len(examenes_validos)}")

# 2. Verificar cuáles ids en examenes_det no existen en examenes
det_ids = set()
for d in db['examenes_det'].find({}, {'id_examen': 1}):
    det_ids.add(d['id_examen'])

ids_invalidos = det_ids - examenes_validos
print(f"⚠️ IDs en examenes_det que no existen en examenes: {len(ids_invalidos)}")

if ids_invalidos:
    print(f"  IDs inválidos: {sorted(list(ids_invalidos))}")

# 3. Opcional: Eliminar registros huérfanos
if ids_invalidos:
    print("\n🗑️ Eliminando registros huérfanos de examenes_det...")
    result = db['examenes_det'].delete_many({'id_examen': {'$in': list(ids_invalidos)}})
    print(f"  Eliminados {result.deleted_count} registros huérfanos") """

""" # Verificar duplicados en examenes por id_examen
pipeline = [
    {'$group': {
        '_id': '$id_examen',
        'count': {'$sum': 1},
        'ids': {'$push': '$_id'}
    }},
    {'$match': {'count': {'$gt': 1}}}
]

duplicados = list(db['examenes'].aggregate(pipeline))

if duplicados:
    print("⚠️ IDs duplicados en examenes:")
    for d in duplicados:
        print(f"  ID {d['_id']} aparece {d['count']} veces")
        for doc_id in d['ids']:
            doc = db['examenes'].find_one({'_id': doc_id})
            print(f"    - Tipo: {doc.get('tipo')}, Fecha: {doc.get('fecha')}")
else:
    print("✅ No hay IDs duplicados en examenes")

# Verificar duplicados en examenes_det por id_examen
pipeline_det = [
    {'$group': {
        '_id': '$id_examen',
        'count': {'$sum': 1},
        'ids': {'$push': '$_id'}
    }},
    {'$match': {'count': {'$gt': 1}}}
]

duplicados_det = list(db['examenes_det'].aggregate(pipeline_det))

if duplicados_det:
    print("\n⚠️ id_examen duplicados en examenes_det:")
    for d in duplicados_det:
        print(f"  ID {d['_id']} aparece {d['count']} veces")
else:
    print("✅ No hay id_examen duplicados en examenes_det") """

""" # 1. Ver cuál es el ID más alto en examenes (encabezados)
max_examen = db['examenes'].find_one(sort=[('id_examen', -1)])
if max_examen:
    max_examen_id = max_examen['id_examen']
    print(f"📊 ID más alto en examenes: {max_examen_id}")
    
    # 2. Actualizar el contador para que comience después del más alto
    db['counters'].update_one(
        {'_id': 'examenes_id_examen'},
        {'$set': {'seq': max_examen_id}},
        upsert=True
    )
    print(f"✅ Contador 'examenes_id_examen' actualizado a {max_examen_id}")

# 3. Verificar también el contador de detalles
max_det = db['examenes_det'].find_one(sort=[('_id', -1)])
if max_det:
    print(f"📊 Último detalle: {max_det['_id']}")

# 4. Mostrar algunos registros de Spark
print("\n📋 Registros de examenes creados por Spark:")
spark_examenes = list(db['examenes'].find().sort('id_examen', -1).limit(5))
for e in spark_examenes:
    print(f"  ID: {e.get('id_examen')}, Tipo: {e.get('tipo')}, Fecha: {e.get('fecha')}") """