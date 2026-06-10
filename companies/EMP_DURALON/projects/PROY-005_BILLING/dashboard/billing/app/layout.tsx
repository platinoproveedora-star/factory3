import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Duralon Billing',
  description: 'Dashboard operativo de cobranza y pagos',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
