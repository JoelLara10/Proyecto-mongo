from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.tree import export_text


# ==========================
# 🔧 PREPARAR DATOS
# ==========================
def preparar_datos(df):

    # 🔥 UMBRAL AJUSTADO (ANTES 50000)
    df["label"] = (df["ingreso"] > 1000).astype(int)

    X = df[["cantidad", "precio", "ingreso"]]
    y = df["label"]

    # 🚨 MUY POCOS DATOS
    if len(df) < 3:
        return None, None, None, None

    return train_test_split(X, y, test_size=0.2, random_state=42)


# ==========================
# 🌳 DECISION TREE
# ==========================
from sklearn.tree import export_text

def modelo_arbol(df):
    data = preparar_datos(df)
    if data[0] is None:
        return 0, "Sin datos suficientes para generar árbol"

    X_train, X_test, y_train, y_test = data

    if len(set(y_train)) < 2:
        return 0, "No hay suficientes clases para generar árbol"

    model = DecisionTreeClassifier(max_depth=4)
    model.fit(X_train, y_train)

    reglas = export_text(model, feature_names=["cantidad", "precio", "ingreso"])

    if not reglas.strip():
        reglas = "Árbol generado sin reglas visibles (pocos datos)"

    pred = model.predict(X_test)
    acc = accuracy_score(y_test, pred)

    return acc, reglas


# ==========================
# 🌲 RANDOM FOREST
# ==========================
def modelo_random_forest(df):
    data = preparar_datos(df)
    if data[0] is None:
        return 0

    X_train, X_test, y_train, y_test = data

    if len(set(y_train)) < 2:
        return 0

    model = RandomForestClassifier(n_estimators=100)
    model.fit(X_train, y_train)

    pred = model.predict(X_test)
    return accuracy_score(y_test, pred)


# ==========================
# 📍 KNN
# ==========================
def modelo_knn(df):
    data = preparar_datos(df)
    if data[0] is None:
        return 0

    X_train, X_test, y_train, y_test = data

    if len(X_train) < 2:
        return 0

    # 🔥 AJUSTE DINÁMICO DE K
    k = min(3, len(X_train))

    model = KNeighborsClassifier(n_neighbors=k)
    model.fit(X_train, y_train)

    pred = model.predict(X_test)
    return accuracy_score(y_test, pred)


# ==========================
# 📈 REGRESIÓN LOGÍSTICA
# ==========================
def modelo_logistico(df):
    data = preparar_datos(df)
    if data[0] is None:
        return 0

    X_train, X_test, y_train, y_test = data

    # 🚨 VALIDAR CLASES (CRÍTICO)
    if len(set(y_train)) < 2:
        return 0

    model = LogisticRegression(max_iter=1000)
    model.fit(X_train, y_train)

    pred = model.predict(X_test)
    return accuracy_score(y_test, pred)