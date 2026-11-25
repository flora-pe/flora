"""Entrenamiento parametrizable — Fase C, FLORA.

Uso:
    python -m scripts.fase_c.train --config A
    python -m scripts.fase_c.train --config B
    python -m scripts.fase_c.train --config C
    python -m scripts.fase_c.train --config E1
    python -m scripts.fase_c.train --config E2
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import time
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
import tensorflow as tf
import keras
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score,
    confusion_matrix, precision_recall_fscore_support,
)

from . import data_pipeline as dp

BASE = Path("data/splits")
SALIDAS = Path("data/reportes/fase_c")
AUG_BY_CONFIG = {"A": "none", "B": "B", "C": "C", "D": "D", "E1": "E1", "E2": "E2", "Cprime": "Cprime", "Cprime2": "Cprime2"}


def build_model(num_classes: int = 7, use_rotation: bool = True):
    base = tf.keras.applications.EfficientNetB0(
        include_top=False, weights="imagenet", input_shape=(*dp.IMG_SIZE, 3)
    )
    base.trainable = False
    inputs = keras.Input(shape=(*dp.IMG_SIZE, 3), name="image")
    if use_rotation:
        x = keras.layers.RandomRotation(0.08, fill_mode="reflect", name="rot")(inputs)
    else:
        x = inputs
    x = base(x, training=False)
    x = keras.layers.GlobalAveragePooling2D()(x)
    x = keras.layers.Dropout(0.3, name="drop")(x)
    outputs = keras.layers.Dense(num_classes, activation="softmax", name="pred")(x)
    return keras.Model(inputs, outputs), base


def compile_model(model, lr):
    model.compile(
        optimizer=keras.optimizers.Adam(lr),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def unfreeze_top(base, n_blocks: int = 2):
    base.trainable = True
    for layer in base.layers[:-20 * n_blocks]:
        layer.trainable = False
    for layer in base.layers:
        if isinstance(layer, keras.layers.BatchNormalization):
            layer.trainable = False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, choices=list(AUG_BY_CONFIG))
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--epochs-ft", type=int, default=10)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--lr-head", type=float, default=1e-3)
    ap.add_argument("--lr-ft", type=float, default=1e-4)
    args = ap.parse_args()

    tf.keras.utils.set_random_seed(dp.SEED)
    out = SALIDAS / args.config
    out.mkdir(parents=True, exist_ok=True)

    rutas_tr, y_tr = dp.listar_archivos(BASE, "train")
    rutas_va, y_va = dp.listar_archivos(BASE, "val")
    print(f"[{args.config}] train={len(rutas_tr)} val={len(rutas_va)}")

    aug_cfg = AUG_BY_CONFIG[args.config]
    ds_tr = dp.make_dataset(rutas_tr, y_tr, training=True, aug_config=aug_cfg, batch_size=args.batch_size)
    ds_va = dp.make_dataset(rutas_va, y_va, training=False, batch_size=args.batch_size)

    cw = None
    if args.config in ("C", "D", "E1", "E2", "Cprime", "Cprime2"):
        cw = dp.compute_class_weights(rutas_tr, y_tr)
        if args.config == "Cprime2":
            cw = {k: v ** 0.5 for k, v in cw.items()}
            print("[Cprime2] aplicando sqrt(weight): Nematode=%.3f Healthy=%.3f" % (cw[3], cw[2]))
        print(f"[{args.config}] class_weight={cw}")

    use_rot = args.config not in ("A",)  # A es el único sin rotación
    model, base = build_model(use_rotation=use_rot)
    compile_model(model, args.lr_head)

    print(f"[{args.config}] Fase 1 (head only, lr={args.lr_head})")
    hist1 = model.fit(
        ds_tr, validation_data=ds_va, epochs=args.epochs, class_weight=cw,
        callbacks=[
            keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=3, restore_best_weights=True),
            keras.callbacks.ReduceLROnPlateau(monitor="val_accuracy", factor=0.5, patience=2, min_lr=1e-6),
            keras.callbacks.ModelCheckpoint(
                filepath=str(out / "best_model.keras"),
                monitor="val_loss", save_best_only=True, verbose=0,
            ),
        ],
        verbose=2,
    )

    print(f"[{args.config}] Fase 2 (fine-tuning top blocks, lr={args.lr_ft})")
    unfreeze_top(base, n_blocks=2)
    compile_model(model, args.lr_ft)
    hist2 = model.fit(
        ds_tr, validation_data=ds_va, epochs=args.epochs_ft, class_weight=cw,
        callbacks=[
            keras.callbacks.EarlyStopping(monitor="val_accuracy", patience=3, restore_best_weights=True),
            keras.callbacks.ReduceLROnPlateau(monitor="val_accuracy", factor=0.5, patience=2, min_lr=1e-7),
            keras.callbacks.ModelCheckpoint(
                filepath=str(out / "best_model.keras"),
                monitor="val_loss", save_best_only=True, verbose=0,
            ),
        ],
        verbose=2,
    )

    model_path = out / "model.keras"
    model.save(model_path)

    # Cargar el modelo con menor val_loss (mejor generalización)
    best_path = out / "best_model.keras"
    if best_path.exists():
        print(f"[{args.config}] Cargando best_model.keras (menor val_loss)")
        model = keras.models.load_model(best_path, compile=False)

    y_pred_probs = model.predict(ds_va, verbose=0)
    y_pred = np.argmax(y_pred_probs, axis=1)

    acc = accuracy_score(y_va, y_pred)
    bacc = balanced_accuracy_score(y_va, y_pred)
    macro = precision_recall_fscore_support(y_va, y_pred, average="macro", zero_division=0)
    weighted = precision_recall_fscore_support(y_va, y_pred, average="weighted", zero_division=0)
    por_clase = precision_recall_fscore_support(
        y_va, y_pred, labels=list(range(len(dp.CLASES))), zero_division=0
    )
    cm = confusion_matrix(y_va, y_pred, labels=list(range(len(dp.CLASES))))

    metricas = {
        "config": args.config,
        "n_train": int(len(rutas_tr)),
        "n_val": int(len(rutas_va)),
        "epochs_head": int(len(hist1.history["loss"])),
        "epochs_ft": int(len(hist2.history["loss"])),
        "accuracy": float(acc),
        "balanced_accuracy": float(bacc),
        "macro": {"precision": float(macro[0]), "recall": float(macro[1]), "f1": float(macro[2])},
        "weighted": {"precision": float(weighted[0]), "recall": float(weighted[1]), "f1": float(weighted[2])},
        "por_clase": {
            c: {
                "precision": float(por_clase[0][i]),
                "recall": float(por_clase[1][i]),
                "f1": float(por_clase[2][i]),
                "support": int(por_clase[3][i]),
            } for i, c in enumerate(dp.CLASES)
        },
        "confusion_matrix": cm.tolist(),
        "clases": dp.CLASES,
        "modelo_path": str(model_path),
        "modelo_evaluado": str(best_path) if best_path.exists() else str(model_path),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    (out / "metricas.json").write_text(json.dumps(metricas, indent=2))
    with (out / "history.csv").open("w", newline="") as f:
        keys_h1 = list(hist1.history.keys())
        keys_h2 = list(hist2.history.keys())
        w = csv.writer(f)
        w.writerow(["fase", "epoca"] + keys_h1)
        for i in range(len(hist1.history["loss"])):
            w.writerow(["head", i] + [hist1.history[k][i] for k in keys_h1])
        for i in range(len(hist2.history["loss"])):
            w.writerow(["ft", i] + [hist2.history[k][i] for k in keys_h2])

    print("\n=== Métricas finales ===")
    print(f"  accuracy          : {acc:.4f}")
    print(f"  balanced_accuracy : {bacc:.4f}")
    print(f"  macro P/R/F1      : {macro[0]:.4f} / {macro[1]:.4f} / {macro[2]:.4f}")
    print(f"  weighted P/R/F1   : {weighted[0]:.4f} / {weighted[1]:.4f} / {weighted[2]:.4f}")
    print(f"  modelo            : {model_path}")


if __name__ == "__main__":
    main()
