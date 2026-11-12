import os
import numpy as np
import pandas as pd
import tensorflow as tf
from sklearn.utils.class_weight import compute_class_weight

# ---------- Configuración ----------
IMG_SIZE, BATCH, SEED = 224, 32, 42
AUTOTUNE = tf.data.AUTOTUNE
CSV_PATH = "splits/potato_splits_256.csv"

# ---------- 1. Cargar CSV de splits ----------
df = pd.read_csv(CSV_PATH)  # columnas: path, clase, split
faltan = (~df.path.apply(os.path.exists)).sum()
assert faltan == 0, f"{faltan} rutas del CSV no existen"

classes = sorted(df["clase"].unique())
df["label"] = df["clase"].map({c: i for i, c in enumerate(classes)})
df_train, df_val, df_test = (df[df.split == s] for s in ["train", "val", "test"])

# ---------- 2. Carga de imágenes ----------
def load(path, label):
    img = tf.io.decode_jpeg(tf.io.read_file(path), channels=3)
    img = tf.image.resize(img, (IMG_SIZE, IMG_SIZE))  # 0-255; EfficientNet normaliza internamente
    return img, label

# ---------- 3. Data augmentation (solo train) ----------
augment = tf.keras.Sequential([
    tf.keras.layers.RandomFlip("horizontal_and_vertical", seed=SEED),
    tf.keras.layers.RandomRotation(0.25, seed=SEED),
    tf.keras.layers.RandomZoom(0.15, seed=SEED),
    tf.keras.layers.RandomContrast(0.1, seed=SEED),
    tf.keras.layers.RandomBrightness(0.1, seed=SEED),
], name="augment")

# ---------- 4. Dataset de train con oversampling ----------
def make_train_ds(df_train, power=1.0):
    """power=1 -> distribución original | 0.5 -> sqrt (recomendado) | 0 -> balance total"""
    counts = df_train["label"].value_counts().sort_index()
    w = counts.astype(float) ** power
    weights = (w / w.sum()).tolist()
    per_class = []
    for lbl in counts.index:
        sub = df_train[df_train.label == lbl]
        ds = tf.data.Dataset.from_tensor_slices((sub.path.values, sub.label.values))
        per_class.append(ds.shuffle(len(sub), seed=SEED).repeat())
    ds = tf.data.Dataset.sample_from_datasets(per_class, weights=weights, seed=SEED)
    ds = (ds.map(load, num_parallel_calls=AUTOTUNE)
            .batch(BATCH)
            .map(lambda x, y: (augment(x, training=True), y), num_parallel_calls=AUTOTUNE)
            .prefetch(AUTOTUNE))
    return ds, len(df_train) // BATCH  # usar steps_per_epoch en fit()

# ---------- 5. Datasets de val y test (sin augmentation, sin balanceo) ----------
def make_eval_ds(df_split):
    ds = tf.data.Dataset.from_tensor_slices((df_split.path.values, df_split.label.values))
    return ds.map(load, num_parallel_calls=AUTOTUNE).batch(BATCH).prefetch(AUTOTUNE)

# Opción A: distribución original + class weights
train_A, steps = make_train_ds(df_train, power=1.0)
cw = compute_class_weight("balanced", classes=np.arange(len(classes)), y=df_train.label)
class_weight_A = dict(enumerate(cw))

# Opción B: oversampling sqrt, sin class weights
train_B, _ = make_train_ds(df_train, power=0.5)

val_ds, test_ds = make_eval_ds(df_val), make_eval_ds(df_test)

# ---------- 6. Verificación ----------
if __name__ == "__main__":
    print("Clases:", classes)
    print("Train / val / test:", len(df_train), len(df_val), len(df_test))
    print("Class weights (opción A):", {classes[k]: round(v, 2) for k, v in class_weight_A.items()})

    orig = df_train["label"].value_counts(normalize=True).sort_index().values
    y = np.concatenate([y.numpy() for _, y in train_B.take(20)])  # 20 batches = 640 imágenes
    muestreo = np.bincount(y, minlength=len(classes)) / len(y)

    print(f"\n{'Clase':<14}{'Original':>10}{'Opción B':>10}")
    for c, o, m in zip(classes, orig, muestreo):
        print(f"{c:<14}{o:>10.1%}{m:>10.1%}")
