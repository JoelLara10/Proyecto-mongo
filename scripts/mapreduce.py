import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))
from config.mongo_spark_conexion import get_spark_session
from pyspark.sql.functions import sum, col

# spark → Sesión Spark
# df → DataFrame cargado desde MongoDB (colección atencion)
# _  → algo adicional que no necesitas

spark, df, _ = get_spark_session()

print("=== MAPREDUCE CUENTAS ABIERTAS ===")

df.filter(col("status") == "ABIERTA") \
  .groupBy("id_atencion") \
  .agg(sum("subtotal").alias("total_subtotal")) \
  .orderBy("total_subtotal", ascending=False) \
  .show()

spark.stop()