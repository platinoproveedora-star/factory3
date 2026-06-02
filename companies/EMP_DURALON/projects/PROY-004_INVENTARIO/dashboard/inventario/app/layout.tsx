import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Duralon Inventario',
  description: 'Dashboard operativo de inventario y kardex',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
