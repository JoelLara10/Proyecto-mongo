# main_mongo.py
from config.spark_config import get_spark_session
from processing.data_processor import DataProcessor
from models.regression_models import HospitalMLModels
from pyspark.sql.functions import col, sum as spark_sum, avg, count
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.regression import LinearRegression, RandomForestRegressor, GBTRegressor
from pyspark.ml.evaluation import RegressionEvaluator
import json
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import io
import base64
import os
import pandas as pd

def generar_y_guardar_analytics():
    """Ejecuta Spark y guarda todos los resultados incluyendo gráficas"""
    
    print("="*60)
    print("🏥 EJECUTANDO ANÁLISIS CON SPARK")
    print("="*60)
    
    spark, db_name = get_spark_session()
    
    # Cargar datos
    processor = DataProcessor(spark)
    collections = processor.load_collections(db_name)
    
    if collections["cuenta_paciente"] is None:
        print("❌ No se pudo cargar cuenta_paciente")
        return None
    
    # Preparar datos
    df = collections["cuenta_paciente"].select(
        col("cantidad").cast("double"),
        col("precio").cast("double"),
        col("subtotal").cast("double").alias("label"),
        col("tipo")
    ).na.drop()
    
    df = df.filter((col("cantidad") > 0) & (col("precio") > 0) & (col("label") > 0))
    
    if df.count() == 0:
        print("❌ No hay datos válidos")
        return None
    
    # Convertir a Pandas para gráficas
    pandas_df = df.toPandas()
    
    print(f"📊 Datos cargados: {len(pandas_df)} registros")
    
    # ========== GENERAR GRÁFICAS ==========
    
    # Figura 1: Dispersión (Cantidad vs Precio)
    print("Generando gráfica 1...")
    fig1, ax1 = plt.subplots(figsize=(10, 6))
    
    # Separar por tipo
    df_lab = pandas_df[pandas_df['tipo'] == 'LABORATORIO']
    df_gab = pandas_df[pandas_df['tipo'] == 'GABINETE']
    
    if len(df_lab) > 0:
        ax1.scatter(df_lab['cantidad'], df_lab['precio'], 
                   label='LABORATORIO', alpha=0.6, c='blue', s=50)
    if len(df_gab) > 0:
        ax1.scatter(df_gab['cantidad'], df_gab['precio'], 
                   label='GABINETE', alpha=0.6, c='green', s=50)
    
    ax1.set_xlabel('Cantidad')
    ax1.set_ylabel('Precio')
    ax1.set_title('Dispersión: Cantidad vs Precio por Tipo')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    img1 = io.BytesIO()
    plt.savefig(img1, format='png', bbox_inches='tight', dpi=100)
    img1.seek(0)
    fig1_base64 = base64.b64encode(img1.getvalue()).decode()
    plt.close(fig1)
    
    # Figura 2: Precio vs Ingreso
    print("Generando gráfica 2...")
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    
    if len(df_lab) > 0:
        ax2.scatter(df_lab['precio'], df_lab['label'], 
                   label='LABORATORIO', alpha=0.6, c='blue', s=50)
    if len(df_gab) > 0:
        ax2.scatter(df_gab['precio'], df_gab['label'], 
                   label='GABINETE', alpha=0.6, c='green', s=50)
    
    ax2.set_xlabel('Precio')
    ax2.set_ylabel('Subtotal (Ingreso)')
    ax2.set_title('Relación: Precio vs Ingreso Total')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    img2 = io.BytesIO()
    plt.savefig(img2, format='png', bbox_inches='tight', dpi=100)
    img2.seek(0)
    fig2_base64 = base64.b64encode(img2.getvalue()).decode()
    plt.close(fig2)
    
    # Figura 3: Boxplot por tipo
    print("Generando gráfica 3...")
    fig3, ax3 = plt.subplots(figsize=(10, 6))
    
    # Preparar datos para boxplot
    boxplot_data = []
    labels = []
    if len(df_lab) > 0:
        boxplot_data.append(df_lab['label'])
        labels.append('LABORATORIO')
    if len(df_gab) > 0:
        boxplot_data.append(df_gab['label'])
        labels.append('GABINETE')
    
    if boxplot_data:
        bp = ax3.boxplot(boxplot_data, labels=labels, patch_artist=True)
        for patch, color in zip(bp['boxes'], ['lightblue', 'lightgreen']):
            patch.set_facecolor(color)
    
    ax3.set_ylabel('Ingreso ($)')
    ax3.set_title('Distribución de Ingresos por Tipo')
    ax3.grid(True, alpha=0.3)
    
    img3 = io.BytesIO()
    plt.savefig(img3, format='png', bbox_inches='tight', dpi=100)
    img3.seek(0)
    fig3_base64 = base64.b64encode(img3.getvalue()).decode()
    plt.close(fig3)
    
    # ========== MODELOS ML ==========
    print("Entrenando modelos...")
    
    # Preparar features
    assembler = VectorAssembler(inputCols=["cantidad", "precio"], outputCol="features")
    df_ml = assembler.transform(df)
    
    train, test = df_ml.randomSplit([0.8, 0.2], seed=42)
    
    evaluator = RegressionEvaluator(labelCol="label", predictionCol="prediction", metricName="r2")
    resultados = {}
    
    # Linear Regression
    lr = LinearRegression(featuresCol="features", labelCol="label")
    lr_model = lr.fit(train)
    pred_lr = lr_model.transform(test)
    resultados["LinearRegression"] = round(evaluator.evaluate(pred_lr), 4)
    
    # Random Forest
    rf = RandomForestRegressor(featuresCol="features", labelCol="label", numTrees=100)
    rf_model = rf.fit(train)
    pred_rf = rf_model.transform(test)
    resultados["RandomForest"] = round(evaluator.evaluate(pred_rf), 4)
    
    # GBT
    gbt = GBTRegressor(featuresCol="features", labelCol="label", maxIter=100)
    gbt_model = gbt.fit(train)
    pred_gbt = gbt_model.transform(test)
    resultados["GBT"] = round(evaluator.evaluate(pred_gbt), 4)
    
    # Figura 4: Comparación de modelos
    print("Generando gráfica 4...")
    fig4, ax4 = plt.subplots(figsize=(10, 6))
    
    modelos = list(resultados.keys())
    scores = list(resultados.values())
    colores = ['#667eea', '#764ba2', '#48bb78']
    
    bars = ax4.bar(modelos, scores, color=colores, alpha=0.7)
    ax4.set_ylabel('R² Score')
    ax4.set_title('Comparación de Modelos de Machine Learning')
    ax4.set_ylim([0, 1.1])
    
    # Agregar valores
    for bar, score in zip(bars, scores):
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f'{score:.4f}', ha='center', va='bottom', fontweight='bold')
    
    plt.xticks(rotation=15)
    
    img4 = io.BytesIO()
    plt.savefig(img4, format='png', bbox_inches='tight', dpi=100)
    img4.seek(0)
    fig4_base64 = base64.b64encode(img4.getvalue()).decode()
    plt.close(fig4)
    
    # ========== GUARDAR RESULTADOS ==========
    
    analytics_data = {
        "fecha_generacion": datetime.now().isoformat(),
        "total_registros": len(pandas_df),
        "total_laboratorio": len(pandas_df[pandas_df['tipo'] == 'LABORATORIO']),
        "total_gabinete": len(pandas_df[pandas_df['tipo'] == 'GABINETE']),
        "ingreso_total": float(pandas_df['label'].sum()),
        "ticket_promedio": float(pandas_df['label'].mean()),
        "resultados_modelos": resultados,
        "fig1": fig1_base64,
        "fig2": fig2_base64,
        "fig3": fig3_base64,
        "fig4": fig4_base64
    }
    
    # Guardar en archivo
    with open("analytics_cache.json", "w", encoding="utf-8") as f:
        json.dump(analytics_data, f, indent=4, ensure_ascii=False)
    
    print("\n✅ Análisis completado!")
    print(f"   - Registros: {len(pandas_df)}")
    print(f"   - Laboratorio: {len(pandas_df[pandas_df['tipo'] == 'LABORATORIO'])}")
    print(f"   - Gabinete: {len(pandas_df[pandas_df['tipo'] == 'GABINETE'])}")
    print(f"   - Ingreso total: ${pandas_df['label'].sum():,.2f}")
    print(f"   - Mejor modelo: {max(resultados, key=resultados.get)} (R²={max(resultados.values()):.4f})")
    print("\n📁 Resultados guardados en analytics_cache.json")
    
    spark.stop()
    return analytics_data

# Verificar si existe el archivo de caché al iniciar
if __name__ == "__main__":
    generar_y_guardar_analytics()