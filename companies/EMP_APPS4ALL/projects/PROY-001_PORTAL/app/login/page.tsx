"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
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
      body: JSON.stringify({ email, password })
    });
    const json = await res.json().catch(() => ({}));
    setLoading(false);
    if (!res.ok) {
      setError(json.error || "No se pudo iniciar sesion");
      return;
    }
    router.push("/");
    router.refresh();
  }

  return (
    <main className="min-h-screen bg-[#f6f7f4] px-5 py-10">
      <section className="mx-auto grid min-h-[calc(100vh-5rem)] max-w-5xl items-center gap-8 md:grid-cols-[1.05fr_0.95fr]">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.22em] text-moss">Apps4All</p>
          <h1 className="mt-4 max-w-xl text-5xl font-semibold leading-tight text-ink">Un solo acceso para operar tus modulos.</h1>
          <p className="mt-5 max-w-lg text-base leading-7 text-slate-600">
            Portal central para Conta4All, Multi Shopper y Gastos. Preparado para multiempresa y cobro futuro con Stripe.
          </p>
        </div>
        <form onSubmit={submit} className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-ink">Iniciar sesion</h2>
          <label className="mt-5 block text-sm font-medium text-slate-600">
            Email
            <input
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="mt-2 w-full rounded-md border border-slate-200 px-3 py-2 outline-none focus:border-steel"
              type="email"
              autoComplete="email"
            />
          </label>
          <label className="mt-4 block text-sm font-medium text-slate-600">
            Password
            <input
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="mt-2 w-full rounded-md border border-slate-200 px-3 py-2 outline-none focus:border-steel"
              type="password"
              autoComplete="current-password"
            />
          </label>
          {error ? <p className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p> : null}
          <button disabled={loading} className="mt-5 w-full rounded-md bg-ink px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-50">
            {loading ? "Entrando..." : "Entrar"}
          </button>
        </form>
      </section>
    </main>
  );
}
