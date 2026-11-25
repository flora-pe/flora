"""FLORA Vision — premium Streamlit UI, connected to the existing private API."""
from __future__ import annotations

import base64
import hashlib
from html import escape
from io import BytesIO

import requests
import streamlit as st
from PIL import Image, ImageOps, UnidentifiedImageError

from mvp.cloud_auth import api_headers

import os

API_URL = os.getenv("FLORA_API_URL", "http://127.0.0.1:8000").rstrip("/")
CLASSES = ("Bacteria", "Fungi", "Healthy", "Nematode", "Pest", "Phytopthora", "Virus")
MAX_BYTES = 10 * 1024 * 1024

st.set_page_config(
    page_title="FLORA | Visión inteligente agrícola",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap');
:root {--forest:#123e30;--green:#1e6848;--mint:#a6e3c0;--cyan:#9fd8d0;--ink:#173c31;--muted:#688175;--bg:#f4f7f1;}
html,body,.stApp,[data-testid="stSidebar"] {font-family:'DM Sans',sans-serif;color:var(--ink)}
.stApp {background:radial-gradient(circle at 80% 0%,#e3f3e9 0%,transparent 35%),linear-gradient(145deg,#f4f7f1,#f8faf7 60%,#edf4ed)}
h1,h2,h3 {font-family:'Outfit',sans-serif!important;color:var(--ink)!important;letter-spacing:-.035em}
[data-testid="stHeader"] {background:transparent}
.block-container {max-width:1620px;padding-top:1.1rem;padding-bottom:3rem}
[data-testid="stSidebar"] {background:linear-gradient(170deg,#f8fcf7,#e9f1e8);border-right:1px solid #d9e7db}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {padding-top:1.6rem}
[data-testid="stSidebar"] .stRadio label {font-weight:650}
[data-testid="stSidebar"] .stRadio [role="radiogroup"] {gap:.3rem}
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label {border-radius:11px;padding:.42rem .5rem}
[data-testid="stSidebar"] .stRadio [role="radiogroup"] label:has(input:checked) {background:#d9efe1}
.brand-lockup{display:flex;align-items:center;gap:11px;margin-bottom:17px}
.brand-glyph{display:grid;place-items:center;width:47px;height:47px;border-radius:14px;background:#123e30;box-shadow:0 7px 19px #123e3024;color:#aeffca;position:relative}
.brand-glyph:after{content:"";width:24px;height:26px;background:linear-gradient(145deg,#b9fc9e,#38b48b);border-radius:0 88% 0 88%;transform:rotate(18deg);box-shadow:0 0 13px #94edb088}.brand-glyph:before{content:"";position:absolute;width:2px;height:24px;background:#d0ffca;transform:rotate(45deg);z-index:1}.brand-name{font:800 1.75rem/1 'Outfit',sans-serif;letter-spacing:-.04em;color:#123e30}
.brand-sub{margin-top:4px;font-size:.63rem;letter-spacing:.12em;font-weight:700;color:#567867}
.side-status{border-radius:12px;padding:13px 15px;background:#dff2e6;color:#13633f;font-size:.78rem;font-weight:700;margin:14px 0}
.side-status.offline{background:#fff0e4;color:#946221}
.side-note{font-size:.75rem;line-height:1.6;color:#698275;margin-top:12px}
.side-divider{height:1px;background:#d7e5d9;margin:18px 0}
.side-kicker{font-size:.68rem;color:#7a9985;font-weight:750;letter-spacing:.12em;margin:10px 0}
.side-disabled{padding:7px 4px;color:#819487;font-size:.84rem}
.flora-hero{display:flex;align-items:center;justify-content:space-between;gap:20px;position:relative;overflow:hidden;min-height:270px;padding:2.1rem 2.6rem;border-radius:24px;background:radial-gradient(circle at 87% 44%,#21724d 0%,transparent 32%),linear-gradient(120deg,#092f25 0%,#15513b 75%,#1b6a43 100%);box-shadow:0 20px 45px #123e301c}
.hero-copy{position:relative;z-index:2;max-width:780px}
.kicker{color:#aaeac0;font-size:.68rem;letter-spacing:.19em;font-weight:800;margin-bottom:1.2rem}
.flora-hero h1{font-family:'Outfit',sans-serif!important;color:#fff!important;font-size:clamp(2rem,3.5vw,3.2rem);line-height:1.06;letter-spacing:-.05em;margin:0 0 1rem!important;font-weight:800}
.flora-hero p{color:#d5eadb;font-size:.95rem;line-height:1.65;max-width:640px;margin:0}
.hero-leaf-scene{position:relative;width:250px;height:220px;flex:0 0 250px}
.hero-leaf{position:absolute;width:135px;height:185px;left:57px;top:4px;border-radius:3% 92% 8% 92%;transform:rotate(30deg);background:linear-gradient(145deg,#9df48e,#358d46 47%,#0d693b 75%,#b1f3a2);border:2px solid #a5f48e;box-shadow:0 0 46px #9af89570, inset 6px 8px 22px #c9f9b73d;animation:leaffloat 5s ease-in-out infinite alternate}
.hero-leaf:after{content:'';position:absolute;left:50%;top:8%;width:2px;height:86%;background:#defcc2b7;transform:rotate(-38deg)}
.scan-corner{position:absolute;width:38px;height:38px;border-color:#80f7aa;border-style:solid;filter:drop-shadow(0 0 8px #63fda5)}
.scan-corner.tl{top:10px;left:13px;border-width:3px 0 0 3px;border-radius:9px 0 0 0}
.scan-corner.tr{top:10px;right:10px;border-width:3px 3px 0 0;border-radius:0 9px 0 0}
.scan-corner.bl{bottom:10px;left:13px;border-width:0 0 3px 3px;border-radius:0 0 0 9px}
.scan-corner.br{bottom:10px;right:10px;border-width:0 3px 3px 0;border-radius:0 0 9px 0}
.scan-line{position:absolute;left:12px;right:10px;height:2px;top:50%;background:linear-gradient(90deg,transparent,#abffd6,transparent);box-shadow:0 0 12px #3fffa6;animation:scanline 3.6s ease-in-out infinite alternate}
.section-eyebrow{font-size:.72rem;letter-spacing:.12em;color:#668a75;font-weight:800;margin:1.7rem 0 .2rem}
.panel-title{font:750 1.35rem/1.2 'Outfit',sans-serif;color:#133e30;margin:.6rem 0 1rem}
.flora-card{background:#fff;border:1px solid #dce9dd;border-radius:17px;padding:1.3rem;box-shadow:0 8px 26px #153c300a;margin:.45rem 0}
.flora-card .result-eyebrow{font-size:.67rem;color:#5d8f72;letter-spacing:.14em;font-weight:800;margin-bottom:.8rem}
.result-label{font:750 clamp(1.35rem,1.8vw,1.8rem)/1.19 'Outfit',sans-serif;color:#173e30;margin:.2rem 0 .8rem}
.result-model{font-size:.81rem;color:#688175}
.conf-label{font-size:.76rem;font-weight:700;color:#536e60}
.conf-number{font:800 2.6rem/1.2 'Outfit',sans-serif;color:#133e30;margin:.3rem 0}
.flora-progress{height:9px;width:100%;overflow:hidden;border-radius:999px;background:#e3eee7;margin:.3rem 0 1.1rem}
.flora-progress>div{height:100%;background:linear-gradient(90deg,#1e6848,#42a776);border-radius:999px}
.flora-warning{background:#fff6e1;border:1px solid #f1e4bc;border-radius:12px;color:#755a2a;padding:.85rem 1rem;font-size:.76rem;line-height:1.55;margin-top:.7rem}
.flora-empty{min-height:180px;display:flex;flex-direction:column;justify-content:center;color:#6c8778}
.flora-empty strong{font:700 1.3rem 'Outfit',sans-serif;color:#1a4736;margin-bottom:10px}
.preview-image{display:block;width:100%;max-height:350px;object-fit:contain;border-radius:14px;background:#e6eee7;box-shadow:0 10px 24px #183b2a0d}
.preview-caption{font-size:.72rem;color:#758d7e;margin:.5rem 0 1rem}
[data-testid="stFileUploader"]{background:#f8fbf9;padding:10px;border:1px solid #d9e9dc;border-radius:16px}
[data-testid="stFileUploader"] section{background:#f8fbf9;border-color:#b8d7c6;border-radius:12px}
.stButton>button[kind="primary"]{background:linear-gradient(110deg,#22825a,#07523a);color:white;border:0;border-radius:12px;min-height:46px;font-weight:750;box-shadow:0 9px 18px #0c5b3d20}
.stButton>button[kind="primary"]:hover{background:#124f39;color:white;border:0}
.holo-card{padding:1.15rem;background:linear-gradient(145deg,#062b22,#093d2e 70%,#0e4b34);border-radius:19px;color:#e9fff1;border:1px solid #247253;box-shadow:0 12px 30px #062d281c;overflow:hidden}
.holo-head{display:flex;justify-content:space-between;gap:8px;align-items:center;font-size:.72rem;font-weight:750;letter-spacing:.08em}
.holo-tag{background:#c2f59d;color:#19442e;padding:5px 8px;border-radius:99px;font-size:.56rem;letter-spacing:.07em;white-space:nowrap}
.holo-stage{position:relative;height:246px;border-radius:15px;margin:14px 0 12px;overflow:hidden;background:radial-gradient(ellipse at 50% 70%,#135c45,#063428 48%,#03221d 83%)}
.holo-stage:before{content:'';position:absolute;inset:0;background:repeating-linear-gradient(0deg,#b2ffe006 0 1px,transparent 1px 18px);pointer-events:none}
.holo-ring{position:absolute;left:12%;width:76%;height:45px;bottom:22px;border:2px solid #2febbe8c;border-radius:50%;box-shadow:0 0 19px #26efa586,inset 0 0 15px #20e7a366;animation:ringpulse 3s ease-in-out infinite}
.holo-ring.r2{left:25%;width:50%;bottom:32px;height:28px;opacity:.55;animation-delay:-1.5s}
.potato-float{position:absolute;inset:28px 13% 46px;display:grid;place-items:center;animation:floatpotato 4.1s ease-in-out infinite}
.potato-form{width:84%;height:134px;position:relative;transform:rotate(-13deg);border-radius:46% 51% 46% 48% / 50% 51% 52% 47%;background:radial-gradient(circle at 24% 29%,#fff2b8 0 5%,transparent 35%),radial-gradient(circle at 68% 74%,#8a5f2b 0,transparent 43%),radial-gradient(circle at 39% 45%,#dfbb72 15%,#b58b4d 58%,#805a30 100%);border:1px solid #ebd19a;box-shadow:inset -18px -15px 24px #5d482a80,inset 10px 8px 22px #fff1ba75,0 11px 30px #020e0abf,0 0 29px #4bf4bc70;overflow:hidden;animation:potatoturn 8s ease-in-out infinite alternate}
.potato-form:before{content:'';position:absolute;inset:0;border-radius:inherit;background:radial-gradient(circle at 14% 36%,#684526 0 2px,transparent 6px),radial-gradient(circle at 63% 27%,#624624 0 3px,transparent 7px),radial-gradient(circle at 43% 72%,#6b4b27 0 3px,transparent 6px),radial-gradient(circle at 81% 59%,#5e4526 0 3px,transparent 8px),radial-gradient(circle at 31% 48%,#8e6a3b 0 1px,transparent 5px);opacity:.8}
.potato-form:after{content:'';position:absolute;inset:0;border-radius:inherit;background:repeating-linear-gradient(12deg,transparent 0 23px,#54ffc24f 23px 24px),repeating-linear-gradient(97deg,transparent 0 32px,#54ffc235 32px 33px),linear-gradient(105deg,transparent 35%,#67ffd150 75%,#2ffec378 98%);mix-blend-mode:screen;opacity:.7}
.holo-scan{position:absolute;top:30%;left:8%;width:84%;height:3px;background:linear-gradient(90deg,transparent,#b8ffe9,transparent);box-shadow:0 0 16px #50ffca;animation:scanline 3s ease-in-out infinite alternate}
.holo-card.is-scanning .holo-scan{animation-duration:.65s}
.holo-card.is-scanning .potato-float{animation-duration:1.5s}
.holo-card.fungi .holo-stage{background:radial-gradient(ellipse at 50% 70%,#296b3e,#09372c 54%,#03221d)}
.holo-card.pest .potato-form:after{filter:hue-rotate(43deg);opacity:.9}
.holo-card.virus .potato-form:after{filter:hue-rotate(120deg);opacity:.9}
.holo-card.healthy .potato-form:after{opacity:.45}
.holo-foot{font-size:.77rem;color:#d5f0df;line-height:1.5}
.holo-state{font-weight:750;color:#b3efbe;margin:.6rem 0}
.holo-disclaimer{font-size:.68rem;color:#b8d5c6;line-height:1.5;border-top:1px solid #4a79658a;margin-top:13px;padding-top:12px}
.small-states{display:flex;gap:5px;flex-wrap:wrap;margin-top:11px}
.small-state{font-size:.65rem;color:#c8e7d3;border:1px solid #57937c70;padding:5px 7px;border-radius:8px}
.small-state.selected{background:#b2efc1;color:#164732;font-weight:800}
.bottom-note{color:#718e7a;font-size:.75rem;margin-top:22px;border-top:1px solid #d6e5d9;padding-top:16px}
@keyframes leaffloat{from{translate:0 0}to{translate:0 -11px}}
@keyframes floatpotato{0%,100%{transform:translateY(2px)}50%{transform:translateY(-10px)}}
@keyframes potatoturn{from{transform:rotate(-15deg) scaleX(1)}to{transform:rotate(-7deg) scaleX(.94)}}
@keyframes scanline{from{transform:translateY(-65px)}to{transform:translateY(75px)}}
@keyframes ringpulse{0%,100%{opacity:.6;transform:scale(.96)}50%{opacity:1;transform:scale(1.06)}}
@media(max-width:1100px){.hero-leaf-scene{width:155px;flex-basis:155px;transform:scale(.7);transform-origin:center}.flora-hero{padding:1.5rem}}
@media(max-width:720px){.hero-leaf-scene{display:none}.flora-hero{min-height:auto;padding:1.5rem}.flora-hero h1{font-size:2rem}.block-container{padding-left:1rem;padding-right:1rem}}
@media(prefers-reduced-motion:reduce){.potato-float,.potato-form,.holo-ring,.holo-scan,.hero-leaf,.scan-line{animation:none!important}}
</style>
""", unsafe_allow_html=True)


def headers() -> dict[str, str]:
    return api_headers(API_URL)


def holo_markup(category: str | None, analyzing: bool = False) -> str:
    state = category if category in CLASSES else "Sin evaluar"
    variant = category.lower() if category in CLASSES else "idle"
    mode = "is-scanning" if analyzing else ""
    state_text = "Analizando fotografía…" if analyzing else (f"Categoría: {state}" if category else "Esperando una imagen")
    pills = "".join(
        f'<span class="small-state {"selected" if c == category else ""}">{escape(c)}</span>'
        for c in ("Healthy", "Fungi", "Pest", "Virus")
    )
    return f"""
<div class="holo-card {variant} {mode}">
 <div class="holo-head"><span>VISUALIZACIÓN HOLOGRÁFICA</span></div>
 <div class="holo-stage"><div class="holo-ring"></div><div class="holo-ring r2"></div>
 <div class="potato-float"><div class="potato-form"></div></div><div class="holo-scan"></div></div>
 <div class="holo-state">{escape(state_text)}</div>
 <div class="small-states">{pills}</div>
</div>
"""


def preview_markup(raw: bytes) -> str:
    with Image.open(BytesIO(raw)) as original:
        image = ImageOps.exif_transpose(original)
        if image.width * image.height > 24_000_000:
            raise ValueError("La imagen supera 24 megapíxeles.")
        image.thumbnail((950, 950))
        output = BytesIO()
        image.convert("RGB").save(output, format="JPEG", quality=82)
    encoded = base64.b64encode(output.getvalue()).decode("ascii")
    return f'<img class="preview-image" alt="Vista previa de hoja cargada" src="data:image/jpeg;base64,{encoded}">'


with st.sidebar:
    st.markdown("""<div class="brand-lockup"><div class="brand-glyph"></div>
    <div><div class="brand-name">FLORA</div><div class="brand-sub">VISIÓN INTELIGENTE AGRÍCOLA</div></div></div>""", unsafe_allow_html=True)
    page = st.radio("Secciones", ("Nueva evaluación", "Acerca de FLORA"), label_visibility="collapsed")
    st.markdown('<div class="side-kicker">PRÓXIMAMENTE</div><div class="side-disabled">Historial de análisis</div><div class="side-disabled">Gestión de cultivos</div>', unsafe_allow_html=True)
    st.markdown('<div class="side-divider"></div>', unsafe_allow_html=True)
    try:
        response = requests.get(f"{API_URL}/ready", headers=headers(), timeout=18)
        ready = response.ok and response.json().get("status") == "ready"
        detail = "Motor conectado · Keras" if ready else "Motor no disponible"
    except Exception:
        ready, detail = False, "Motor no disponible"
    st.markdown(f'<div class="side-status {"" if ready else "offline"}">● {escape(detail)}</div>', unsafe_allow_html=True)
    st.markdown('<div class="side-note">Análisis inteligente de hojas de papa.</div>', unsafe_allow_html=True)

if page == "Acerca de FLORA":
    st.markdown('<div class="section-eyebrow">FLORA VISION / ACERCA DEL SISTEMA</div>', unsafe_allow_html=True)
    st.title("Inteligencia visual para la salud vegetal")
    st.write("FLORA clasifica fotografías de hojas de papa en siete categorías mediante un modelo EfficientNet-B0. Es una herramienta experimental de apoyo, no un diagnóstico agronómico.")
    st.info("La confianza reportada no mide severidad ni está calibrada. No tomar decisiones de tratamiento basándose únicamente en la predicción.")
    st.markdown("**Categorías:** " + " · ".join(CLASSES))
    st.stop()

st.markdown("""
<section class="flora-hero">
 <div class="hero-copy"><div class="kicker">FLORA VISION · INTELIGENCIA APLICADA AL CAMPO</div>
 <h1>Analizá la salud de las hojas<br>con inteligencia artificial.</h1>
 <p>Subí una fotografía de una hoja de papa y recibí una clasificación preliminar entre siete categorías. Visualizá las hipótesis del modelo de forma clara.</p></div>
 <div class="hero-leaf-scene" aria-hidden="true"><div class="hero-leaf"></div>
 <div class="scan-corner tl"></div><div class="scan-corner tr"></div><div class="scan-corner bl"></div><div class="scan-corner br"></div><div class="scan-line"></div></div>
</section>
<div class="section-eyebrow">01 / NUEVA EVALUACIÓN · VISIÓN COMPUTACIONAL</div>
""", unsafe_allow_html=True)

col_upload, col_result, col_holo = st.columns([1.15, 1.04, .99], gap="medium")
with col_holo:
    st.markdown('<div class="panel-title">Lectura holográfica</div>', unsafe_allow_html=True)
    hologram = st.empty()
    previous = st.session_state.get("flora_result")
    hologram.markdown(holo_markup(previous.get("class_id") if isinstance(previous, dict) else None), unsafe_allow_html=True)

with col_upload:
    st.markdown('<div class="panel-title">Fotografía de la hoja</div>', unsafe_allow_html=True)
    file = st.file_uploader("Subí una imagen JPG, PNG o WebP (máx. 10 MB)", type=["jpg", "jpeg", "png", "webp"])
    raw: bytes | None = None
    valid = False
    if file is not None:
        raw = file.getvalue()
        signature = hashlib.sha256(raw).hexdigest()
        if st.session_state.get("flora_image_sig") != signature:
            st.session_state["flora_image_sig"] = signature
            st.session_state.pop("flora_result", None)
            hologram.markdown(holo_markup(None), unsafe_allow_html=True)
        if len(raw) > MAX_BYTES:
            st.error("La imagen supera el máximo de 10 MB.")
        else:
            try:
                st.markdown(preview_markup(raw), unsafe_allow_html=True)
                st.markdown(f'<div class="preview-caption">{escape(file.name)}</div>', unsafe_allow_html=True)
                valid = True
            except (UnidentifiedImageError, ValueError, OSError):
                st.error("No se pudo interpretar la imagen. Probá con otro archivo.")
    else:
        if st.session_state.get("flora_image_sig"):
            st.session_state.pop("flora_image_sig", None)
            st.session_state.pop("flora_result", None)
            hologram.markdown(holo_markup(None), unsafe_allow_html=True)
        st.markdown('<div class="flora-card"><div class="flora-empty"><strong>Capturá una hoja para empezar</strong>Admitimos JPG, PNG y WebP. Elegí una fotografía nítida y bien iluminada.</div></div>', unsafe_allow_html=True)
    run = st.button("◈  Analizar fotografía", type="primary", use_container_width=True, disabled=not valid)
    if run and file is not None and raw is not None:
        st.session_state.pop("flora_result", None)
        hologram.markdown(holo_markup(None, analyzing=True), unsafe_allow_html=True)
        with st.spinner("Analizando la fotografía con EfficientNet-B0…"):
            try:
                res = requests.post(
                    f"{API_URL}/predict",
                    headers=headers(),
                    files={"file": (file.name, raw, file.type or "image/jpeg")},
                    timeout=120,
                )
                if res.ok:
                    st.session_state["flora_result"] = res.json()
                else:
                    try:
                        detail = res.json().get("detail", "Error de predicción")
                    except ValueError:
                        detail = "Error de predicción"
                    st.error(f"No se pudo analizar la fotografía: {detail}")
            except requests.RequestException as exc:
                st.error(f"No se pudo conectar a la API ({type(exc).__name__}).")
            except Exception:
                st.error("No se pudo autenticar con el servicio de predicción.")
        current = st.session_state.get("flora_result")
        hologram.markdown(holo_markup(current.get("class_id") if isinstance(current, dict) else None), unsafe_allow_html=True)

with col_result:
    st.markdown('<div class="panel-title">Resultado del análisis</div>', unsafe_allow_html=True)
    result = st.session_state.get("flora_result")
    if result and file is not None:
        label = escape(str(result.get("label", "Sin clasificación")))
        model = escape(str(result.get("model", "Modelo de clasificación")))
        conf = max(0., min(1., float(result.get("confidence", 0.))))
        st.markdown(f'''<div class="flora-card"><div class="result-eyebrow">PREDICCIÓN PRELIMINAR</div>
          <div class="result-label">{label}</div><div class="result-model">Motor: {model}</div></div>
          <div class="flora-card"><div class="conf-label">Confianza del modelo</div>
          <div class="conf-number">{conf:.1%}</div><div class="flora-progress"><div style="width:{conf*100:.1f}%"></div></div></div>''', unsafe_allow_html=True)
        st.markdown("**Tres categorías más probables**")
        for pred in result.get("top_predictions", [])[:3]:
            val = max(0., min(1., float(pred.get("confidence", 0.))))
            cls = escape(str(pred.get("class_id", "")))
            st.markdown(f'<div style="font-size:.81rem;color:#365c49">{cls} · {val:.1%}</div><div class="flora-progress"><div style="width:{val*100:.1f}%"></div></div>', unsafe_allow_html=True)
        if result.get("needs_review"):
            st.warning("La clasificación necesita revisión humana.")
    else:
        st.markdown('<div class="flora-card"><div class="flora-empty"><strong>Tu análisis aparecerá acá</strong>Descubrí la categoría detectada y los resultados del análisis.</div></div>', unsafe_allow_html=True)

st.markdown('<div class="bottom-note">FLORA · VISIÓN INTELIGENTE AGRÍCOLA · Tecnología aplicada a la salud vegetal.</div>', unsafe_allow_html=True)
