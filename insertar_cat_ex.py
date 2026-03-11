# probar_login.py
from pymongo import MongoClient
import bcrypt


def probar_login():
    client = MongoClient('mongodb://localhost:27017/')
    db_name = input("Nombre de la base de datos: ")
    db = client[db_name]
    users_coll = db['users']

    print("\n=== PROBANDO LOGIN ===\n")

    pruebas = [
        ("admin", "admin"),
        ("medico", "medico"),
        ("enfermero", "enfermero"),
        ("admin", "wrongpass")
    ]

    for username, password in pruebas:
        print(f"Probando: {username} / {password}")

        user = users_coll.find_one({"username": username})

        if not user:
            print(f"  ✗ Usuario no encontrado")
            continue

        stored = user['password']
        print(f"  ✓ Usuario encontrado")
        print(f"  Tipo contraseña: {type(stored)}")

        try:
            password_bytes = password.encode('utf-8')

            if bcrypt.checkpw(password_bytes, stored):
                print(f"  ✓ LOGIN EXITOSO!")
            else:
                print(f"  ✗ Contraseña incorrecta")
        except Exception as e:
            print(f"  ✗ Error: {e}")

        print()


if __name__ == "__main__":
    probar_login()