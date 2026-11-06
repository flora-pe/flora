import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

ROOT = Path("data/raw/potato_agml")
OUT = Path("reports")
OUT.mkdir(exist_ok=True)


def dhash(im, n=8):
    g = np.asarray(im.convert("L").resize((n + 1, n)), dtype=np.int16)
    return "".join("1" if b else "0" for b in (g[:, 1:] > g[:, :-1]).flatten())


# 1. Metadatos por imagen
rows = []
for f in sorted(ROOT.rglob("*")):
    if not f.is_file():
        continue
    r = {"clase": f.parent.name, "path": str(f), "ext": f.suffix.lower(), "kb": f.stat().st_size / 1024}
    try:
        with Image.open(f) as im:
            r.update(ancho=im.size[0], alto=im.size[1], modo=im.mode)
            im.draft("RGB", (128, 128))
            small = im.convert("RGB").resize((64, 64))
        a = np.asarray(small, dtype=np.float32)
        r.update(ok=True, brillo=a.mean(), verde=a[..., 1].mean() - a[..., [0, 2]].mean(), dhash=dhash(small))
    except Exception:
        r.update(ok=False)
    r["md5"] = hashlib.md5(f.read_bytes()).hexdigest()
    rows.append(r)
df = pd.DataFrame(rows)
ok = df[df["ok"]]

# 2. Por clase: volumen y posibles atajos
por_clase = ok.groupby("clase").agg(
    n=("path", "size"), ancho_med=("ancho", "median"), alto_med=("alto", "median"),
    kb_med=("kb", "median"), brillo=("brillo", "mean"), verde=("verde", "mean")).round(1)
por_clase["pct"] = (100 * por_clase["n"] / por_clase["n"].sum()).round(1)

# 3. Duplicados exactos y casi idénticos
dup_exact = df[df.duplicated("md5", keep=False)]
conf_exact = int((df.groupby("md5")["clase"].nunique() > 1).sum())
near = ok[ok.duplicated("dhash", keep=False)].sort_values("dhash")
conf_near = int((ok.groupby("dhash")["clase"].nunique() > 1).sum())
near[["dhash", "clase", "path"]].to_csv(OUT / "casi_duplicados_potato.csv", index=False)

tamanos = ok.groupby(["ancho", "alto"]).size().sort_values(ascending=False).head(5)

lineas = [
    "# EDA Potato Leaf Disease (AgML)",
    f"Imágenes: {len(df)} | corruptas: {int((~df['ok']).sum())} | clases: {df['clase'].nunique()}",
    f"Desbalance (máx/mín): {por_clase['n'].max()}/{por_clase['n'].min()} = {por_clase['n'].max() / por_clase['n'].min():.1f}x",
    f"Duplicados exactos: {len(dup_exact)} imágenes en {dup_exact['md5'].nunique()} grupos | con clase distinta: {conf_exact}",
    f"Casi idénticas (mismo dHash, incluye exactas): {len(near)} imágenes en {near['dhash'].nunique()} grupos | con clase distinta: {conf_near}",
    "Lista para revisar a mano: reports/casi_duplicados_potato.csv",
    "", "## Por clase (medianas de tamaño y peso; medias de brillo y verdor)", "```", por_clase.to_string(), "```",
    "", "## Tamaños más comunes (px)", "```", tamanos.to_string(), "```",
    "", "## Modos de color", "```", ok["modo"].value_counts().to_string(), "```",
    "", "## Extensiones", "```", df["ext"].value_counts().to_string(), "```",
]
reporte = "\n".join(lineas)
print(reporte)
(OUT / "eda_potato_agml.md").write_text(reporte, encoding="utf-8")

# 4. Hoja de muestra: 6 imágenes por clase
T, N = 170, 6
clases = list(por_clase.index)
hoja = Image.new("RGB", (N * T, len(clases) * (T + 22)), "white")
d = ImageDraw.Draw(hoja)
for fila, c in enumerate(clases):
    sub = ok[ok["clase"] == c]
    for col, p in enumerate(sub["path"].sample(min(N, len(sub)), random_state=42)):
        with Image.open(p) as im:
            im.draft("RGB", (T * 2, T * 2))
            im = im.convert("RGB")
            im.thumbnail((T, T))
            hoja.paste(im, (col * T, fila * (T + 22)))
    d.text((4, fila * (T + 22) + T + 5), c, fill="black")
hoja.save(OUT / "muestra_potato_agml.jpg", quality=90)
print("\nGuardado: reports/eda_potato_agml.md, muestra_potato_agml.jpg y casi_duplicados_potato.csv")
