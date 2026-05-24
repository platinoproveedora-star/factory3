"""Service for security_gate - static analysis of external skills."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", "node_modules", ".venv", "venv"}
TEXT_EXTENSIONS = {
    ".md", ".py", ".txt", ".json", ".toml", ".yaml", ".yml",
    ".js", ".ts", ".mjs", ".cjs", ".sh", ".bash", ".ps1",
    ".cfg", ".ini", ".env", ".example",
}
CODE_EXTENSIONS = {".py", ".js", ".ts", ".mjs", ".cjs", ".sh", ".bash", ".ps1"}
PROMPT_EXTENSIONS = {".md", ".txt"}

SECRET_FILE_NAMES = {
    ".env", "credentials.json", "service-account.json", "id_rsa", "id_dsa",
    "id_ecdsa", "id_ed25519",
}
SECRET_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}

SECRET_PATTERNS = [
    (r"(?i)\b(api[_-]?key|secret|token|password|private[_-]?key)\b\s*[:=]", "SECRET-TEXT", "Possible secret assignment"),
    (r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----", "SECRET-KEY", "Private key material"),
    (r"(?i)anthropic_api_key|openai_api_key|github_token|aws_secret_access_key", "SECRET-NAMED", "Named credential reference"),
]

CODE_PATTERNS = [
    (r"\beval\s*\(", "CODE-EXEC", "eval can execute arbitrary code", "CRITICAL"),
    (r"\bexec\s*\(", "CODE-EXEC", "exec can execute arbitrary code", "CRITICAL"),
    (r"\bos\.system\s*\(", "CMD-EXEC", "os.system executes shell commands", "CRITICAL"),
    (r"\bos\.popen\s*\(", "CMD-EXEC", "os.popen executes shell commands", "CRITICAL"),
    (r"\bsubprocess\.\w+\([^)]*shell\s*=\s*True", "CMD-EXEC", "subprocess shell=True can allow injection", "CRITICAL"),
    (r"\brequests\.(post|put|patch)\s*\(", "NET-EXFIL", "Outbound write request can exfiltrate data", "CRITICAL"),
    (r"\bhttpx\.(post|put|patch|AsyncClient)\s*\(", "NET-EXFIL", "HTTP client can exfiltrate data", "CRITICAL"),
    (r"\bsocket\.(connect|create_connection)\s*\(", "NET-EXFIL", "Raw network connection", "CRITICAL"),
    (r"\bos\.environ(\.get)?\s*\([^)]*(SECRET|TOKEN|PASSWORD|PRIVATE|API_KEY)", "CRED-READ", "Reads sensitive env var", "CRITICAL"),
    (r"\b(shutil\.rmtree|os\.remove|os\.unlink)\s*\(", "FS-DESTRUCT", "Deletes files or directories", "HIGH"),
    (r"\bimportlib\.import_module\s*\(", "DYNAMIC-IMPORT", "Dynamic import needs review", "HIGH"),
    (r"\bpickle\.loads?\s*\(", "DESERIAL", "Unsafe deserialization", "HIGH"),
    (r"\byaml\.(load|unsafe_load)\s*\(", "DESERIAL", "Potential unsafe YAML load", "HIGH"),
    (r"\bbase64\.b64decode\s*\(", "OBFUSCATION", "Base64 decoding may hide payloads", "HIGH"),
]

PROMPT_PATTERNS = [
    (r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+instructions", "PROMPT-OVERRIDE", "Prompt override attempt", "CRITICAL"),
    (r"(?i)(disable|bypass|skip)\s+(safety|security|content)\s+(checks?|filters?|rules?)", "SAFETY-BYPASS", "Safety bypass instruction", "CRITICAL"),
    (r"(?i)(read|open|access|get)\s+.*(\.env|credentials|secrets?|api.?keys?|\.ssh|\.aws)", "PROMPT-EXFIL", "Instruction to access secrets", "CRITICAL"),
    (r"(?i)(send|upload|post|transmit|exfiltrate)\s+.*(file|data|contents?|secrets?)\s+.*\b(to|http|https|url|endpoint|server)\b", "PROMPT-EXFIL", "Instruction to transmit data", "CRITICAL"),
    (r"[​‌‍﻿­]", "HIDDEN-INSTR", "Invisible characters", "HIGH"),
]

TYPOSQUATS = {
    "reqeusts": "requests", "requets": "requests", "numpi": "numpy",
    "pyyaml2": "pyyaml", "djagno": "django", "flaskk": "flask", "httppx": "httpx",
}


@dataclass
class Finding:
    severity: str
    category: str
    file: str
    line: int
    pattern: str
    risk: str
    fix: str


class SecurityGateService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "verdict": "FAIL", "error": error}

        skill_path = Path(context["path"]).resolve()
        findings: list[Finding] = []

        self._scan_structure(skill_path, findings)
        self._scan_files(skill_path, findings)
        self._scan_dependencies(skill_path, findings)

        summary = self._summary(findings)
        verdict = self._verdict(summary, strict=context.get("strict", False))
        return {
            "ok": verdict != "FAIL",
            "verdict": verdict,
            "summary": summary,
            "skill_path": str(skill_path),
            "findings": [asdict(f) for f in findings],
        }

    # --- validacion ---

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not isinstance(context, dict):
            return False, "context debe ser un diccionario"
        path = context.get("path")
        if not path:
            return False, "path es requerido"
        if not isinstance(path, str):
            return False, "path debe ser texto"
        if not Path(path).exists():
            return False, f"path no existe: {path}"
        if not Path(path).is_dir():
            return False, f"path no es carpeta: {path}"
        if not isinstance(context.get("strict", False), bool):
            return False, "strict debe ser booleano"
        return True, None

    # --- scanners ---

    def _scan_structure(self, skill_path: Path, findings: list[Finding]) -> None:
        if not (skill_path / "SKILL.md").exists():
            findings.append(self._finding("HIGH", "STRUCTURE", "SKILL.md", 0, "missing", "Missing SKILL.md", "Add SKILL.md"))
        if not (skill_path / "skill.py").exists():
            findings.append(self._finding("HIGH", "STRUCTURE", "skill.py", 0, "missing", "Missing runtime entrypoint", "Add thin skill.py wrapper"))

    def _scan_files(self, skill_path: Path, findings: list[Finding]) -> None:
        for path in self._walk(skill_path):
            rel = str(path.relative_to(skill_path))
            if path.name in SECRET_FILE_NAMES or path.suffix.lower() in SECRET_SUFFIXES:
                findings.append(self._finding("CRITICAL", "SECRET-FILE", rel, 0, path.name, "Sensitive file in skill", "Remove secrets from skill package"))
            if path.is_symlink():
                findings.append(self._finding("CRITICAL", "FS-SYMLINK", rel, 0, rel, "Symlink can escape skill boundary", "Remove symlink"))
            if path.suffix.lower() in {".exe", ".dll", ".so", ".dylib", ".bin"}:
                findings.append(self._finding("CRITICAL", "BINARY", rel, 0, path.name, "Binary payload in skill", "Remove binary files"))
            if path.is_file() and path.stat().st_size > 1_000_000:
                findings.append(self._finding("INFO", "LARGE-FILE", rel, 0, str(path.stat().st_size), "Large file needs review", "Confirm file is required"))
            if path.suffix.lower() in TEXT_EXTENSIONS or path.name in SECRET_FILE_NAMES:
                self._scan_text_file(skill_path, path, findings)

    def _scan_text_file(self, skill_path: Path, path: Path, findings: list[Finding]) -> None:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return
        rel = str(path.relative_to(skill_path))
        for line_no, line in enumerate(lines, 1):
            stripped = line.strip()
            for regex, category, risk in SECRET_PATTERNS:
                if re.search(regex, line):
                    findings.append(self._finding("CRITICAL", category, rel, line_no, stripped[:140], risk, "Remove secret or replace with documented env contract"))
            if path.suffix.lower() in CODE_EXTENSIONS:
                for regex, category, risk, severity in CODE_PATTERNS:
                    if re.search(regex, line):
                        findings.append(self._finding(severity, category, rel, line_no, stripped[:140], risk, "Remove or justify and isolate this operation"))
            if path.suffix.lower() in PROMPT_EXTENSIONS:
                for regex, category, risk, severity in PROMPT_PATTERNS:
                    if re.search(regex, line):
                        findings.append(self._finding(severity, category, rel, line_no, stripped[:140], risk, "Remove hostile or hidden instruction"))

    def _scan_dependencies(self, skill_path: Path, findings: list[Finding]) -> None:
        req = skill_path / "requirements.txt"
        if req.exists():
            self._scan_requirements(req, skill_path, findings)
        package_json = skill_path / "package.json"
        if package_json.exists():
            self._scan_package_json(package_json, skill_path, findings)

    def _scan_requirements(self, req: Path, skill_path: Path, findings: list[Finding]) -> None:
        for line_no, raw in enumerate(req.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith("-r "):
                continue
            name = re.split(r"[<>=!\[]", line)[0].strip().lower()
            if name in TYPOSQUATS:
                findings.append(self._finding("HIGH", "DEPS-TYPOSQUAT", str(req.relative_to(skill_path)), line_no, line, f"Possible typo of {TYPOSQUATS[name]}", "Verify package name"))
            if "==" not in line and not line.startswith((".", "-e ")):
                findings.append(self._finding("INFO", "DEPS-UNPINNED", str(req.relative_to(skill_path)), line_no, line, "Unpinned Python dependency", "Pin exact versions when possible"))

    def _scan_package_json(self, package_json: Path, skill_path: Path, findings: list[Finding]) -> None:
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            findings.append(self._finding("HIGH", "DEPS-INVALID", str(package_json.relative_to(skill_path)), 0, "invalid json", "package.json invalid", "Fix JSON"))
            return
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        for name, version in deps.items():
            if name.lower() in TYPOSQUATS:
                findings.append(self._finding("HIGH", "DEPS-TYPOSQUAT", str(package_json.relative_to(skill_path)), 0, name, f"Possible typo of {TYPOSQUATS[name.lower()]}", "Verify package name"))
            if isinstance(version, str) and version.startswith(("^", "~", "*")):
                findings.append(self._finding("INFO", "DEPS-UNPINNED", str(package_json.relative_to(skill_path)), 0, f"{name}: {version}", "Loose npm version range", "Pin or review version range"))

    # --- helpers ---

    def _walk(self, root: Path):
        for path in root.rglob("*"):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.is_file() or path.is_symlink():
                yield path

    def _summary(self, findings: list[Finding]) -> dict:
        return {
            "critical": sum(1 for f in findings if f.severity == "CRITICAL"),
            "high": sum(1 for f in findings if f.severity == "HIGH"),
            "info": sum(1 for f in findings if f.severity == "INFO"),
            "total": len(findings),
        }

    def _verdict(self, summary: dict, strict: bool) -> str:
        if summary["critical"] > 0:
            return "FAIL"
        if summary["high"] > 0:
            return "FAIL" if strict else "WARN"
        return "PASS"

    def _finding(self, severity: str, category: str, file: str, line: int, pattern: str, risk: str, fix: str) -> Finding:
        return Finding(severity=severity, category=category, file=file, line=line, pattern=pattern, risk=risk, fix=fix)
