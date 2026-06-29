import PageHeader from "@/components/page-header";

export default function SettingsPage() {
  const rows = [
    ["Schema", process.env.MULTI_SHOPPER_SCHEMA || "-"],
    ["Modulo", process.env.MULTI_SHOPPER_MODULE_CODE || "-"],
    ["Empresa", process.env.MULTI_SHOPPER_COMPANY_ID || "-"],
    ["Proyecto", process.env.MULTI_SHOPPER_PROJECT_CODE || "-"],
  ];
  return (
    <div>
      <PageHeader title="Configuracion" subtitle="Contexto runtime del dashboard" />
      <div className="card max-w-2xl">
        <div className="divide-y divide-border">
          {rows.map(([label, value]) => (
            <div className="flex items-center justify-between gap-4 py-3" key={label}>
              <span className="text-sm text-muted">{label}</span>
              <span className="font-mono text-sm text-slate-200">{value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
