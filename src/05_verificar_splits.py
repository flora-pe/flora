# src/05_verificar_splits.py
"""
Comprueba que ningún hash MD5 aparezca en más de un split.
"""
import hashlib
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SPLITS = RAIZ / "data" / "splits"
def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(8192), b""):
            h.update(c)
    return h.hexdigest()

vistos = defaultdict(list)
for split in ["train", "val", "test"]:
    for img in (SPLITS / split).rglob("*"):
        if img.is_file():
            vistos[md5(img)].append(split)

leaks = {h: s for h, s in vistos.items() if len(set(s)) > 1}
if leaks:
     print(f"❌ LEAKAGE detectado en {len(leaks)} hashes:")
     for h, s in list(leaks.items())[:10]:
        print(f"   {h[:10]} → {set(s)}")
else:
    print("✅ No hay leakage entre splits.")

for split in ["train", "val", "test"]:
    n = sum(1 for _ in (SPLITS / split).rglob("*") if _.is_file())
    print(f"   {split}: {n} imágenes")
