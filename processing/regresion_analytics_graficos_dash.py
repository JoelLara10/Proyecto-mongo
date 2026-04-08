import plotly.express as px
import pandas as pd

# 🔹 DISPERSIÓN
def grafica_dispersion(df):

    fig = px.scatter(
        df,
        x="cantidad",
        y="ingreso",
        color="producto",
        size="precio",
        title="Cantidad vs Ingreso"
    )

    return fig


# 🔹 DISTRIBUCIÓN
def grafica_distribucion(df):

    fig = px.histogram(
        df,
        x="ingreso",
        color="producto",
        nbins=20,
        title="Distribución de Ingresos"
    )

    return fig


# 🔹 PRECIO VS INGRESO
def grafica_precio_vs_ingreso(df):

    fig = px.scatter(
        df,
        x="precio",
        y="ingreso",
        color="producto",
        trendline="ols",
        title="Precio vs Ingreso"
    )

    return fig


# 🔹 MODELOS
def grafica_modelos(resultados):

    df_modelos = pd.DataFrame(
        list(resultados.items()),
        columns=["Modelo", "Score"]
    )

    fig = px.bar(
        df_modelos,
        x="Modelo",
        y="Score",
        color="Modelo",
        title="Comparación de Modelos"
    )

    return fig