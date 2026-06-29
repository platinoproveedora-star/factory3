"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

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
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json().catch(() => ({}));
    setLoading(false);
    if (!res.ok || !data.ok) {
      setError(data.error || "No se pudo iniciar sesion");
      return;
    }
    router.push("/dashboard");
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <form onSubmit={submit} className="card w-full max-w-sm">
        <p className="mb-1 text-sm text-muted">Purchasing IA Engine</p>
        <h1 className="mb-6 text-2xl font-bold">Multi Shopper</h1>
        {error && <div className="mb-4 rounded-lg border border-red-800 bg-red-900/20 px-3 py-2 text-sm text-red-300">{error}</div>}
        <label className="label">Email</label>
        <input className="input mb-4" type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
        <label className="label">Password</label>
        <input className="input mb-5" type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
        <button disabled={loading} className="btn-primary w-full">{loading ? "Entrando" : "Entrar"}</button>
        <Link href="/register" className="mt-4 block text-center text-sm text-muted hover:text-white">
          Crear acceso
        </Link>
      </form>
    </main>
  );
}
