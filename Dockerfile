FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TF_CPP_MIN_LOG_LEVEL=2 \
    TF_NUM_INTRAOP_THREADS=1 \
    TF_NUM_INTEROP_THREADS=1 \
    OMP_NUM_THREADS=1 \
    FLORA_MODEL_BACKEND=keras

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-cloud-run.txt .

RUN pip install --no-cache-dir -r requirements-cloud-run.txt

COPY mvp/ /app/mvp/

# Modelo v1, descargado desde el Release oficial de Flora.
# Su integridad se verifica con el SHA-256 registrado.
RUN mkdir -p /app/models \
    && python -c "from urllib.request import urlretrieve; urlretrieve('https://github.com/flora-pe/flora/releases/download/modelo-v1/effnetb0_ft_opcion_B.keras', '/app/models/effnetb0_ft_opcion_B.keras')" \
    && echo "d2d73e2884f0c5731992cd7894fe73a663ab25d2ee9cd52f42956e7875602de4  /app/models/effnetb0_ft_opcion_B.keras" | sha256sum -c -

USER 10001

CMD ["sh", "-c", "exec uvicorn mvp.api:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]
