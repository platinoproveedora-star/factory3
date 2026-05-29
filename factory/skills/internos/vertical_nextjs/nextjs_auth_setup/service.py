from __future__ import annotations

from pathlib import Path


class NextjsAuthSetupService:
    def ejecutar(self, context: dict) -> dict:
        out_dir = Path(context.get("output_dir") or ".")
        files = {"app/login/page.tsx": self._login(), "lib/auth.ts": self._auth()}
        if context.get("save", True):
            for rel, content in files.items():
                path = out_dir / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
        return {"ok": True, "data": {"files": sorted(files.keys()), "output_dir": str(out_dir), "note": "MVP placeholder; conectar auth real por cliente."}}

    def _login(self) -> str:
        return """export default function LoginPage() {
  return (
    <main className="grid min-h-screen place-items-center bg-slate-50">
      <form className="w-full max-w-sm rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="text-xl font-semibold">Acceso</h1>
        <input className="mt-4 w-full rounded-md border px-3 py-2" placeholder="Email" />
        <input className="mt-3 w-full rounded-md border px-3 py-2" placeholder="Password" type="password" />
        <button className="mt-4 w-full rounded-md bg-slate-950 px-3 py-2 text-white">Entrar</button>
      </form>
    </main>
  );
}
"""

    def _auth(self) -> str:
        return """export function authEnabled() {
  return process.env.NEXT_PUBLIC_AUTH_ENABLED === 'true';
}
"""

