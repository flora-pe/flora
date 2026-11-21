"""Pipeline de datos para Fase C — FLORA.

- Train: augmentation dinámica vía tf.data.map.
- Val/test: solo resize + float32 (SIN augmentation, SIN normalización).
- Splits congelados desde data/splits/{train,val,test}.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import tensorflow as tf
from sklearn.utils.class_weight import compute_class_weight

from . import augmentations as aug

CLASES = ["Bacteria", "Fungi", "Healthy", "Nematode", "Pest", "Phytopthora", "Virus"]
IMG_SIZE = (224, 224)
SEED = 42


def listar_archivos(base: Path, split: str):
    rutas, etiquetas = [], []
    for idx, c in enumerate(CLASES):
        d = base / split / c
        if not d.is_dir():
            continue
        for p in sorted(d.iterdir()):
            if p.suffix.lower() in (".jpg", ".jpeg", ".png"):
                rutas.append(str(p))
                etiquetas.append(idx)
    return rutas, np.array(etiquetas, dtype=np.int32)


def _load_and_resize(ruta: tf.Tensor, label: tf.Tensor):
    img = tf.io.read_file(ruta)
    img = tf.image.decode_image(img, channels=3, expand_animations=False)
    img = tf.image.convert_image_dtype(img, tf.float32) * 255.0
    img = tf.image.resize(img, IMG_SIZE, method="bilinear")
    img.set_shape((*IMG_SIZE, 3))
    return img, label


def _apply_train_aug(image, label, aug_config: str):
    if aug_config == "none":
        return image, label
    if aug_config in ("B", "C", "D", "E1", "E2"):
        # Cprime NO entra aquí: solo rotación del modelo + class_weight
        image, label = aug.random_resized_crop(image, label)
        image, label = aug.random_flip(image, label)
        image, label = aug.random_translation(image, label, max_shift=0.1)
        return image, label
    return image, label


def make_dataset(rutas, etiquetas, training: bool, aug_config: str = "none",
                 batch_size: int = 32, num_classes: int = 7):
    ds = tf.data.Dataset.from_tensor_slices((rutas, etiquetas))
    if training:
        ds = ds.shuffle(buffer_size=len(rutas), seed=SEED, reshuffle_each_iteration=True)
    ds = ds.map(_load_and_resize, num_parallel_calls=tf.data.AUTOTUNE)
    if training and aug_config != "none":
        ds = ds.map(lambda x, y: _apply_train_aug(x, y, aug_config),
                    num_parallel_calls=tf.data.AUTOTUNE)
    ds = ds.batch(batch_size, drop_remainder=False)

    if training and aug_config == "E2":
        def _cutmix_batch(images, labels):
            images, labels, lam = aug.cutmix(images, labels, alpha=1.0)
            return (images, labels, lam)
        ds = ds.map(_cutmix_batch, num_parallel_calls=tf.data.AUTOTUNE)
    elif training and aug_config == "E1":
        def _mosaic_batch(images, labels):
            images, labels = aug.mosaic(images, labels, num_classes)
            return (images, labels, tf.ones([tf.shape(images)[0]]))
        ds = ds.map(_mosaic_batch, num_parallel_calls=tf.data.AUTOTUNE)
    # Nota: NO agregamos sample_weight para A/B/C/Cprime/D.
    # Keras rechaza usar class_weight + sample_weight simultáneamente.
    # Solo E1 (Mosaic) y E2 (CutMix) devuelven 3-tuple porque su loss es distinta.

    ds = ds.prefetch(tf.data.AUTOTUNE)
    return ds


def compute_class_weights(rutas, etiquetas, num_classes=7):
    clases_unicas = np.unique(etiquetas)
    pesos = compute_class_weight("balanced", classes=clases_unicas, y=etiquetas)
    return {int(c): float(w) for c, w in zip(clases_unicas, pesos)}
