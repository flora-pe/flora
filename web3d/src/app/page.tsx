"use client";

/* eslint-disable @next/next/no-img-element */
import { ChangeEvent, DragEvent, useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import type { VisualCategory } from "@/components/PotatoScene";

const PotatoScene = dynamic(() => import("@/components/PotatoScene"), {
  ssr: false,
  loading: () => <div className="hologram-loading">Inicializando visualizador tridimensional…</div>,
});

type Prediction = {
  class_id: string;
  label: string;
  confidence: number;
  model?: string;
  top_predictions?: Array<{ class_id: string; label?: string; confidence: number }>;
  needs_review?: boolean;
};

type PreviewState = { category: VisualCategory; intensity: number };
const STATES: Array<PreviewState & { name: string; subtitle: string; img: string }> = [
  { category: "Healthy", intensity: 0.18, name: "Healthy", subtitle: "sana", img: "/assets/states/healthy.webp" },
  { category: "Fungi", intensity: 0.46, name: "Fungi", subtitle: "hongos", img: "/assets/states/fungi.webp" },
  { category: "Pest", intensity: 0.72, name: "Pest", subtitle: "plagas", img: "/assets/states/pest.webp" },
  { category: "Virus", intensity: 0.94, name: "Virus", subtitle: "virus", img: "/assets/states/virus.webp" },
];
const CLASS_NAMES: Record<VisualCategory, string> = {
  Healthy: "Hoja sana", Fungi: "Posible enfermedad fúngica",
  Pest: "Posible daño por plagas", Virus: "Posible infección viral",
  Bacteria: "Posible enfermedad bacteriana", Nematode: "Posible daño por nematodos",
  Phytopthora: "Posible Phytophthora",
};
const MAX_BYTES = 10 * 1024 * 1024;
const ACCEPTED = new Set(["image/jpeg", "image/png", "image/webp"]);

function getCategory(value?: string): VisualCategory {
  const raw = (value ?? "").toLowerCase();
  if (raw.includes("healthy") || raw.includes("sana")) return "Healthy";
  if (raw.includes("fung")) return "Fungi";
  if (raw.includes("pest")) return "Pest";
  if (raw.includes("virus")) return "Virus";
  if (raw.includes("bact")) return "Bacteria";
  if (raw.includes("nemat")) return "Nematode";
  if (raw.includes("phyto")) return "Phytopthora";
  return "Healthy";
}
const fmt = (value: number) => `${(Math.max(0, Math.min(1, value)) * 100).toFixed(1)}%`;

function Icon({ name, size = 19 }: { name: "home" | "layers" | "chart" | "leaf" | "settings" | "upload" | "play" | "close" | "info" | "move" | "scan" | "spark"; size?: number }) {
  const props = { width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.85, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  const paths = {
    home: <><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z" /></>,
    layers: <><path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 16l9 5 9-5"/></>,
    chart: <><path d="M4 20V11m5 9V4m5 16v-8m5 8V7"/></>,
    leaf: <><path d="M20 4C9 4 4 10 4 17c0 2 1 3 3 3 7 0 13-5 13-16ZM5 19c3-5 7-8 12-11"/></>,
    settings: <><circle cx="12" cy="12" r="3"/><path d="M12 2v3m0 14v3M2 12h3m14 0h3M5 5l2.1 2.1m9.8 9.8L19 19M19 5l-2.1 2.1m-9.8 9.8L5 19"/></>,
    upload: <><path d="M12 16V4m-5 5 5-5 5 5"/><path d="M4 16v4h16v-4"/></>,
    play: <><path d="m8 5 11 7-11 7V5Z"/></>,
    close: <><path d="M6 6l12 12M18 6 6 18"/></>,
    info: <><circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v.1"/></>,
    move: <><path d="M12 3v18M3 12h18m-9-9-3 3m3-3 3 3m-3 15-3-3m3 3 3-3M3 12l3-3m-3 3 3 3m15-3-3-3m3 3-3 3"/></>,
    scan: <><path d="M7 3H5a2 2 0 0 0-2 2v2m14-4h2a2 2 0 0 1 2 2v2M3 17v2a2 2 0 0 0 2 2h2m14-4v2a2 2 0 0 1-2 2h-2M3 12h18"/></>,
    spark: <><path d="m12 3 2 7 7 2-7 2-2 7-2-7-7-2 7-2 2-7Z"/></>,
  };
  return <svg {...props} aria-hidden="true">{paths[name]}</svg>;
}
function Brand({ large = false }: { large?: boolean }) {
  return (
    <div className={`brand ${large ? "brand-large" : ""}`}>
      <img className="brand-mark" src="/assets/brand/flora-mark.svg" alt="" />
      <div className="brand-lettering"><div className="brand-name">FLORA</div><div className="brand-subline">VISIÓN INTELIGENTE AGRÍCOLA</div></div>
    </div>
  );
}

export default function Home() {
  const inputRef = useRef<HTMLInputElement>(null);
  const photoUrl = useRef<string | null>(null);
  const [page, setPage] = useState<"analyze" | "about">("analyze");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [status, setStatus] = useState<"checking" | "ready" | "offline">("checking");
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [demo, setDemo] = useState<PreviewState | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    fetch("/api/ready", { signal: ctrl.signal, cache: "no-store" })
      .then((r) => { if (!ctrl.signal.aborted) setStatus(r.ok ? "ready" : "offline"); })
      .catch(() => { if (!ctrl.signal.aborted) setStatus("offline"); });
    return () => { ctrl.abort(); if (photoUrl.current) URL.revokeObjectURL(photoUrl.current); };
  }, []);

  function chooseFile(next: File | null) {
    if (photoUrl.current) { URL.revokeObjectURL(photoUrl.current); photoUrl.current = null; }
    setPreview(null); setFile(null); setPrediction(null); setDemo(null); setError("");
    if (inputRef.current) inputRef.current.value = "";
    if (!next) return;
    if (!ACCEPTED.has(next.type)) { setError("Seleccioná una fotografía JPG, PNG o WebP."); return; }
    if (next.size === 0 || next.size > MAX_BYTES) { setError("La fotografía debe pesar menos de 10 MB."); return; }
    photoUrl.current = URL.createObjectURL(next);
    setFile(next); setPreview(photoUrl.current);
  }
  function onInput(event: ChangeEvent<HTMLInputElement>) { chooseFile(event.target.files?.[0] ?? null); }
  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault(); setDragging(false);
    if (!busy) chooseFile(event.dataTransfer.files?.[0] ?? null);
  }
  function reset() { chooseFile(null); setPage("analyze"); }

  async function analyze() {
    if (!file || busy) return;
    setBusy(true); setPrediction(null); setDemo(null); setError("");
    const form = new FormData(); form.set("file", file, file.name);
    try {
      const response = await fetch("/api/predict", { method: "POST", body: form });
      const data = await response.json() as Prediction & { detail?: string };
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "No pudimos completar el análisis.");
      if (!data.class_id || typeof data.confidence !== "number" || !Number.isFinite(data.confidence)) throw new Error("El motor devolvió un resultado incompleto.");
      setPrediction(data); setStatus("ready");
    } catch (e) { setError(e instanceof Error ? e.message : "No se pudo analizar la fotografía."); }
    finally { setBusy(false); }
  }

  const resultCategory = getCategory(prediction?.class_id);
  const activeScene: PreviewState = demo ?? (prediction
    ? { category: resultCategory, intensity: resultCategory === "Healthy" ? 0.12 : prediction.confidence }
    : { category: "Healthy", intensity: 0.18 });
  const top = prediction?.top_predictions?.filter((p) => typeof p.confidence === "number")?.slice(0, 3) ?? [];

  return (
    <div className="flora-page">
      <header className="masthead">
        <div className="masthead-brand"><Brand large /></div>
        <div className="masthead-divider" />
        <div className="masthead-message">
          <h1>Salud de cultivos<br />con <em>inteligencia artificial</em></h1>
          <p>Analizá, clasificá y conocé mejor tus cultivos mediante visión por computadora.</p>
        </div>
        <div className="masthead-photo" />
      </header>

      <div className="dashboard">
        <aside className="sidebar">
          <Brand />
          <nav className="sidebar-nav" aria-label="Navegación principal">
            <button type="button" className={`nav-link ${page === "analyze" ? "active" : ""}`} onClick={reset}><Icon name="home"/> Nueva evaluación</button>
            <div className="nav-link disabled" title="Próximamente"><Icon name="layers"/> Historial</div>
            <div className="nav-link disabled" title="Próximamente"><Icon name="chart"/> Análisis</div>
            <div className="nav-link disabled" title="Próximamente"><Icon name="leaf"/> Cultivos</div>
            <button type="button" className={`nav-link ${page === "about" ? "active" : ""}`} onClick={() => setPage("about")}><Icon name="settings"/> Acerca de FLORA</button>
          </nav>
          <div className="sidebar-bottom"><div className="farm-art" aria-hidden="true"/><div className={`engine ${status}`}><span className="engine-dot"/>{status === "ready" ? "Motor conectado · Keras" : status === "checking" ? "Conectando motor…" : "Motor sin conexión"}</div></div>
        </aside>

        <section className="workspace">
          {page === "about" ? (
            <section className="about-card">
              <p className="eyebrow">FLORA VISION · TECNOLOGÍA AGRÍCOLA</p>
              <h2>Inteligencia aplicada a la salud vegetal.</h2>
              <p>FLORA convierte una fotografía de hoja en información útil para cuidar tus cultivos. Con una evaluación visual rápida podés reconocer posibles problemas, conocer las causas más probables y decidir dónde conviene prestar atención primero.</p>
              <div className="about-benefits">
                <div><span>01</span><strong>Observá</strong><small>Analizá imágenes de hojas desde el campo o la oficina.</small></div>
                <div><span>02</span><strong>Comprendé</strong><small>Conocé la clasificación y otras posibles causas.</small></div>
                <div><span>03</span><strong>Actuá</strong><small>Priorizá qué plantas revisar con mayor detalle.</small></div>
              </div>
              <p>Una herramienta práctica para productores, asesores y equipos agrícolas que buscan observaciones más ágiles y decisiones mejor informadas. Los resultados son orientativos y se deben contrastar con la evaluación en campo.</p>
              <button type="button" className="analyze-button" onClick={() => setPage("analyze")}>Volver a la evaluación</button>
            </section>
          ) : (
            <>
              <div className="workspace-hero">
                <div className="workspace-hero-copy">
                  <p className="eyebrow">FLORA VISION · ANÁLISIS DE HOJAS</p>
                  <h2>Analizá la salud de tus cultivos<br/>con inteligencia artificial</h2>
                  <p>Subí la fotografía de una hoja y obtené una clasificación preliminar en segundos.</p>
                </div>
                <span className="workspace-hero-scan" aria-hidden="true" />
              </div>
              <div className="form-columns">
                <section className="column"><h3>Fotografía de la hoja</h3><div className="surface upload-surface">
                  <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" onChange={onInput} hidden />
                  <div
                    className={`upload-target ${dragging ? "dragging" : ""} ${preview ? "has-file" : ""}`}
                    onClick={() => inputRef.current?.click()}
                    onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); inputRef.current?.click(); } }}
                    onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                    onDragLeave={() => setDragging(false)}
                    onDrop={onDrop}
                    role="button" tabIndex={0} aria-label="Seleccionar una fotografía de hoja"
                  >
                    {preview ? <img className="uploaded-image" src={preview} alt="Hoja seleccionada para análisis"/> : (
                      <><div className="upload-symbol"><Icon name="upload" size={30}/></div><strong>Arrastrá una imagen aquí<br/>o seleccioná un archivo</strong><span>JPG, PNG o WebP · máximo 10 MB</span></>
                    )}
                  </div>
                  {file ? <div className="file-label"><span className="file-name">{file.name}</span><button type="button" onClick={() => chooseFile(null)} aria-label="Quitar fotografía"><Icon name="close" size={16}/></button></div> : null}
                  <button type="button" onClick={analyze} disabled={!file || busy} className="analyze-button"><Icon name="play" size={19}/>{busy ? "Analizando fotografía…" : "Analizar fotografía"}</button>
                  {error ? <div className="error" role="alert">{error}</div> : null}
                </div></section>

                <section className="column"><h3>Resultado del análisis</h3><div className="surface result-surface">
                  <div className="result-top">
                    <div className="result-icon"><Icon name="scan" size={28}/></div>
                    <div><div className="result-title">{prediction ? prediction.label || CLASS_NAMES[resultCategory] : "Esperando una fotografía"}</div><div className="result-subtitle">{prediction ? "Análisis completado" : "El resultado aparecerá acá"}</div></div>
                  </div>
                  <div className="confidence-label">Confianza del modelo</div>
                  <div className="confidence-number">{prediction ? fmt(prediction.confidence) : "—"}</div>
                  <div className="confidence-track"><div className="confidence-fill" style={{ width: prediction ? fmt(prediction.confidence) : "0%" }}/></div>
                  <div className="probabilities">
                    <p>{prediction ? "Otras hipótesis del modelo" : "Resultados de clasificación"}</p>
                    {top.length ? top.map((item) => (
                      <div className="prob-row" key={item.class_id}><div><span>{item.label || item.class_id}</span><span>{fmt(item.confidence)}</span></div><div className="prob-track"><i style={{ width: fmt(item.confidence) }}/></div></div>
                    )) : <div className="empty-predictions">Las probabilidades se mostrarán después del análisis.</div>}
                  </div>
                </div></section>
              </div>
            </>
          )}
        </section>

        <aside className="hologram-panel">
          <div className="hologram-heading"><h2>Lectura holográfica</h2><span className="active-badge"><i/> 3D ACTIVO</span></div>
          <div className="holo-stage" data-intensity={activeScene.intensity > .8 ? "high" : "normal"}>
            <div className="holo-stars" aria-hidden="true"/>
            <div className="hud-corner tl"/><div className="hud-corner tr"/><div className="hud-corner bl"/><div className="hud-corner br"/>
            <PotatoScene category={activeScene.category} intensity={activeScene.intensity} analyzing={busy}/>
            <div className="holo-tools" aria-hidden="true"><div className="holo-tool"><Icon name="leaf" size={26}/></div><div className="holo-tool"><Icon name="chart" size={26}/></div></div>
            <div className="holo-caption"><Icon name="move" size={13}/> Arrastrá para girar · Rueda para acercar</div>
            {demo ? <span className="preview-tag">VISTA PREVIA</span> : prediction ? <span className="preview-tag">{activeScene.category.toUpperCase()}</span> : null}
          </div>
          <div className="state-heading"><h3>Estados visuales</h3><span>EXPLORÁ LOS ESTADOS</span></div>
          <div className="state-thumbnails">
            {STATES.map((state) => (
              <button key={state.category} type="button" onClick={() => setDemo({ category: state.category, intensity: state.intensity })}
                className={`state-option ${demo?.category === state.category ? "selected" : ""}`} aria-pressed={demo?.category === state.category}>
                <img src={state.img} alt={`Estado visual de referencia: ${state.name}`}/><strong>{state.name}</strong><span>({state.subtitle})</span>
              </button>
            ))}
          </div>
          <div className="intensity-controls">
            <div className="intensity-head"><span>Intensidad visual</span><strong>{Math.round(activeScene.intensity * 100)}%</strong></div>
            <input type="range" min="0" max="100" step="1" value={Math.round(activeScene.intensity * 100)}
              onChange={(e) => setDemo({ category: activeScene.category, intensity: Number(e.target.value)/100 })}
              aria-label="Modificar la intensidad de los efectos holográficos" />
            <div className="intensity-scale"><span>Suave</span><span>Moderado</span><span>Marcado</span><span>Intenso</span></div>
          </div>
          <div className="hologram-bottom"><Icon name="spark" size={14}/> El visor muestra efectos gráficos; el modelo analiza hojas, no tubérculos.</div>
        </aside>
      </div>
    </div>
  );
}
