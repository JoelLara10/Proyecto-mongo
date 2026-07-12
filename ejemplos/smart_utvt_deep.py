# SmartUTVT: análisis de rendimiento estudiantil.
# Objetivos: predecir calificación final e identificar riesgo de reprobación.

# Sección 1: carga y exploración de datos.

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier

from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    confusion_matrix,
    classification_report,
    accuracy_score,
    r2_score
)

from sklearn.model_selection import train_test_split

plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

print("=" * 80)
print("SMARTUTVT - ANÁLISIS DE RENDIMIENTO ESTUDIANTIL")
print("=" * 80)
print("\n")

# 1.2 Crear DataFrame.

datos = {
    'Alumno': ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8'],
    'Asistencia': [95, 80, 60, 50, 85, 40, 90, 55],
    'Horas_Estudio': [5, 4, 2, 1, 4, 1, 5, 2],
    'Tareas': [10, 8, 6, 4, 9, 3, 10, 5],
    'Promedio': [92, 80, 65, 50, 88, 45, 94, 55],
    'Parcial': [95, 82, 60, 45, 90, 40, 96, 50],
    'Calificacion': ['Sí', 'Sí', 'No', 'No', 'Sí', 'No', 'Sí', 'No'],
    'Final': [95, 82, 60, 45, 90, 40, 96, 50]
}

df = pd.DataFrame(datos)

print("1.2 DATAFRAME CREADO")
print("-" * 80)
print("Datos de estudiantes:")
print(df)
print("\n")

# 1.3 Estadísticas descriptivas.

print("1.3 ESTADÍSTICAS DESCRIPTIVAS")
print("-" * 80)

# Variables numéricas.
variables_numericas = ['Asistencia', 'Horas_Estudio', 'Tareas', 'Promedio', 'Parcial', 'Final']

print("Estadísticas de variables numéricas:")
print(df[variables_numericas].describe())
print("\n")

# Variables categóricas.
print("Distribución de aprobados/reprobados:")
print(df['Calificacion'].value_counts())
print("\n")

# Matriz de correlación.

print("Matriz de correlación:")
print(df[variables_numericas].corr().round(4))
print("\n")

# Sección 2: modelos de regresión.

print("=" * 80)
print("SECCIÓN 2: MODELOS DE REGRESIÓN")
print("=" * 80)
print("\n")

# Preparar datos para regresión (train/test).
X_regresion = df[['Asistencia', 'Horas_Estudio', 'Tareas', 'Promedio', 'Parcial']]
y_regresion = df['Final']
X_train_reg, X_test_reg, y_train_reg, y_test_reg = train_test_split(
    X_regresion, y_regresion, test_size=0.25, random_state=42
)

# Preparar datos para clasificación (train/test con balance de clases).
y_clasificacion = df['Calificacion'].map({'Sí': 1, 'No': 0})
X_train_clf, X_test_clf, y_train_clf, y_test_clf = train_test_split(
    X_regresion, y_clasificacion, test_size=0.25, random_state=42, stratify=y_clasificacion
)

# 2.1 Regresión lineal simple.

print("2.1 REGRESIÓN LINEAL SIMPLE")
print("-" * 80)

# Usar solo Horas_Estudio como predictor.
X_train_simple = X_train_reg[['Horas_Estudio']]
X_test_simple = X_test_reg[['Horas_Estudio']]

# Crear y entrenar modelo.
modelo_simple = LinearRegression()
modelo_simple.fit(X_train_simple, y_train_reg)

# Obtener coeficientes.
m = modelo_simple.coef_[0]
b = modelo_simple.intercept_

print(f"Ecuación de la recta: Final = {m:.4f} × Horas_Estudio + {b:.4f}")
print(f"Interpretación: Por cada hora adicional de estudio, la calificación final aumenta {m:.4f} puntos")

# Predicciones.
y_pred_simple = modelo_simple.predict(X_test_simple)

# Métrica R².

