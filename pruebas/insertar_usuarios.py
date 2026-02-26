import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))
    )
)

from bd import get_db_connection
import bcrypt


db = get_db_connection()
users = db['users']

users.insert_many([
    {
        "id": 1,
        "username": "admin",
        "password": bcrypt.hashpw("admin123".encode("utf-8"), bcrypt.gensalt()),
        "role": "admin"
    },
    {
        "id": 2,
        "username": "medico",
        "password": bcrypt.hashpw("medico123".encode("utf-8"), bcrypt.gensalt()),
        "role": "medico"
    },
    {
        "id": 3,
        "username": "enfermero",
        "password": bcrypt.hashpw("enfermero123".encode("utf-8"), bcrypt.gensalt()),
        "role": "enfermero"
    }
])

print("Usuarios creados correctamente")