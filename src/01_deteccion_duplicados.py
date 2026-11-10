# src/01_detectar_duplicados.py
"""
Detecta duplicados exactos (MD5) y casi-duplicados (pHash) en potato_agml.
NO borra nada: genera un reporte CSV para que revises antes de decidir.

Requiere: pip install imagehash Pillow tqdm
"""
import csv
import hashlib
import sys
from collections import defaultdict
from pathlib import Path
from PIL import Image
from tqdm import tqdm
import imagehash

RAIZ = Path(__file__).resolve().parent.parent
DATASET = RAIZ / "data" / "potato_agml"
REPORTES = RAIZ / "data" / "reportes"
REPORTES.mkdir(parents=True, exist_ok=True)

EXTENSIONES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
UMBRAL_PHASH = 6   # distancia Hamming <= 6 → casi-duplicado (ajustable)

def md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

# 1) Recolectar imágenes
imagenes = []
for clase_dir in sorted(DATASET.iterdir()):
    if not clase_dir.is_dir() or clase_dir.name.startswith("."):
        continue
    for img in clase_dir.rglob("*"):
        if img.is_file() and not img.name.startswith(".") and img.suffix.lower() in EXTENSIONES:
            imagenes.append((clase_dir.name, img))

print(f"Total imágenes: {len(imagenes)}")

# 2) Duplicados exactos por MD5
print("\n🔎 Calculando MD5...")
por_md5 = defaultdict(list)
for clase, img in tqdm(imagenes):
    por_md5[md5(img)].append((clase, img))

duplicados_exactos = {h: v for h, v in por_md5.items() if len(v) > 1}

# 3) Duplicados perceptuales por pHash (dentro de cada clase; cruzado es más caro)
print("\n🔎 Calculando pHash...")
hashes = []
for clase, img in tqdm(imagenes):
    try:
        with Image.open(img) as im:
            ph = imagehash.phash(im)
        hashes.append((clase, img, ph))
    except Exception as e:
        print(f"  ⚠️  {img}: {e}")

duplicados_casi = []
vistos = set()
# Comparación dentro de la misma clase (los duplicados entre clases distintas
# también importan, pero primero resolvemos los intra-clase)

for i in tqdm(range(len(hashes)), desc="  comparando"):
    c1, p1, h1 = hashes[i]
    if str(p1) in vistos:
        continue
    grupo = [(c1, p1)]
    for j in range(i + 1, len(hashes)):
        c2, p2, h2 = hashes[j]
        if c2 != c1:
            continue
        if h1 - h2 <= UMBRAL_PHASH:
            grupo.append((c2, p2))
            vistos.add(str(p2))
    if len(grupo) > 1:
        duplicados_casi.append(grupo)

# 4) Reportes CSV
csv_exactos = REPORTES / "duplicados_exactos.csv"
with open(csv_exactos, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["md5", "clase", "ruta", "es_original"])
    for h, grupo in duplicados_exactos.items():
        for idx, (clase, img) in enumerate(grupo):
            w.writerow([h, clase, str(img), idx == 0])

csv_casi = REPORTES / "duplicados_casi.csv"
with open(csv_casi, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["grupo_id", "clase", "ruta", "es_original"])
    for gid, grupo in enumerate(duplicados_casi):
        for idx, (clase, img) in enumerate(grupo):
            w.writerow([gid, clase, str(img), idx == 0])

# 5) Resumen
n_exactos_extra = sum(len(v) - 1 for v in duplicados_exactos.values())
n_casi_extra = sum(len(g) - 1 for g in duplicados_casi)
print("\n" + "=" * 60)
print("📊 RESUMEN DE DUPLICADOS")
print("=" * 60)
print(f"Grupos de duplicados exactos: {len(duplicados_exactos)}  "
      f"(sobran {n_exactos_extra} archivos)")
print(f"Grupos de casi-duplicados:    {len(duplicados_casi)}  "
      f"(sobran {n_casi_extra} archivos)")
print(f"\n📄 Reportes guardados en: {REPORTES}")
print("   Revisa los CSV antes de borrar nada.")
