# data_processor.py
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, sum, avg, count, to_date, when, isnan
from pyspark.sql.types import DoubleType

class DataProcessor:
    def __init__(self, spark):
        self.spark = spark

    def load_collections(self, db_name):
        """Carga todas las colecciones importantes con manejo de errores"""
        collections = {}
        
        # Colecciones que necesitas para el análisis
        required_collections = ["cuenta_paciente", "examenes", "catalogo_examenes"]
        
        for coll in required_collections:
            try:
                collections[coll] = self.spark.read \
                    .format("mongodb") \
                    .option("database", db_name) \
                    .option("collection", coll) \
                    .load()
                print(f" Colección '{coll}' cargada: {collections[coll].count()} registros")
            except Exception as e:
                print(f" Error cargando '{coll}': {e}")
                collections[coll] = None
        
        return collections

    def prepare_financial_data(self, df_cuenta):
        """Prepara datos para análisis financiero y ML"""
        if df_cuenta is None:
            raise ValueError("No se pudo cargar la colección cuenta_paciente")
        
        # Convertir columnas a double y limpiar nulos
        df = df_cuenta.select(
            col("cantidad").cast(DoubleType()),
            col("precio").cast(DoubleType()),
            col("subtotal").cast(DoubleType()),
            col("tipo"),
            col("descripcion"),
            col("fecha"),
            col("id_atencion"),
            col("Id_exp")
        )
        
        # Limpiar datos nulos o inválidos
        df = df.filter(
            (col("cantidad").isNotNull()) & 
            (col("precio").isNotNull()) & 
            (col("subtotal").isNotNull()) &
            (col("cantidad") > 0) &
            (col("precio") > 0) &
            (col("subtotal") > 0)
        )
        
        # Si hay columna fecha, formatearla
        if "fecha" in df.columns:
            df = df.withColumn("fecha", to_date(col("fecha")))
        
        # Agregaciones básicas por tipo
        resumen = df.groupBy("tipo").agg(
            count("*").alias("total_transacciones"),
            sum("subtotal").alias("ingreso_total"),
            avg("subtotal").alias("ticket_promedio")
        )
        
        print(f"Datos financieros preparados: {df.count()} registros válidos")
        return df, resumen