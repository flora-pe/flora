# src/00_explorar_potato.py
"""
Radiografía del dataset potato_agml antes de limpiarlo.
NO modifica archivos. Solo reporta.
"""
import sys
from collections import Counter, defaultdict
from pathlib import Path
from PIL import Image
from tqdm import tqdm

RAIZ = Path(__file__).resolve().parent.parent
DATASET = RAIZ / "data" / "potato_agml"
EXTENSIONES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}

if not DATASET.exists():
    print(f"❌ No existe {DATASET}")
    sys.exit(1)

# 1) Carpetas de primer nivel = clases candidatas
clases = sorted([p for p in DATASET.iterdir() if p.is_dir() and not p.name.startswith(".")])
print(f"📂 Clases detectadas ({len(clases)}):")
for c in clases:
    print(f"   - {c.name}")

# 2) Conteo por clase, extensión y resolución
conteo_clase = Counter()
conteo_ext = Counter()
resoluciones = Counter()
corruptas = []
min_lado = defaultdict(lambda: 10**9)
max_lado = defaultdict(int)

for clase_dir in clases:
    for img in tqdm(clase_dir.rglob("*"), desc=f"  {clase_dir.name}"):
        if not img.is_file() or img.name.startswith("."):
            continue
        if img.suffix.lower() not in EXTENSIONES:
            continue
        conteo_clase[clase_dir.name] += 1
        conteo_ext[img.suffix.lower()] += 1
        try:
            with Image.open(img) as im:
                im.verify()
            with Image.open(img) as im:
                w, h = im.size
                resoluciones[(w, h)] += 1
                min_lado[clase_dir.name] = min(min_lado[clase_dir.name], min(w, h))
                max_lado[clase_dir.name] = max(max_lado[clase_dir.name], max(w, h))
        except Exception as e:
            corruptas.append((str(img), str(e)))

# 3) Reporte
print("\n" + "=" * 60)
print("📊 REPORTE")
print("=" * 60)
total = sum(conteo_clase.values())
print(f"Total de imágenes: {total}")
print("\nPor clase:")
for c, n in conteo_clase.most_common():
    print(f"  - {c}: {n}  ({n/total*100:.1f}%)")
    print(f"      lado mín: {min_lado[c]}px, lado máx: {max_lado[c]}px")

print("\nPor extensión:")
for e, n in conteo_ext.most_common():
    print(f"  - {e}: {n}")
print(f"\nResoluciones distintas: {len(resoluciones)}")
for (w, h), n in resoluciones.most_common(10):
    print(f"  - {w}x{h}: {n}")

if corruptas:
    print(f"\n⚠️  Imágenes corruptas/ilegibles: {len(corruptas)}")
    for p, e in corruptas[:10]:
        print(f"  - {p}: {e}")
else:
    print("\n✅ No se detectaron imágenes corruptas.")

# 4) Alerta de desbalance
print("\n⚖️  Balance de clases:")
vals = list(conteo_clase.values())
if vals:
    ratio = max(vals) / max(min(vals), 1)
    print(f"   Ratio mayor/menor: {ratio:.2f}")
    if ratio > 3:
        print("   ⚠️  Desbalance fuerte: considera class weights o oversampling.")
    else:
        print("   ✅ Balance aceptable.")
