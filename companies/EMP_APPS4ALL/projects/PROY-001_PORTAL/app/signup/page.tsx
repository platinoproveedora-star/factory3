"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function SignupPage() {
  const router = useRouter();
  const [company_name, setCompanyName] = useState("");
  const [email, setEmail]             = useState("");
  const [password, setPassword]       = useState("");
  const [confirm, setConfirm]         = useState("");
  const [error, setError]             = useState("");
  const [loading, setLoading]         = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const res = await fetch("/api/auth/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ company_name, email, password, password_confirm: confirm })
    });
    const json = await res.json().catch(() => ({}));
    setLoading(false);
    if (!res.ok) { setError(json.error || "No se pudo crear la cuenta"); return; }
    router.push("/");
    router.refresh();
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-bg px-5">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-white">Apps4All</h1>
          <p className="mt-1 text-sm text-muted">Crea tu cuenta y empieza gratis</p>
        </div>
        <form onSubmit={submit} className="card space-y-4">
          <div>
            <label className="label">Nombre de empresa</label>
            <input value={company_name} onChange={(e) => setCompanyName(e.target.value)} type="text" required className="input" placeholder="Mi Empresa S.A." />
          </div>
          <div>
            <label className="label">Email</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" autoComplete="email" required className="input" placeholder="usuario@empresa.com" />
          </div>
          <div>
            <label className="label">Contraseña</label>
            <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" autoComplete="new-password" required minLength={8} className="input" placeholder="mínimo 8 caracteres" />
          </div>
          <div>
            <label className="label">Confirmar contraseña</label>
            <input value={confirm} onChange={(e) => setConfirm(e.target.value)} type="password" autoComplete="new-password" required className="input" placeholder="••••••••" />
          </div>
          {error && <p className="rounded-lg border border-red-800 bg-red-900/30 px-3 py-2 text-sm text-red-400">{error}</p>}
          <button disabled={loading} className="btn-primary w-full">
            {loading ? "Creando cuenta..." : "Crear cuenta"}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-muted">
          ¿Ya tienes cuenta?{" "}
          <Link href="/login" className="text-steel hover:underline">Inicia sesión</Link>
        </p>
      </div>
    </main>
  );
}
