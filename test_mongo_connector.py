# test_mongo_final.py
from pyspark.sql import SparkSession
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")

print("=== TEST MONGODB ===\n")
print(f"📌 Base de datos: {DB_NAME}")

# Buscar JAR
jars_dir = Path("jars")
jar_files = list(jars_dir.glob("mongo-spark-connector*.jar"))
jar_path = str(jar_files[0]) if jar_files else ""

print(f"📦 Usando JAR: {jar_path}")

# Crear SparkSession
spark = SparkSession.builder \
    .appName("MongoTest") \
    .master("local[2]") \
    .config("spark.jars", jar_path) \
    .config("spark.mongodb.read.connection.uri", MONGO_URI) \
    .config("spark.mongodb.write.connection.uri", MONGO_URI) \
    .config("spark.driver.memory", "2g") \
    .getOrCreate()

print(f"✅ Spark {spark.version} iniciada\n")

# Probar lectura de MongoDB
print("📖 Leyendo colección 'cuenta_paciente'...")
try:
    df = spark.read \
        .format("mongodb") \
        .option("database", DB_NAME) \
        .option("collection", "cuenta_paciente") \
        .load()
    
    print(f"✅ Conexión exitosa!")
    count = df.count()
    print(f"📊 Total de registros en cuenta_paciente: {count}")
    
    if count > 0:
        print("\n📋 Esquema de los datos:")
        df.printSchema()
        
        print("\n📄 Primeros 5 registros:")
        df.show(5, truncate=True)
    else:
        print("⚠️ La colección está vacía")
    
except Exception as e:
    print(f"❌ Error al leer MongoDB: {e}")

spark.stop()
print("\n✅ Prueba completada!")