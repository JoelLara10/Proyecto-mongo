from pathlib import Path
import sys

# ==========================================
# Agregar la raíz del proyecto al path
# ==========================================
ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

# Importar función de conexión a Mongo + Spark
from configuracion.mongo_spark_conexion import get_spark_session

# Importar funciones de Spark
from pyspark.sql import functions as F


# ==========================================
# INICIAR SPARK Y CARGAR COLECCIONES
# ==========================================

spark, dfs, _ = get_spark_session()

# DataFrames provenientes de MongoDB
pacientes = dfs["pacientes"]
atencion = dfs["atencion"]
cuenta = dfs["cuenta_paciente"]

print("\n=========== REPORTE DE ATENCIONES ABIERTAS ===========\n")


# ==========================================
# 1 FILTRAR SOLO ATENCIONES ABIERTAS
# ==========================================

a = atencion.filter(
    F.col("status") == "ABIERTA"
).alias("a")


# ==========================================
# 2 JOIN CON PACIENTES
# (equivalente a $lookup en Mongo)
# ==========================================

ap = a.join(
    pacientes.alias("p"),
    F.col("a.Id_exp") == F.col("p.Id_exp"),
    "inner"
)


# ==========================================
# 3 JOIN CON CUENTA_PACIENTE
# ==========================================

joined = ap.join(
    cuenta.alias("cp"),
    F.col("a.id_atencion") == F.col("cp.id_atencion"),
    "left"
)


# ==========================================
# 4 SELECCIONAR Y FORMATEAR DATOS
# (evita errores de ambigüedad)
# ==========================================

datos = joined.select(
    F.col("a.id_atencion").alias("id_atencion"),
    F.col("a.Id_exp").alias("expediente"),
    F.col("a.area"),
    F.col("a.especialidad"),
    F.col("a.fecha_ing"),
    F.col("a.id_cama").alias("cama"),

    # Crear nombre completo del paciente
    F.concat_ws(
        " ",
        F.col("p.papell"),
        F.col("p.sapell"),
        F.col("p.nom_pac")
    ).alias("paciente"),

    F.col("cp.subtotal")
)


# ==========================================
# 5 MAPREDUCE (AGRUPACIÓN + SUMA)
# ==========================================

reporte = (
    datos.groupBy(
        "id_atencion",
        "expediente",
        "area",
        "especialidad",
        "fecha_ing",
        "cama",
        "paciente"
    )
    .agg(
        F.coalesce(
            F.sum("subtotal"),
            F.lit(0)
        ).alias("total_cuenta")
    )
    .orderBy(
        F.desc("total_cuenta"),
        F.desc("fecha_ing")
    )
)


# ==========================================
# 6 MOSTRAR REPORTE
# ==========================================

reporte.show(truncate=False)


# ==========================================
# 7 CERRAR SESIÓN DE SPARK
# ==========================================

spark.stop()