# ============================================
# ECO MART - ANÁLISIS COMPLETO
# EJECUTAR TODO EN UN SOLO ARCHIVO .py
# ============================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_absolute_error

# OBTENER LA RUTA DONDE ESTÁ EL SCRIPT
ruta_script = os.path.dirname(os.path.abspath(__file__))
print(f"El script está en: {ruta_script}")

# CREAR CARPETA PARA RESULTADOS DENTRO DE LA MISMA CARPETA DEL SCRIPT
carpeta_resultados = os.path.join(ruta_script, "resultados_ecomart")
if not os.path.exists(carpeta_resultados):
    os.makedirs(carpeta_resultados)
    print(f"Carpeta creada: '{carpeta_resultados}'")
else:
    print(f"Usando carpeta existente: '{carpeta_resultados}'")

print("="*50)
print("ECO MART - SISTEMA DE ANÁLISIS DE INVENTARIO")
print("="*50)

# 1. CREAR DATAFRAME
datos = {
    'Producto': ['Leche', 'Carne Res', 'Yogurt', 'Pollo', 'Queso', 'Pan', 'Carne Cerdo', 'Mantequilla', 'Crema'],
    'Categoria': ['Lácteos', 'Carnes', 'Lácteos', 'Carnes', 'Lácteos', 'Panadería', 'Carnes', 'Lácteos', 'Lácteos'],
    'Ventas_Totales': [120, 85, np.nan, 60, 150, 200, np.nan, 90, 110],
    'Stock_Disponible': [10, 8, 20, 12, 5, 40, 14, 9, 13],
    'Precio_Unitario': [1.2, 5.5, 0.9, 3.2, 2.1, 0.8, 4.8, 1.5, 1.3]
}

df = pd.DataFrame(datos)
print("\n DataFrame creado")

# 2. LIMPIEZA DE NULOS
mediana = df['Ventas_Totales'].median()
df['Ventas_Totales'] = df['Ventas_Totales'].fillna(mediana)
print(f" Nulos reemplazados con mediana: {mediana}")

# 3. CREAR NUEVAS COLUMNAS
df['Valor_Inventario'] = df['Stock_Disponible'] * df['Precio_Unitario']

scaler = MinMaxScaler()
df[['Ventas_Norm', 'Stock_Norm']] = scaler.fit_transform(df[['Ventas_Totales', 'Stock_Disponible']])

df['Riesgo'] = np.where(
    (df['Stock_Disponible'] < 10) & (df['Ventas_Totales'] > 100), 'Alto',
    np.where(df['Stock_Disponible'] < 15, 'Medio', 'Bajo')
)

# 4. ANÁLISIS EXPLORATORIO
print("\n" + "="*50)
print("ANÁLISIS EXPLORATORIO")
print("="*50)

producto_caro = df.loc[df['Precio_Unitario'].idxmax()]
print(f"1. Producto más caro: {producto_caro['Producto']} - ${producto_caro['Precio_Unitario']:.2f}")

mayor_stock = df.loc[df['Stock_Disponible'].idxmax()]
print(f"2. Mayor inventario: {mayor_stock['Producto']} - {mayor_stock['Stock_Disponible']} unidades")

mayor_valor = df.loc[df['Valor_Inventario'].idxmax()]
print(f"3. Mayor valor económico: {mayor_valor['Producto']} - ${mayor_valor['Valor_Inventario']:.2f}")

# 4. Categoría con más productos
categoria_top = df['Categoria'].value_counts().idxmax()
print("4. Categoría con más productos:")
print(f"   {categoria_top}\n")

# 5. MODELO DE REGRESIÓN
X = df[['Stock_Disponible', 'Precio_Unitario']]
y = df['Ventas_Totales']

modelo = LinearRegression()
modelo.fit(X, y)
df['Ventas_Predichas'] = modelo.predict(X)

print(f"\n Modelo entrenado - R²: {r2_score(y, df['Ventas_Predichas']):.2%}")
print(f"   Error absoluto medio: {mean_absolute_error(y, df['Ventas_Predichas']):.2f}")

# 6. GUARDAR RESULTADOS (dentro de la subcarpeta)
df.to_csv(os.path.join(carpeta_resultados, 'resultado_final.csv'), index=False)
df.to_excel(os.path.join(carpeta_resultados, 'resultado_final.xlsx'), index=False)
df.to_json(os.path.join(carpeta_resultados, 'resultado_final.json'), orient='records', indent=2)

# Guardar solo productos en riesgo
alerta = df[df['Riesgo'].isin(['Alto', 'Medio'])]
alerta.to_csv(os.path.join(carpeta_resultados, 'alerta_desabasto.csv'), index=False)

print(f"\n Archivos guardados en carpeta: '{carpeta_resultados}'")
print(f"   - resultado_final.csv")
print(f"   - resultado_final.xlsx")
print(f"   - resultado_final.json")
print(f"   - alerta_desabasto.csv")

# 7. GENERAR GRÁFICO
plt.figure(figsize=(10, 6))
plt.bar(df['Producto'], df['Stock_Disponible'], color='skyblue', alpha=0.7, label='Stock Actual')
plt.plot(df['Producto'], df['Ventas_Predichas'], 'ro-', label='Ventas Predichas', linewidth=2)
plt.xticks(rotation=45, ha='right')
plt.xlabel('Producto')
plt.ylabel('Unidades')
plt.title('Análisis de Inventario - Eco Mart')
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()

# Guardar gráfico dentro de la subcarpeta
ruta_grafico = os.path.join(carpeta_resultados, 'analisis_ecomart.png')
plt.savefig(ruta_grafico, dpi=150)
plt.show()
print(f" Gráfico guardado: {carpeta_resultados}/analisis_ecomart.png")

# 8. GUARDAR ESTADÍSTICAS EN ARCHIVO DE TEXTO
with open(os.path.join(carpeta_resultados, 'estadisticas.txt'), 'w', encoding='utf-8') as f:
    f.write("="*50 + "\n")
    f.write("RESUMEN ESTADÍSTICO - ECO MART\n")
    f.write("="*50 + "\n\n")
    
    f.write(f"Total de productos: {len(df)}\n")
    f.write(f"Categorías: {df['Categoria'].nunique()}\n")
    f.write(f"Stock total: {df['Stock_Disponible'].sum()} unidades\n")
    f.write(f"Valor total inventario: ${df['Valor_Inventario'].sum():.2f}\n\n")
    
    f.write("Productos por categoría:\n")
    for cat, count in df['Categoria'].value_counts().items():
        f.write(f"  - {cat}: {count} productos\n")
    
    f.write(f"\nR² del modelo: {r2_score(y, df['Ventas_Predichas']):.2%}\n")
    f.write(f"Error absoluto medio: {mean_absolute_error(y, df['Ventas_Predichas']):.2f}\n")

print(f" Estadísticas guardadas: {carpeta_resultados}/estadisticas.txt")

print("\n" + "="*50)
print("PROCESO COMPLETADO EXITOSAMENTE")
print("="*50)

# Mostrar resultados finales
print("\n DATAFRAME FINAL:")
print(df[['Producto', 'Categoria', 'Stock_Disponible', 'Ventas_Totales', 'Ventas_Predichas', 'Riesgo']].round(2))

# Mostrar ubicación de los archivos
print(f"\n Todos los archivos generados están en:")
print(f"   {carpeta_resultados}")