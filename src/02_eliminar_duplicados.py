# src/02_eliminar_duplicados.py
"""
Borra duplicados según los reportes CSV de la fase 01.
- Mueve los descartados a data/potato_agml_descartados/ (no borra).
- Conserva siempre el 'es_original=True' de cada grupo.
"""
import csv
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATASET = RAIZ / "data" / "potato_agml"
DESCARTADOS = RAIZ / "data" / "potato_agml_descartados"
REPORTES = RAIZ / "data" / "reportes"
if not (REPORTES / "duplicados_casi.csv").exists():
    print("❌ Ejecuta primero src/01_detectar_duplicados.py")
    sys.exit(1)

DESCARTADOS.mkdir(parents=True, exist_ok=True)

def mover_descartados(csv_path: Path):
    movidos = 0
    with open(csv_path) as f:
        for row in csv.DictReader(f):
            if row["es_original"] == "True":
                continue
            src = Path(row["ruta"])
            if not src.exists():
                continue
            rel = src.relative_to(DATASET)
            dst = DESCARTADOS / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            movidos += 1
    return movidos

print("Moviendo duplicados exactos...")
n1 = mover_descartados(REPORTES / "duplicados_exactos.csv")
print(f"  → {n1} archivos movidos")

print("Moviendo casi-duplicados...")
n2 = mover_descartados(REPORTES / "duplicados_casi.csv")
print(f"  → {n2} archivos movidos")

print(f"\n✅ Total descartados: {n1 + n2}")
print(f"   Revisión en: {DESCARTADOS}")
print("   Si algo se movió por error, puedes recuperarlo desde ahí.")
