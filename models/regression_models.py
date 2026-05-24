# regression_models.py
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.regression import LinearRegression, RandomForestRegressor, GBTRegressor
from pyspark.ml.evaluation import RegressionEvaluator

class HospitalMLModels:
    def __init__(self):
        self.evaluator = RegressionEvaluator(
            labelCol="subtotal", 
            predictionCol="prediction", 
            metricName="r2"
        )

    def train_regression(self, df):
        # Verificar que hay suficientes datos
        if df.count() < 10:
            raise ValueError(f"Se requieren al menos 10 registros para entrenar. Solo hay {df.count()}")
        
        # Preparar features
        assembler = VectorAssembler(
            inputCols=["cantidad", "precio"],
            outputCol="features"
        )
        df_features = assembler.transform(df)
        
        # Split
        train, test = df_features.randomSplit([0.8, 0.2], seed=42)
        
        print(f"Entrenamiento: {train.count()} registros")
        print(f"Prueba: {test.count()} registros")
        
        resultados = {}
        modelos = {}
        
        # Linear Regression
        print("\n Entrenando Regresión Lineal...")
        lr = LinearRegression(featuresCol="features", labelCol="subtotal")
        lr_model = lr.fit(train)
        pred_lr = lr_model.transform(test)
        resultados["LinearRegression"] = self.evaluator.evaluate(pred_lr)
        modelos["LinearRegression"] = lr_model
        print(f"   R² = {resultados['LinearRegression']:.4f}")
        
        # Random Forest
        print("\n Entrenando Random Forest...")
        rf = RandomForestRegressor(
            featuresCol="features", 
            labelCol="subtotal", 
            numTrees=100,
            maxDepth=10,
            seed=42
        )
        rf_model = rf.fit(train)
        pred_rf = rf_model.transform(test)
        resultados["RandomForest"] = self.evaluator.evaluate(pred_rf)
        modelos["RandomForest"] = rf_model
        print(f"   R² = {resultados['RandomForest']:.4f}")
        
        # Gradient Boosted Trees (mejor para ciertos casos)
        print("\n Entrenando GBT...")
        gbt = GBTRegressor(
            featuresCol="features",
            labelCol="subtotal",
            maxIter=100,
            maxDepth=5,
            seed=42
        )
        gbt_model = gbt.fit(train)
        pred_gbt = gbt_model.transform(test)
        resultados["GBT"] = self.evaluator.evaluate(pred_gbt)
        modelos["GBT"] = gbt_model
        print(f"   R² = {resultados['GBT']:.4f}")
        
        # Mostrar mejores resultados
        print("\n" + "="*50)
        print(" RESULTADOS DE MODELOS:")
        print("="*50)
        for model, score in sorted(resultados.items(), key=lambda x: x[1], reverse=True):
            print(f"   {model}: R² = {score:.4f}")
        
        mejor_modelo = max(resultados, key=resultados.get)
        print(f"\n Mejor modelo: {mejor_modelo} (R² = {resultados[mejor_modelo]:.4f})")
        
        return resultados, modelos[mejor_modelo]