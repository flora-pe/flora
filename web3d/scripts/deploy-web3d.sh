#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[[ -n "$ROOT" && -f "$ROOT/web3d/Dockerfile" ]] || { echo 'Ejecutá este script dentro de flora.' >&2; exit 1; }
[[ "$(git -C "$ROOT" branch --show-current)" == "feat/flora-3d-web" ]] || { echo 'Rama inesperada. No se despliega.' >&2; exit 1; }
[[ -z "$(git -C "$ROOT" status --porcelain -- web3d)" ]] || { echo 'Hay archivos de web3d sin guardar en Git. Hacé commit y push antes del despliegue.' >&2; exit 1; }
for cmd in docker gcloud curl git; do command -v "$cmd" >/dev/null || { echo "Falta $cmd" >&2; exit 1; }; done
PROJECT=flora-deep-learning
REGION=us-central1
SERVICE=flora-web
API_URL=https://flora-api-1024612601650.us-central1.run.app
EXPECTED_SA=flora-streamlit-invoker@flora-deep-learning.iam.gserviceaccount.com
IMAGE="us-central1-docker.pkg.dev/$PROJECT/cloud-run-source-deploy/flora-web:next3d-$(git -C "$ROOT" rev-parse --short HEAD)"
CURRENT_SA="$(gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" --format='value(spec.template.spec.serviceAccountName)')"
[[ "$CURRENT_SA" == "$EXPECTED_SA" ]] || { echo "Cuenta de servicio inesperada: $CURRENT_SA. No se modifica producción." >&2; exit 1; }
CURRENT_REV="$(gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" --format='value(status.traffic[0].revisionName)')"
[[ -n "$CURRENT_REV" ]] || { echo 'No se pudo establecer revisión anterior. No se modifica producción.' >&2; exit 1; }
DEFAULT_URL="$(gcloud run services describe "$SERVICE" --project "$PROJECT" --region "$REGION" --format='value(status.url)')"
printf '\nPreflight OK: %s, revisión activa %s\n' "$SERVICE" "$CURRENT_REV"
printf 'Se actualizará la imagen de flora-web; se conserva la URL personalizada flora-vision.cloud.run.\n'
printf 'Imagen: %s\n' "$IMAGE"
printf 'La API permanece privada y se utilizará la cuenta %s\n\n' "$EXPECTED_SA"
# No force: explicit action to deploy requires user passing --deploy.
if [[ "${1:-}" != '--deploy' ]]; then
  echo "Este es un preflight seguro. Para desplegar realmente ejecutá: bash scripts/deploy-web3d.sh --deploy"
  exit 0
fi
cd "$ROOT"
gcloud auth configure-docker us-central1-docker.pkg.dev --quiet
docker build --platform linux/amd64 -f web3d/Dockerfile -t "$IMAGE" web3d
docker push "$IMAGE"
echo 'Actualizando Cloud Run...'
gcloud run deploy "$SERVICE" \
  --image="$IMAGE" \
  --project="$PROJECT" \
  --region="$REGION" \
  --service-account="$EXPECTED_SA" \
  --update-env-vars="FLORA_API_URL=$API_URL,FLORA_API_AUTH=gcp" \
  --memory=1Gi --cpu=1 --min-instances=0 --max-instances=1 --timeout=900
printf '\nValidando API privada desde el frontend público...\n'
if ! curl --fail --silent --show-error --retry 3 --retry-delay 3 --max-time 45 "$DEFAULT_URL/api/ready"; then
  echo 'El frontend no puede comunicarse correctamente con la API; restaurando revisión anterior.' >&2
  gcloud run services update-traffic "$SERVICE" --project="$PROJECT" --region="$REGION" --to-revisions="$CURRENT_REV=100"
  exit 1
fi
printf '\nDeploy verificado. Revisión anterior para rollback: %s\n' "$CURRENT_REV"
echo 'Frontend: https://flora-vision.cloud.run/'
echo 'Probá además una predicción de hoja real antes de dar el cambio por cerrado.'
