# ============================================================
# PROYECTO: SmartUTVT
# ASIGNATURA: Extracción de conocimiento en Bases de Datos
# OBJETIVO:
# 1. Predecir la calificación final de los estudiantes
# 2. Identificar estudiantes en riesgo de reprobar
# ============================================================


# ============================================================
# SECCIÓN 1: IMPORTACIÓN DE LIBRERÍAS
# ============================================================
import pandas as pd
import numpy as np

from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier

from sklearn.metrics import mean_absolute_error, mean_squared_error, confusion_matrix


# ============================================================
# SECCIÓN 2: CREACIÓN Y EXPLORACIÓN DEL DATAFRAME
# ============================================================

# Datos proporcionados por la universidad
data = {
    'Asistencia': [95, 80, 60, 50, 85, 40, 90, 55],
    'Horas_Estudio': [5, 4, 2, 1, 4, 1, 5, 2],
    'Tareas': [10, 8, 6, 4, 9, 3, 10, 5],
    'Promedio_Parcial': [92, 80, 65, 50, 88, 45, 94, 55],
    'Calificacion_Final': [95, 82, 60, 45, 90, 40, 96, 50],
    'Aprueba': [1, 1, 0, 0, 1, 0, 1, 0]  # 1 = Sí, 0 = No
}

df = pd.DataFrame(data)

# Mostrar datos
print("DATAFRAME:")
print(df)

print("\nESTADÍSTICAS DESCRIPTIVAS:")
print(df.describe())

# INTERPRETACIÓN:
# Se observa que valores altos de asistencia, tareas y promedio parcial
# están asociados a calificaciones finales altas.


# ============================================================
# SECCIÓN 3: REGRESIÓN LINEAL SIMPLE
# ============================================================

# PROCEDIMIENTO MATEMÁTICO:
# y = β0 + β1 * x
# donde:
# y = Calificación Final
# x = Promedio Parcial
# β0 = intercepto
# β1 = coeficiente de la variable

X_simple = df[['Promedio_Parcial']]
y = df['Calificacion_Final']

modelo_rl_simple = LinearRegression()
modelo_rl_simple.fit(X_simple, y)

print("\nREGRESIÓN LINEAL SIMPLE")
print("Coeficiente (β1):", modelo_rl_simple.coef_[0])
print("Intercepto (β0):", modelo_rl_simple.intercept_)

# INTERPRETACIÓN:
# Por cada punto que aumenta el promedio parcial,
# la calificación final aumenta aproximadamente β1 puntos.


# ============================================================
# SECCIÓN 4: REGRESIÓN LINEAL MÚLTIPLE
# ============================================================

# PROCEDIMIENTO MATEMÁTICO:
# y = β0 + β1*x1 + β2*x2 + β3*x3 + β4*x4

X_multi = df[['Asistencia', 'Horas_Estudio', 'Tareas', 'Promedio_Parcial']]
y = df['Calificacion_Final']

modelo_rl_multiple = LinearRegression()
modelo_rl_multiple.fit(X_multi, y)

print("\nREGRESIÓN LINEAL MÚLTIPLE")
print("Coeficientes:", modelo_rl_multiple.coef_)
print("Intercepto:", modelo_rl_multiple.intercept_)

# INTERPRETACIÓN:
# La calificación final es resultado de la combinación
# de asistencia, horas de estudio, tareas y promedio parcial.


# ============================================================
# SECCIÓN 5: REGRESIÓN LOGÍSTICA (APROBAR / REPROBAR)
# ============================================================

# PROCEDIMIENTO MATEMÁTICO:
# P(y=1) = 1 / (1 + e^-(β0 + β1x1 + ... + βnxn))

X_log = df[['Asistencia', 'Horas_Estudio', 'Tareas', 'Promedio_Parcial']]
y_log = df['Aprueba']

modelo_logistico = LogisticRegression()
modelo_logistico.fit(X_log, y_log)

pred_log = modelo_logistico.predict(X_log)

print("\nREGRESIÓN LOGÍSTICA")
print("Predicciones aprobar/reprobar:", pred_log)

# INTERPRETACIÓN:
# El modelo predice la probabilidad de que un alumno apruebe.


# ============================================================
# SECCIÓN 6: ÁRBOL DE DECISIÓN
# ============================================================

arbol = DecisionTreeClassifier()
arbol.fit(X_log, y_log)

pred_arbol = arbol.predict(X_log)

print("\nÁRBOL DE DECISIÓN")
print("Predicciones:", pred_arbol)

# INTERPRETACIÓN:
# El árbol crea reglas lógicas basadas en las variables
# para decidir si un alumno aprueba o no.


# ============================================================
# SECCIÓN 7: BOSQUE ALEATORIO
# ============================================================

bosque = RandomForestClassifier(n_estimators=100)
bosque.fit(X_log, y_log)

pred_bosque = bosque.predict(X_log)

print("\nBOSQUE ALEATORIO")
print("Predicciones:", pred_bosque)

# INTERPRETACIÓN:
# Combina múltiples árboles para mejorar la precisión
# y reducir el sobreajuste.


# ============================================================
# SECCIÓN 8: MÉTRICAS DE EVALUACIÓN
# ============================================================

# PREDICCIÓN REGRESIÓN LINEAL
predicciones = modelo_rl_multiple.predict(X_multi)

# PROCEDIMIENTO MATEMÁTICO MAE:
# MAE = (1/n) * Σ |y_real - y_pred|

mae = mean_absolute_error(y, predicciones)

# PROCEDIMIENTO MATEMÁTICO MSE:
# MSE = (1/n) * Σ (y_real - y_pred)^2

mse = mean_squared_error(y, predicciones)

print("\nMÉTRICAS DE ERROR")
print("MAE:", mae)
print("MSE:", mse)

# INTERPRETACIÓN:
# MAE indica el error promedio.
# MSE penaliza más los errores grandes.


# ============================================================
# SECCIÓN 9: MATRIZ DE CONFUSIÓN
# ============================================================

matriz = confusion_matrix(y_log, pred_log)

print("\nMATRIZ DE CONFUSIÓN")
print(matriz)

# INTERPRETACIÓN:
# Muestra verdaderos positivos, falsos positivos,
# verdaderos negativos y falsos negativos.


# ============================================================
# CONCLUSIÓN FINAL
# ============================================================

# La regresión lineal múltiple es adecuada para predecir calificaciones.
# La regresión logística, árboles y bosques son ideales para
# clasificar alumnos en riesgo de reprobar.