import { NextRequest, NextResponse } from "next/server";


const MAX_BYTES = 10 * 1024 * 1024;
const ALLOWED = new Set(["image/jpeg", "image/png", "image/webp"]);

async function backendHeaders(): Promise<HeadersInit> {
  if (process.env.FLORA_API_AUTH !== "gcp") return {};
  const audience = process.env.FLORA_API_URL;
  if (!audience) throw new Error("FLORA_API_URL no configurada");
  // En Cloud Run, Metadata Server emite el token ID de la cuenta de servicio del frontend.
  const endpoint = `http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience=${encodeURIComponent(audience)}`;
  const response = await fetch(endpoint, {
    headers: { "Metadata-Flavor": "Google" },
    cache: "no-store",
    signal: AbortSignal.timeout(5000),
  });
  if (!response.ok) throw new Error("No se obtuvo token de servicio");
  return { Authorization: `Bearer ${await response.text()}` };
}

export async function POST(request: NextRequest) {
  try {
    const type = request.headers.get("content-type") || "";
    if (!type.includes("multipart/form-data")) {
      return NextResponse.json({ detail: "Se requiere una fotografía." }, { status: 400 });
    }
    const form = await request.formData();
    const file = form.get("file");
    if (!(file instanceof File) || !ALLOWED.has(file.type)) {
      return NextResponse.json({ detail: "Formato permitido: JPG, PNG o WebP." }, { status: 400 });
    }
    if (file.size === 0 || file.size > MAX_BYTES) {
      return NextResponse.json({ detail: "La fotografía debe pesar menos de 10 MB." }, { status: 413 });
    }
    const url = (process.env.FLORA_API_URL || "http://127.0.0.1:8085").replace(/\/$/, "");
    const upstreamForm = new FormData();
    upstreamForm.set("file", file, file.name);
    const upstream = await fetch(`${url}/predict`, {
      method: "POST",
      body: upstreamForm,
      headers: await backendHeaders(),
      cache: "no-store",
      signal: AbortSignal.timeout(120000),
    });
    const payload = await upstream.text();
    const responseType = upstream.headers.get("content-type") || "";
    if (!responseType.includes("application/json")) {
      return NextResponse.json({ detail: "El servicio de análisis no devolvió una respuesta válida." }, { status: 502 });
    }
    return new NextResponse(payload, {
      status: upstream.status,
      headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
    });
  } catch (error) {
    console.error("FLORA predict proxy:", error instanceof Error ? error.message : "Error interno");
    return NextResponse.json({ detail: "No pudimos completar el análisis. Intentá nuevamente." }, { status: 502 });
  }
}
