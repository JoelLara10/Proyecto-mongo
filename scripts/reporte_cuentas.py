    from pathlib import Path
    from dotenv import load_dotenv
    from decimal import Decimal

    ROOT = Path(__file__).resolve().parent.parent
    load_dotenv(ROOT / ".env")

    import sys
    sys.path.append(str(ROOT))

    from bd import get_db_connection  # noqa: E402


    def main():
        db = get_db_connection()

        # Colecciones
        atencion = db["atencion"]

        pipeline = [
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
            }},

            {"$project": {
                "_id": 0,
                "id_atencion": 1,
                "Id_exp": 1,
                "area": 1,
                "especialidad": 1,
                "fecha_ing": 1,
                "num_cama": 1,
                "paciente": {"$concat": ["$paciente.papell", " ", "$paciente.sapell", " ", "$paciente.nom_pac"]},
                "subtotal": 1
            }},

            {"$sort": {"fecha_ing": -1}}
        ]

        rows = list(atencion.aggregate(pipeline))

        IVA_RATE = Decimal("0.16")

        # Totales globales
        total_sub = Decimal("0")
        total_iva = Decimal("0")
        total_gen = Decimal("0")

        print("\n===============================================")
        print("   REPORTE: CUENTAS DE PACIENTES ACTIVOS")
        print("===============================================\n")

        if not rows:
            print("No hay cuentas activas (status ABIERTA).")
            return

        for r in rows:
            sub = Decimal(str(r.get("subtotal", 0) or 0))
            iva = sub * IVA_RATE
            tot = sub + iva

            total_sub += sub
            total_iva += iva
            total_gen += tot

            print(f"Atención: {r.get('id_atencion')}   Exp: {r.get('Id_exp')}   Cama: {r.get('num_cama')}")
            print(f"Paciente: {r.get('paciente')}")
            print(f"Área: {r.get('area')}   Especialidad: {r.get('especialidad')}")
            print(f"Subtotal: ${sub:,.2f}   IVA: ${iva:,.2f}   Total: ${tot:,.2f}")
            print("-" * 55)

        print("\n============== TOTALES GENERALES ==============")
        print(f"Subtotal general: ${total_sub:,.2f}")
        print(f"IVA general:      ${total_iva:,.2f}")
        print(f"TOTAL general:    ${total_gen:,.2f}")
        print("===============================================\n")


    if __name__ == "__main__":
        main()