r2_simple = r2_score(y_test_reg, y_pred_simple)
print(f"\nR²: {r2_simple:.4f}")
print(f"Interpretación: El {r2_simple*100:.2f}% de la variación en la calificación final")
print(f"es explicada por las horas de estudio")
print("\n")

# 2.2 Regresión lineal múltiple.

print("2.2 REGRESIÓN LINEAL MÚLTIPLE")
print("-" * 80)

# Usar todas las variables predictoras.
X_multiple_train = X_train_reg
X_multiple_test = X_test_reg
y_multiple_test = y_test_reg

# Crear y entrenar modelo.
modelo_multiple = LinearRegression()
modelo_multiple.fit(X_multiple_train, y_train_reg)

# Mostrar ecuación con coeficientes.
print("Ecuación del modelo:")
print(f"Final = {modelo_multiple.intercept_:.4f}")
for i, col in enumerate(X_multiple_train.columns):
    signo = "+" if modelo_multiple.coef_[i] >= 0 else "-"
    print(f"        {signo} {abs(modelo_multiple.coef_[i]):.4f} × {col}")

# Predicciones.
y_pred_multiple = modelo_multiple.predict(X_multiple_test)

# Métrica R².
r2_multiple = r2_score(y_multiple_test, y_pred_multiple)
print(f"\nR²: {r2_multiple:.4f}")
print(f"Interpretación: El {r2_multiple*100:.2f}% de la variación en la calificación final")
print(f"es explicada por todas las variables")
print("\n")

# 2.3 Regresión logística.

print("2.3 REGRESIÓN LOGÍSTICA")
print("-" * 80)

# Crear y entrenar modelo.
modelo_logistic = LogisticRegression(max_iter=1000, random_state=42)
modelo_logistic.fit(X_train_clf, y_train_clf)

# Predicciones.
y_pred_logistic = modelo_logistic.predict(X_test_clf)
y_pred_proba = modelo_logistic.predict_proba(X_test_clf)

# Mostrar resultados con probabilidades.
print("Predicciones del modelo logístico:")
resultados_log = pd.DataFrame({
    'Alumno': df.loc[X_test_clf.index, 'Alumno'].values,
    'Real': df.loc[X_test_clf.index, 'Calificacion'].values,
    'Predicho': ['Sí' if p == 1 else 'No' for p in y_pred_logistic],
    'Prob_Aprobar': y_pred_proba[:, 1].round(4),
    'Prob_Reprobar': y_pred_proba[:, 0].round(4)
})
print(resultados_log)

# Precisión del modelo.
precision_log = accuracy_score(y_test_clf, y_pred_logistic)
print(f"\nPrecisión del modelo: {precision_log:.2%}")
print("\n")

# Sección 3: árbol de decisión y bosque aleatorio.

print("=" * 80)
print("SECCIÓN 3: ÁRBOL DE DECISIÓN Y BOSQUE ALEATORIO")
print("=" * 80)
print("\n")

# 3.1 Árbol de decisión.

print("3.1 ÁRBOL DE DECISIÓN")
print("-" * 80)

# Crear y entrenar modelo.
modelo_arbol = DecisionTreeClassifier(max_depth=3, random_state=42)
modelo_arbol.fit(X_train_clf, y_train_clf)

# Predicciones.
y_pred_arbol = modelo_arbol.predict(X_test_clf)

# Precisión.
precision_arbol = accuracy_score(y_test_clf, y_pred_arbol)
print(f"Precisión del Árbol de Decisión: {precision_arbol:.2%}")

# Importancia de características.
print("\nImportancia de características:")
importancia_arbol = pd.DataFrame({
    'Variable': X_train_clf.columns,
    'Importancia': modelo_arbol.feature_importances_
}).sort_values('Importancia', ascending=False)
print(importancia_arbol)
print("\n")

# 3.2 Bosque aleatorio.

print("3.2 BOSQUE ALEATORIO")
print("-" * 80)

# Crear y entrenar modelo.
modelo_forest = RandomForestClassifier(n_estimators=100, random_state=42)
modelo_forest.fit(X_train_clf, y_train_clf)

