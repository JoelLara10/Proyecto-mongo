# crisp_dm_analytics.py
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.window import Window
from pyspark.ml.feature import VectorAssembler, StandardScaler, StringIndexer
from pyspark.ml.regression import LinearRegression, RandomForestRegressor, GBTRegressor
from pyspark.ml.clustering import KMeans
from pyspark.ml.classification import LogisticRegression
from pyspark.ml.evaluation import RegressionEvaluator, ClusteringEvaluator, MulticlassClassificationEvaluator
from pyspark.ml import Pipeline
import matplotlib.pyplot as plt
import builtins
import math
import matplotlib
matplotlib.use('Agg')
import io
import base64
import pandas as pd
from datetime import datetime
import json
import os
from pathlib import Path

# Crear carpeta results si no existe
RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

class CRISPDMAnalytics:
    """
    Implementación de metodología CRISP-DM para análisis hospitalario
    Fases: 1. Business Understanding, 2. Data Understanding, 
            3. Data Preparation, 4. Modeling, 5. Evaluation, 6. Deployment
    """
    
    def __init__(self, spark, db_name):
        self.spark = spark
        self.db_name = db_name
        self.data = {}
        self.results = {}
        self.results_dir = RESULTS_DIR
        
    def _save_json(self, data, filename):
        """Guarda un archivo JSON en la carpeta results"""
        filepath = self.results_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"  💾 Guardado: {filepath}")
        return filepath
    
    # ==================== FASE 1: BUSINESS UNDERSTANDING ====================
    def business_understanding(self):
        """
        Definición de objetivos de negocio:
        - Análisis de ingresos hospitalarios
        - Segmentación de pacientes
        - Predicción de ingresos por servicio
        - Identificación de patrones de comportamiento
        """
        self.results['business_objectives'] = {
            'objective_1': 'Analizar ingresos por tipo de servicio y especialidad',
            'objective_2': 'Segmentar pacientes por comportamiento de consumo',
            'objective_3': 'Predecir ingresos basado en cantidad y precio',
            'objective_4': 'Identificar servicios más rentables',
            'objective_5': 'Optimizar asignación de recursos hospitalarios'
        }
        
        # Guardar business understanding
        self._save_json(self.results['business_objectives'], "01_business_understanding.json")
        
        return self.results['business_objectives']
    
    # ==================== FASE 2: DATA UNDERSTANDING ====================
    def load_data(self):
        """Carga todas las colecciones necesarias de MongoDB"""
        print("\n📊 FASE 2: DATA UNDERSTANDING - Cargando datos...")
        
        collections_to_load = [
            "cuenta_paciente", "pacientes", "atencion", 
            "catalogo_examenes", "examenes", "camas"
        ]
        
        for coll in collections_to_load:
            try:
                self.data[coll] = self.spark.read \
                    .format("mongodb") \
                    .option("database", self.db_name) \
                    .option("collection", coll) \
                    .load()
                print(f"  ✅ {coll}: {self.data[coll].count()} registros")
            except Exception as e:
                print(f"  ❌ Error cargando {coll}: {e}")
                self.data[coll] = None
        
        return self.data
    
    def data_understanding(self):
        """Análisis exploratorio de datos"""
        print("\n📈 DATA UNDERSTANDING - Análisis exploratorio...")
        
        stats = {}
        
        # Análisis de cuenta_paciente
        if self.data.get("cuenta_paciente"):
            df_cuenta = self.data["cuenta_paciente"]
            stats['cuenta_paciente'] = {
                'total_registros': df_cuenta.count(),
                'tipos_servicio': [row['tipo'] for row in df_cuenta.select("tipo").distinct().collect() if row['tipo']],
                'rango_precios': {
                    'min': df_cuenta.agg(min("precio")).collect()[0][0],
                    'max': df_cuenta.agg(max("precio")).collect()[0][0]
                },
                'ingreso_total': float(df_cuenta.agg(sum("subtotal")).collect()[0][0] or 0)
            }
            print(f"  📊 Total ingresos: ${stats['cuenta_paciente']['ingreso_total']:,.2f}")
        
        # Análisis de pacientes
        if self.data.get("pacientes"):
            df_pacientes = self.data["pacientes"]
            stats['pacientes'] = {
                'total_pacientes': df_pacientes.count(),
                'total_expedientes': df_pacientes.select("Id_exp").distinct().count()
            }
            print(f"  👥 Total pacientes: {stats['pacientes']['total_pacientes']}")
        
        # Análisis de atenciones
        if self.data.get("atencion"):
            df_atencion = self.data["atencion"]
            stats['atenciones'] = {
                'total_atenciones': df_atencion.count(),
                'areas': [row['area'] for row in df_atencion.select("area").distinct().collect()],
                'especialidades': df_atencion.select("especialidad").distinct().count()
            }
            print(f"  🏥 Total atenciones: {stats['atenciones']['total_atenciones']}")
        
        self.results['data_understanding'] = stats
        
        # Guardar data understanding
        self._save_json(stats, "02_data_understanding.json")
        
        return stats
    
    # ==================== FASE 3: DATA PREPARATION ====================
    def prepare_financial_data(self):
        """Preparación de datos financieros para análisis"""
        print("\n🛠️ FASE 3: DATA PREPARATION - Preparando datos...")
        
        df_cuenta = self.data.get("cuenta_paciente")
        if df_cuenta is None:
            raise ValueError("No se encontraron datos de cuenta_paciente")
        
        # Limpieza y transformación
        df_clean = df_cuenta.select(
            col("cantidad").cast("double"),
            col("precio").cast("double"),
            col("subtotal").cast("double"),
            col("tipo"),
            col("estado"),
            to_date(col("fecha")).alias("fecha"),
            col("id_atencion").cast("int"),
            col("Id_exp").cast("int")
        ).na.drop(subset=["cantidad", "precio", "subtotal"])
        
        # Filtrar valores válidos
        df_clean = df_clean.filter(
            (col("cantidad") > 0) & 
            (col("precio") > 0) & 
            (col("subtotal") > 0)
        )
        
        # Agregar columnas derivadas
        df_clean = df_clean.withColumn("mes", month("fecha"))
        df_clean = df_clean.withColumn("anio", year("fecha"))
        df_clean = df_clean.withColumn("margen", col("subtotal") / col("precio"))
        
        self.data['financial_clean'] = df_clean
        print(f"  ✅ Datos preparados: {df_clean.count()} registros válidos")
        tasa = (df_clean.count() / df_cuenta.count() * 100) if df_cuenta.count() > 0 else 0
        # Guardar estadísticas de preparación
        prep_stats = {
            'registros_iniciales': df_cuenta.count(),
            'registros_validos': df_clean.count(),
            'tasa_limpieza': builtins.round(tasa, 2)
        }
        self._save_json(prep_stats, "03_data_preparation_stats.json")
        
        return df_clean
    
    def prepare_patient_data(self):
        """Enriquecimiento de datos con información de pacientes"""
        df_financial = self.data.get('financial_clean')
        df_pacientes = self.data.get('pacientes')
        df_atencion = self.data.get('atencion')
        
        if df_pacientes and df_financial:
            # Unir con datos de pacientes
            df_enriched = df_financial.join(
                df_pacientes.select("Id_exp", "nom_pac", "papell"),
                on="Id_exp",
                how="left"
            )
            
            if df_atencion:
                df_enriched = df_enriched.join(
                    df_atencion.select("id_atencion", "area", "especialidad"),
                    df_enriched["id_atencion"] == df_atencion["id_atencion"],
                    how="left"
                )
            
            self.data['enriched_data'] = df_enriched
            print(f"  ✅ Datos enriquecidos: {df_enriched.count()} registros")
            return df_enriched
        
        return df_financial
    
    # ==================== FASE 4: MODELING ====================
    def descriptive_analytics(self):
        """Análisis Descriptivo - Métricas básicas y agregaciones"""
        print("\n📊 FASE 4: MODELING - Análisis Descriptivo...")
        
        df = self.data.get('financial_clean')
        if df is None:
            return None
        
        descriptive = {}
        
        # 1. Ingresos por tipo de servicio
        descriptive['ingresos_por_tipo'] = df.groupBy("tipo").agg(
            count("*").alias("total_transacciones"),
            sum("subtotal").alias("ingreso_total"),
            avg("subtotal").alias("ticket_promedio"),
            max("subtotal").alias("max_ingreso"),
            min("subtotal").alias("min_ingreso")
        ).toPandas().to_dict('records')
        
        # 2. Ingresos por estado
        descriptive['ingresos_por_estado'] = df.groupBy("estado").agg(
            sum("subtotal").alias("ingreso_total"),
            count("*").alias("cantidad")
        ).toPandas().to_dict('records')
        
        # 3. Top servicios por ingreso
        descriptive['top_servicios'] = df.groupBy("tipo").agg(
            sum("subtotal").alias("total")
        ).orderBy(col("total").desc()).limit(5).toPandas().to_dict('records')
        
        # 4. Estadísticas generales
        stats = df.agg(
            mean("subtotal").alias("mean_ingreso"),
            stddev("subtotal").alias("std_ingreso"),
            sum("subtotal").alias("total_ingreso"),
            count("*").alias("total_transacciones")
        ).collect()[0]
        
        descriptive['estadisticas_generales'] = {
            'ingreso_promedio': float(stats['mean_ingreso'] or 0),
            'desviacion_ingreso': float(stats['std_ingreso'] or 0),
            'ingreso_total': float(stats['total_ingreso'] or 0),
            'total_transacciones': int(stats['total_transacciones'] or 0)
        }
        
        self.results['descriptive'] = descriptive
        
        # Guardar análisis descriptivo
        self._save_json(descriptive, "04_descriptive_analytics.json")
        
        print(f"  ✅ Ingreso total: ${descriptive['estadisticas_generales']['ingreso_total']:,.2f}")
        print(f"  ✅ Ticket promedio: ${descriptive['estadisticas_generales']['ingreso_promedio']:.2f}")
        
        return descriptive
    
    def diagnostic_analytics(self):
        """Análisis Diagnóstico - Causas y correlaciones"""
        print("\n🔍 Análisis Diagnóstico...")
        
        df = self.data.get('enriched_data')
        if df is None:
            df = self.data.get('financial_clean')
        
        diagnostic = {}
        
        # 1. Correlación entre cantidad y subtotal
        corr = df.stat.corr("cantidad", "subtotal")
        if corr is None or (isinstance(corr, float) and math.isnan(corr)):
            diagnostic['correlacion_cantidad_subtotal'] = None
        else:
            diagnostic['correlacion_cantidad_subtotal'] = builtins.round(corr, 4)
        
        # 2. Análisis por especialidad
        if "especialidad" in df.columns:
            diagnostic['analisis_por_especialidad'] = df.groupBy("especialidad").agg(
                sum("subtotal").alias("ingreso_total"),
                count("*").alias("transacciones"),
                avg("subtotal").alias("promedio")
            ).orderBy(col("ingreso_total").desc()).limit(5).toPandas().to_dict('records')
        
        # 3. Análisis por área
        if "area" in df.columns:
            diagnostic['analisis_por_area'] = df.groupBy("area").agg(
                sum("subtotal").alias("ingreso_total"),
                count("*").alias("transacciones")
            ).toPandas().to_dict('records')
        
        # 4. Distribución de montos
        diagnostic['distribucion_montos'] = {
            'menos_100': df.filter(col("subtotal") < 100).count(),
            'entre_100_500': df.filter((col("subtotal") >= 100) & (col("subtotal") < 500)).count(),
            'entre_500_1000': df.filter((col("subtotal") >= 500) & (col("subtotal") < 1000)).count(),
            'mas_1000': df.filter(col("subtotal") >= 1000).count()
        }
        
        self.results['diagnostic'] = diagnostic
        
        # Guardar análisis diagnóstico
        self._save_json(diagnostic, "05_diagnostic_analytics.json")
        
        print(f"  ✅ Correlación cantidad-subtotal: {diagnostic['correlacion_cantidad_subtotal']}")
        
        return diagnostic
    
    def predictive_modeling(self):
        """Modelos Predictivos - Regresión y Clasificación"""
        print("\n🤖 Modelos Predictivos...")
        
        df = self.data.get('financial_clean')
        if df is None or df.count() < 10:
            print("  ⚠️ Datos insuficientes para modelos predictivos")
            return None

        # ==========================
        # Preparar features
        # ==========================
        assembler = VectorAssembler(
            inputCols=["cantidad", "precio"],
            outputCol="features_unscaled"
        )
        df_features = assembler.transform(df)

        scaler = StandardScaler(
            inputCol="features_unscaled",
            outputCol="features",
            withStd=True,
            withMean=True
        )
        scaler_model = scaler.fit(df_features)
        df_scaled = scaler_model.transform(df_features)

        train, test = df_scaled.randomSplit([0.8, 0.2], seed=42)

        predictive = {}
        evaluator = RegressionEvaluator(
            labelCol="subtotal",
            predictionCol="prediction",
            metricName="r2"
        )

        # ==========================
        # Modelo 1: Regresión Lineal
        # ==========================
        print("  📈 Entrenando Regresión Lineal...")
        lr = LinearRegression(
            featuresCol="features",
            labelCol="subtotal",
            regParam=0.1
        )
        lr_model = lr.fit(train)
        lr_pred = lr_model.transform(test)

        lr_r2 = evaluator.evaluate(lr_pred)
        predictive['linear_regression_r2'] = (
            builtins.round(lr_r2, 4) if not math.isnan(lr_r2) else None
        )

        # ==========================
        # Modelo 2: Random Forest
        # ==========================
        print("  🌲 Entrenando Random Forest...")
        rf = RandomForestRegressor(
            featuresCol="features",
            labelCol="subtotal",
            numTrees=50,
            seed=42
        )
        rf_model = rf.fit(train)
        rf_pred = rf_model.transform(test)

        rf_r2 = evaluator.evaluate(rf_pred)
        predictive['random_forest_r2'] = (
            builtins.round(rf_r2, 4) if not math.isnan(rf_r2) else None
        )

        # ==========================
        # Modelo 3: GBT
        # ==========================
        print("  🚀 Entrenando GBT...")
        gbt = GBTRegressor(
            featuresCol="features",
            labelCol="subtotal",
            maxIter=50,
            seed=42
        )
        gbt_model = gbt.fit(train)
        gbt_pred = gbt_model.transform(test)

        gbt_r2 = evaluator.evaluate(gbt_pred)
        predictive['gbt_r2'] = (
            builtins.round(gbt_r2, 4) if not math.isnan(gbt_r2) else None
        )

        # ==========================
        # Importancia de features
        # ==========================
        if hasattr(rf_model, "featureImportances"):
            predictive['feature_importance'] = {
                'cantidad': float(rf_model.featureImportances[0]),
                'precio': float(rf_model.featureImportances[1])
            }

        self.results['predictive'] = predictive
        self._save_json(predictive, "06_predictive_models.json")

        # Mejor modelo
        valid_scores = {k: v for k, v in predictive.items() if isinstance(v, float)}
        if valid_scores:
            best_model = builtins.max(valid_scores, key=valid_scores.get)
            print(f"  ✅ Mejor modelo: {best_model} (R²={valid_scores[best_model]:.4f})")
        else:
            print("  ⚠️ No se pudo determinar el mejor modelo")

        return predictive
    
    def segmentation_analysis(self):
        """Segmentación de datos - K-Means (KDD)"""
        print("\n🔖 Segmentación de Datos (KDD - Clustering)...")

        df = self.data.get('financial_clean')
        if df is None or df.count() < 10:
            print("  ⚠️ Datos insuficientes para segmentación")
            return None

        assembler = VectorAssembler(
            inputCols=["cantidad", "precio", "subtotal"],
            outputCol="features"
        )
        df_cluster = assembler.transform(df)

        scaler = StandardScaler(
            inputCol="features",
            outputCol="scaled_features"
        )
        scaler_model = scaler.fit(df_cluster)
        df_scaled = scaler_model.transform(df_cluster)

        kmeans = KMeans(
            featuresCol="scaled_features",
            k=3,
            seed=42
        )
        kmeans_model = kmeans.fit(df_scaled)
        clustered = kmeans_model.transform(df_scaled)

        segmentation = {
            'num_clusters': 3,
            'centros': [list(map(float, c)) for c in kmeans_model.clusterCenters()],
            'distribucion': clustered.groupBy("prediction").count().toPandas().to_dict("records")
        }

        cluster_stats = clustered.groupBy("prediction").agg(
            avg("cantidad").alias("promedio_cantidad"),
            avg("precio").alias("promedio_precio"),
            avg("subtotal").alias("promedio_subtotal")
        ).toPandas().to_dict("records")

        segmentation['cluster_statistics'] = cluster_stats
        self.results['segmentation'] = segmentation

        self._save_json(segmentation, "07_segmentation_analysis.json")
        print(f"  ✅ Segmentos identificados: {len(segmentation['distribucion'])}")

        return segmentation
    
    # ==================== FASE 5: EVALUATION ====================
    def evaluate_results(self):
        """Evaluación de resultados"""
        print("\n⭐ FASE 5: EVALUATION - Evaluando resultados...")
        
        evaluation = {
            'calidad_modelos': {},
            'insights': [],
            'recomendaciones': []
        }
        
        descriptive = self.results.get('descriptive', {})
        predictive = self.results.get('predictive', {})
        segmentation = self.results.get('segmentation', {})

        # Evaluar modelos predictivos
        if predictive:
            valid_models = {
                k: v for k, v in predictive.items()
                if isinstance(v, (int, float))
            }

            if valid_models:
                best_model = builtins.max(valid_models, key=valid_models.get)
                best_score = valid_models[best_model]

                if best_score >= 0.9:
                    evaluation['calidad_modelos']['predictivo'] = "Excelente"
                elif best_score >= 0.7:
                    evaluation['calidad_modelos']['predictivo'] = "Bueno"
                else:
                    evaluation['calidad_modelos']['predictivo'] = "Mejorable"

                evaluation['mejor_modelo'] = best_model
                evaluation['mejor_puntaje'] = best_score
                evaluation['insights'].append(
                    f"El mejor modelo predictivo es {best_model.replace('_', ' ').title()} con R² de {best_score:.4f}."
                )
            else:
                evaluation['calidad_modelos']['predictivo'] = "No evaluable"

        # Generar insights descriptivos
        if descriptive:
            ingresos_por_tipo = sorted(
                descriptive.get('ingresos_por_tipo', []),
                key=lambda x: x.get('ingreso_total', 0),
                reverse=True
            )
            if ingresos_por_tipo:
                top_servicio = ingresos_por_tipo[0]
                evaluation['insights'].append(
                    f"El servicio con mayor ingreso es {top_servicio['tipo']} con ${top_servicio['ingreso_total']:,.2f}."
                )

            ingresos_por_estado = sorted(
                descriptive.get('ingresos_por_estado', []),
                key=lambda x: x.get('ingreso_total', 0),
                reverse=True
            )
            if ingresos_por_estado:
                mejor_estado = ingresos_por_estado[0]
                evaluation['insights'].append(
                    f"El estado con mayor ingreso es {mejor_estado['estado']} con ${mejor_estado['ingreso_total']:,.2f}."
                )

            stats = descriptive.get('estadisticas_generales', {})
            if stats:
                evaluation['insights'].append(
                    f"El ingreso promedio por transacción es ${stats.get('ingreso_promedio', 0):,.2f}."
                )

        # Generar insights de segmentación
        if segmentation and segmentation.get('num_clusters'):
            evaluation['insights'].append(
                f"Se identificaron {segmentation['num_clusters']} segmentos en el análisis de clustering."
            )

        # Recomendaciones
        evaluation['recomendaciones'] = [
            "Optimizar precios en servicios de laboratorio (ticket promedio bajo)",
            "Invertir en servicios de gabinete (mayor margen de ganancia)",
            "Implementar campañas para aumentar frecuencia de clientes",
            "Analizar viabilidad de paquetes de servicios combinados"
        ]
        
        if not evaluation['insights']:
            evaluation['insights'].append(
                "No se generaron insights automáticos; revisa los datos de entrada y el pipeline de evaluación."
            )

        self.results['evaluation'] = evaluation
        
        # Guardar evaluación
        self._save_json(evaluation, "08_evaluation_results.json")
        
        print(f"  ✅ Insights generados: {len(evaluation['insights'])}")
        
        return evaluation
    
    # ==================== FASE 6: DEPLOYMENT ====================
    def generate_visualizations(self):
        """Generar visualizaciones para deployment"""
        print("\n🚀 FASE 6: DEPLOYMENT - Generando visualizaciones...")
        
        df = self.data.get('financial_clean')
        if df is None:
            return {}
        
        pandas_df = df.toPandas()
        visualizations = {}
        
        # Crear subcarpeta para visualizaciones
        viz_dir = self.results_dir / "visualizaciones"
        viz_dir.mkdir(exist_ok=True)
        
        # Gráfico 1: Ingresos por tipo
        fig1, ax1 = plt.subplots(figsize=(10, 6))
        ingresos_tipo = pandas_df.groupby('tipo')['subtotal'].sum()
        colors = ['#667eea', '#764ba2']
        ingresos_tipo.plot(kind='bar', ax=ax1, color=colors)
        ax1.set_title('Ingresos por Tipo de Servicio', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Tipo de Servicio')
        ax1.set_ylabel('Ingreso Total ($)')
        ax1.tick_params(axis='x', rotation=0)
        
        for i, v in enumerate(ingresos_tipo.values):
            ax1.text(i, v + 100, f'${v:,.0f}', ha='center', fontweight='bold')
        
        img1 = io.BytesIO()
        plt.savefig(img1, format='png', bbox_inches='tight', dpi=100)
        img1.seek(0)
        visualizations['ingresos_por_tipo'] = base64.b64encode(img1.getvalue()).decode()
        
        # Guardar imagen
        fig1.savefig(viz_dir / "ingresos_por_tipo.png", bbox_inches='tight', dpi=100)
        plt.close()
        
        # Gráfico 2: Distribución de precios
        fig2, ax2 = plt.subplots(figsize=(10, 6))
        ax2.hist(pandas_df['precio'], bins=20, color='#667eea', alpha=0.7, edgecolor='black')
        ax2.set_title('Distribución de Precios', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Precio ($)')
        ax2.set_ylabel('Frecuencia')
        ax2.axvline(pandas_df['precio'].mean(), color='red', linestyle='dashed', 
                   linewidth=2, label=f"Media: ${pandas_df['precio'].mean():.2f}")
        ax2.legend()
        
        fig2.savefig(viz_dir / "distribucion_precios.png", bbox_inches='tight', dpi=100)
        img2 = io.BytesIO()
        plt.savefig(img2, format='png', bbox_inches='tight', dpi=100)
        img2.seek(0)
        visualizations['distribucion_precios'] = base64.b64encode(img2.getvalue()).decode()
        plt.close()
        
        # Gráfico 3: Scatter plot
        fig3, ax3 = plt.subplots(figsize=(10, 6))
        scatter = ax3.scatter(pandas_df['cantidad'], pandas_df['precio'], 
                             c=pandas_df['subtotal'], cmap='viridis', s=50, alpha=0.6)
        ax3.set_xlabel('Cantidad')
        ax3.set_ylabel('Precio ($)')
        ax3.set_title('Relación: Cantidad vs Precio (color = Ingreso)', fontsize=14, fontweight='bold')
        plt.colorbar(scatter, ax=ax3, label='Ingreso ($)')
        
        fig3.savefig(viz_dir / "scatter_cantidad_precio.png", bbox_inches='tight', dpi=100)
        img3 = io.BytesIO()
        plt.savefig(img3, format='png', bbox_inches='tight', dpi=100)
        img3.seek(0)
        visualizations['scatter_cantidad_precio'] = base64.b64encode(img3.getvalue()).decode()
        plt.close()
        
        # Gráfico 4: Comparación de modelos
        if 'predictive' in self.results:
            fig4, ax4 = plt.subplots(figsize=(10, 6))
            modelos = ['Linear Regression', 'Random Forest', 'GBT']
            scores = [
                self.results['predictive'].get('linear_regression_r2', 0),
                self.results['predictive'].get('random_forest_r2', 0),
                self.results['predictive'].get('gbt_r2', 0)
            ]
            colors_models = ['#48bb78', '#4299e1', '#ed8936']
            bars = ax4.bar(modelos, scores, color=colors_models, alpha=0.7)
            ax4.set_ylabel('R² Score')
            ax4.set_title('Comparación de Modelos de Machine Learning', fontsize=14, fontweight='bold')
            ax4.set_ylim([0, 1.1])
            
            for bar, score in zip(bars, scores):
                ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                        f'{score:.4f}', ha='center', va='bottom', fontweight='bold')
            
            plt.xticks(rotation=15)
            
            fig4.savefig(viz_dir / "comparacion_modelos.png", bbox_inches='tight', dpi=100)
            img4 = io.BytesIO()
            plt.savefig(img4, format='png', bbox_inches='tight', dpi=100)
            img4.seek(0)
            visualizations['comparacion_modelos'] = base64.b64encode(img4.getvalue()).decode()
            plt.close()
        
        self.results['visualizations'] = visualizations
        
        # Guardar visualizaciones en JSON
        self._save_json({'visualizaciones_generadas': list(visualizations.keys())}, "09_visualizations_summary.json")
        
        print(f"  ✅ {len(visualizations)} visualizaciones generadas")
        print(f"  📁 Imágenes guardadas en: {viz_dir}")
        
        return visualizations
    
    def deploy_results(self):
        """Desplegar resultados en JSON dentro de results/"""
        print("\n📦 DEPLOYMENT - Guardando resultados...")
        
        # Preparar resultados para exportación
        deploy_data = {
            'timestamp': datetime.now().isoformat(),
            'business_understanding': self.results.get('business_objectives', {}),
            'data_understanding': self.results.get('data_understanding', {}),
            'descriptive_analytics': self.results.get('descriptive', {}),
            'diagnostic_analytics': self.results.get('diagnostic', {}),
            'predictive_modeling': self.results.get('predictive', {}),
            'segmentation_analysis': self.results.get('segmentation', {}),
            'evaluation': self.results.get('evaluation', {}),
            'insights_summary': self.results.get('evaluation', {}).get('insights', []),
            'recommendations': self.results.get('evaluation', {}).get('recomendaciones', [])
        }
        
        # Guardar resultados completos
        self._save_json(deploy_data, "10_complete_crisp_dm_results.json")
        
        print(f"  ✅ Resultados completos guardados")
        
        return deploy_data
    
    def run_complete_analysis(self):
        """Ejecutar análisis completo CRISP-DM"""
        print("\n" + "="*60)
        print("🏥 ANÁLISIS HOSPITALARIO - METODOLOGÍA CRISP-DM")
        print(f"📁 Resultados guardados en: {self.results_dir}")
        print("="*60)
        
        # Fase 1: Business Understanding
        self.business_understanding()
        
        # Fase 2: Data Understanding
        self.load_data()
        self.data_understanding()
        
        # Fase 3: Data Preparation
        self.prepare_financial_data()
        self.prepare_patient_data()
        
        # Fase 4: Modeling
        self.descriptive_analytics()
        self.diagnostic_analytics()
        self.predictive_modeling()
        self.segmentation_analysis()
        
        # Fase 5: Evaluation
        self.evaluate_results()
        
        # Fase 6: Deployment
        self.generate_visualizations()
        deploy_data = self.deploy_results()
        
        print("\n" + "="*60)
        print("✅ ANÁLISIS CRISP-DM COMPLETADO EXITOSAMENTE")
        print(f"📁 Todos los archivos están en: {self.results_dir}")
        print("="*60)
        
        return deploy_data


# ==================== KDD (Knowledge Discovery in Databases) ====================
class KDDAnalytics:
    """
    Metodología KDD para descubrimiento de conocimiento:
    1. Selección de datos
    2. Preprocesamiento
    3. Transformación
    4. Minería de datos
    5. Interpretación/Evaluación
    """
    
    def __init__(self, spark, db_name):
        self.spark = spark
        self.db_name = db_name
        self.data = None
        self.knowledge = {}
        self.results_dir = RESULTS_DIR
        
    def _save_json(self, data, filename):
        """Guarda un archivo JSON en la carpeta results"""
        filepath = self.results_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"  💾 Guardado: {filepath}")
        return filepath
    
    def data_selection(self):
        """Selección de datos relevantes"""
        print("\n📁 KDD - Fase 1: Selección de Datos")
        
        df_cuenta = self.spark.read \
            .format("mongodb") \
            .option("database", self.db_name) \
            .option("collection", "cuenta_paciente") \
            .load()
        
        # Seleccionar atributos relevantes
        self.data = df_cuenta.select(
            "cantidad", "precio", "subtotal", "tipo", "estado", "fecha"
        )
        
        selection_stats = {
            'total_registros': self.data.count(),
            'columnas_seleccionadas': self.data.columns,
            'fase': 'data_selection'
        }
        self._save_json(selection_stats, "kdd_01_data_selection.json")
        
        print(f"  ✅ Datos seleccionados: {self.data.count()} registros")
        return self.data
    
    def preprocessing(self):
        """Preprocesamiento y limpieza"""
        print("\n🧹 KDD - Fase 2: Preprocesamiento")
        
        initial_count = self.data.count()
        
        # Limpiar datos
        self.data = self.data.na.drop()
        self.data = self.data.filter(
            (col("cantidad") > 0) & 
            (col("precio") > 0) & 
            (col("subtotal") > 0)
        )
        
        final_count = self.data.count()
        
        prep_stats = {
            'registros_iniciales': initial_count,
            'registros_finales': final_count,
            'registros_eliminados': initial_count - final_count,
            'tasa_retencion': builtins.round(final_count / initial_count * 100, 2) if initial_count > 0 else 0,
            'fase': 'preprocessing'
        }
        self._save_json(prep_stats, "kdd_02_preprocessing.json")
        
        print(f"  ✅ Datos limpios: {final_count} registros")
        return self.data
    
    def transformation(self):
        """Transformación de datos"""
        print("\n🔄 KDD - Fase 3: Transformación")
        
        # Crear nuevas features
        self.data = self.data.withColumn("precio_por_unidad", col("subtotal") / col("cantidad"))
        self.data = self.data.withColumn("mes", month(to_date(col("fecha"))))
        self.data = self.data.withColumn("rango_precio", 
            when(col("precio") < 100, "Bajo")
            .when(col("precio") < 300, "Medio")
            .otherwise("Alto"))
        
        transform_stats = {
            'nuevas_features': ['precio_por_unidad', 'mes', 'rango_precio'],
            'registros_transformados': self.data.count(),
            'fase': 'transformation'
        }
        self._save_json(transform_stats, "kdd_03_transformation.json")
        
        print(f"  ✅ Nuevas features creadas")
        return self.data
    
    def data_mining(self):
        """Minería de datos - Búsqueda de patrones"""
        print("\n⛏️ KDD - Fase 4: Minería de Datos")
        
        patterns = {}

        from pyspark.sql.functions import col

        # 🔒 CONVERSIÓN SEGURA: fechas → string (ANTES de toPandas)
        for campo, tipo in self.data.dtypes:
            if tipo in ("date", "timestamp"):
                self.data = self.data.withColumn(campo, col(campo).cast("string"))

        # Convertir a Pandas
        df_pandas = self.data.toPandas()

        # 🔧 Asegurar tipos numéricos
        for c in ['cantidad', 'precio', 'subtotal']:
            if c in df_pandas.columns:
                df_pandas[c] = df_pandas[c].astype(float)

        # Patrón 1: Servicios más frecuentes
        if 'tipo' in df_pandas.columns:
            patterns['servicios_frecuentes'] = df_pandas['tipo'].value_counts().to_dict()

        # Patrón 2: Ingresos por rango de precio
        if 'rango_precio' in df_pandas.columns:
            patterns['ingresos_por_rango'] = (
                df_pandas.groupby('rango_precio')['subtotal']
                .sum()
                .to_dict()
            )

        # Patrón 3: Estacionalidad por mes
        if 'mes' in df_pandas.columns:
            patterns['ingresos_por_mes'] = (
                df_pandas.groupby('mes')['subtotal']
                .sum()
                .to_dict()
            )

        # Patrón 4: Estadísticas por tipo de servicio
        if 'tipo' in df_pandas.columns:
            patterns['estadisticas_por_tipo'] = (
                df_pandas.groupby('tipo')
                .agg(
                    subtotal_sum=('subtotal', 'sum'),
                    subtotal_mean=('subtotal', 'mean'),
                    subtotal_count=('subtotal', 'count'),
                    precio_mean=('precio', 'mean'),
                    precio_std=('precio', 'std')
                )
                .to_dict()
            )

        # Patrón 5: Correlaciones
        numeric_cols = [c for c in ['cantidad', 'precio', 'subtotal'] if c in df_pandas.columns]
        if len(numeric_cols) >= 2:
            patterns['correlaciones'] = df_pandas[numeric_cols].corr().to_dict()

        self.knowledge['patterns'] = patterns

        # Guardar patrones
        self._save_json(patterns, "kdd_04_data_mining_patterns.json")

        print(f"  ✅ Patrones encontrados: {len(patterns)}")

        return patterns
    
    def interpretation(self):
        """Interpretación de resultados"""
        print("\n📖 KDD - Fase 5: Interpretación")
        
        interpretation = {
            'hallazgos_clave': [],
            'recomendaciones_kdd': []
        }
        
        patterns = self.knowledge.get('patterns', {})
        
        # Interpretar patrones
        for tipo, count in patterns.get('servicios_frecuentes', {}).items():
            interpretation['hallazgos_clave'].append(
                f"Los servicios de {tipo} son los más solicitados con {count} transacciones"
            )
        
        for rango, ingreso in patterns.get('ingresos_por_rango', {}).items():
            interpretation['hallazgos_clave'].append(
                f"Los servicios de precio {rango} generan ${ingreso:,.2f}"
            )
        
        for mes, ingreso in patterns.get('ingresos_por_mes', {}).items():
            interpretation['hallazgos_clave'].append(
                f"En el mes {mes} se generaron ${ingreso:,.2f}"
            )
        
        interpretation['recomendaciones_kdd'] = [
            "Enfocar recursos en servicios de laboratorio (mayor volumen)",
            "Optimizar precios de servicios de gabinete (mayor ticket)",
            "Analizar estacionalidad para planificar capacidad",
            "Implementar estrategias de up-selling en servicios de alto valor"
        ]
        
        interpretation['resumen_ejecutivo_kdd'] = {
            'total_patrones_encontrados': len(patterns),
            'principales_servicios': list(patterns.get('servicios_frecuentes', {}).keys()),
            'rango_mas_rentable': builtins.max(patterns.get('ingresos_por_rango', {}), key=patterns.get('ingresos_por_rango', {}).get) if patterns.get('ingresos_por_rango') else 'N/A'
        }
        
        self.knowledge['interpretation'] = interpretation
        
        # Guardar interpretación
        self._save_json(interpretation, "kdd_05_interpretation.json")
        
        # Guardar conocimiento completo de KDD
        self._save_json(self.knowledge, "kdd_complete_results.json")
        
        print(f"  ✅ {len(interpretation['hallazgos_clave'])} hallazgos identificados")
        
        return interpretation
    
    def run_kdd_analysis(self):
        """Ejecutar análisis KDD completo"""
        print("\n" + "="*60)
        print("🔍 ANÁLISIS HOSPITALARIO - METODOLOGÍA KDD")
        print(f"📁 Resultados guardados en: {self.results_dir}")
        print("="*60)
        
        self.data_selection()
        self.preprocessing()
        self.transformation()
        self.data_mining()
        self.interpretation()
        
        print("\n✅ Análisis KDD completado")
        return self.knowledge