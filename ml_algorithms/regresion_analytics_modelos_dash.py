from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split

def ejecutar_modelos(df):

    X = df[["cantidad", "precio"]]
    y = df["ingreso"]

    resultados = {}

    # 🚨 SI HAY MUY POCOS DATOS
    if len(df) < 3:
        model = LinearRegression()
        model.fit(X, y)
        pred = model.predict(X)

        resultados["Lineal"] = r2_score(y, pred)
        resultados["Ridge"] = 0
        resultados["Lasso"] = 0

        return resultados, pred

    # 🔹 NORMAL (cuando ya tengas datos reales)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # LINEAL
    model = LinearRegression()
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    resultados["Lineal"] = r2_score(y_test, pred)

    # RIDGE
    ridge = Ridge(alpha=1.0)
    ridge.fit(X_train, y_train)
    pred_ridge = ridge.predict(X_test)
    resultados["Ridge"] = r2_score(y_test, pred_ridge)

    # LASSO
    lasso = Lasso(alpha=0.1)
    lasso.fit(X_train, y_train)
    pred_lasso = lasso.predict(X_test)
    resultados["Lasso"] = r2_score(y_test, pred_lasso)

    return resultados, pred