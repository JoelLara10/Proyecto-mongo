from pymongo import MongoClient
import os
from dotenv import load_dotenv
from pathlib import Path

# Cargar .env desde la raíz del proyecto
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

# Variables de entorno
mongo_uri = os.getenv("MONGO_URI")
database_name = os.getenv("DB_NAME")

# Conexión
client = MongoClient(mongo_uri)
db = client[database_name]

# ⚠️ Cambia "ventas" por el nombre real de tu colección
coleccion = db["ventas"]

# Pipeline de agregación
pipeline = [
    {
        "$group": {
            "_id": "$producto",
            "total_cantidad": {"$sum": "$cantidad"},
            "promedio_precio": {"$avg": "$precio"},
            "ventas_registradas": {"$sum": 1},
            # total = sumatoria (precio por cantidad)
            "total_ingresos": {
                "$sum": {
                    "$multiply": ["$precio", "$cantidad"]
                }
            }
        }
    },
    {
        "$sort": {"total_cantidad": -1}
    }
]

resultados = list(coleccion.aggregate(pipeline))

# Mostrar resultados
for r in resultados:
    print(f"Producto: {r['_id']}")
    print(f"  Total vendido: {r['total_cantidad']}")
    print(f"  Promedio precio: {r['promedio_precio']:.2f}")
    print(f"  Ventas registradas: {r['ventas_registradas']}")
    print(f"  Total de ingresos: {r['total_ingresos']}")
    print("-" * 40)