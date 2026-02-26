from pathlib import Path
from dotenv import load_dotenv
import sys
import random
from datetime import datetime

# cargar .env
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
sys.path.append(str(ROOT))

from bd import get_db_connection  # noqa


def main():
    db = get_db_connection()

    pacientes_coll = db["pacientes"]
    atencion_coll = db["atencion"]
    cuenta_coll = db["cuenta_paciente"]

    nombres = ["Ana", "Luis", "María", "Carlos"]
    apellidos = ["García", "López", "Martínez", "Sánchez"]
    areas = ["Urgencias", "Hospitalización", "Pediatría", "UCI"]
    especialidades = ["Cardiología", "Medicina General", "Traumatología", "Neonatología"]

    insertados = 0

    for i in range(4):
        id_exp = random.randint(2000, 3000)
        id_atencion = random.randint(5000, 6000)
        id_cama = random.randint(1, 20)

        nombre = nombres[i]
        papell = random.choice(apellidos)
        sapell = random.choice(apellidos)

        # 1️ insertar paciente
        pacientes_coll.insert_one({
            "Id_exp": id_exp,
            "nom_pac": nombre,
            "papell": papell,
            "sapell": sapell
        })

        # 2️insertar atención ABIERTA
        atencion_coll.insert_one({
            "id_atencion": id_atencion,
            "Id_exp": id_exp,
            "id_cama": id_cama,
            "area": random.choice(areas),
            "especialidad": random.choice(especialidades),
            "fecha_ing": datetime.now(),
            "status": "ABIERTA"
        })

        # 3️ insertar cargos en cuenta_paciente
        for _ in range(random.randint(1, 3)):
            subtotal = random.randint(500, 2000)

            cuenta_coll.insert_one({
                "id_atencion": id_atencion,
                "concepto": "Servicio médico",
                "subtotal": subtotal
            })

        insertados += 1

    print(f" {insertados} pacientes de prueba insertados correctamente.")


if __name__ == "__main__":
    main()