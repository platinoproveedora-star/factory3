"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function RegisterPage() {
  const router = useRouter();
  const [nombre, setNombre] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const res = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nombre, email, password }),
    });
    const data = await res.json().catch(() => ({}));
    setLoading(false);
    if (!res.ok || !data.ok) {
      setError(data.error || "No se pudo registrar");
      return;
    }
    router.push("/login");
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <form onSubmit={submit} className="card w-full max-w-sm">
        <p className="mb-1 text-sm text-muted">Nuevo acceso</p>
        <h1 className="mb-6 text-2xl font-bold">Multi Shopper</h1>
        {error && <div className="mb-4 rounded-lg border border-red-800 bg-red-900/20 px-3 py-2 text-sm text-red-300">{error}</div>}
        <label className="label">Nombre</label>
        <input className="input mb-4" value={nombre} onChange={(event) => setNombre(event.target.value)} />
        <label className="label">Email</label>
        <input className="input mb-4" type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
        <label className="label">Password</label>
        <input className="input mb-5" type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
        <button disabled={loading} className="btn-primary w-full">{loading ? "Guardando" : "Registrar"}</button>
        <Link href="/login" className="mt-4 block text-center text-sm text-muted hover:text-white">
          Volver a login
        </Link>
      </form>
    </main>
  );
}
