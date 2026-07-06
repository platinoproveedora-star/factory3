import type { Metadata } from 'next';
import './globals.css';
import projectContext from '../project-context.json';

export const metadata: Metadata = {
  title: `${projectContext.company_label} Pedidos 2`,
  description: 'Pedidos moviles con conversion a remision',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
