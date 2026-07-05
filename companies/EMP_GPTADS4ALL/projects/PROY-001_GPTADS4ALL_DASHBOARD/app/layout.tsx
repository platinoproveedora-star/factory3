import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GPTAds4All",
  description: "Campanas y creativos publicitarios por empresa"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
