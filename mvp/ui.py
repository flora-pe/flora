"""Flora Vision MVP — Streamlit front end. API calls stay on the local machine."""
from __future__ import annotations

import os
import hashlib
import requests
import streamlit as st

API_URL = os.getenv("FLORA_API_URL", "http://127.0.0.1:8000").rstrip("/")
st.set_page_config(page_title="Flora | Inteligencia para el campo", page_icon="🌿", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Outfit:wght@500;600;700;800&display=swap');
html,body,[class*="css"],.stApp {font-family:'DM Sans',system-ui,sans-serif;}
.stApp {background:linear-gradient(155deg,#f7faf4 0%,#f0f5ea 50%,#fcfdfb 100%);color:#173c31;}
[data-testid="stHeader"] {background:transparent}
.block-container {max-width:1120px;padding-top:2rem;padding-bottom:3rem;}
h1,h2,h3 {font-family:'Outfit',system-ui,sans-serif!important;color:#153c30!important;letter-spacing:-.028em;}
.hero {background:linear-gradient(115deg,#123e30,#1c5b43);border-radius:22px;padding:2.2rem 2.5rem;color:#ecf9e9;box-shadow:0 18px 50px rgba(17,59,39,.16);}
.hero h1 {color:white!important;font-size:clamp(2rem,4.4vw,3.2rem);margin:0 0 .5rem;line-height:1.05;}
.hero p{font-size:1rem;color:#d1e8d5;max-width:650px;line-height:1.6;margin-bottom:0}
.eyebrow{font-size:.78rem;letter-spacing:.13em;text-transform:uppercase;color:#b1dec5;font-weight:700;margin-bottom:1rem}
.chip{display:inline-block;background:#e5f2e6;border:1px solid #c7dfc9;color:#235c42;border-radius:100px;padding:.4rem .85rem;font-size:.78rem;font-weight:700;margin-top:.8rem}
.section-label{font-size:.78rem;letter-spacing:.1em;text-transform:uppercase;font-weight:700;color:#62836f;margin:1.5rem 0 .5rem}
.result{border-radius:17px;padding:1.3rem 1.6rem;background:white;border:1px solid #dbe6dc;box-shadow:0 6px 25px rgba(16,65,35,.04)}
.result h2{margin:.3rem 0 .5rem;font-size:1.7rem}
.disclaimer{background:#fef8e8;color:#745a2f;border:1px solid #ecdfa9;border-radius:10px;padding:.8rem 1rem;margin-top:1rem;font-size:.86rem}
[data-testid="stFileUploader"]{background:white;border-radius:16px;padding:1rem;border:1px solid #dce8dc;}
[data-testid="stMetric"]{background:white;border-radius:12px;border:1px solid #dce8dc;padding:.7rem 1rem}
.stButton button[kind="primary"]{background:#1e6848;color:white;border-radius:10px;border:0;padding:.65rem 1.8rem;font-weight:700}
footer {visibility:hidden}
@media(max-width:700px){.hero{padding:1.5rem}.block-container{padding-left:1rem;padding-right:1rem}}

.confidence-card {
    background: #ffffff !important;
    color: #173c31 !important;
    border: 1px solid #dbe6dc;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin: .4rem 0 1rem;
}
.confidence-card .confidence-label {
    color: #425c50 !important;
    font-size: .88rem;
    font-weight: 600;
}
.confidence-card .confidence-value {
    color: #173c31 !important;
    font-family: 'Outfit', system-ui, sans-serif;
    font-size: 2.25rem;
    font-weight: 700;
    line-height: 1.2;
    margin-top: .35rem;
}

.flora-progress-track {
    width: 100%;
    height: 12px;
    background: #d9e7de !important;
    border: 1px solid #b5cdbe;
    border-radius: 999px;
    overflow: hidden;
    margin: .4rem 0 1.3rem;
}
.flora-progress-fill {
    height: 100%;
    background: #1e6848 !important;
    border-radius: 999px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""<div class="hero"><div class="eyebrow">FLORA VISION · PROTOTIPO EXPERIMENTAL</div><h1>Una mirada más clara<br>para cada hoja.</h1><p>Subí la fotografía de una hoja de papa. Flora analiza patrones visuales y devuelve una clasificación preliminar en siete categorías.</p></div>""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🌱 Flora Vision")
    st.caption("MVP del bootcamp · modo local")
    try:
        r = requests.get(f"{API_URL}/ready", timeout=4)
        if r.ok:
            info = r.json()
            st.success(f"Motor conectado · {info['backend']}")
        else:
            st.warning("API disponible, modelo pendiente")
    except requests.RequestException:
        st.error("API no conectada")
    st.caption(f"Servidor de predicción: `{API_URL}`")
    st.markdown("---")
    st.caption("El sistema no reemplaza una evaluación agronómica ni indica tratamientos químicos.")

st.markdown('<div class="section-label">01 / Nueva evaluación</div>', unsafe_allow_html=True)
left, right = st.columns([1,1],gap="large")
with left:
    st.subheader("Fotografía de la hoja")
    file = st.file_uploader("Elegí una imagen JPG, PNG o WebP", type=["jpg","jpeg","png","webp"], help="Preferentemente fotografía de una única hoja, enfocada y con buena luz.")
    if file:
        signature = hashlib.sha256(file.getvalue()).hexdigest()
        if st.session_state.get("flora_image_sig") != signature:
            st.session_state.pop("flora_result", None)
            st.session_state["flora_image_sig"] = signature
        st.image(file, caption="Imagen cargada · no se guarda en el servidor", use_container_width=True)
    else:
        st.info("📷 Subí una imagen para comenzar. La predicción se ejecuta localmente.")
    button = st.button("Analizar fotografía", type="primary", disabled=file is None, use_container_width=True)
with right:
    st.subheader("Resultado del análisis")
    if button and file is not None:
        st.session_state.pop("flora_result", None)
        with st.spinner("Analizando la imagen…"):
            try:
                res = requests.post(f"{API_URL}/predict", files={"file":(file.name,file.getvalue(),file.type or "image/jpeg")}, timeout=90)
                if res.status_code != 200:
                    try: detail = res.json().get("detail",res.text)
                    except ValueError: detail = res.text
                    st.error(f"No fue posible analizar la imagen: {detail}")
                else:
                    st.session_state["flora_result"] = res.json()
            except requests.RequestException as exc:
                st.error(f"No se pudo conectar a la API local ({type(exc).__name__}).")
    if "flora_result" in st.session_state:
        result = st.session_state["flora_result"]
        st.markdown(f'<div class="result"><div class="eyebrow" style="color:#5e8a70">Predicción preliminar</div><h2>{result["label"]}</h2><p>Motor: {result["model"]}</p></div>',unsafe_allow_html=True)
        st.markdown(
            '<div class="confidence-card">'
            '<div class="confidence-label">Confianza del modelo (no calibrada)</div>'
            f'<div class="confidence-value">{result["confidence"]:.1%}</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown("**Tres clases más probables**")
        for item in result["top_predictions"]:
            st.write(f'{item["class_id"]} · {item["confidence"]:.1%}')
            pct = max(0.0, min(100.0, float(item["confidence"]) * 100.0))
            st.markdown(
                f'<div class="flora-progress-track" role="progressbar" '
                f'aria-label="Probabilidad estimada" aria-valuemin="0" '
                f'aria-valuemax="100" aria-valuenow="{pct:.1f}">'
                f'<div class="flora-progress-fill" style="width:{pct:.1f}%"></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        if result["needs_review"]:
            st.warning("Requiere revisión humana: la confianza puede ser insuficiente o el modelo es preliminar.")
        st.markdown(f'<div class="disclaimer">{result["warning"]} No aplicar pesticidas basándose solo en este resultado.</div>',unsafe_allow_html=True)
    else:
        st.markdown('<div class="result"><h2>Tu resultado aparecerá acá</h2><p>Flora devolverá la clase más probable, otras hipótesis y advertencias de uso.</p></div>',unsafe_allow_html=True)
        st.caption("Categorías: Bacteria · Fungi · Healthy · Nematode · Pest · Phytopthora · Virus")
st.markdown("---")
st.caption("FLORA · Proyecto de Deep Learning | Datos experimentales; no validado para decisiones agronómicas de campo.")
