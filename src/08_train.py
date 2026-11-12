import argparse
import importlib
import os
import numpy as np
import tensorflow as tf
from sklearn.metrics import (classification_report, f1_score,
                             balanced_accuracy_score, confusion_matrix)

# ---------- Argumentos ----------
p = argparse.ArgumentParser()
p.add_argument("--opcion", choices=["A", "B"], required=True)
p.add_argument("--epochs", type=int, default=15)
args = p.parse_args()

# ---------- Datos (reutiliza el pipeline de 06) ----------
d = importlib.import_module("06_dataset_tf")
tf.keras.utils.set_random_seed(d.SEED)

if args.opcion == "A":
    train_ds = d.train_A
    class_weight = {k: float(v) for k, v in d.class_weight_A.items()}
else:
    train_ds = d.train_B
    class_weight = None

# ---------- Modelo: EfficientNetB0 congelado + cabeza nueva ----------
base = tf.keras.applications.EfficientNetB0(
    include_top=False, weights="imagenet", input_shape=(d.IMG_SIZE, d.IMG_SIZE, 3))
base.trainable = False

inputs = tf.keras.Input((d.IMG_SIZE, d.IMG_SIZE, 3))
x = base(inputs, training=False)
x = tf.keras.layers.GlobalAveragePooling2D()(x)
x = tf.keras.layers.Dropout(0.3)(x)
outputs = tf.keras.layers.Dense(len(d.classes), activation="softmax")(x)
model = tf.keras.Model(inputs, outputs)

model.compile(optimizer=tf.keras.optimizers.Adam(1e-3),
              loss="sparse_categorical_crossentropy",
              metrics=["accuracy"])

# ---------- Entrenamiento ----------
early = tf.keras.callbacks.EarlyStopping(
    monitor="val_loss", patience=4, restore_best_weights=True)

hist = model.fit(train_ds,
                 steps_per_epoch=d.steps,
                 validation_data=d.val_ds,
                 epochs=args.epochs,
                 class_weight=class_weight,
                 callbacks=[early])

# ---------- Evaluación en val ----------
y_true = d.df_val.label.values
y_pred = model.predict(d.val_ds).argmax(axis=1)

macro = f1_score(y_true, y_pred, average="macro")
bal = balanced_accuracy_score(y_true, y_pred)
rep = classification_report(y_true, y_pred, target_names=d.classes, digits=3)
cm = confusion_matrix(y_true, y_pred)

txt = (f"Opción {args.opcion} | epochs entrenadas: {len(hist.history['loss'])}\n"
       f"Macro-F1: {macro:.3f} | Balanced accuracy: {bal:.3f}\n\n{rep}\n"
       f"Matriz de confusión (filas = real, columnas = predicho)\n"
       f"Orden: {d.classes}\n{cm}\n")
print("\n" + txt)

# ---------- Guardar ----------
os.makedirs("reports", exist_ok=True)
with open(f"reports/train_opcion_{args.opcion}.txt", "w") as f:
    f.write(txt)

os.makedirs("models", exist_ok=True)
model.save(f"models/effnetb0_opcion_{args.opcion}.keras")
print(f"✅ Reporte en reports/train_opcion_{args.opcion}.txt")
