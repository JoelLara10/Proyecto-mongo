# main_clinical_analytics.py
from config.spark_config import get_spark_session
from processing.clinical_analytics import ClinicalAnalytics, RESULTS_DIR
import json
from datetime import datetime

def main():
    print("🏥 SISTEMA DE ANALYTICS CLÍNICO")
    print("=" * 60)
    print(f"📁 Resultados guardados en: {RESULTS_DIR}")
    print("=" * 60)

    # Inicializar Spark
    spark, db_name = get_spark_session()

    print(f"\n✅ Conectado a MongoDB: {db_name}")
    print(f"✅ Spark version: {spark.version}")

    # Ejecutar análisis clínico
    clinical = ClinicalAnalytics(spark, db_name)
    results = clinical.run_complete_analysis()

    # Resumen ejecutivo
    print("\n" + "=" * 60)
    print("📋 RESUMEN EJECUTIVO - ANÁLISIS CLÍNICO")
    print("=" * 60)

    diabetes = results.get('diabetes_prediction', {})
    reingresos = results.get('readmission_prediction', {})
    ocupacion = results.get('occupancy_analysis', {})
    anomalias = results.get('anomaly_detection', {})
    segmentacion = results.get('patient_segmentation', {})
    inteligencia = results.get('clinical_intelligence', {})

    print(f"\n🩺 PREDICCIÓN DE DIABETES:")
    print(f"   - Riesgo ALTO: {diabetes.get('riesgo_alto', 0)} pacientes")
    print(f"   - Riesgo MEDIO: {diabetes.get('riesgo_medio', 0)} pacientes")
    print(f"   - Riesgo BAJO: {diabetes.get('riesgo_bajo', 0)} pacientes")

    print(f"\n🏥 PREDICCIÓN DE REINGRESOS:")
    print(f"   - Riesgo ALTO: {reingresos.get('riesgo_alto', 0)} pacientes")
    print(f"   - Riesgo MEDIO: {reingresos.get('riesgo_medio', 0)} pacientes")
    print(f"   - Promedio atenciones: {reingresos.get('promedio_atenciones', 0):.2f}")

    print(f"\n🛏️ OCUPACIÓN HOSPITALARIA:")
    print(f"   - Ocupación general: {ocupacion.get('porcentaje_ocupacion_general', 0)}%")
    print(f"   - Camas ocupadas: {ocupacion.get('camas_ocupadas', 0)}")
    print(f"   - Camas disponibles: {ocupacion.get('camas_disponibles', 0)}")

    print(f"\n⚠️ ANOMALÍAS DETECTADAS:")
    print(f"   - Exámenes anómalos: {anomalias.get('total_anomalias_examenes', 0)}")
    print(f"   - Signos vitales anómalos: {anomalias.get('total_anomalias_signos', 0)}")

    print(f"\n📊 SEGMENTACIÓN:")
    for seg in segmentacion.get('segmentos', []):
        print(f"   - {seg.get('nombre_segmento')}: {seg.get('total_pacientes')} pacientes (edad: {seg.get('edad_promedio')}, atenciones: {seg.get('atenciones_promedio')})")

    print(f"\n🧠 INTELIGENCIA CLÍNICA:")
    for rec in inteligencia.get('recomendaciones', []):
        print(f"   • {rec}")

    print("\n" + "=" * 60)
    print("✅ ANÁLISIS CLÍNICO COMPLETADO")
    print("=" * 60)

    spark.stop()


if __name__ == "__main__":
    main()