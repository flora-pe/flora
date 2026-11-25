import io

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
import joblib

from mvp.api import app
from mvp.core import CLASSES, InvalidImage, baseline_features, load_predictor, read_image

client = TestClient(app)

def sample_image(color=(100,180,90)):
    f=io.BytesIO()
    Image.new("RGB", (80, 70),color).save(f,format="PNG")
    return f.getvalue()

def test_liveness():
    assert client.get("/health").status_code==200
    assert len(client.get("/classes").json()["classes"])==7

def test_invalid_image_is_rejected():
    r=client.post("/predict",files={"file":("bad.png",b"not-an-image","image/png")})
    assert r.status_code==400

def test_wrong_mime_rejected():
    r=client.post("/predict",files={"file":("bad.txt",b"not-an-image","text/plain")})
    assert r.status_code==415

def test_empty_image_rejected():
    with pytest.raises(InvalidImage):read_image(b"")

def test_missing_model_is_not_faked(tmp_path,monkeypatch):
    monkeypatch.setenv("FLORA_MODEL_BACKEND","baseline")
    monkeypatch.setenv("FLORA_MODEL_PATH",str(tmp_path/"does-not-exist.joblib"))
    load_predictor.cache_clear()
    assert client.get("/ready").status_code==503
    assert client.post("/predict",files={"file":("leaf.png",sample_image(),"image/png")}).status_code==503
    load_predictor.cache_clear()

def test_real_supervised_model_integration(tmp_path,monkeypatch):
    # Synthetic data here is exclusively for a unit/integration test, never shipped as a model.
    rng=np.random.default_rng(17)
    xs=[];ys=[]
    for idx,name in enumerate(CLASSES):
        for _ in range(8):
            c=[int((idx*31+k*51+rng.integers(-7,8))%255) for k in range(3)]
            xs.append(baseline_features(Image.new("RGB",(80,70),tuple(c))))
            ys.append(name)
    model=make_pipeline(StandardScaler(),LogisticRegression(max_iter=300))
    model.fit(np.asarray(xs),ys)
    path=tmp_path/"trained.joblib"
    joblib.dump(model,path)
    monkeypatch.setenv("FLORA_MODEL_BACKEND","baseline")
    monkeypatch.setenv("FLORA_MODEL_PATH",str(path))
    load_predictor.cache_clear()
    assert client.get("/ready").status_code==200
    r=client.post("/predict",files={"file":("leaf.png",sample_image(),"image/png")})
    assert r.status_code==200,r.text
    data=r.json()
    assert data["class_id"] in CLASSES
    assert len(data["top_predictions"])==3
    assert data["backend"]=="baseline"
    assert data["needs_review"] is True
    load_predictor.cache_clear()
