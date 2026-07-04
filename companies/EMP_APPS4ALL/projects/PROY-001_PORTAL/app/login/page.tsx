"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState("");
  const [loading, setLoading]   = useState(false);

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
    if (!res.ok) { setError(json.error || "No se pudo iniciar sesion"); return; }
    router.push("/");
    router.refresh();
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-bg px-5">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-white">Apps4All</h1>
          <p className="mt-1 text-sm text-muted">Un solo acceso para todos tus módulos</p>
        </div>
        <form onSubmit={submit} className="card space-y-4">
          <div>
            <label className="label">Usuario o email</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} type="text" autoComplete="username" required className="input" placeholder="admintotal" />
          </div>
          <div>
            <label className="label">Contraseña</label>
            <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" autoComplete="current-password" required className="input" placeholder="••••••••" />
          </div>
          {error && <p className="rounded-lg border border-red-800 bg-red-900/30 px-3 py-2 text-sm text-red-400">{error}</p>}
          <button disabled={loading} className="btn-primary w-full">
            {loading ? "Entrando..." : "Entrar"}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-muted">
          ¿No tienes cuenta?{" "}
          <Link href="/signup" className="text-steel hover:underline">Regístrate gratis</Link>
        </p>
      </div>
    </main>
  );
}
