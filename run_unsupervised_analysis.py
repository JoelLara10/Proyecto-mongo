# run_unsupervised_analysis.py
"""
Script para ejecutar análisis no supervisado desde la terminal
Uso: python run_unsupervised_analysis.py
"""

import sys
from pathlib import Path

# Agregar el directorio base al path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from processing.unsupervised_analytics import UnsupervisedAnalytics
from config.spark_config import get_spark_session


def main():
    print("\n" + "="*70)
    print("🔬 EJECUTANDO ANÁLISIS NO SUPERVISADO DESDE TERMINAL")
    print("="*70)
    print("Este análisis incluye:")
    print("  📊 PCA - Análisis de Componentes Principales")
    print("  🔍 K-Means Clustering")
    print("  📈 Método del Codo (Inercia)")
    print("  📊 Índice de Silueta")
    print("="*70)
    
    try:
        # Inicializar Spark
        print("\n🚀 Inicializando Spark...")
        spark, db_name = get_spark_session()
        print(f"✅ Conectado a MongoDB: {db_name}")
        print(f"✅ Spark version: {spark.version}")
        
        # Ejecutar análisis
        print("\n" + "-"*70)
        analytics = UnsupervisedAnalytics(spark, db_name)
        results = analytics.run_complete_analysis()
        
        # Mostrar resumen
        print("\n" + "="*70)
        print("📊 RESUMEN DE RESULTADOS")
        print("="*70)
        
        if results:
            # CORREGIDO: Verificar que pca no sea None antes de usar .get()
            pca = results.get('pca')
            kmeans = results.get('kmeans')
            
            print(f"\n📊 PCA:")
            if pca:
                print(f"   - Componentes: {pca.get('num_components', 0)}")
                explained_var = pca.get('explained_variance', [])
                if explained_var:
                    print(f"   - Varianza explicada: {[round(v*100, 2) for v in explained_var]}%")
                print(f"   - Total pacientes: {pca.get('total_patients', 0)}")
            else:
                print("   ❌ No se generaron resultados de PCA")
            
            print(f"\n🔍 K-MEANS CLUSTERING:")
            if kmeans:
                print(f"   - Clusters seleccionados: {kmeans.get('selected_k', 0)}")
                print(f"   - Inercia: {kmeans.get('selected_model', {}).get('inertia', 0):.4f}")
                print(f"   - Silueta: {kmeans.get('selected_model', {}).get('silhouette_score', 0):.4f}")
                print(f"   - Total pacientes clusterizados: {kmeans.get('total_patients_clustered', 0)}")
                
                print(f"\n🏷️ PERFILES DE CLUSTERS:")
                clusters = kmeans.get('clusters', [])
                if clusters:
                    for cluster in clusters:
                        print(f"   Cluster {cluster.get('cluster', 0)}: {cluster.get('total_pacientes', 0)} pacientes")
                        print(f"      - {cluster.get('perfil', 'Sin perfil')}")
                        print(f"      - Edad: {cluster.get('edad_promedio', 0)} años")
                        print(f"      - Atenciones: {cluster.get('atenciones_promedio', 0)}")
                        print(f"      - Exámenes: {cluster.get('examenes_promedio', 0)}")
                else:
                    print("   ❌ No se generaron clusters")
            else:
                print("   ❌ No se generaron resultados de K-Means")
            
            # Verificar archivos generados
            print(f"\n📁 ARCHIVOS GENERADOS:")
            results_dir = Path(__file__).resolve().parent / "processing" / "results"
            archivos = [
                "unsupervised_00_complete_results.json",
                "unsupervised_01_pca_results.json",
                "unsupervised_02_kmeans_results.json",
                "unsupervised_03_visualizations_metadata.json"
            ]
            
            for archivo in archivos:
                filepath = results_dir / archivo
                if filepath.exists():
                    size = filepath.stat().st_size
                    print(f"   ✅ {archivo} ({size} bytes)")
                else:
                    print(f"   ❌ {archivo} (No encontrado)")
            
            # Verificar visualizaciones
            viz_dir = results_dir / "unsupervised_visualizations"
            if viz_dir.exists():
                imagenes = list(viz_dir.glob("*.png"))
                print(f"\n🖼️ VISUALIZACIONES GENERADAS ({len(imagenes)} imágenes):")
                for img in sorted(imagenes):
                    size = img.stat().st_size
                    print(f"   ✅ {img.name} ({size} bytes)")
            else:
                print(f"\n⚠️ No se encontraron visualizaciones")
            
            print("\n" + "="*70)
            print("✅ ANÁLISIS COMPLETADO EXITOSAMENTE")
            print("="*70)
            print("\n💡 Ahora puedes ver los resultados en:")
            print("   http://localhost:5000/admin/unsupervised-clustering")
            print("="*70)
            
        else:
            print("\n❌ Error: No se obtuvieron resultados")
            return 1
        
        spark.stop()
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())