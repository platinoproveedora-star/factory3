import Link from "next/link";
import { LogOut } from "lucide-react";
import type { SessionUser } from "@/lib/auth";

export function PortalShell({ user, children }: { user: SessionUser; children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-bg">
      <header className="sticky top-0 z-10 border-b border-border bg-card/50 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-3">
          <Link href="/" className="text-lg font-bold text-white">Apps4All</Link>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-sm font-medium text-slate-200">{user.email}</p>
              <p className="text-xs text-muted">{user.company_name || user.company_id}</p>
            </div>
            <form action="/api/auth/logout" method="post">
              <button className="btn-ghost inline-flex h-9 w-9 items-center justify-center p-0" title="Salir">
                <LogOut size={16} />
              </button>
            </form>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-5 py-6">{children}</main>
    </div>
  );
}
