from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from configuracion.mongo_spark_conexion import get_spark_session

# Funciones de Spark (NO son funciones normales de Python)
from pyspark.sql import functions as F


spark, dfs, _ = get_spark_session()

# DataFrames (colecciones)
pacientes = dfs["pacientes"]
atencion = dfs["atencion"]
cuenta = dfs["cuenta_paciente"]


print("=== MAPREDUCE (INEO) ===")

# 1) Filtrar atenciones ABIERTAS (equivalente a $match)
a = atencion.filter(F.col("status") == F.lit("ABIERTA")).alias("a")

# 2) Join con pacientes por Id_exp (equivalente a $lookup + $unwind)
ap = (
    a.join(
        pacientes.alias("p"),
        on=F.col("a.Id_exp") == F.col("p.Id_exp"),
        how="inner"
    )
)

# 3) Join con cuenta_paciente por id_atencion (equivalente a $lookup items)
joined = (
    ap.join(
        cuenta.alias("cp"),
        on=F.col("a.id_atencion") == F.col("cp.id_atencion"),
        how="left"
    )
)

# 4) MapReduce real:
# - groupBy(id_atencion, ...) => SHUFFLE por llave
# - sum(cp.subtotal) => REDUCE (agregación)
reporte = (
    joined.groupBy(
        F.col("a.id_atencion").alias("id_atencion"),
        F.col("a.Id_exp").alias("Id_exp"),
        F.col("a.area").alias("area"),
        F.col("a.especialidad").alias("especialidad"),
        F.col("a.fecha_ing").alias("fecha_ing"),
        F.col("a.id_cama").alias("cama"),
        F.concat_ws(" ", F.col("p.papell"), F.col("p.sapell"), F.col("p.nom_pac")).alias("paciente"),
    )
    .agg(
        F.coalesce(F.sum(F.col("cp.subtotal")), F.lit(0)).alias("subtotal")
    )
    .orderBy(F.col("subtotal").desc(), F.col("fecha_ing").desc())
)

# Imprime el resultado en consola (como tu ejemplo)
reporte.show(truncate=False)

spark.stop()