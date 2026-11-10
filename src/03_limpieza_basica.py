# src/03_limpieza_basica.py
"""
Elimina (mueve) imágenes corruptas, <64px o con extensiones raras.
Normaliza todas las extensiones a .jpg (opcional, comentado).
"""
import shutil
import sys
from pathlib import Path
from PIL import Image
from tqdm import tqdm

RAIZ = Path(__file__).resolve().parent.parent
DATASET = RAIZ / "data" / "potato_agml"
DESCARTADOS = RAIZ / "data" / "potato_agml_descartados" / "limpieza"
LADO_MIN = 64
EXTENSIONES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}

DESCARTADOS.mkdir(parents=True, exist_ok=True)
motivos = {"corrupta": [], "diminuta": [], "formato": []}

for clase_dir in sorted(DATASET.iterdir()):
    if not clase_dir.is_dir() or clase_dir.name.startswith("."):
        continue
    for img in tqdm(list(clase_dir.rglob("*")), desc=clase_dir.name):
        if not img.is_file() or img.name.startswith("."):
            continue
        if img.suffix.lower() not in EXTENSIONES:
            motivos["formato"].append(img)
            continue
        try:
            with Image.open(img) as im:
                im.verify()
            with Image.open(img) as im:
                w, h = im.size
            if min(w, h) < LADO_MIN:
                motivos["diminuta"].append(img)
        except Exception:
            motivos["corrupta"].append(img)

def mover(lista, motivo):
    for img in lista:
        rel = img.relative_to(DATASET)
        dst = DESCARTADOS / motivo / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(img), str(dst))

for motivo, lista in motivos.items():
    if lista:
        mover(lista, motivo)
        print(f"  {motivo}: {len(lista)} archivos movidos")
print(f"\n✅ Limpieza completa. Revisión en {DESCARTADOS}")
