import os
import pandas as pd
from PIL import Image
from tqdm import tqdm

SRC_CSV = "splits/potato_splits.csv"
DST_CSV = "splits/potato_splits_256.csv"
DST_DIR = "data/processed_256"
SIZE = 256

df = pd.read_csv(SRC_CSV)
new_paths = []
for path, clase in tqdm(zip(df.path, df.clase), total=len(df)):
    name = os.path.splitext(os.path.basename(path))[0] + ".jpg"  # unifica .JPG -> .jpg
    out = os.path.join(DST_DIR, clase, name)
    if not os.path.exists(out):
        os.makedirs(os.path.dirname(out), exist_ok=True)
        Image.open(path).convert("RGB").resize((SIZE, SIZE), Image.LANCZOS).save(out, quality=95)
    new_paths.append(out)

df["path"] = new_paths
assert df.path.is_unique, "Hay nombres de archivo repetidos tras unificar extensiones"
df.to_csv(DST_CSV, index=False)
print(f"✅ {len(df)} imágenes en {DST_DIR} | CSV: {DST_CSV}")
