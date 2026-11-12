import importlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import tensorflow as tf
from PIL import Image

d = importlib.import_module("06_dataset_tf")
model = tf.keras.models.load_model("models/effnetb0_ft_opcion_B.keras")

probs = model.predict(d.val_ds)
df = d.df_val.copy().reset_index(drop=True)
df["pred"] = [d.classes[i] for i in probs.argmax(axis=1)]
df["conf"] = probs.max(axis=1)

par = ["Fungi", "Pest"]
errs = (df[(df.clase != df.pred) & df.clase.isin(par) & df.pred.isin(par)]
        .sort_values("conf", ascending=False))
errs.to_csv("reports/errores_fungi_pest.csv", index=False)
print(f"Errores Fungi <-> Pest en val: {len(errs)}")

n = min(len(errs), 24)
cols = 6
rows = int(np.ceil(n / cols))
fig, axes = plt.subplots(rows, cols, figsize=(cols * 3, rows * 3.3))
for ax in np.atleast_1d(axes).flat:
    ax.axis("off")
for ax, (_, r) in zip(np.atleast_1d(axes).flat, errs.head(n).iterrows()):
    ax.imshow(Image.open(r.path))
    ax.set_title(f"real: {r.clase}\npred: {r.pred} ({r.conf:.0%})", fontsize=9)

plt.tight_layout()
plt.savefig("reports/errores_fungi_pest.png", dpi=100)
print("✅ reports/errores_fungi_pest.png")
