"""Test automático de inferencia — FLORA v2.

Corre 5 verificaciones:
  1. El modelo carga correctamente.
  2. Predicción sobre una imagen real (path) devuelve estructura válida.
  3. Predicción sobre bytes devuelve el mismo resultado que el path.
  4. Predicción sobre np.ndarray devuelve el mismo resultado que el path.
  5. Entradas inválidas (archivo inexistente, tipo no soportado) son rechazadas.

Uso:
    python -m scripts.fase_c.test_inference
"""
from __future__ import annotations

import os
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

from pathlib import Path
import numpy as np
import pytest
from PIL import Image

from scripts.fase_c.inference import CLASES, load_model, predict

MODELO = Path("artifacts/flora_effnetb0_diego_v2.keras")
TEST_DIR = Path("data/splits/test")


def _primera_imagen(clase: str) -> Path:
    d = TEST_DIR / clase
    for p in sorted(d.iterdir()):
        if p.suffix.lower() in (".jpg", ".jpeg", ".png"):
            return p
    raise FileNotFoundError(f"Sin imágenes en {d}")


@pytest.fixture(scope="module")
def model():
    return load_model(MODELO)


def test_01_modelo_carga(model):
    """El modelo carga y tiene la firma esperada."""
    assert model.count_params() == 4_058_538
    assert model.input_shape == (None, 224, 224, 3)
    assert model.output_shape == (None, 7)


def test_02_prediccion_path(model):
    """Predicción desde path devuelve estructura válida."""
    img = _primera_imagen("Fungi")
    r = predict(model, img)
    assert r["class"] in CLASES
    assert 0.0 <= r["probability"] <= 1.0
    assert len(r["all_probs"]) == 7
    assert abs(sum(r["all_probs"].values()) - 1.0) < 1e-5
    assert len(r["top_k"]) == 3
    assert r["top_k"][0]["class"] == r["class"]


def test_03_prediccion_bytes(model):
    """Predicción desde bytes == predicción desde path."""
    img = _primera_imagen("Bacteria")
    r_path = predict(model, img)
    r_bytes = predict(model, img.read_bytes())
    assert r_path["class"] == r_bytes["class"]
    assert abs(r_path["probability"] - r_bytes["probability"]) < 1e-5


def test_04_prediccion_ndarray(model):
    """Predicción desde ndarray == predicción desde path."""
    img = _primera_imagen("Virus")
    arr = np.asarray(Image.open(img).convert("RGB"), dtype=np.float32)
    r_path = predict(model, img)
    r_arr = predict(model, arr)
    assert r_path["class"] == r_arr["class"]
    assert abs(r_path["probability"] - r_arr["probability"]) < 1e-5


def test_05_entradas_invalidas(model):
    """Entradas inválidas son rechazadas con excepción."""
    with pytest.raises(FileNotFoundError):
        predict(model, "/ruta/que/no/existe.jpg")
    with pytest.raises(TypeError):
        predict(model, 12345)
    with pytest.raises(ValueError):
        predict(model, np.zeros((10, 10), dtype=np.float32))  # falta canal


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v", "-s"]))
