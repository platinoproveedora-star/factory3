import EmptyState from "@/components/empty-state";
import PageHeader from "@/components/page-header";
import StatusBadge from "@/components/status-badge";
import { fmtDate, getDashboardData } from "@/lib/data";

export default async function DocumentsPage() {
  const { data } = await getDashboardData();
  return (
    <div>
      <PageHeader title="Documentos" subtitle="Archivos cargados, texto extraido y estado IA" />
      {data.documents.length ? (
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[760px]">
            <thead className="table-head">
              <tr><th className="px-3 py-2">Folio</th><th>Archivo</th><th>Tipo archivo</th><th>Tipo documento</th><th>Estado</th><th>Fecha</th></tr>
            </thead>
            <tbody>
              {data.documents.map((row) => (
                <tr key={row.id}>
                  <td className="table-cell font-mono text-xs">{row.folio || "-"}</td>
                  <td className="table-cell">{row.file_name}</td>
                  <td className="table-cell">{row.file_type || "-"}</td>
                  <td className="table-cell">{row.document_type || "-"}</td>
                  <td className="table-cell"><StatusBadge value={row.processing_status || "pending"} /></td>
                  <td className="table-cell text-muted">{fmtDate(row.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <EmptyState label="Sin documentos" />}
    </div>
  );
}
