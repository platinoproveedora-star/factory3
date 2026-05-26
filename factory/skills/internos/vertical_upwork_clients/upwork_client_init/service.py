from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


class UpworkClientInitService:
    def ejecutar(self, context: dict) -> dict:
        root = Path(context.get("clients_root") or "companies/EMP_FREELANCE_GROWTH/clients")
        registry_path = root / "registry.json"
        registry = self._read_json(registry_path) or {"next_number": 101, "clients": []}
        client_id = context.get("client_id") or f"UC-{int(registry.get('next_number', 101)):03d}"
        client_name = (context.get("client_name") or context.get("name") or "Cliente por definir").strip()
        slug = self._slug(client_name)
        folder = root / client_id
        now = datetime.utcnow().isoformat() + "Z"
        client = {
            "client_id": client_id,
            "client_name": client_name,
            "company_name": context.get("company_name", ""),
            "contact_name": context.get("contact_name", ""),
            "contact_email": context.get("contact_email", ""),
            "platform": context.get("platform", "upwork"),
            "status": context.get("status", "prospect"),
            "source_job_url": context.get("source_job_url", ""),
            "notes": context.get("notes", ""),
            "folder": str(folder).replace("\\", "/"),
            "created_at": now,
            "updated_at": now,
        }
        if not context.get("dry_run", False):
            root.mkdir(parents=True, exist_ok=True)
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "client.json").write_text(json.dumps(client, ensure_ascii=False, indent=2), encoding="utf-8")
            existing = [c for c in registry.get("clients", []) if c.get("client_id") != client_id]
            existing.append({"client_id": client_id, "client_name": client_name, "slug": slug, "status": client["status"], "folder": str(folder).replace("\\", "/")})
            registry["clients"] = sorted(existing, key=lambda c: c["client_id"])
            if not context.get("client_id"):
                registry["next_number"] = max(int(registry.get("next_number", 101)), int(client_id.split("-")[1]) + 1)
            registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"ok": True, "data": {"client": client, "client_id": client_id, "folder": str(folder), "registry": str(registry_path)}}

    def _read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _slug(self, text: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "cliente"
