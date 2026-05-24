"""Service for github_add_secret - adds a secret to a GitHub repository."""
from __future__ import annotations
import base64
import json
import os
import urllib.request


class GithubAddSecretService:

    def ejecutar(self, context: dict) -> dict:
        valido, error = self._validar(context)
        if not valido:
            return {"ok": False, "error": error}
        if context.get("dry_run", False):
            return {"ok": True, "message": "dry_run", "data": context}
        return self._ejecutar(context)

    def _validar(self, context: dict) -> tuple[bool, str | None]:
        if not isinstance(context, dict):
            return False, "context debe ser un diccionario"
        for field in ("repo", "name", "value"):
            if not context.get(field):
                return False, f"{field} es requerido"
        return True, None

    def _ejecutar(self, context: dict) -> dict:
        repo = context["repo"]
        name = context["name"].upper()
        value = context["value"]
        try:
            key_info = self._request("GET", f"/repos/{repo}/actions/secrets/public-key")
            encrypted = self._encrypt(key_info["key"], value)
            self._request("PUT", f"/repos/{repo}/actions/secrets/{name}", payload={
                "encrypted_value": encrypted,
                "key_id": key_info["key_id"],
            })
            return {"ok": True, "message": f"Secret '{name}' agregado a {repo}"}
        except ImportError:
            return {
                "ok": False,
                "error": "PyNaCl no instalado. Ejecuta: pip install PyNaCl",
                "manual": f"Ve a github.com/{repo}/settings/secrets/actions y agrega '{name}' manualmente",
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _encrypt(self, public_key_b64: str, value: str) -> str:
        from nacl import encoding, public
        pk = public.PublicKey(public_key_b64.encode("utf-8"), encoding.Base64Encoder)
        box = public.SealedBox(pk)
        encrypted = box.encrypt(value.encode("utf-8"))
        return base64.b64encode(encrypted).decode("utf-8")

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("GITHUB_TOKEN no configurada")
        data = json.dumps(payload).encode("utf-8") if payload else None
        req = urllib.request.Request(
            f"https://api.github.com{path}", data=data, method=method,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}
