"""Limpia duplicados y genera un split estratificado reproducible (70/15/15)."""
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

ROOT = Path("data/raw/potato_agml")
DUPS = Path("reports/casi_duplicados_potato.csv")
OUT = Path("splits")
OUT.mkdir(exist_ok=True)
SEED = 42

df = pd.DataFrame({"path": sorted(str(p) for p in ROOT.rglob("*") if p.suffix.lower() == ".jpg")})
df["clase"] = df["path"].map(lambda p: Path(p).parent.name)
assert len(df) == 3076, f"Esperaba 3076 imágenes y hay {len(df)}. Corre ./scripts/download_data.sh"

# Grupos contradictorios: fuera completos. Duplicados normales: se queda una copia.
excl = []
for _, g in pd.read_csv(DUPS).groupby("dhash"):
    g = g.sort_values("path")
    if g["clase"].nunique() > 1:
        excl += [(p, "etiqueta contradictoria") for p in g["path"]]
    else:
        excl += [(p, "duplicado") for p in g["path"].iloc[1:]]
excl = pd.DataFrame(excl, columns=["path", "motivo"])
limpio = df[~df["path"].isin(excl["path"])]

train, temp = train_test_split(limpio, test_size=0.30, stratify=limpio["clase"], random_state=SEED)
val, test = train_test_split(temp, test_size=0.50, stratify=temp["clase"], random_state=SEED)
splits = pd.concat([train.assign(split="train"), val.assign(split="val"),
                    test.assign(split="test")]).sort_values("path")

splits.to_csv(OUT / "potato_splits.csv", index=False)
excl.to_csv(OUT / "excluidas.csv", index=False)

n_dup = int((excl["motivo"] == "duplicado").sum())
print(f"Excluidas: {len(excl)} ({n_dup} duplicados, {len(excl) - n_dup} por etiqueta contradictoria)")
print(f"Quedan: {len(splits)}\n")
tabla = pd.crosstab(splits["clase"], splits["split"], margins=True, margins_name="total")
print(tabla[["train", "val", "test", "total"]].to_string())
