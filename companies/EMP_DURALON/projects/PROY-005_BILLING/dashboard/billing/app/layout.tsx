import './globals.css';
import type { Metadata } from 'next';
import projectContext from '../project-context.json';

const companyLabel = projectContext.company_label || projectContext.company_id;

export const metadata: Metadata = {
  title: `${companyLabel} Billing`,
  description: 'Dashboard operativo de cobranza y pagos',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
