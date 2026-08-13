import { requireModuleSession } from "@/lib/guard";
import Nav from "@/components/Nav";
import SettingsForm from "./SettingsForm";

export default async function SettingsPage() {
  const user = await requireModuleSession();

  return (
    <div>
      <Nav active="settings" />
      <div className="mx-auto max-w-4xl px-5 py-6">
        <section>
          <p className="text-sm font-semibold uppercase tracking-[0.18em] text-moss">Configuración</p>
          <h1 className="mt-2 text-3xl font-semibold text-ink">Empresa / Configuración</h1>
          <p className="mt-1 text-sm leading-6 text-slate-600">
            Emisor fiscal, credenciales del PAC, CSD y series de folios. {user.company_name || user.company_id}.
          </p>
        </section>
        <SettingsForm />
      </div>
    </div>
  );
}
