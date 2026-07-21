import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Logistics4All",
  description: "Logistics4All"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
