"""Augmentations para Fase C — FLORA.

Diseño:
- Todo se aplica con tf.data.map (dinámico, varía por época).
- Val/test NO usan ninguna de estas funciones.
- Sin inversiones de color (el color de la lesión es señal diagnóstica).
- RandomResizedCrop se implementa custom porque Keras 3.15.1 no lo trae.
"""
from __future__ import annotations

import tensorflow as tf


def random_flip(image, label):
    """Horizontal + vertical flip. Ambos preservan la semántica de la lesión."""
    image = tf.image.random_flip_left_right(image)
    image = tf.image.random_flip_up_down(image)
    return image, label


def random_rotation(image, label, max_deg: float = 25.0):
    """Rotación aleatoria — placeholder. La rotación real se aplica como capa
    keras.layers.RandomRotation dentro del modelo (ver train.py).
    """
    return image, label


def random_zoom(image, label, factor: float = 0.15):
    """Zoom aleatorio entre (1-factor, 1+factor). Preserva las 4 esquinas."""
    scale = tf.random.uniform([], 1.0 - factor, 1.0 + factor)
    h, w = tf.shape(image)[0], tf.shape(image)[1]
    new_h = tf.cast(tf.cast(h, tf.float32) / scale, tf.int32)
    new_w = tf.cast(tf.cast(w, tf.float32) / scale, tf.int32)
    y0 = tf.maximum(0, (h - new_h) // 2)
    x0 = tf.maximum(0, (w - new_w) // 2)
    cropped = image[y0:y0 + new_h, x0:x0 + new_w]
    return tf.image.resize(cropped, [h, w]), label


def random_translation(image, label, max_shift: float = 0.1):
    """Traslación aleatoria hasta ±max_shift * tamaño, con padding REFLECT."""
    h, w = tf.shape(image)[0], tf.shape(image)[1]
    tx = tf.cast(tf.cast(w, tf.float32) * max_shift * tf.random.uniform([], -1.0, 1.0), tf.int32)
    ty = tf.cast(tf.cast(h, tf.float32) * max_shift * tf.random.uniform([], -1.0, 1.0), tf.int32)
    padded = tf.pad(image, [[tf.abs(ty), tf.abs(ty)], [tf.abs(tx), tf.abs(tx)], [0, 0]], mode="REFLECT")
    y0 = tf.abs(ty) - ty
    x0 = tf.abs(tx) - tx
    return padded[y0:y0 + h, x0:x0 + w], label


def random_resized_crop(image, label, scale=(0.7, 1.0), target_size=224):
    """Equivalente a torchvision.RandomResizedCrop (crop aleatorio + resize)."""
    h = tf.cast(tf.shape(image)[0], tf.float32)
    w = tf.cast(tf.shape(image)[1], tf.float32)
    area = h * w
    target_area = tf.random.uniform([], scale[0], scale[1]) * area
    log_ratio = tf.random.uniform([], tf.math.log(3.0 / 4.0), tf.math.log(4.0 / 3.0))
    ratio = tf.exp(log_ratio)
    new_w = tf.cast(tf.round(tf.sqrt(target_area * ratio)), tf.int32)
    new_h = tf.cast(tf.round(tf.sqrt(target_area / ratio)), tf.int32)
    new_w = tf.clip_by_value(new_w, 1, tf.cast(w, tf.int32))
    new_h = tf.clip_by_value(new_h, 1, tf.cast(h, tf.int32))
    y0 = tf.random.uniform([], 0, tf.cast(h, tf.int32) - new_h + 1, dtype=tf.int32)
    x0 = tf.random.uniform([], 0, tf.cast(w, tf.int32) - new_w + 1, dtype=tf.int32)
    crop = image[y0:y0 + new_h, x0:x0 + new_w]
    return tf.image.resize(crop, [target_size, target_size]), label


def cutmix(images, labels, alpha: float = 1.0, prob: float = 0.5):
    """CutMix: pega un parche de otra imagen. Devuelve (imgs, labels, lam)."""
    batch = tf.shape(images)[0]
    h = tf.shape(images)[1]
    w = tf.shape(images)[2]
    lam = tf.compat.v1.distributions.Beta(alpha, alpha).sample([batch])
    lam = tf.maximum(lam, 1.0 - lam)
    cut_ratio = tf.sqrt(1.0 - lam)
    cut_h = tf.cast(tf.cast(h, tf.float32) * cut_ratio, tf.int32)
    cut_w = tf.cast(tf.cast(w, tf.float32) * cut_ratio, tf.int32)
    cy = tf.random.uniform([batch], 0, h, dtype=tf.int32)
    cx = tf.random.uniform([batch], 0, w, dtype=tf.int32)
    y1 = tf.clip_by_value(cy - cut_h // 2, 0, h)
    y2 = tf.clip_by_value(cy + cut_h // 2, 0, h)
    x1 = tf.clip_by_value(cx - cut_w // 2, 0, w)
    x2 = tf.clip_by_value(cx + cut_w // 2, 0, w)
    perm = tf.random.shuffle(tf.range(batch))
    images_b = tf.gather(images, perm)
    labels_b = tf.gather(labels, perm)

    def _mix_one(args):
        img, img_b, yy1, yy2, xx1, xx2 = args
        mask_rows = tf.concat([tf.ones([yy1, w, 3]), tf.zeros([yy2 - yy1, w, 3]),
                               tf.ones([h - yy2, w, 3])], axis=0)
        mask_cols = tf.concat([tf.ones([h, xx1, 3]), tf.zeros([h, xx2 - xx1, 3]),
                               tf.ones([h, w - xx2, 3])], axis=1)
        mask = mask_rows * mask_cols
        return img * mask + img_b * (1.0 - mask)

    images_mixed = tf.map_fn(
        _mix_one, (images, images_b, y1, y2, x1, x2),
        fn_output_signature=tf.float32, parallel_iterations=8,
    )
    return images_mixed, labels, lam


def mosaic(images, labels, num_classes: int, prob: float = 1.0):
    """Mosaic 2×2. Etiqueta = imagen principal (cuadrante superior izquierdo)."""
    batch = tf.shape(images)[0]
    h = tf.shape(images)[1]
    w = tf.shape(images)[2]
    half_h, half_w = h // 2, w // 2
    idx = tf.random.shuffle(tf.range(batch))
    img0 = images
    img1 = tf.gather(images, idx)
    img2 = tf.gather(images, tf.random.shuffle(idx))
    img3 = tf.gather(images, tf.random.shuffle(idx))
    img0_r = tf.image.resize(img0, [half_h, half_w])
    img1_r = tf.image.resize(img1, [half_h, half_w])
    img2_r = tf.image.resize(img2, [half_h, half_w])
    img3_r = tf.image.resize(img3, [half_h, half_w])
    top = tf.concat([img0_r, img1_r], axis=2)
    bottom = tf.concat([img2_r, img3_r], axis=2)
    return tf.concat([top, bottom], axis=1), labels