# Predicciones.
y_pred_forest = modelo_forest.predict(X_test_clf)

# Precisión.
precision_forest = accuracy_score(y_test_clf, y_pred_forest)
print(f"Precisión del Bosque Aleatorio: {precision_forest:.2%}")

# Importancia de características.
print("\nImportancia de características:")
importancia_forest = pd.DataFrame({
    'Variable': X_train_clf.columns,
    'Importancia': modelo_forest.feature_importances_
}).sort_values('Importancia', ascending=False)
print(importancia_forest)
print("\n")

# Sección 4: errores y matriz de confusión.

print("=" * 80)
print("SECCIÓN 4: CÁLCULO DE ERRORES Y MATRIZ DE CONFUSIÓN")
print("=" * 80)
print("\n")

# 4.1 Error absoluto medio (MAE).

print("4.1 ERROR ABSOLUTO MEDIO (MAE)")
print("-" * 80)

# Calcular MAE para regresión múltiple.
mae_multiple = mean_absolute_error(y_multiple_test, y_pred_multiple)
print(f"MAE del modelo múltiple: {mae_multiple:.4f}")
print(f"Interpretación: En promedio, el modelo se equivoca por {mae_multiple:.2f} puntos")
print("\n")

# 4.2 Error cuadrático medio (MSE).

print("4.2 ERROR CUADRÁTICO MEDIO (MSE)")
print("-" * 80)

# Calcular MSE para regresión múltiple.
mse_multiple = mean_squared_error(y_multiple_test, y_pred_multiple)
rmse_multiple = np.sqrt(mse_multiple)

print(f"MSE del modelo múltiple: {mse_multiple:.4f}")
print(f"RMSE del modelo múltiple: {rmse_multiple:.4f}")
print(f"Interpretación: El error cuadrático medio es de {mse_multiple:.2f} puntos²")
print("\n")

# 4.3 Matriz de confusión y métricas de clasificación.

print("4.3 MATRIZ DE CONFUSIÓN")
print("-" * 80)

# Usar el modelo de bosque aleatorio.
y_real = y_test_clf
y_pred = y_pred_forest

# Calcular matriz de confusión.
cm = confusion_matrix(y_real, y_pred)

print("Matriz de Confusión del Bosque Aleatorio:")
print("-" * 40)
print(f"{'':>12} {'Predicho Sí':>15} {'Predicho No':>15}")
print(f"{'Real Sí':>12} {cm[1][1]:>15} {cm[1][0]:>15}")
print(f"{'Real No':>12} {cm[0][1]:>15} {cm[0][0]:>15}")
print("-" * 40)

# Interpretación de la matriz.
print("\nInterpretación de la matriz:")
print(f"Verdaderos Positivos (Sí correctos):  {cm[1][1]}")
print(f"Falsos Negativos (Sí pero predijo No): {cm[1][0]}")
print(f"Falsos Positivos (No pero predijo Sí): {cm[0][1]}")
print(f"Verdaderos Negativos (No correctos):  {cm[0][0]}")

# Métricas derivadas.
print("\nMétricas derivadas:")
total = cm.sum()
accuracy = (cm[1][1] + cm[0][0]) / total
sensibilidad = cm[1][1] / (cm[1][1] + cm[1][0]) if (cm[1][1] + cm[1][0]) > 0 else 0
especificidad = cm[0][0] / (cm[0][0] + cm[0][1]) if (cm[0][0] + cm[0][1]) > 0 else 0
precision = cm[1][1] / (cm[1][1] + cm[0][1]) if (cm[1][1] + cm[0][1]) > 0 else 0
f1_score = 2 * (precision * sensibilidad) / (precision + sensibilidad) if (precision + sensibilidad) > 0 else 0

print(f"Exactitud (Accuracy): {accuracy:.2%}")
print(f"Sensibilidad (Recall): {sensibilidad:.2%}")
print(f"Especificidad: {especificidad:.2%}")
print(f"Precisión (Precision): {precision:.2%}")
print(f"F1-Score: {f1_score:.2%}")

