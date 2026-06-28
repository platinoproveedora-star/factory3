import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Conta4all",
  description: "Plataforma contable para México",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
