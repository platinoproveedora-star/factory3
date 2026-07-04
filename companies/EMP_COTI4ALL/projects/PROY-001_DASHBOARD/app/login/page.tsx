"use client";

import { ArrowRight, ReceiptText, ShieldCheck } from "lucide-react";
import { useState } from "react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const json = await res.json().catch(() => ({}));
    setLoading(false);
    if (!res.ok) {
      setError(json.error || "No se pudo iniciar sesion");
      return;
    }
    window.location.assign("/cotizador");
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-8 text-slate-900">
      <section className="w-full max-w-md">
        <div className="mb-5 text-center text-white">
          <span className="inline-flex items-center gap-2 rounded-full border border-blue-300/40 bg-blue-500/15 px-3 py-1 text-xs font-semibold uppercase text-blue-100">
            <ShieldCheck size={14} /> Apps4All secure access
          </span>
          <h1 className="mt-4 text-3xl font-semibold text-white">Coti4All</h1>
          <p className="mt-2 text-sm leading-6 text-slate-300">
            Cotizaciones, margen y documento final para tu empresa.
          </p>
        </div>

        <form onSubmit={submit} className="rounded-xl border border-slate-200 bg-white p-6 shadow-2xl">
          <div className="text-center">
            <span className="mx-auto inline-flex h-12 w-12 items-center justify-center rounded-lg bg-blue-50 text-blue-700">
              <ReceiptText size={24} />
            </span>
            <h2 className="mt-4 text-xl font-semibold text-slate-950">Entrar al cotizador</h2>
            <p className="mt-1 text-sm text-slate-600">Usa tu cuenta autorizada de Apps4All.</p>
          </div>

          <div className="mt-6 space-y-4">
            <label className="block">
              <span className="mb-1 block text-sm font-semibold text-slate-700">Usuario o email</span>
              <input
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                type="text"
                autoComplete="username"
                required
                className="block w-full rounded-lg border border-slate-300 bg-white px-3 py-3 text-center text-base text-slate-950 outline-none placeholder:text-slate-400 focus:border-blue-600 focus:ring-2 focus:ring-blue-100"
                placeholder="admintotal"
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-sm font-semibold text-slate-700">Password</span>
              <input
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                autoComplete="current-password"
                required
                className="block w-full rounded-lg border border-slate-300 bg-white px-3 py-3 text-center text-base text-slate-950 outline-none placeholder:text-slate-400 focus:border-blue-600 focus:ring-2 focus:ring-blue-100"
                placeholder="admintotal"
              />
            </label>
          </div>

          {error && <p className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-center text-sm text-red-700">{error}</p>}

          <button
            disabled={loading}
            className="mt-5 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-3 text-base font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-60"
          >
            {loading ? "Entrando..." : "Entrar"} {!loading && <ArrowRight size={18} />}
          </button>
        </form>

        <div className="mt-4 grid gap-2 text-center sm:grid-cols-3">
          <LoginMetric label="Catalogo" value="Multiempresa" />
          <LoginMetric label="Margen" value="Preview" />
          <LoginMetric label="PDF" value="HTML" />
        </div>
      </section>
    </main>
  );
}

function LoginMetric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 px-4 py-3">
      <p className="text-xs font-semibold uppercase text-slate-400">{label}</p>
      <p className="mt-1 text-sm font-semibold text-white">{value}</p>
    </div>
  );
}
