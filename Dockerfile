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

# Artefacto oficial de FLORA Diego v2 (release modelo-v2, comprobado por SHA-256).
# NO versionar el binario Keras en Git ni cambiar el orden de sus siete clases.
ENV FLORA_MODEL_PATH=/app/models/flora_effnetb0_diego_v2.keras \
    FLORA_MODEL_VERSION=diego-v2
RUN mkdir -p /app/models \
    && python -c "from urllib.request import urlretrieve; urlretrieve('https://github.com/flora-pe/flora/releases/download/modelo-v2/flora_effnetb0_diego_v2.keras', '/app/models/flora_effnetb0_diego_v2.keras')" \
    && echo "325ae7b678c0cd4093dc33f37f288ab6ffeca2051f019a9ffb85a1d155affe86  /app/models/flora_effnetb0_diego_v2.keras" | sha256sum -c -

USER 10001

CMD ["sh", "-c", "exec uvicorn mvp.api:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]
