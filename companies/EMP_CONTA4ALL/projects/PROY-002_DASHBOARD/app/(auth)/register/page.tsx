"use client";
import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({ nombre: "", email: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const passwordRef = useRef<HTMLInputElement>(null);
  const confirmRef = useRef<HTMLInputElement>(null);

  function set(k: string) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((f) => ({ ...f, [k]: e.target.value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    const password = passwordRef.current?.value ?? "";
    const confirm = confirmRef.current?.value ?? "";
    if (password !== confirm) {
      setError("Las contraseñas no coinciden");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...form, password, modulo_code: "conta4all" }),
      });
      const data = await res.json();
      if (!data.ok) {
        setError(data.error || "Error al registrarse");
        return;
      }
      router.push("/login?registered=1");
    } catch {
      setError("Error de conexión");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-white">Conta4all</h1>
          <p className="text-muted text-sm mt-1">Crea tu cuenta</p>
        </div>
        <div className="card">
          <h2 className="text-lg font-semibold mb-5">Registro</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label">Nombre</label>
              <input type="text" className="input" placeholder="Juan Pérez" value={form.nombre} onChange={set("nombre")} required />
            </div>
            <div>
              <label className="label">Correo electrónico</label>
              <input type="email" className="input" placeholder="tu@correo.com" value={form.email} onChange={set("email")} required />
            </div>
            <div>
              <label className="label">Contraseña</label>
              <input ref={passwordRef} type="password" className="input" placeholder="Mínimo 8 caracteres" autoComplete="new-password" required minLength={8} />
            </div>
            <div>
              <label className="label">Confirmar contraseña</label>
              <input ref={confirmRef} type="password" className="input" placeholder="••••••••" autoComplete="new-password" required />
            </div>
            {error && (
              <p className="text-red-400 text-sm bg-red-900/20 border border-red-800 rounded-lg px-3 py-2">
                {error}
              </p>
            )}
            <button type="submit" className="btn-primary w-full" disabled={loading}>
              {loading ? "Creando cuenta..." : "Crear cuenta"}
            </button>
          </form>
          <p className="text-center text-sm text-muted mt-4">
            ¿Ya tienes cuenta?{" "}
            <Link href="/login" className="text-primary hover:underline">
              Inicia sesión
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
