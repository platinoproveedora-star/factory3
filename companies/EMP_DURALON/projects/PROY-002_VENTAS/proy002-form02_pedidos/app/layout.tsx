import type { Metadata } from 'next';
import './globals.css';
import projectContext from '../project-context.json';

export const metadata: Metadata = {
  title: `${projectContext.company_label} Pedidos`,
  description: 'Captura movil de pedidos ERP',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
