# spark_config.py - VERSIÓN FUNCIONAL
from pyspark.sql import SparkSession
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

def get_spark_session():
    mongo_uri = os.getenv("MONGO_URI")
    db_name = os.getenv("DB_NAME")

    if not mongo_uri or not db_name:
        raise ValueError("MONGO_URI o DB_NAME no encontrados en .env")

    # Buscar el JAR
    jars_dir = ROOT / "jars"
    jar_files = list(jars_dir.glob("mongo-spark-connector*.jar"))
    
    if not jar_files:
        raise FileNotFoundError(f"No se encontró el conector MongoDB en {jars_dir}")
    
    jar_path = str(jar_files[0])
    print(f"📦 Usando conector: {jar_path}")

    # Configuración que FUNCIONA
    spark = SparkSession.builder \
        .appName("HospitalAnalytics") \
        .master("local[*]") \
        .config("spark.jars", jar_path) \
        .config("spark.mongodb.read.connection.uri", mongo_uri) \
        .config("spark.mongodb.write.connection.uri", mongo_uri) \
        .config("spark.driver.memory", "4g") \
        .config("spark.executor.memory", "4g") \
        .getOrCreate()
    
    return spark, db_name