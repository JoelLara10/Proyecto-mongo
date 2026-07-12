# processing/unsupervised_analytics.py
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, count, avg, stddev, min as spark_min, max as spark_max, 
    floor, months_between, current_date, to_date,
    when, expr, lit, sum as spark_sum, desc, asc, coalesce
)
from pyspark.sql.types import DoubleType
from pyspark.ml.feature import VectorAssembler, StandardScaler, PCA
from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import ClusteringEvaluator
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import numpy as np
import pandas as pd
from datetime import datetime
import json
from pathlib import Path
import builtins
import math
import traceback
import sys

# Carpeta de resultados
RESULTS_DIR = Path(__file__).resolve().parent.parent / "processing" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


class UnsupervisedAnalytics:
    """
    Análisis No Supervisado con Spark
    - PCA (Análisis de Componentes Principales)
    - K-Means Clustering con evaluación de inercia
    - Método del Codo (Elbow Method)
    - Índice de Silueta (Silhouette Score)
    """

    def __init__(self, spark, db_name):
        self.spark = spark
        self.db_name = db_name
        self.data = {}
        self.results = {}
        self.results_dir = RESULTS_DIR
        self.pca_results = None
        self.kmeans_results = None
        self.features_df = None

    def _save_json(self, data, filename):
        """Guardar resultados en JSON"""
        try:
            filepath = self.results_dir / filename
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print(f"  💾 Guardado: {filepath}")
            return filepath
        except Exception as e:
            print(f"  ⚠️ Error guardando {filename}: {e}")
            return None

    def _to_python_types(self, value):
        """Convertir a tipos Python puros"""
        if isinstance(value, (list, tuple)):
            return [self._to_python_types(v) for v in value]
        elif isinstance(value, dict):
            return {k: self._to_python_types(v) for k, v in value.items()}
        elif isinstance(value, (int, float, str, bool, type(None))):
            return value
        else:
            try:
                return float(value) if isinstance(value, (int, float)) else str(value)
            except:
                return str(value)

    def _safe_count(self, df):
        """Contar registros de forma segura"""
        try:
            if df is None:
                return 0
            return df.count()
        except Exception:
            return 0

    def load_clinical_data(self):
        """Cargar datos necesarios para el análisis no supervisado"""
        print("\n📊 Cargando datos para análisis no supervisado...")

        collections = ["pacientes", "atencion", "examenes_det", "examenes", "diagnosticos"]

        for coll in collections:
            try:
                self.data[coll] = self.spark.read \
                    .format("mongodb") \
                    .option("database", self.db_name) \
                    .option("collection", coll) \
                    .load()
                count = self._safe_count(self.data[coll])
                print(f"  ✅ {coll}: {count} registros")
            except Exception as e:
                print(f"  ❌ Error cargando {coll}: {e}")
                self.data[coll] = None

        return self.data

    def prepare_features(self):
        """
        Preparar dataset de características para PCA y K-Means
        Variables:
        - Edad del paciente
        - Número de atenciones
        - Número de exámenes realizados
        - Número de diagnósticos
        - Monto total gastado en exámenes
        """
        print("\n🔧 Preparando características...")

        df_pacientes = self.data.get("pacientes")
        df_atencion = self.data.get("atencion")
        df_examenes_det = self.data.get("examenes_det")
        df_examenes = self.data.get("examenes")
        df_diagnosticos = self.data.get("diagnosticos")

        if df_pacientes is None:
            print("  ❌ No hay datos de pacientes")
            return None

        try:
            # 1. Calcular edad
            pacientes = df_pacientes.withColumn(
                "edad", 
                floor(months_between(current_date(), to_date(col("fecnac"))) / 12)
            ).filter(col("edad") > 0)

            print(f"  📊 Pacientes con edad válida: {self._safe_count(pacientes)}")

            # 2. Número de atenciones por paciente
            if df_atencion is not None and self._safe_count(df_atencion) > 0:
                atenciones = df_atencion.groupBy("Id_exp").agg(
                    count("*").alias("num_atenciones")
                )
                pacientes = pacientes.join(atenciones, "Id_exp", "left")
                print(f"  📊 Atenciones agrupadas: {self._safe_count(atenciones)} pacientes")
            else:
                pacientes = pacientes.withColumn("num_atenciones", lit(0))

            # 3. Número de exámenes y monto total por paciente
            if df_examenes_det is not None and df_examenes is not None:
                if self._safe_count(df_examenes_det) > 0 and self._safe_count(df_examenes) > 0:
                    try:
                        # Primero unir examenes_det con examenes para obtener id_atencion
                        examenes_con_atencion = df_examenes_det.join(
                            df_examenes.select("id_examen", "id_atencion"),
                            "id_examen",
                            "left"
                        )
                        
                        # Luego unir con atencion para obtener Id_exp
                        examenes_con_paciente = examenes_con_atencion.join(
                            df_atencion.select("id_atencion", "Id_exp"),
                            "id_atencion",
                            "left"
                        )
                        
                        # Agrupar por paciente
                        examenes_agg = examenes_con_paciente.groupBy("Id_exp").agg(
                            count("*").alias("num_examenes"),
                            spark_sum(coalesce(col("subtotal").cast("double"), lit(0.0))).alias("monto_total")
                        )
                        pacientes = pacientes.join(examenes_agg, "Id_exp", "left")
                        print(f"  📊 Exámenes agrupados: {self._safe_count(examenes_agg)} pacientes")
                    except Exception as e:
                        print(f"  ⚠️ Error procesando exámenes: {e}")
                        pacientes = pacientes.withColumn("num_examenes", lit(0))
                        pacientes = pacientes.withColumn("monto_total", lit(0.0))
                else:
                    pacientes = pacientes.withColumn("num_examenes", lit(0))
                    pacientes = pacientes.withColumn("monto_total", lit(0.0))
            else:
                pacientes = pacientes.withColumn("num_examenes", lit(0))
                pacientes = pacientes.withColumn("monto_total", lit(0.0))

            # 4. Número de diagnósticos por paciente
            if df_diagnosticos is not None and df_atencion is not None:
                if self._safe_count(df_diagnosticos) > 0 and self._safe_count(df_atencion) > 0:
                    try:
                        # Unir diagnosticos con atencion para obtener Id_exp
                        diagnosticos_con_paciente = df_diagnosticos.join(
                            df_atencion.select("id_atencion", "Id_exp"),
                            "id_atencion",
                            "left"
                        )
                        
                        diagnosticos_agg = diagnosticos_con_paciente.groupBy("Id_exp").agg(
                            count("*").alias("num_diagnosticos")
                        )
                        pacientes = pacientes.join(diagnosticos_agg, "Id_exp", "left")
                        print(f"  📊 Diagnósticos agrupados: {self._safe_count(diagnosticos_agg)} pacientes")
                    except Exception as e:
                        print(f"  ⚠️ Error procesando diagnósticos: {e}")
                        pacientes = pacientes.withColumn("num_diagnosticos", lit(0))
                else:
                    pacientes = pacientes.withColumn("num_diagnosticos", lit(0))
            else:
                pacientes = pacientes.withColumn("num_diagnosticos", lit(0))

            # 5. Limpiar y llenar valores nulos
            pacientes = pacientes.fillna({
                "edad": 0,
                "num_atenciones": 0,
                "num_examenes": 0,
                "monto_total": 0.0,
                "num_diagnosticos": 0
            })

            # 6. Seleccionar solo pacientes con datos válidos
            pacientes_validos = pacientes.filter(
                (col("edad") > 0) & (col("edad") < 120)
            )

            # 7. Seleccionar las columnas de features
            self.features_df = pacientes_validos.select(
                "Id_exp",
                col("edad").cast("double"),
                col("num_atenciones").cast("double"),
                col("num_examenes").cast("double"),
                col("monto_total").cast("double"),
                col("num_diagnosticos").cast("double")
            ).na.drop()

            count_features = self._safe_count(self.features_df)
            print(f"  ✅ Dataset preparado: {count_features} pacientes")
            print(f"  📊 Features: Edad, Atenciones, Exámenes, Monto, Diagnósticos")

            if count_features < 3:
                print("  ⚠️ Pocos pacientes para análisis. Se necesitan al menos 3.")
                return None

            return self.features_df

        except Exception as e:
            print(f"  ❌ Error preparando features: {e}")
            traceback.print_exc()
            return None

    def perform_pca(self, k=3):
        """
        Análisis de Componentes Principales (PCA)
        """
        print("\n📊 REALIZANDO PCA (Análisis de Componentes Principales)")

        if self.features_df is None:
            print("  ❌ No hay datos de features")
            return None

        try:
            count_features = self._safe_count(self.features_df)
            if count_features < 3:
                print(f"  ⚠️ Pocos datos para PCA: {count_features} pacientes")
                return None

            # 1. Definir columnas de features
            feature_cols = ["edad", "num_atenciones", "num_examenes", "monto_total", "num_diagnosticos"]
            
            # 2. Vector Assembler
            assembler = VectorAssembler(inputCols=feature_cols, outputCol="features_unscaled")
            df_assembled = assembler.transform(self.features_df)

            # 3. Standard Scaler
            scaler = StandardScaler(
                inputCol="features_unscaled",
                outputCol="features_scaled",
                withStd=True,
                withMean=True
            )
            scaler_model = scaler.fit(df_assembled)
            df_scaled = scaler_model.transform(df_assembled)

            # 4. PCA
            pca = PCA(k=k, inputCol="features_scaled", outputCol="pca_features")
            pca_model = pca.fit(df_scaled)
            
            # 5. Transformar los datos
            df_pca = pca_model.transform(df_scaled)

            # 6. Extraer resultados
            explained_variance = pca_model.explainedVariance.toArray().tolist()
            
            # 7. Calcular varianza acumulada
            cumulative_variance = []
            cum_sum = 0
            for var in explained_variance:
                cum_sum += var
                cumulative_variance.append(cum_sum)

            # 8. Crear resultados - CORREGIDO: usar builtins.sum en lugar de sum de Spark
            self.pca_results = {
                "num_features": len(feature_cols),
                "num_components": k,
                "feature_names": feature_cols,
                "explained_variance": [self._to_python_types(v) for v in explained_variance],
                "cumulative_variance": [self._to_python_types(v) for v in cumulative_variance],
                "total_explained_variance": self._to_python_types(builtins.sum(explained_variance)),
                "method": "PCA con StandardScaler",
                "total_patients": count_features
            }

            # 9. Guardar resultados
            self._save_json(self.pca_results, "unsupervised_01_pca_results.json")

            print(f"  ✅ PCA completado: {k} componentes")
            print(f"  📊 Varianza explicada: {[round(v*100, 2) for v in explained_variance]}%")

            return self.pca_results

        except Exception as e:
            print(f"  ❌ Error en PCA: {e}")
            traceback.print_exc()
            return None

    def perform_kmeans_elbow(self, max_k=10):
        """
        Realizar K-Means clustering con evaluación de:
        - Inercia (Within Set Sum of Squared Errors)
        - Método del Codo (Elbow Method)
        - Índice de Silueta (Silhouette Score)
        """
        print("\n🔍 REALIZANDO K-MEANS CLUSTERING")

        if self.features_df is None:
            print("  ❌ No hay datos de features")
            return None

        count_features = self._safe_count(self.features_df)
        if count_features < 3:
            print(f"  ⚠️ Pocos datos para K-Means: {count_features} pacientes")
            return None

        # CORREGIDO: usar builtins.min en lugar de min de Spark
        max_k = builtins.min(max_k, count_features - 1)
        if max_k < 3:
            max_k = 3
        
        print(f"  Evaluando k de 2 a {max_k}...")

        try:
            # 1. Preparar datos escalados
            feature_cols = ["edad", "num_atenciones", "num_examenes", "monto_total", "num_diagnosticos"]
            
            assembler = VectorAssembler(inputCols=feature_cols, outputCol="features_unscaled")
            df_assembled = assembler.transform(self.features_df)

            scaler = StandardScaler(
                inputCol="features_unscaled",
                outputCol="features_scaled",
                withStd=True,
                withMean=True
            )
            scaler_model = scaler.fit(df_assembled)
            df_scaled = scaler_model.transform(df_assembled)

            # 2. Evaluar diferentes k
            elbow_data = []
            silhouette_scores = []
            k_models = []

            for k in range(2, max_k + 1):
                print(f"  🔄 Probando k={k}...")
                
                # K-Means
                kmeans = KMeans(
                    featuresCol="features_scaled",
                    k=k,
                    seed=42,
                    maxIter=20
                )
                model = kmeans.fit(df_scaled)
                
                # Transformar datos
                predictions = model.transform(df_scaled)
                
                # Calcular WSSSE (Inercia)
                wssse = model.summary.trainingCost
                wssse = float(wssse) if not math.isnan(wssse) else 0.0
                
                # Calcular Índice de Silueta
                evaluator = ClusteringEvaluator(
                    featuresCol="features_scaled",
                    predictionCol="prediction",
                    metricName="silhouette"
                )
                silhouette = evaluator.evaluate(predictions)
                silhouette = float(silhouette) if not math.isnan(silhouette) else 0.0
                
                elbow_data.append({
                    "k": k,
                    "inertia": builtins.round(wssse, 4)
                })
                
                silhouette_scores.append({
                    "k": k,
                    "silhouette_score": builtins.round(silhouette, 4)
                })
                
                k_models.append({
                    "k": k,
                    "model": model,
                    "predictions": predictions,
                    "wssse": wssse,
                    "silhouette": silhouette
                })
                
                print(f"    - Inercia: {wssse:.4f}")
                print(f"    - Silueta: {silhouette:.4f}")

            # 3. Encontrar el mejor k según silueta
            best_silhouette = max(silhouette_scores, key=lambda x: x['silhouette_score'])
            best_silhouette_k = best_silhouette['k']
            best_silhouette_score = best_silhouette['silhouette_score']

            # 4. Encontrar el codo (máxima curvatura)
            inertia_values = [d['inertia'] for d in elbow_data]
            k_values = [d['k'] for d in elbow_data]
            elbow_k = self._find_elbow_point(k_values, inertia_values)
            
            # 5. Obtener modelo del mejor k según codo
            best_model_data = None
            for model_data in k_models:
                if model_data['k'] == elbow_k:
                    best_model_data = model_data
                    break

            if best_model_data is None:
                best_model_data = max(k_models, key=lambda x: x['silhouette'])
                elbow_k = best_model_data['k']

            # 6. Resultados finales del mejor modelo
            best_predictions = best_model_data['predictions']
            best_wssse = best_model_data['wssse']
            best_silhouette = best_model_data['silhouette']

            # 7. Estadísticas de clusters
            cluster_stats = best_predictions.groupBy("prediction").agg(
                count("*").alias("count"),
                avg("edad").alias("avg_edad"),
                avg("num_atenciones").alias("avg_atenciones"),
                avg("num_examenes").alias("avg_examenes"),
                avg("monto_total").alias("avg_monto"),
                avg("num_diagnosticos").alias("avg_diagnosticos")
            ).orderBy("prediction").collect()

            clusters = []
            for row in cluster_stats:
                clusters.append({
                    "cluster": int(row["prediction"]),
                    "total_pacientes": int(row["count"]),
                    "edad_promedio": builtins.round(float(row["avg_edad"]), 2) if row["avg_edad"] else 0,
                    "atenciones_promedio": builtins.round(float(row["avg_atenciones"]), 2) if row["avg_atenciones"] else 0,
                    "examenes_promedio": builtins.round(float(row["avg_examenes"]), 2) if row["avg_examenes"] else 0,
                    "monto_promedio": builtins.round(float(row["avg_monto"]), 2) if row["avg_monto"] else 0,
                    "diagnosticos_promedio": builtins.round(float(row["avg_diagnosticos"]), 2) if row["avg_diagnosticos"] else 0
                })

            # 8. Perfiles de clusters
            for cluster in clusters:
                cluster["perfil"] = self._get_cluster_profile(cluster)

            # 9. Guardar resultados
            self.kmeans_results = {
                "method": "K-Means Clustering",
                "num_clusters_evaluated": max_k - 1,
                "features_used": feature_cols,
                "elbow_data": elbow_data,
                "silhouette_scores": silhouette_scores,
                "best_k_by_silhouette": {
                    "k": best_silhouette_k,
                    "score": best_silhouette_score
                },
                "best_k_by_elbow": elbow_k,
                "selected_k": elbow_k,
                "selected_model": {
                    "k": elbow_k,
                    "inertia": builtins.round(best_wssse, 4),
                    "silhouette_score": builtins.round(best_silhouette, 4)
                },
                "clusters": clusters,
                "total_patients_clustered": count_features
            }

            self._save_json(self.kmeans_results, "unsupervised_02_kmeans_results.json")

            # 10. Generar visualizaciones
            self._generate_elbow_plot(elbow_data, silhouette_scores, elbow_k, best_silhouette_k)

            print(f"\n  ✅ K-Means completado")
            print(f"  📊 Mejor k según codo: {elbow_k}")
            print(f"  📊 Mejor k según silueta: {best_silhouette_k} (score: {best_silhouette_score:.4f})")
            print(f"  📊 Inercia final: {best_wssse:.4f}")
            
            for cluster in clusters:
                print(f"  🏷️ Cluster {cluster['cluster']}: {cluster['total_pacientes']} pacientes - {cluster['perfil']}")

            return self.kmeans_results

        except Exception as e:
            print(f"  ❌ Error en K-Means: {e}")
            traceback.print_exc()
            return None

    def _find_elbow_point(self, k_values, inertia_values):
        """Encontrar el punto de codo usando el método de la distancia máxima"""
        if len(k_values) < 3:
            return k_values[-1] if k_values else 2

        try:
            # Normalizar valores
            k_norm = np.array(k_values, dtype=float)
            inertia_norm = np.array(inertia_values, dtype=float)
            
            k_min, k_max = k_norm.min(), k_norm.max()
            i_min, i_max = inertia_norm.min(), inertia_norm.max()
            
            if k_max == k_min or i_max == i_min:
                return k_values[-1]
            
            k_scaled = (k_norm - k_min) / (k_max - k_min)
            i_scaled = (inertia_norm - i_min) / (i_max - i_min)
            
            # Línea de (k_scaled[0], i_scaled[0]) a (k_scaled[-1], i_scaled[-1])
            x1, y1 = k_scaled[0], i_scaled[0]
            x2, y2 = k_scaled[-1], i_scaled[-1]
            
            max_dist = -1
            elbow_idx = 0
            
            for i in range(len(k_scaled)):
                if (x2 - x1) == 0:
                    dist = abs(k_scaled[i] - x1)
                else:
                    numerator = abs((x2 - x1) * (y1 - i_scaled[i]) - (x1 - k_scaled[i]) * (y2 - y1))
                    denominator = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                    dist = numerator / denominator if denominator > 0 else 0
                
                if dist > max_dist:
                    max_dist = dist
                    elbow_idx = i
            
            return int(k_values[elbow_idx])
        except Exception:
            return k_values[-1] if k_values else 2

    def _get_cluster_profile(self, cluster):
        """Determinar perfil del cluster basado en características promedio"""
        edad = cluster.get("edad_promedio", 0)
        atenciones = cluster.get("atenciones_promedio", 0)
        examenes = cluster.get("examenes_promedio", 0)
        diagnosticos = cluster.get("diagnosticos_promedio", 0)
        monto = cluster.get("monto_promedio", 0)

        perfil = []

        if edad >= 65:
            perfil.append("Adulto Mayor")
        elif edad >= 40:
            perfil.append("Adulto")
        else:
            perfil.append("Joven")

        if atenciones >= 5:
            perfil.append("Alta Frecuencia")
        elif atenciones >= 2:
            perfil.append("Frecuencia Media")
        else:
            perfil.append("Baja Frecuencia")

        if diagnosticos >= 3 and examenes >= 5:
            perfil.append("Alta Complejidad")
        elif diagnosticos >= 1 and examenes >= 2:
            perfil.append("Complejidad Media")
        else:
            perfil.append("Complejidad Baja")

        if monto >= 500000:
            perfil.append("Alto Gasto")
        elif monto >= 100000:
            perfil.append("Gasto Medio")
        else:
            perfil.append("Bajo Gasto")

        return " | ".join(perfil)

    def _generate_elbow_plot(self, elbow_data, silhouette_scores, elbow_k, silhouette_k):
        """Generar visualizaciones del método del codo y silueta"""
        print("\n📊 Generando visualizaciones...")
        viz_dir = self.results_dir / "unsupervised_visualizations"
        viz_dir.mkdir(exist_ok=True)

        try:
            # Gráfico 1: Método del Codo + Silueta
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

            k_values = [d['k'] for d in elbow_data]
            inertia_values = [d['inertia'] for d in elbow_data]

            ax1.plot(k_values, inertia_values, 'bo-', linewidth=2, markersize=10)
            ax1.axvline(x=elbow_k, color='red', linestyle='--', linewidth=2, label=f'Codo (k={elbow_k})')
            ax1.set_xlabel('Número de Clusters (k)', fontsize=12)
            ax1.set_ylabel('Inercia (WSSSE)', fontsize=12)
            ax1.set_title('Método del Codo', fontsize=14, fontweight='bold')
            ax1.grid(True, alpha=0.3)
            ax1.legend()

            silhouette_values = [d['silhouette_score'] for d in silhouette_scores]
            k_sil_values = [d['k'] for d in silhouette_scores]

            ax2.plot(k_sil_values, silhouette_values, 'go-', linewidth=2, markersize=10)
            ax2.axvline(x=silhouette_k, color='orange', linestyle='--', linewidth=2,
                       label=f'Mejor Silueta (k={silhouette_k})')
            ax2.set_xlabel('Número de Clusters (k)', fontsize=12)
            ax2.set_ylabel('Índice de Silueta', fontsize=12)
            ax2.set_title('Índice de Silueta', fontsize=14, fontweight='bold')
            ax2.grid(True, alpha=0.3)
            ax2.legend()

            plt.tight_layout()
            filepath = viz_dir / "01_elbow_silhouette_analysis.png"
            plt.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close()
            print(f"  ✅ Gráfico Codo + Silueta: {filepath.name}")

            # Gráfico 2: Varianza PCA
            if self.pca_results:
                fig, ax = plt.subplots(figsize=(10, 6))
                
                explained_var = self.pca_results.get('explained_variance', [])
                cumulative_var = self.pca_results.get('cumulative_variance', [])
                
                if len(explained_var) > 0:
                    x_pos = np.arange(len(explained_var))
                    bars = ax.bar(x_pos, explained_var, alpha=0.7, label='Varianza Explicada')
                    ax.plot(x_pos, cumulative_var, 'ro-', linewidth=2, label='Varianza Acumulada')
                    
                    for i, (bar, var) in enumerate(zip(bars, explained_var)):
                        height = bar.get_height()
                        ax.text(bar.get_x() + bar.get_width()/2., height,
                               f'{var*100:.1f}%', ha='center', va='bottom', fontsize=10)
                    
                    ax.set_xlabel('Componentes Principales', fontsize=12)
                    ax.set_ylabel('Proporción de Varianza', fontsize=12)
                    ax.set_title('Varianza Explicada por PCA', fontsize=14, fontweight='bold')
                    ax.set_xticks(x_pos)
                    ax.set_xticklabels([f'PC{i+1}' for i in range(len(explained_var))])
                    ax.set_ylim(0, 1.1)
                    ax.grid(True, alpha=0.3)
                    ax.legend()
                    
                    plt.tight_layout()
                    filepath = viz_dir / "02_pca_explained_variance.png"
                    plt.savefig(filepath, dpi=150, bbox_inches='tight')
                    plt.close()
                    print(f"  ✅ Gráfico Varianza PCA: {filepath.name}")

            # Gráfico 3: Perfiles de clusters
            if self.kmeans_results:
                clusters = self.kmeans_results.get('clusters', [])
                if clusters:
                    fig, ax = plt.subplots(figsize=(10, 6))
                    
                    cluster_ids = [c['cluster'] for c in clusters]
                    cluster_sizes = [c['total_pacientes'] for c in clusters]
                    
                    bars = ax.bar(cluster_ids, cluster_sizes, color='skyblue', edgecolor='black')
                    ax.set_xlabel('Cluster', fontsize=12)
                    ax.set_ylabel('Número de Pacientes', fontsize=12)
                    ax.set_title('Distribución de Pacientes por Cluster', fontsize=14, fontweight='bold')
                    
                    for bar, size in zip(bars, cluster_sizes):
                        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 0.5,
                               f'{size}', ha='center', va='bottom', fontweight='bold')
                    
                    plt.tight_layout()
                    filepath = viz_dir / "03_cluster_distribution.png"
                    plt.savefig(filepath, dpi=150, bbox_inches='tight')
                    plt.close()
                    print(f"  ✅ Gráfico Distribución de Clusters: {filepath.name}")

        except Exception as e:
            print(f"  ⚠️ Error generando visualizaciones: {e}")
            traceback.print_exc()

    def run_complete_analysis(self):
        """
        Ejecutar análisis completo no supervisado
        """
        print("\n" + "="*60)
        print("🔬 ANÁLISIS NO SUPERVISADO - CLÍNICO")
        print("="*60)
        print("Contenido:")
        print("  📊 PCA - Análisis de Componentes Principales")
        print("  🔍 K-Means Clustering")
        print("  📈 Método del Codo (Inercia)")
        print("  📊 Índice de Silueta")
        print("="*60)

        try:
            # 1. Cargar datos
            self.load_clinical_data()

            # 2. Preparar características
            if self.prepare_features() is None:
                print("❌ No se pudieron preparar los datos")
                return self._create_error_result("No se pudieron preparar los datos")

            # 3. PCA
            pca_results = self.perform_pca(k=3)

            # 4. K-Means con codo y silueta
            kmeans_results = self.perform_kmeans_elbow(max_k=10)

            # 5. Resultado completo
            complete_results = {
                "timestamp": datetime.now().isoformat(),
                "analisis_tipo": "no_supervisado",
                "pca": pca_results,
                "kmeans": kmeans_results,
                "total_pacientes": self._safe_count(self.features_df)
            }

            self.results = complete_results
            self._save_json(complete_results, "unsupervised_00_complete_results.json")

            print("\n" + "="*60)
            print("✅ ANÁLISIS NO SUPERVISADO COMPLETADO")
            print("="*60)
            
            return complete_results

        except Exception as e:
            print(f"❌ Error en análisis: {e}")
            traceback.print_exc()
            return self._create_error_result(str(e))

    def _create_error_result(self, error_msg):
        """Crear resultado de error"""
        error_result = {
            "timestamp": datetime.now().isoformat(),
            "analisis_tipo": "no_supervisado",
            "error": error_msg,
            "pca": None,
            "kmeans": None,
            "total_pacientes": 0
        }
        self._save_json(error_result, "unsupervised_00_complete_results.json")
        return error_result


# ==================== PUNTO DE ENTRADA ====================
def main():
    try:
        import sys
        sys.path.append(str(Path(__file__).resolve().parent.parent))
        
        try:
            from config.spark_config import get_spark_session
        except ImportError:
            print("❌ No se encontró config.spark_config")
            print("⚠️ Usando SparkSession por defecto...")
            spark = SparkSession.builder \
                .appName("UnsupervisedClinicalAnalytics") \
                .config("spark.mongodb.input.uri", "mongodb://localhost:27017/hospital") \
                .config("spark.jars.packages", "org.mongodb.spark:mongo-spark-connector_2.12:3.0.1") \
                .config("spark.sql.adaptive.enabled", "false") \
                .getOrCreate()
            db_name = "hospital"
        else:
            spark, db_name = get_spark_session()

        print(f"✅ Conectado a MongoDB: {db_name}")
        print(f"✅ Spark version: {spark.version}")

        # Ejecutar análisis
        analytics = UnsupervisedAnalytics(spark, db_name)
        results = analytics.run_complete_analysis()

        spark.stop()
        
    except Exception as e:
        print(f"❌ Error en main: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()