import type { Gasto } from './db';

export function gastosToCSV(gastos: Gasto[]): string {
  const header = 'folio,fecha,monto,descripcion,metodo_captura,vehiculo,categoria,nombre_usuario';
  const rows = gastos.map((g) =>
    [
      g.folio,
      g.fecha,
      g.monto,
      `"${(g.descripcion ?? '').replace(/"/g, '""')}"`,
      g.metodo_captura,
      `"${g.vehiculo ?? ''}"`,
      `"${g.categoria}"`,
      `"${g.nombre_usuario}"`,
    ].join(',')
  );
  return [header, ...rows].join('\n');
}

export function downloadCSV(filename: string, csv: string) {
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
