"use client";

import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";

export default function Nav({ email, empresa }: { email: string; empresa: string }) {
  const router = useRouter();

  async function handleLogout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
  }

  return (
    <nav className="sticky top-0 z-10 border-b border-border bg-card/50 backdrop-blur">
      <div className="mx-auto flex min-h-14 max-w-7xl items-center justify-between px-4">
        <div className="flex items-center gap-3">
          <span className="font-bold text-white">Gastos4All</span>
          <span className="rounded-full bg-primary/20 px-2 py-0.5 text-xs font-medium text-primary">
            {empresa}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted">{email}</span>
          <button
            onClick={handleLogout}
            className="btn-ghost inline-flex items-center gap-1 py-1 text-xs"
          >
            <LogOut size={13} /> Salir
          </button>
        </div>
      </div>
    </nav>
  );
}
