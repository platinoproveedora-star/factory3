import Link from "next/link";
import { LogOut } from "lucide-react";
import type { SessionUser } from "@/lib/auth";

export function PortalShell({ user, children }: { user: SessionUser; children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#f6f7f4]">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4">
          <Link href="/" className="text-lg font-semibold text-ink">Apps4All</Link>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-sm font-medium text-ink">{user.email}</p>
              <p className="text-xs text-slate-500">{user.company_name || user.company_id}</p>
            </div>
            <form action="/api/auth/logout" method="post">
              <button className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-500 hover:bg-slate-50" title="Salir">
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
