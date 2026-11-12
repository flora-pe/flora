import argparse
import importlib
import os
import tensorflow as tf
from sklearn.metrics import (classification_report, f1_score,
                             balanced_accuracy_score, confusion_matrix)

# ---------- Argumentos ----------
p = argparse.ArgumentParser()
p.add_argument("--opcion", choices=["A", "B"], default="B")
p.add_argument("--epochs", type=int, default=15)
p.add_argument("--unfreeze", type=int, default=40)  # capas finales a descongelar
p.add_argument("--lr", type=float, default=1e-5)
args = p.parse_args()

# ---------- Datos ----------
d = importlib.import_module("06_dataset_tf")
tf.keras.utils.set_random_seed(d.SEED)

if args.opcion == "A":
    train_ds = d.train_A
    class_weight = {k: float(v) for k, v in d.class_weight_A.items()}
else:
    train_ds = d.train_B
    class_weight = None

# ---------- Cargar modelo entrenado en 08 ----------
model = tf.keras.models.load_model(f"models/effnetb0_opcion_{args.opcion}.keras")
base = model.get_layer("efficientnetb0")

# Descongelar las últimas N capas, manteniendo BatchNorm congelado
base.trainable = True
for layer in base.layers[:-args.unfreeze]:
    layer.trainable = False
for layer in base.layers:
    if isinstance(layer, tf.keras.layers.BatchNormalization):
        layer.trainable = False

n_train = sum(l.trainable for l in base.layers)
print(f"Capas entrenables en la base: {n_train} de {len(base.layers)}")

model.compile(optimizer=tf.keras.optimizers.Adam(args.lr),
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

txt = (f"Fine-tuning opción {args.opcion} | unfreeze {args.unfreeze} | lr {args.lr} | "
       f"epochs entrenadas: {len(hist.history['loss'])}\n"
       f"Macro-F1: {macro:.3f} | Balanced accuracy: {bal:.3f}\n\n{rep}\n"
       f"Matriz de confusión (filas = real, columnas = predicho)\n"
       f"Orden: {d.classes}\n{cm}\n")
print("\n" + txt)

# ---------- Guardar ----------
with open(f"reports/finetune_opcion_{args.opcion}.txt", "w") as f:
    f.write(txt)
model.save(f"models/effnetb0_ft_opcion_{args.opcion}.keras")
print(f"✅ Reporte en reports/finetune_opcion_{args.opcion}.txt")
