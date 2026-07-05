from __future__ import annotations

import json
import re
from pathlib import Path


MODULE_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class Apps4AllAuthBridgeScaffoldService:
    def ejecutar(self, context: dict) -> dict:
        repo_root = Path(__file__).resolve().parents[5]
        project_path = self._project_path(repo_root, context)
        if not project_path.get("ok"):
            return project_path
        target = project_path["path"]
        project_json = self._read_json(target / "project.json")
        module_code = str(context.get("module_code") or project_json.get("module_code") or "").strip()
        if not MODULE_RE.match(module_code):
            return {"ok": False, "error": "module_code requerido con formato snake_case"}

        files = self._files(module_code, str(context.get("cookie_name") or f"{module_code}_token"))
        plan = [{"path": self._rel(target / rel, repo_root), "bytes": len(content)} for rel, content in files.items()]
        if context.get("dry_run", True):
            return {"ok": True, "message": "dry_run", "data": {"files": plan}}
        if context.get("confirm_scaffold") is not True:
            return {"ok": False, "error": "confirm_scaffold=true requerido para escribir"}

        overwrite = bool(context.get("overwrite", False))
        written = []
        for rel, content in files.items():
            path = target / rel
            if path.exists() and not overwrite:
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            written.append(self._rel(path, repo_root))
        return {"ok": True, "data": {"written": written, "skipped": len(files) - len(written)}}

    def _project_path(self, repo_root: Path, context: dict) -> dict:
        raw = str(context.get("project_path") or "").strip()
        if not raw:
            return {"ok": False, "error": "project_path requerido"}
        path = Path(raw)
        if not path.is_absolute():
            path = repo_root / path
        try:
            path.resolve().relative_to(repo_root.resolve())
        except ValueError:
            return {"ok": False, "error": "project_path fuera del repo"}
        if not path.exists():
            return {"ok": False, "error": "project_path no existe"}
        return {"ok": True, "path": path}

    def _files(self, module_code: str, cookie_name: str) -> dict[str, str]:
        auth_ts = f'''import {{ jwtVerify, SignJWT }} from "jose";
import {{ cookies }} from "next/headers";

export const COOKIE_NAME = "{cookie_name}";
export const APPS4ALL_COOKIE_NAME = "apps4all_token";
export const MODULE_CODE = "{module_code}";

export type SessionUser = {{
  sub: string;
  email: string;
  company_id: string;
  company_name?: string;
  modulo_code: string;
  role: string;
  grant_id?: string;
  plan_code?: string;
  subscription_status?: string;
  exp: number;
}};

function jwtSecret() {{
  const secret = process.env.PLATFORM_JWT_SECRET;
  if (!secret || secret.length < 32) throw new Error("PLATFORM_JWT_SECRET requerido >= 32 chars");
  return new TextEncoder().encode(secret);
}}

export async function signSession(payload: Omit<SessionUser, "exp">, maxAge = 7200) {{
  const now = Math.floor(Date.now() / 1000);
  return new SignJWT(payload).setProtectedHeader({{ alg: "HS256" }}).setIssuedAt(now).setExpirationTime(now + maxAge).sign(jwtSecret());
}}

export async function getSession(): Promise<SessionUser | null> {{
  const cookieStore = await cookies();
  const token = cookieStore.get(APPS4ALL_COOKIE_NAME)?.value || cookieStore.get(COOKIE_NAME)?.value;
  if (!token) return null;
  try {{
    const {{ payload }} = await jwtVerify(token, jwtSecret());
    const session = payload as unknown as SessionUser;
    return session.modulo_code === MODULE_CODE || session.modulo_code === "apps4all_portal" ? session : null;
  }} catch {{
    return null;
  }}
}}

export function cookieOptions(maxAge: number) {{
  return {{ httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "strict" as const, path: "/", maxAge }};
}}

export function activeSubscription(status?: string) {{
  return ["active", "trialing", "manual", "comped"].includes(String(status || "manual"));
}}
'''
        middleware_ts = f'''import {{ NextResponse }} from "next/server";
import {{ jwtVerify }} from "jose";

const COOKIE_NAME = "{cookie_name}";
const APPS4ALL_COOKIE_NAME = "apps4all_token";

function jwtSecret() {{
  return new TextEncoder().encode(process.env.PLATFORM_JWT_SECRET || "");
}}

export const middleware = async (req: any) => {{
  const publicPaths = ["/login", "/signup", "/_next", "/favicon.ico"];
  const publicPrefixes = ["/_next/static/"];
  const isPublic = publicPaths.includes(req.nextUrl.pathname) || publicPrefixes.some((prefix: string) => req.nextUrl.pathname.startsWith(prefix));
  const ssoToken = req.nextUrl.searchParams.get("sso");
  if (ssoToken) {{
    try {{
      await jwtVerify(ssoToken, jwtSecret());
      const cleanUrl = new URL(req.nextUrl);
      cleanUrl.searchParams.delete("sso");
      const res = NextResponse.redirect(cleanUrl);
      res.cookies.set(APPS4ALL_COOKIE_NAME, ssoToken, {{ httpOnly: true, secure: true, sameSite: "lax", path: "/", maxAge: 7200 }});
      return res;
    }} catch {{}}
  }}
  const session = req.cookies.get(COOKIE_NAME)?.value || req.cookies.get(APPS4ALL_COOKIE_NAME)?.value;
  if (isPublic && !session) return NextResponse.next();
  if (isPublic && session) return NextResponse.redirect(new URL("/", req.url));
  if (!isPublic && !session) return NextResponse.redirect(new URL("/login", req.url));
  return NextResponse.next();
}};

export const config = {{ matcher: ["/((?!api/auth/|api/|static|.*\\\\..*).*)"] }};
'''
        return {"lib/auth.ts": auth_ts, "middleware.ts": middleware_ts}

    def _read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            return {}

    def _rel(self, path: Path, repo_root: Path) -> str:
        try:
            return str(path.relative_to(repo_root)).replace("\\", "/")
        except ValueError:
            return str(path)
