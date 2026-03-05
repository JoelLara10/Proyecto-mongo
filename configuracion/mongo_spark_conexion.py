from pyspark.sql import SparkSession
from pathlib import Path
from dotenv import load_dotenv
import os

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _read_coll(spark: SparkSession, db_name: str, coll: str):
    return (
        spark.read
        .format("mongodb")
        .option("database", db_name)
        .option("collection", coll)
        .load()
    )


def get_spark_session():
    mongo_uri = os.getenv("MONGO_URI")
    db_name = os.getenv("DB_NAME")

    if not mongo_uri or not db_name:
        raise ValueError("Faltan variables en .env: MONGO_URI o DB_NAME")

    spark = (
        SparkSession.builder
        .appName("MongoSparkApp")
        .config("spark.mongodb.read.connection.uri", mongo_uri)
        .config("spark.mongodb.write.connection.uri", mongo_uri)
        # ✅ Spark 4 -> Scala 2.13
        .config("spark.jars.packages", "org.mongodb.spark:mongo-spark-connector_2.13:11.0.0")
        .getOrCreate()
    )

    dfs = {
        "pacientes": _read_coll(spark, db_name, "pacientes"),
        "atencion": _read_coll(spark, db_name, "atencion"),
        "cuenta_paciente": _read_coll(spark, db_name, "cuenta_paciente"),
    }

    return spark, dfs, mongo_uri