import { NextResponse } from "next/server";


export async function GET() {
  try {
    const url = (process.env.FLORA_API_URL || "http://127.0.0.1:8085").replace(/\/$/, "");
    let headers: HeadersInit = {};
    if (process.env.FLORA_API_AUTH === "gcp") {
      const response = await fetch(
        `http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience=${encodeURIComponent(url)}`,
        { headers: { "Metadata-Flavor": "Google" }, cache: "no-store", signal: AbortSignal.timeout(5000) },
      );
      if (!response.ok) throw new Error("Auth no disponible");
      headers = { Authorization: `Bearer ${await response.text()}` };
    }
    const upstream = await fetch(`${url}/ready`, {
      headers,
      cache: "no-store",
      signal: AbortSignal.timeout(12000),
    });
    if (!upstream.ok) throw new Error(`Backend no disponible: ${upstream.status}`);
    const data: unknown = await upstream.json();
    if (typeof data !== "object" || data === null || !("status" in data) || data.status !== "ready") {
      throw new Error("Modelo no listo");
    }
    return NextResponse.json(data, { headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ status: "offline" }, { status: 503, headers: { "Cache-Control": "no-store" } });
  }
}
