import json
from config.mongo_spark_conexion_sinnulos import get_spark_session
from ml_algorithms.regresion_analytics_modelos_dash import ejecutar_modelos

print("🚀 Iniciando Spark...")

spark, _, df = get_spark_session()

print("📊 Datos cargados")

# Ejecutar modelos
resultados, _ = ejecutar_modelos(df)

print("🤖 Modelos ejecutados")

# Convertir a formato JSON seguro
resultados_limpios = {k: float(v) for k, v in resultados.items()}

# Guardar resultados
with open("resultados.json", "w") as f:
    json.dump(resultados_limpios, f, indent=4)

print("✅ Resultados guardados en resultados.json")

spark.stop()
print("🛑 Spark finalizado")