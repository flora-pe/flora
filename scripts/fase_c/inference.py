"""Inferencia del modelo FLORA v2.

Uso:
    from scripts.fase_c.inference import load_model, predict
    model = load_model()                          # cacheado
    result = predict(model, "path/imagen.jpg")
    # → {"class": "Fungi", "probability": 0.93, "top_k": [...], "all_probs": {...}}

Contrato de entrada:
    - str, Path: ruta a archivo de imagen (jpg/png)
    - bytes: contenido binario de imagen
    - np.ndarray: (H, W, 3), dtype float32 o uint8, RGB

Contrato de salida:
    - class: str (una de las 7 clases)
    - probability: float en [0, 1]
    - top_k: lista de {class, probability} ordenada desc
    - all_probs: dict {clase: prob} con las 7 probabilidades

Nota crítica:
    EfficientNetB0 incluye su propia capa Rescaling(/255). Por eso el array
    se pasa en [0, 255], NO en [0, 1]. Si se normaliza, el modelo falla.
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Union, Dict

import numpy as np
from PIL import Image

CLASES = ["Bacteria", "Fungi", "Healthy", "Nematode", "Pest", "Phytopthora", "Virus"]
IMG_SIZE = (224, 224)
MODELO_DEFAULT = Path("artifacts/flora_effnetb0_diego_v2.keras")

_CACHE = {}


def load_model(path: Union[str, Path] = MODELO_DEFAULT):
    """Carga el modelo (cacheado por path)."""
    from tensorflow import keras
    key = str(path)
    if key not in _CACHE:
        if not Path(path).is_file():
            raise FileNotFoundError(f"Modelo no encontrado: {path}")
        _CACHE[key] = keras.models.load_model(path, compile=False)
    return _CACHE[key]


def _to_array(source: Union[str, Path, bytes, np.ndarray]) -> np.ndarray:
    """Convierte entrada a np.ndarray float32 (H,W,3) en [0,255] RGB."""
    if isinstance(source, np.ndarray):
        arr = source
        if arr.ndim != 3 or arr.shape[2] != 3:
            raise ValueError(f"ndarray debe ser (H,W,3), recibido {arr.shape}")
        if arr.dtype != np.float32:
            arr = arr.astype(np.float32)
        if arr.max() <= 1.0:  # si viene en [0,1], reescalar a [0,255]
            arr = arr * 255.0
    elif isinstance(source, bytes):
        img = Image.open(io.BytesIO(source)).convert("RGB")
        arr = np.asarray(img, dtype=np.float32)
    elif isinstance(source, (str, Path)):
        p = Path(source)
        if not p.is_file():
            raise FileNotFoundError(f"Imagen no encontrada: {p}")
        img = Image.open(p).convert("RGB")
        arr = np.asarray(img, dtype=np.float32)
    else:
        raise TypeError(f"Tipo de entrada no soportado: {type(source).__name__}")

    img = Image.fromarray(arr.astype(np.uint8)).convert("RGB").resize(IMG_SIZE)
    return np.asarray(img, dtype=np.float32)


def predict(model, source: Union[str, Path, bytes, np.ndarray], top_k: int = 3) -> Dict:
    """Predice una imagen. Retorna dict con predicción principal, top_k y probs completas."""
    arr = _to_array(source)
    batch = np.expand_dims(arr, axis=0)
    probs = model.predict(batch, verbose=0)[0]
    idx = int(np.argmax(probs))

    top = sorted(
        [{"class": CLASES[i], "probability": float(probs[i])} for i in range(len(CLASES))],
        key=lambda x: x["probability"],
        reverse=True,
    )[:top_k]

    return {
        "class": CLASES[idx],
        "probability": float(probs[idx]),
        "top_k": top,
        "all_probs": {c: float(probs[i]) for i, c in enumerate(CLASES)},
    }


def predict_batch(model, sources, top_k: int = 3):
    """Predice una lista de imágenes (una por una, para estabilidad de memoria)."""
    return [predict(model, s, top_k=top_k) for s in sources]
