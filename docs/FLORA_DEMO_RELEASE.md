# FLORA Vision — release para demo (Diego v2 + Next.js 3D)

## Arquitectura

- Frontend público: **Next.js + React Three Fiber / Three.js**, servicio Cloud Run `flora-web`.
- Backend privado: **FastAPI**, servicio Cloud Run `flora-api`.
- Autenticación: `flora-web` invoca `flora-api` con **Google ID token** de la cuenta de servicio; no se publica la API directamente.
- Modelo: `flora_effnetb0_diego_v2.keras`, release [modelo-v2](https://github.com/flora-pe/flora/releases/tag/modelo-v2). La imagen Docker de API lo descarga en build y verifica SHA-256.
- URL de demo: https://flora-vision.cloud.run/

## Contrato

- Input: RGB `float32` 224 × 224 × 3, rango `[0, 255]` (no normalizar; reescalado incorporado en EfficientNetB0).
- Clases: `Bacteria`, `Fungi`, `Healthy`, `Nematode`, `Pest`, `Phytopthora`, `Virus`.
- API: `GET /ready`, `POST /predict` (`multipart/form-data`, campo `file`, JPG/PNG/WebP hasta 10 MB).
- Salida: `class_id`, `label`, `confidence`, `top_predictions`, `model`, `backend`, `needs_review`.
- La respuesta de `/ready` incluye `model_version=diego-v2`; Next.js reenvía este valor en `/api/ready`.

## Métricas y límites del modelo

- Test separado, 453 imágenes: accuracy 0,7572; macro-F1 0,7665; macro-recall 0,7883.
- Las confusiones Fungi/Pest son relevantes. Healthy precision publicada 0,5778 y Nematode tiene solo 11 muestras test.
- Evitar afirmar que la variación vs el viejo conjunto de validación mide una mejora comparable: no fueron evaluaciones con el mismo test.
- Los porcentajes del modelo **no miden severidad ni diagnóstico definitivo**. El holograma utiliza una intensidad visual ilustrativa.

## Despliegue controlado

Ver `FLORA_Cierre_Demo_Seguro.sh` (archivo entregado al equipo por separado). Comandos:

1. `prepare`: adapta el backend, agrega versión visible y valida el frontend.
2. `publish-branch`: crea commit y push en `feat/flora-3d-web` (no toca `main`).
3. `deploy-api`: compila, descarga modelo v2, comprueba checksum, valida Docker local, prueba canary privada y promueve si pasa.
4. `deploy-web`: compila Next, valida canary y predicción real end-to-end, luego promueve la revisión en `flora-web`.
5. `verify`: verifica la URL pública, backend v2 y servicios Cloud Run.

Recuperación: `rollback-api` y `rollback-web` restauran la revisión anterior guardada localmente en `~/.cache/flora-demo-release/`.

## Antes de la presentación

- Abrir en celular real (360–430 px) y escritorio.
- Cargar una foto real de hoja y comprobar clase, porcentaje y holograma.
- Verificar `https://flora-vision.cloud.run/api/ready` contiene `model_version: diego-v2`.
- Confirmar que `flora-api` sigue devolviendo HTTP 403 sin autenticación.
- Fusionar PRs #59 → #60 → #61 → nuevo PR de `feat/flora-3d-web`; integrar también `feat/diego-augmentation-model` a `main` tras revisar conflictos. No subir modelos `.keras` al repositorio.
