from pathlib import Path
from dotenv import load_dotenv
from decimal import Decimal
import sys
import random

# cargar .env
ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
sys.path.append(str(ROOT))

from bd import get_db_connection  # noqa


IVA_RATE = Decimal("0.16")


def pipeline_cuentas_activas():
    return [
        {"$match": {"status": "ABIERTA"}},

        {"$lookup": {
            "from": "pacientes",
            "localField": "Id_exp",
            "foreignField": "Id_exp",
            "as": "paciente"
        }},
        {"$unwind": "$paciente"},

        {"$lookup": {
            "from": "camas",
            "localField": "id_cama",
            "foreignField": "id_cama",
            "as": "cama"
        }},
        {"$unwind": {"path": "$cama", "preserveNullAndEmptyArrays": True}},

        {"$lookup": {
            "from": "cuenta_paciente",
            "localField": "id_atencion",
            "foreignField": "id_atencion",
            "as": "items"
        }},

        {"$addFields": {
            "num_cama": {"$ifNull": ["$cama.numero", "Sin cama"]},
            "subtotal": {"$ifNull": [{"$sum": "$items.subtotal"}, 0]},
            "paciente_nombre": {
                "$concat": ["$paciente.papell", " ", "$paciente.sapell", " ", "$paciente.nom_pac"]
            }
        }},

        {"$project": {
            "_id": 0,
            "id_atencion": 1,
            "Id_exp": 1,
            "paciente": "$paciente_nombre",
            "area": 1,
            "especialidad": 1,
            "num_cama": 1,
            "fecha_ing": 1,
            "subtotal": 1
        }}
    ]


def upsert_cuenta(cuenta_coll, r):
    sub = Decimal(str(r.get("subtotal", 0) or 0))
    iva = sub * IVA_RATE
    total = sub + iva

    doc = {
        "id_atencion": r["id_atencion"],
        "Id_exp": r["Id_exp"],
        "paciente": r["paciente"],
        "area": r.get("area"),
        "especialidad": r.get("especialidad"),
        "num_cama": r.get("num_cama"),
        "fecha_ing": r.get("fecha_ing"),
        "subtotal": float(sub),
        "iva": float(iva),
        "total": float(total),
        "anticipos": 0
    }

    cuenta_coll.update_one(
        {"id_atencion": r["id_atencion"]},
        {"$set": doc},
        upsert=True
    )


def main():
    db = get_db_connection()
    cuenta_coll = db["cuenta_pacientes"]

    # 1) Traer cuentas reales (ABIERTAS)
    rows = list(db["atencion"].aggregate(pipeline_cuentas_activas()))

    if not rows:
        print("No hay atenciones ABIERTAS para sincronizar.")
        return

    # 2) Sincronizar TODAS (reales)
    for r in rows:
        upsert_cuenta(cuenta_coll, r)

    print(f" {len(rows)} cuentas reales sincronizadas en 'cuenta_pacientes'.")

    # 3) Elegir 5 REALES al azar (sin inventar)
    sample_size = min(5, len(rows))
    seleccion = random.sample(rows, sample_size)

    print(f"\n Mostrando {sample_size} cuentas REALES aleatorias:\n")

    for r in seleccion:
        sub = Decimal(str(r.get("subtotal", 0) or 0))
        iva = sub * IVA_RATE
        total = sub + iva

        print(f"Atención: {r['id_atencion']} | Exp: {r['Id_exp']} | Cama: {r.get('num_cama')}")
        print(f"Paciente: {r.get('paciente')}")
        print(f"Área: {r.get('area')} | Especialidad: {r.get('especialidad')}")
        print(f"Subtotal: ${sub:,.2f} | IVA: ${iva:,.2f} | Total: ${total:,.2f}")
        print("-" * 60)


if __name__ == "__main__":
    main()