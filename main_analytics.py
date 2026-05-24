# main_analytics.py
from config.spark_config import get_spark_session
from processing.crisp_dm_analytics import CRISPDMAnalytics, KDDAnalytics, RESULTS_DIR
import json
from datetime import datetime
import os
from pathlib import Path
import builtins

def main():
    print("🏥 SISTEMA DE ANALYTICS HOSPITALARIO")
    print("=" * 60)
    print(f"📁 Los resultados se guardarán en: {RESULTS_DIR}")
    print("=" * 60)
    
    # Inicializar Spark
    spark, db_name = get_spark_session()
    
    print(f"\n✅ Conectado a MongoDB: {db_name}")
    print(f"✅ Spark version: {spark.version}")
    
    # ==================== METODOLOGÍA CRISP-DM ====================
    print("\n" + "=" * 60)
    print("📊 METODOLOGÍA CRISP-DM")
    print("=" * 60)
    
    crisp_dm = CRISPDMAnalytics(spark, db_name)
    crisp_results = crisp_dm.run_complete_analysis()
    
    # ==================== METODOLOGÍA KDD ====================
    print("\n" + "=" * 60)
    print("🔍 METODOLOGÍA KDD")
    print("=" * 60)
    
    kdd = KDDAnalytics(spark, db_name)
    kdd_results = kdd.run_kdd_analysis()
    
    # ==================== RESULTADOS INTEGRADOS ====================
    print("\n" + "=" * 60)
    print("📋 REPORTE INTEGRADO DE ANALYTICS")
    print("=" * 60)
    predictive_models = crisp_results.get('predictive_modeling', {})
    valid_models = {
            k: v for k, v in predictive_models.items()
            if isinstance(v, (int, float))
        }
    
    # Resumen ejecutivo
    executive_summary = {
        'fecha_analisis': datetime.now().isoformat(),
        'directorio_resultados': str(RESULTS_DIR),
        'archivos_generados': [],
        'total_registros_analizados': crisp_results.get('data_understanding', {})
                                      .get('cuenta_paciente', {}).get('total_registros', 0),
        'ingreso_total': crisp_results.get('descriptive_analytics', {})
                          .get('estadisticas_generales', {}).get('ingreso_total', 0),
        
        'mejor_modelo_prediccion': (
            builtins.max(valid_models, key=valid_models.get)
            if valid_models else 'N/A'
        ) if crisp_results.get('predictive_modeling') else 'N/A',
        'segmentos_identificados': crisp_results.get('segmentation_analysis', {})
                                     .get('num_clusters', 0),
        'insights_principales': crisp_results.get('insights_summary', [])[:5],
        'recomendaciones': crisp_results.get('recommendations', [])
    }
    
    # Listar archivos generados
    for file in RESULTS_DIR.iterdir():
        if file.is_file():
            executive_summary['archivos_generados'].append(file.name)
    
    # Guardar resumen ejecutivo
    resumen_path = RESULTS_DIR / "00_resumen_ejecutivo.json"
    with open(resumen_path, "w", encoding="utf-8") as f:
        json.dump(executive_summary, f, indent=4, ensure_ascii=False)
    
    print("\n📈 RESUMEN EJECUTIVO:")
    print(f"   • Directorio: {RESULTS_DIR}")
    print(f"   • Total registros: {executive_summary['total_registros_analizados']}")
    print(f"   • Ingreso total: ${executive_summary['ingreso_total']:,.2f}")
    print(f"   • Mejor modelo: {executive_summary['mejor_modelo_prediccion']}")
    print(f"   • Segmentos identificados: {executive_summary['segmentos_identificados']}")
    
    print("\n💡 INSIGHTS PRINCIPALES:")
    for i, insight in enumerate(executive_summary['insights_principales'], 1):
        print(f"   {i}. {insight}")
    
    print("\n🎯 RECOMENDACIONES:")
    for i, rec in enumerate(executive_summary['recomendaciones'], 1):
        print(f"   {i}. {rec}")
    
    print("\n" + "=" * 60)
    print("✅ ANÁLISIS COMPLETADO")
    print(f"📁 Todos los archivos se encuentran en: {RESULTS_DIR}")
    print("\n📋 ARCHIVOS GENERADOS:")
    print("   CRISP-DM:")
    print("   ├── 01_business_understanding.json")
    print("   ├── 02_data_understanding.json")
    print("   ├── 03_data_preparation_stats.json")
    print("   ├── 04_descriptive_analytics.json")
    print("   ├── 05_diagnostic_analytics.json")
    print("   ├── 06_predictive_models.json")
    print("   ├── 07_segmentation_analysis.json")
    print("   ├── 08_evaluation_results.json")
    print("   ├── 09_visualizations_summary.json")
    print("   └── 10_complete_crisp_dm_results.json")
    print("\n   KDD:")
    print("   ├── kdd_01_data_selection.json")
    print("   ├── kdd_02_preprocessing.json")
    print("   ├── kdd_03_transformation.json")
    print("   ├── kdd_04_data_mining_patterns.json")
    print("   ├── kdd_05_interpretation.json")
    print("   └── kdd_complete_results.json")
    print("\n   VISUALIZACIONES:")
    print("   └── visualizaciones/ (carpeta con imágenes PNG)")
    print("\n   INTEGRADOS:")
    print("   └── 00_resumen_ejecutivo.json")
    print("=" * 60)
    
    spark.stop()

if __name__ == "__main__":
    main()