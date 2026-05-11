"""Lee service.py de un skill y detecta patrones peligrosos o inseguros."""
from __future__ import annotations

import re
from pathlib import Path


_SKILLS_ROOT = Path(__file__).parent.parent.parent   # factory/skills/

_DANGEROUS_PATTERNS = [
    (r"\bos\.system\b",           "os.system — ejecución de comandos shell"),
    (r"\bsubprocess\b",           "subprocess — ejecución de procesos externos"),
    (r"\beval\s*\(",              "eval() — ejecución dinámica de código"),
    (r"\bexec\s*\(",              "exec() — ejecución dinámica de código"),
    (r"__import__\s*\(",          "__import__() — importación dinámica"),
    (r"\bpickle\b",               "pickle — deserialización insegura"),
    (r"\bopen\s*\(.+['\"]w['\"]", "open(..., 'w') — escritura de archivos"),
    (r"\bshutil\.rmtree\b",       "shutil.rmtree — borrado recursivo"),
    (r"\bos\.remove\b",           "os.remove — borrado de archivos"),
    (r"\bos\.unlink\b",           "os.unlink — borrado de archivos"),
    (r"DROP\s+TABLE",             "DROP TABLE — SQL destructivo"),
    (r"DELETE\s+FROM",            "DELETE FROM — SQL destructivo sin filtro visible"),
    (r"\bpassword\s*=\s*['\"][^'\"]+['\"]", "contraseña hardcodeada"),
    (r"\bsecret\s*=\s*['\"][^'\"]+['\"]",   "secret hardcodeado"),
    (r"api_key\s*=\s*['\"][^'\"]+['\"]",    "api_key hardcodeada"),
]

_DRY_RUN_PATTERN = re.compile(r"dry_run", re.IGNORECASE)


class SkillSafetyEvalService:

    def ejecutar(self, context: dict) -> dict:
        skill_name = (context.get("skill_name") or "").strip()
        source     = (context.get("source") or "internos").strip()

        if not skill_name:
            return {"ok": False, "error": "skill_name requerido"}

        skill_path = self._resolve_skill_path(skill_name, source)
        if not skill_path:
            return {"ok": False, "error": f"skill no encontrado: {skill_name}"}

        service_file = skill_path / "service.py"
        if not service_file.exists():
            return {"ok": False, "error": "service.py no encontrado"}

        code = service_file.read_text(encoding="utf-8", errors="replace")
        findings = self._analizar(code)
        has_dry_run = bool(_DRY_RUN_PATTERN.search(code))
        has_writes  = any(f["severidad"] == "alta" for f in findings)

        safe = len([f for f in findings if f["severidad"] == "alta"]) == 0
        score = 1.0 if safe else max(0.0, 1.0 - len(findings) * 0.15)

        return {
            "ok": True,
            "message": f"{'SEGURO' if safe else 'ADVERTENCIAS'} — {len(findings)} hallazgos",
            "data": {
                "skill_name": skill_name,
                "safe": safe,
                "score": round(score, 2),
                "tiene_dry_run": has_dry_run,
                "hallazgos": findings,
                "lineas_revisadas": len(code.splitlines()),
            },
        }

    def _analizar(self, code: str) -> list:
        findings = []
        lines = code.splitlines()
        for lineno, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for pattern, descripcion in _DANGEROUS_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    sev = "alta" if any(k in descripcion for k in ["eval", "exec", "pickle", "DROP", "contraseña", "secret", "api_key"]) else "media"
                    findings.append({
                        "linea": lineno,
                        "patron": pattern,
                        "descripcion": descripcion,
                        "severidad": sev,
                        "fragmento": stripped[:80],
                    })
        return findings

    def _resolve_skill_path(self, name: str, source: str) -> Path | None:
        roots = {
            "internos": _SKILLS_ROOT / "internos",
            "meta":     _SKILLS_ROOT / "meta",
            "eval":     _SKILLS_ROOT / "eval",
        }
        root = roots.get(source)
        if root is None:
            candidate = Path(source) / name
            if (candidate / "service.py").exists():
                return candidate
            return None
        candidate = root / name
        if (candidate / "service.py").exists():
            return candidate
        return None
