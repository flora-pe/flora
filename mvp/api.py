"""Flora local FastAPI service. No external network calls or data persistence."""
from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from mvp.core import CLASSES, InvalidImage, ModelUnavailable, configured_model, load_predictor, predict, read_image

app = FastAPI(title="Flora Vision API", version="0.1.0", description="MVP local de clasificación experimental de hojas de papa")

class Prediction(BaseModel):
    class_id: str
    label: str
    confidence: float
    top_predictions: list[dict]
    model: str
    backend: str
    warning: str
    needs_review: bool

@app.get("/health")
def health():
    """Liveness: 200 means the web process responds, not necessarily model-ready."""
    mode, path = configured_model()
    return {"status": "ok", "model_present": bool(path and path.is_file()), "selected_backend": mode}

@app.get("/ready")
def ready():
    """Readiness: 200 only if a real trained model loads."""
    try:
        mode, _ = load_predictor()
    except ModelUnavailable as exc:
        return JSONResponse(status_code=503, content={"status": "not_ready", "detail": str(exc)})
    return {"status": "ready", "backend": mode, "classes": CLASSES}

@app.get("/classes")
def classes():
    return {"classes": CLASSES}

@app.post("/predict", response_model=Prediction)
async def prediction(file: UploadFile = File(...)):
    if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=415, detail="Solo se aceptan imágenes JPG, PNG y WebP.")
    try:
        raw = await file.read(10 * 1024 * 1024 + 1)
        image = read_image(raw)
    except InvalidImage as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        await file.close()
    try:
        return predict(image)
    except ModelUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
