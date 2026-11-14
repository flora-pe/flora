# Flora MVP local — guía de instalación y demostración

## Alcance y resguardo del trabajo compartido

Esta PR de integración no modifica `src/`, `splits/`, `potato_agml/`, `main` ni `feat/balanceo`. No cambia el dataset ni las etiquetas. API, UI, pruebas y baseline están aislados en `mvp/`, `scripts/train_mvp_baseline.py` y `tests/`.

**Modelo preferido:** artefacto `models/effnetb0_ft_opcion_B.keras` entrenado por Brian (fuera de Git). La inferencia replica el preprocesamiento de `src/06_dataset_tf.py`: RGB → 224x224 → float32 [0,255], normalización interna de EfficientNetB0, clases en orden alfabético. Confirmar esta compatibilidad con el checkpoint concreto antes del merge.

**Plan de contingencia:** baseline supervisado que se entrena localmente con las imágenes REALES de AgML; NO es una predicción simulada. Tiene menos capacidad y no está validado comercialmente. El test queda intacto. Solo sirve para demostrar el flujo cuando el checkpoint de Brian no esté disponible.

## En Ubuntu WSL / macOS (desde la raíz del repo)

```bash
# Usá el entorno pyenv flora existente y comprobá que estás en la rama de integración.
python --version
python -m pip install -r requirements-mvp.txt

# Si no están las fotos en data/raw/potato_agml/ y tampoco en potato_agml/:
./scripts/download_data.sh

# Sin checkpoint de Brian: entrena baseline con el manifiesto actual, sin tocar test
python scripts/train_mvp_baseline.py

# API y frontend juntos; Ctrl+C detiene ambos
bash scripts/run_mvp_local.sh
```

Abre `http://127.0.0.1:8501` y subí una foto de una hoja. API Swagger: `http://127.0.0.1:8000/docs`, salud: `/health`, disponibilidad real: `/ready`.

Si faltan dependencias compatibles, ejecuta `python -m pip check` y revisa la versión de Python (3.10 a 3.12 recomendado). Preferí crear un virtualenv aislado antes de instalar si tu env `flora` tiene paquetes previos incompatibles.

## Usar el checkpoint de Brian en lugar del baseline

1. Brian comparte de manera autorizada el archivo `.keras`, idealmente junto con versión TensorFlow, clases, imagen 224x224, método de preprocesamiento y commit del código de entrenamiento. **No subir el archivo a Git.**
2. Guardar como `models/effnetb0_ft_opcion_B.keras` en la copia local; el directorio `models/` está ignorado.
3. Instalar la opción TensorFlow: `python -m pip install -r requirements-model-tf.txt`.
4. `FLORA_MODEL_BACKEND=keras bash scripts/run_mvp_local.sh`
5. Probar `/ready`, `/predict` y fotos de validación; verificar resultado vs notebook del entrenamiento.

Si `.keras` no existe, `/predict` responde HTTP 503 (no se inventa una predicción). Podés forzar el baseline con `FLORA_MODEL_BACKEND=baseline` si ambos modelos están presentes.

## Contrato de API

- `GET /health`: estado del proceso + si existe un archivo de modelo (no valida pesos)
- `GET /ready`: 200 si el modelo real carga, 503 en caso contrario
- `GET /classes`: siete clases en orden estable
- `POST /predict`: multipart/form-data, campo `file`, JPG/PNG/WebP hasta 10 MB; resultado `class_id`, `label`, `confidence`, `top_predictions`, `model`, `backend`, `needs_review`, `warning`

Las probabilidades NO están calibradas. La app no prescribe pesticidas ni indica áreas de fumigación; es una clasificación de imagen experimental.

## Comandos rápidos de prueba

```bash
PYTHONPATH=. python -m pytest -q tests/test_mvp.py
python -m pip check
curl -s http://127.0.0.1:8000/ready
curl -s -F 'file=@/RUTA/UNA_HOJA.jpg' http://127.0.0.1:8000/predict
```

## Tareas pendientes para el equipo

- **Diego:** reconciliar 2973 vs 3010; definir un único manifiesto verificado. **No** borrar datos ni regenerar splits de Brian sin acuerdo. El baseline y el checkpoint original deben mantener su manifiesto hasta reentrenar.
- **Brian:** entregar checkpoint y entorno de entrenamiento; revisar `/predict` contra su modelo. PR #58 no se mergea aquí.
- **Mikha:** revisión UX, smoke test real en WSL, aprobación de contrato y pruebas E2E. No mergear esta PR sin revisión.
- **Todos:** registrar resultados en GitHub Project, corregir backlog que todavía propone PyTorch y acordar si la versión final incorpora un modelo con mejor score.

## Limitaciones reconocidas

- Sin checkpoint disponible en esta PR; el baseline debe ser ENTRENADO localmente antes de tener predicciones.
- Las pruebas automatizadas usan imágenes sintéticas exclusivamente para verificar cableado, NO para afirmar desempeño sobre enfermedades reales.
- No existe aquí un estudio de calibración, auditoría cross-domain ni validación agronómica.
- Probar entorno de cada compañero; estas instrucciones no demuestran por sí solas que corre en sus tres máquinas.
