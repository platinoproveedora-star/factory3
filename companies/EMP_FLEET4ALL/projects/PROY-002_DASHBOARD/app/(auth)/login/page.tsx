"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

const LOGIN_TIMEOUT_MS = 12000;

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    const controller = new AbortController();
    const timer = window.setTimeout(() => controller.abort(), LOGIN_TIMEOUT_MS);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), password }),
        signal: controller.signal,
      });
      const data = await res.json().catch(() => ({ ok: false, error: "Respuesta invalida del servidor" }));
      if (!res.ok || !data.ok) {
        setError(data.error || `Error al iniciar sesion (${res.status})`);
        return;
      }
      router.push("/dashboard");
    } catch (error) {
      const message = error instanceof Error && error.name === "AbortError"
        ? "El login tardo demasiado. Intenta otra vez."
        : "Error de conexion";
      setError(message);
    } finally {
      window.clearTimeout(timer);
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-white">Fleet4All</h1>
          <p className="text-muted text-sm mt-1">Tu plataforma de gestion de flotilla</p>
        </div>
        <div className="card">
          <h2 className="text-lg font-semibold mb-5">Iniciar sesion</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label">Usuario o correo electronico</label>
              <input
                type="text"
                className="input"
                placeholder="admintotal"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
                autoComplete="username"
              />
            </div>
            <div>
              <label className="label">Password</label>
              <input
                type="password"
                className="input"
                placeholder="admintotal"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </div>
            {error && (
              <p className="text-red-400 text-sm bg-red-900/20 border border-red-800 rounded-lg px-3 py-2">
                {error}
              </p>
            )}
            <button type="submit" className="btn-primary w-full" disabled={loading}>
              {loading ? "Entrando..." : "Entrar"}
            </button>
          </form>
          <p className="text-center text-sm text-muted mt-4">
            No tienes cuenta?{" "}
            <Link href="/register" className="text-primary hover:underline">
              Registrate
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
