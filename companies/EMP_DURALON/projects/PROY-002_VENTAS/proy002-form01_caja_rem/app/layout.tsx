import type { Metadata } from 'next';
import projectContext from '../project-context.json';
import './globals.css';

export const metadata: Metadata = {
  title: `Caja Remisiones - ${projectContext.company_label}`,
  description: `${projectContext.project_label} Ventas`,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="bg-slate-50 text-slate-900 antialiased">{children}</body>
    </html>
  );
}
