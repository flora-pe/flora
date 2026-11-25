"""Inference adapters shared by API and the reproducible fallback trainer.

The production EfficientNet-B0 artifact is NOT included. The fallback is a
supervised baseline trained on Flora's actual labelled images; it is not a mock.
"""
from __future__ import annotations

import io
import os
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

ROOT = Path(__file__).resolve().parent.parent
CLASSES = ("Bacteria", "Fungi", "Healthy", "Nematode", "Pest", "Phytopthora", "Virus")
DISPLAY = {
    "Bacteria": "Posible infección bacteriana",
    "Fungi": "Posible enfermedad fúngica",
    "Healthy": "Sin indicios detectados en esta clasificación",
    "Nematode": "Posibles nematodos",
    "Pest": "Posible presencia de plagas",
    "Phytopthora": "Posible Phytopthora (etiqueta del dataset)",
    "Virus": "Posible infección viral",
}
MAX_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 24_000_000

class ModelUnavailable(RuntimeError):
    pass

class InvalidImage(ValueError):
    pass


def read_image(raw: bytes) -> Image.Image:
    if not raw or len(raw) > MAX_BYTES:
        raise InvalidImage("La imagen está vacía o supera el límite de 10 MB.")
    try:
        with Image.open(io.BytesIO(raw)) as img:
            if img.width * img.height > MAX_PIXELS:
                raise InvalidImage("Resolución excesiva; máximo 24 megapíxeles.")
            img.load()
            image = ImageOps.exif_transpose(img).convert("RGB")
            return image
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        if isinstance(exc, InvalidImage):
            raise
        raise InvalidImage("El archivo no contiene una imagen legible.") from exc


def baseline_features(image: Image.Image) -> np.ndarray:
    """Deterministic RGB colour/texture features; fast CPU-only fallback."""
    image = image.convert("RGB").resize((48, 48), Image.Resampling.BILINEAR)
    a = np.asarray(image, dtype=np.float32) / 255.0
    # Coarse spatial appearance and global channel distributions.
    small = np.asarray(image.resize((10, 10), Image.Resampling.BILINEAR), dtype=np.float32) / 255.0
    hist = np.concatenate([np.histogram(a[..., k], bins=16, range=(0, 1))[0] for k in range(3)]).astype(np.float32)
    hist /= (48 * 48)
    gray = .299 * a[..., 0] + .587 * a[..., 1] + .114 * a[..., 2]
    gx, gy = np.diff(gray, axis=1), np.diff(gray, axis=0)
    texture = np.array([np.mean(abs(gx)), np.mean(abs(gy)), np.std(gx), np.std(gy)], dtype=np.float32)
    return np.concatenate([small.ravel(), hist, texture])


def configured_model() -> tuple[str, Path | None]:
    mode = os.getenv("FLORA_MODEL_BACKEND", "auto").strip().lower()
    explicit = os.getenv("FLORA_MODEL_PATH", "").strip()
    keras_default = ROOT / "models" / "effnetb0_ft_opcion_B.keras"
    baseline_default = ROOT / "models" / "flora_baseline.joblib"
    if mode not in {"auto", "keras", "baseline"}:
        raise ModelUnavailable("FLORA_MODEL_BACKEND debe ser auto, keras o baseline.")
    if explicit:
        path = Path(explicit).expanduser().resolve()
        return ("baseline" if path.suffix == ".joblib" else "keras") if mode == "auto" else mode, path
    if mode == "keras":
        return "keras", keras_default
    if mode == "baseline":
        return "baseline", baseline_default
    if keras_default.exists():
        return "keras", keras_default
    if baseline_default.exists():
        return "baseline", baseline_default
    return "none", None


@lru_cache(maxsize=1)
def load_predictor():
    mode, path = configured_model()
    if mode == "none" or not path or not path.is_file():
        raise ModelUnavailable(
            "No hay modelo entrenado. Ejecutá 'python scripts/train_mvp_baseline.py' "
            "o copiá el .keras de Brian a models/effnetb0_ft_opcion_B.keras."
        )
    if mode == "keras":
        try:
            import tensorflow as tf
        except ImportError as exc:
            raise ModelUnavailable("Para usar el modelo .keras instalá requirements-model-tf.txt.") from exc
        try:
            model = tf.keras.models.load_model(path, compile=False)
        except Exception as exc:
            raise ModelUnavailable(f"No se puede cargar el modelo Keras: {type(exc).__name__}") from exc
        if tuple(model.input_shape[1:]) != (224, 224, 3):
            raise ModelUnavailable("El checkpoint no tiene la entrada RGB 224x224x3 esperada.")
        if int(model.output_shape[-1]) != len(CLASSES):
            raise ModelUnavailable("El checkpoint no tiene las siete clases esperadas.")
        return mode, model
    # joblib deserializa pickle; cargar solamente un artefacto generado localmente y de confianza.
    try:
        import joblib
        model = joblib.load(path)
    except Exception as exc:
        raise ModelUnavailable(f"No se puede cargar el baseline: {type(exc).__name__}") from exc
    if tuple(getattr(model, "classes_", [])) != CLASSES:
        raise ModelUnavailable("Las etiquetas del baseline no coinciden con las siete clases del dataset.")
    return mode, model


def predict(image: Image.Image) -> dict:
    mode, model = load_predictor()
    if mode == "keras":
        # Consistent with src/06_dataset_tf.py: EfficientNetB0 handles scaling internally.
        tensor = np.asarray(image.resize((224, 224)), dtype=np.float32)
        probs = np.asarray(model.predict(tensor[None, ...], verbose=0)[0], dtype=np.float64)
        model_name = os.getenv("FLORA_MODEL_VERSION", "EfficientNet-B0 fine-tuned")
    else:
        probs = np.asarray(model.predict_proba(baseline_features(image)[None, :])[0], dtype=np.float64)
        model_name = "Baseline supervisado (color y textura)"
    if probs.shape != (len(CLASSES),) or not np.isfinite(probs).all():
        raise RuntimeError("El modelo devolvió probabilidades inválidas.")
    probs = np.clip(probs, 0, 1)
    probs /= probs.sum()
    order = np.argsort(-probs)
    idx = int(order[0])
    result = {
        "class_id": CLASSES[idx],
        "label": DISPLAY[CLASSES[idx]],
        "confidence": round(float(probs[idx]), 4),
        "top_predictions": [
            {"class_id": CLASSES[int(i)], "label": DISPLAY[CLASSES[int(i)]], "confidence": round(float(probs[i]), 4)}
            for i in order[:3]
        ],
        "model": model_name,
        "backend": mode,
        "warning": "Resultado experimental; las probabilidades no están calibradas y no son un diagnóstico agronómico.",
        "needs_review": bool(probs[idx] < 0.70 or mode == "baseline"),
    }
    return result
