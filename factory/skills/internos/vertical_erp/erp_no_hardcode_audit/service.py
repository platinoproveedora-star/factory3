from __future__ import annotations

import re
from pathlib import Path


PATTERNS = [
    ("company_id", re.compile(r"\bEMP_[A-Z0-9_]+\b")),
    ("legacy_client_id", re.compile(r"\bUC-\d+\b")),
    ("schema", re.compile(r"\b[a-z][a-z0-9]*_proy\d{3,}\b")),
    ("project_code", re.compile(r"\bPROY-\d{3}\b")),
    ("render_url", re.compile(r"https?://[^\s'\"`]+onrender\.com")),
    ("vercel_url", re.compile(r"https?://[^\s'\"`]+vercel\.app")),
    ("service_role_secret", re.compile(r"SUPABASE_SERVICE_ROLE_KEY|SERVICE_ROLE_KEY")),
    ("write_key", re.compile(r"NEXT_PUBLIC_WRITE_KEY|FACTORY_WRITE_KEY")),
]

CODE_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
CONFIG_EXTENSIONS = {".json", ".yaml", ".yml", ".md", ".sql", ".example"}
SKIP_PARTS = {"node_modules", ".next", ".git", "__pycache__", "dist", "build", ".venv", "venv"}
ALLOWED_FILENAMES = {
    "project.json",
    "modules.json",
    "render.yaml",
    ".env.example",
    "schema.sql",
}


class ErpNoHardcodeAuditService:
    def ejecutar(self, context: dict) -> dict:
        if not isinstance(context, dict):
            return {"ok": False, "error": "context debe ser dict"}
        repo_root = Path(__file__).resolve().parents[5]
        raw_paths = context.get("paths") or context.get("scan_paths") or []
        if isinstance(raw_paths, str):
            raw_paths = [raw_paths]
        if not raw_paths:
            raw_paths = self._default_paths(context)
        if not raw_paths:
            return {"ok": False, "error": "paths requerido o company_id/project_code para resolver ruta"}

        findings = []
        for raw in raw_paths:
            root = Path(str(raw))
            if not root.is_absolute():
                root = repo_root / root
            if not root.exists():
                findings.append({"severity": "warning", "kind": "missing_path", "path": str(root), "line": 0, "match": "", "message": "ruta no existe"})
                continue
            files = [root] if root.is_file() else [path for path in root.rglob("*") if path.is_file() and not self._skip(path)]
            for path in files:
                findings.extend(self._scan_file(path, repo_root))

        blockers = [row for row in findings if row["severity"] == "blocker"]
        warnings = [row for row in findings if row["severity"] == "warning"]
        allowed = [row for row in findings if row["severity"] == "allowed"]
        return {
            "ok": not blockers,
            "data": {
                "ready": not blockers,
                "summary": {"blockers": len(blockers), "warnings": len(warnings), "allowed": len(allowed), "total": len(findings)},
                "blockers": blockers,
                "warnings": warnings,
                "allowed": allowed if context.get("include_allowed") else [],
                "scan_paths": [str(path) for path in raw_paths],
            },
            "error": f"{len(blockers)} hardcodes bloqueantes" if blockers else None,
        }

    def _default_paths(self, context: dict) -> list[str]:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        project_code = str(context.get("project_code") or "").strip()
        if not company_id:
            return []
        base = Path("companies") / company_id
        if project_code:
            return [str(base / "projects" / project_code)]
        return [str(base)]

    def _scan_file(self, path: Path, repo_root: Path) -> list[dict]:
        text = self._read_text(path)
        if text is None:
            return []
        rel = self._rel(path, repo_root)
        findings = []
        for line_no, line in enumerate(text.splitlines(), start=1):
            for kind, pattern in PATTERNS:
                for match in pattern.finditer(line):
                    severity = self._severity(path, kind, line)
                    findings.append(
                        {
                            "severity": severity,
                            "kind": kind,
                            "path": rel,
                            "line": line_no,
                            "match": match.group(0),
                            "message": self._message(severity, kind, path),
                        }
                    )
        return findings

    def _severity(self, path: Path, kind: str, line: str) -> str:
        name = path.name
        suffix = path.suffix.lower()
        lower = str(path).replace("\\", "/").lower()
        if name in ALLOWED_FILENAMES or suffix in CONFIG_EXTENSIONS or "/docs/" in lower:
            return "allowed"
        if kind in {"service_role_secret", "write_key"}:
            return "warning"
        if suffix in CODE_EXTENSIONS:
            if "process.env" in line or "os.getenv" in line or "context.get" in line:
                return "warning"
            return "blocker"
        return "warning"

    def _message(self, severity: str, kind: str, path: Path) -> str:
        if severity == "blocker":
            return f"{kind} fijo en codigo vendible; mover a contexto/config"
        if severity == "allowed":
            return f"{kind} permitido en documentacion/config"
        return f"{kind} requiere revision"

    def _skip(self, path: Path) -> bool:
        return any(part in SKIP_PARTS for part in path.parts)

    def _read_text(self, path: Path) -> str | None:
        try:
            if path.stat().st_size > 2_000_000:
                return None
            return path.read_text(encoding="utf-8-sig", errors="ignore")
        except Exception:
            return None

    def _rel(self, path: Path, repo_root: Path) -> str:
        try:
            return str(path.relative_to(repo_root)).replace("\\", "/")
        except ValueError:
            return str(path)
