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
    <main className="flex min-h-screen items-center justify-center bg-paper px-5">
      <form onSubmit={submit} className="w-full max-w-sm border border-line bg-white p-5 shadow-sm">
        <h1 className="text-2xl font-semibold text-ink">Logistics4All</h1>
        <div className="mt-5 space-y-4">
          <div>
            <label className="label">Usuario o email</label>
            <input value={email} onChange={(event) => setEmail(event.target.value)} className="input" autoComplete="username" required />
          </div>
          <div>
            <label className="label">Contrasena</label>
            <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" className="input" autoComplete="current-password" required />
          </div>
          {error && <p className="border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>}
          <button disabled={loading} className="btn-primary w-full">{loading ? "Entrando..." : "Entrar"}</button>
        </div>
        <Link href={process.env.NEXT_PUBLIC_APPS4ALL_PORTAL_URL || "#"} className="mt-4 block text-center text-sm font-semibold text-steel">
          Apps4All
        </Link>
      </form>
    </main>
  );
}
