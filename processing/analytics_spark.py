# analytics_spark.py
from pyspark.sql import SparkSession
from pyspark.ml.regression import LinearRegression, RandomForestRegressor, GBTRegressor
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.feature import VectorAssembler
from pyspark.sql.functions import col
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # Para evitar problemas con GUI
import io
import base64
from pathlib import Path
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def get_spark_session():
    """Inicializa Spark con MongoDB"""
    mongo_uri = os.getenv("MONGO_URI")
    db_name = os.getenv("DB_NAME")
    
    jars_dir = Path("jars")
    jar_files = list(jars_dir.glob("mongo-spark-connector*.jar"))
    jar_path = str(jar_files[0]) if jar_files else ""
    
    spark = SparkSession.builder \
        .appName("AnalyticsDashboard") \
        .master("local[*]") \
        .config("spark.jars", jar_path) \
        .config("spark.mongodb.read.connection.uri", mongo_uri) \
        .config("spark.mongodb.write.connection.uri", mongo_uri) \
        .config("spark.driver.memory", "4g") \
        .getOrCreate()
    
    return spark, db_name

def generar_analytics():
    """Genera todas las visualizaciones y resultados"""
    
    print("📊 Conectando a MongoDB con Spark...")
    spark, db_name = get_spark_session()
    
    # Cargar datos
    df = spark.read \
        .format("mongodb") \
        .option("database", db_name) \
        .option("collection", "cuenta_paciente") \
        .load()
    
    # Filtrar datos válidos
    df_ml = df.select(
        col("cantidad").cast("double"),
        col("precio").cast("double"),
        col("subtotal").cast("double").alias("label"),
        col("tipo")
    ).na.drop()
    
    # Convertir a Pandas para visualizaciones
    pandas_df = df_ml.toPandas()
    
    # Figura 1: Dispersión (Cantidad vs Precio)
    fig1, ax1 = plt.subplots(figsize=(10, 6))
    colors = {'LABORATORIO': 'blue', 'GABINETE': 'green'}
    for tipo, color in colors.items():
        subset = pandas_df[pandas_df['tipo'] == tipo]
        ax1.scatter(subset['cantidad'], subset['precio'], 
                   label=tipo, alpha=0.6, c=color, s=50)
    ax1.set_xlabel('Cantidad')
    ax1.set_ylabel('Precio')
    ax1.set_title('Dispersión: Cantidad vs Precio por Tipo')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    img1 = io.BytesIO()
    plt.savefig(img1, format='png', bbox_inches='tight', dpi=100)
    img1.seek(0)
    fig1_base64 = base64.b64encode(img1.getvalue()).decode()
    plt.close()
    
    # Figura 2: Precio vs Ingreso
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    for tipo, color in colors.items():
        subset = pandas_df[pandas_df['tipo'] == tipo]
        ax2.scatter(subset['precio'], subset['label'], 
                   label=tipo, alpha=0.6, c=color, s=50)
    ax2.set_xlabel('Precio')
    ax2.set_ylabel('Subtotal (Ingreso)')
    ax2.set_title('Relación: Precio vs Ingreso Total')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    img2 = io.BytesIO()
    plt.savefig(img2, format='png', bbox_inches='tight', dpi=100)
    img2.seek(0)
    fig2_base64 = base64.b64encode(img2.getvalue()).decode()
    plt.close()
    
    # Figura 3: Distribución de ingresos por tipo
    fig3, ax3 = plt.subplots(figsize=(10, 6))
    pandas_df.boxplot(column='label', by='tipo', ax=ax3)
    ax3.set_title('Distribución de Ingresos por Tipo de Servicio')
    ax3.set_xlabel('Tipo de Servicio')
    ax3.set_ylabel('Ingreso ($)')
    plt.suptitle('')  # Quitar título automático
    
    img3 = io.BytesIO()
    plt.savefig(img3, format='png', bbox_inches='tight', dpi=100)
    img3.seek(0)
    fig3_base64 = base64.b64encode(img3.getvalue()).decode()
    plt.close()
    
    # Preparar datos para ML
    assembler = VectorAssembler(inputCols=["cantidad", "precio"], outputCol="features")
    df_ml = assembler.transform(df_ml)
    
    train, test = df_ml.randomSplit([0.8, 0.2], seed=42)
    
    # Entrenar modelos
    evaluator = RegressionEvaluator(labelCol="label", predictionCol="prediction", metricName="r2")
    resultados = {}
    
    # Linear Regression
    lr = LinearRegression(featuresCol="features", labelCol="label")
    lr_model = lr.fit(train)
    pred_lr = lr_model.transform(test)
    resultados["Linear Regression"] = round(evaluator.evaluate(pred_lr), 4)
    
    # Random Forest
    rf = RandomForestRegressor(featuresCol="features", labelCol="label", numTrees=100)
    rf_model = rf.fit(train)
    pred_rf = rf_model.transform(test)
    resultados["Random Forest"] = round(evaluator.evaluate(pred_rf), 4)
    
    # GBT
    gbt = GBTRegressor(featuresCol="features", labelCol="label", maxIter=100)
    gbt_model = gbt.fit(train)
    pred_gbt = gbt_model.transform(test)
    resultados["GBT"] = round(evaluator.evaluate(pred_gbt), 4)
    
    # Figura 4: Comparación de modelos
    fig4, ax4 = plt.subplots(figsize=(10, 6))
    models = list(resultados.keys())
    scores = list(resultados.values())
    colors_models = ['#667eea', '#764ba2', '#48bb78']
    bars = ax4.bar(models, scores, color=colors_models, alpha=0.7)
    ax4.set_ylabel('R² Score')
    ax4.set_title('Comparación de Modelos de Machine Learning')
    ax4.set_ylim([0, 1.1])
    
    # Agregar valores en las barras
    for bar, score in zip(bars, scores):
        ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f'{score:.4f}', ha='center', va='bottom', fontweight='bold')
    
    plt.xticks(rotation=15)
    
    img4 = io.BytesIO()
    plt.savefig(img4, format='png', bbox_inches='tight', dpi=100)
    img4.seek(0)
    fig4_base64 = base64.b64encode(img4.getvalue()).decode()
    plt.close()
    
    spark.stop()
    
    return {
        'fig1': fig1_base64,
        'fig2': fig2_base64,
        'fig3': fig3_base64,
        'fig4': fig4_base64,
        'resultados': resultados,
        'total_registros': len(pandas_df),
        'total_laboratorio': len(pandas_df[pandas_df['tipo'] == 'LABORATORIO']),
        'total_gabinete': len(pandas_df[pandas_df['tipo'] == 'GABINETE']),
        'ingreso_total': pandas_df['label'].sum(),
        'ticket_promedio': pandas_df['label'].mean()
    }