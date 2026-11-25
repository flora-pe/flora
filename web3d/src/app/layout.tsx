import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FLORA Vision | Inteligencia para el campo",
  description: "Visión inteligente agrícola: análisis de hojas de papa con inteligencia artificial.",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="es"><body>{children}</body></html>;
}