# Reporte de clasificación completo.
print("\nReporte de clasificación completo:")
print(classification_report(y_real, y_pred, target_names=['No', 'Sí']))

print("\n" + "=" * 80)

# Sección 5: visualización de resultados.

print("\n" + "=" * 80)
print("SECCIÓN 5: VISUALIZACIÓN DE RESULTADOS")
print("=" * 80)

# Crear figura con 6 subgráficos.
fig, axes = plt.subplots(2, 3, figsize=(15, 10))

# Gráfico 1: comparación de R².
axes[0, 0].bar(['Simple', 'Múltiple'], [r2_simple, r2_multiple], 
               color=['blue', 'green'])
axes[0, 0].set_ylabel('R²')
axes[0, 0].set_title('Comparación de Modelos de Regresión')
axes[0, 0].set_ylim(0, 1.1)
for i, v in enumerate([r2_simple, r2_multiple]):
    axes[0, 0].text(i, v + 0.02, f'{v:.4f}', ha='center')

# Gráfico 2: valores reales vs predichos.
axes[0, 1].scatter(y_multiple_test, y_pred_multiple, color='green', s=100)
min_val = min(y_multiple_test.min(), y_pred_multiple.min())
max_val = max(y_multiple_test.max(), y_pred_multiple.max())
axes[0, 1].plot([min_val, max_val], [min_val, max_val], 'r--', linewidth=2)
axes[0, 1].set_xlabel('Valores Reales')
axes[0, 1].set_ylabel('Valores Predichos')
axes[0, 1].set_title('Regresión Múltiple: Real vs Predicho')
axes[0, 1].grid(True, alpha=0.3)

# Gráfico 3: comparación de clasificadores.
modelos = ['Logística', 'Árbol', 'Bosque']
precisiones = [precision_log, precision_arbol, precision_forest]
axes[0, 2].bar(modelos, precisiones, color=['orange', 'purple', 'green'])
axes[0, 2].set_ylabel('Precisión')
axes[0, 2].set_title('Comparación de Clasificadores')
axes[0, 2].set_ylim(0, 1.1)
for i, v in enumerate(precisiones):
    axes[0, 2].text(i, v + 0.02, f'{v:.2%}', ha='center')

# Gráfico 4: matriz de confusión (heatmap).
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[1, 0],
            xticklabels=['No', 'Sí'], yticklabels=['No', 'Sí'])
axes[1, 0].set_title('Matriz de Confusión - Bosque Aleatorio')
axes[1, 0].set_xlabel('Predicción')
axes[1, 0].set_ylabel('Real')

# Gráfico 5: importancia de características.
axes[1, 1].barh(importancia_forest['Variable'], importancia_forest['Importancia'],
                color='green')
axes[1, 1].set_xlabel('Importancia')
axes[1, 1].set_title('Importancia de Características\n(Bosque Aleatorio)')
axes[1, 1].grid(True, alpha=0.3)

# Gráfico 6: distribución de calificaciones.
axes[1, 2].hist(df['Final'], bins=10, color='skyblue', edgecolor='black')
axes[1, 2].axvline(df['Final'].mean(), color='red', linestyle='--', 
                   label=f'Media: {df["Final"].mean():.1f}')
axes[1, 2].set_xlabel('Calificación Final')
axes[1, 2].set_ylabel('Frecuencia')
axes[1, 2].set_title('Distribución de Calificaciones')
axes[1, 2].legend()
axes[1, 2].grid(True, alpha=0.3)

# Ajustar layout y guardar.
plt.tight_layout()
plt.savefig('smartutvt_analisis.png', dpi=300, bbox_inches='tight')
if 'agg' not in plt.get_backend().lower():
    plt.show()

print("\nGráficas guardadas en: smartutvt_analisis.png")
print("=" * 80)
print("\nANÁLISIS COMPLETO FINALIZADO")
print("=" * 80)