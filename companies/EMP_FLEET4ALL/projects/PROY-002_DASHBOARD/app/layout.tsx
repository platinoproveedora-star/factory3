import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Fleet4All",
  description: "Gestion de flotillas: viajes, cobranza, carta porte, liquidaciones, combustible y mantenimiento",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
