import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Apps4All",
  description: "Portal central de modulos Factory3"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
