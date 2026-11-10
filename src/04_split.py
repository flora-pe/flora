# src/04_split.py
"""
Split estratificado 70/15/15 con prefijo Bacteria__/Fungi__ como etiqueta.
Genera data/splits/{train,val,test}/<clase>/*.jpg
"""
import random
import shutil
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DATASET = RAIZ / "data" / "potato_agml"
SPLITS = RAIZ / "data" / "splits"
SEED = 42
PROPORCIONES = (0.70, 0.15, 0.15)

if SPLITS.exists():
    r = input(f"⚠️  {SPLITS} existe. ¿Borrar y regenerar? [s/N]: ").strip().lower()
    if r == "s":
        shutil.rmtree(SPLITS)
    else:
        sys.exit(0)

random.seed(SEED)

# 1) Agrupar por clase
por_clase = defaultdict(list)
for clase_dir in DATASET.iterdir():
    if not clase_dir.is_dir() or clase_dir.name.startswith("."):
        continue
    for img in clase_dir.rglob("*"):
        if img.is_file() and not img.name.startswith("."):
            por_clase[clase_dir.name].append(img)

# 2) Split estratificado
for clase, imgs in por_clase.items():
    random.shuffle(imgs)
    n = len(imgs)
    n_train = int(n * PROPORCIONES[0])
    n_val = int(n * PROPORCIONES[1])
    particiones = {
        "train": imgs[:n_train],
        "val": imgs[n_train:n_train + n_val],
        "test": imgs[n_train + n_val:],
    }
    print(f"\n📁 {clase} ({n} imgs)")
    for split, lista in particiones.items():
        destino_dir = SPLITS / split / clase
        destino_dir.mkdir(parents=True, exist_ok=True)
        for img in lista:
            shutil.copy2(img, destino_dir / img.name)
        print(f"   {split}: {len(lista)}")

print(f"\n✅ Splits en {SPLITS}")
