"""Train an actual supervised CPU baseline using the existing 3010-image manifest.

Emergency MVP only. No synthetic or random predictions; no test-set tuning.
This DOES NOT replace Brian's EfficientNetB0 model or adjudicate Diego's split.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, f1_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

# When executed as `python scripts/train_mvp_baseline.py`, scripts/ is sys.path[0].
# Add the repository root explicitly; do not require PYTHONPATH from the user.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mvp.core import ROOT, CLASSES, baseline_features


def resolve_path(value: str) -> Path:
    p = ROOT / value
    if p.is_file():
        return p
    original = Path(value)
    alternatives = [ROOT / "potato_agml" / original.parent.name / original.name,
                    ROOT / "data" / "potato_agml" / original.parent.name / original.name]
    for candidate in alternatives:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Imagen ausente: {value}. Ejecutá ./scripts/download_data.sh desde la raíz.")


def build(split: pd.DataFrame):
    x, y = [], []
    for row in split.itertuples(index=False):
        with Image.open(resolve_path(row.path)) as image:
            x.append(baseline_features(image))
        y.append(row.clase)
    return np.asarray(x, dtype=np.float32), np.asarray(y)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="splits/potato_splits.csv")
    parser.add_argument("--output", default="models/flora_baseline.joblib")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    manifest = ROOT / args.manifest
    if not manifest.is_file():
        raise SystemExit(f"No existe {manifest}.")
    out = ROOT / args.output
    if out.exists() and not args.overwrite:
        raise SystemExit(f"Ya existe {out}. Usá --overwrite solamente si querés reemplazarlo.")
    df = pd.read_csv(manifest)
    expected = {"path", "clase", "split"}
    if not expected.issubset(df.columns) or set(df.clase.unique()) != set(CLASSES):
        raise SystemExit("Manifiesto incompatible: se requieren path, clase, split y las 7 clases.")
    if not set(df.split.unique()).issubset({"train","val","test"}) or "train" not in df.split.values or "val" not in df.split.values:
        raise SystemExit("Split inválido: debe haber train y val.")
    if df.path.duplicated().any():
        raise SystemExit("Una misma ruta se repite; revisar leakage antes de entrenar.")
    train_df, val_df = df[df.split=="train"],df[df.split=="val"]
    print(f"Entrenando baseline supervisado con {len(train_df)} imágenes; validando con {len(val_df)}. TEST NO SE UTILIZA.")
    x_train,y_train=build(train_df)
    x_val,y_val=build(val_df)
    model=make_pipeline(StandardScaler(), LogisticRegression(max_iter=500, class_weight="balanced"))
    model.fit(x_train,y_train)
    preds=model.predict(x_val)
    report={"backend":"baseline", "trained_at":datetime.now(timezone.utc).isoformat(),
            "manifest":args.manifest,"classes":list(CLASSES),"train_samples":len(train_df),"val_samples":len(val_df),
            "macro_f1_validation":float(f1_score(y_val,preds,average="macro")),
            "balanced_accuracy_validation":float(balanced_accuracy_score(y_val,preds)),
            "note":"Baseline CPU experimental; NO es el modelo final de Brian ni está calibrado. Test intacto."}
    out.parent.mkdir(parents=True,exist_ok=True)
    joblib.dump(model,out)
    meta=out.with_suffix(".json")
    meta.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps(report,indent=2,ensure_ascii=False))
    print(f"Modelo local: {out} | Meta: {meta}")

if __name__=="__main__":
    main()
