from __future__ import annotations
import json, os, urllib.request, urllib.parse, urllib.error
from pathlib import Path

_VERSION = "v24.0"
_UA = "FactoryFactory/0.1 (+https://github.com/)"


def _runner():
    from factory.engine import SkillLoader, SkillRunner
    root = Path(__file__).parent.parent.parent
    ext_root = root.parent / "externos"
    ext_root.mkdir(parents=True, exist_ok=True)
    loader = SkillLoader(internal_root=root, external_root=ext_root,
                         extra_roots={"meta": root.parent / "meta", "eval": root.parent / "eval"})
    return SkillRunner(loader)


def _run(name: str, ctx: dict) -> dict:
    return _runner().run(name, ctx, source="internos")


class IgListService:

    def ejecutar(self, context: dict) -> dict:
        tipo = (context.get("tipo") or "posts").strip().lower()

        if tipo == "leads":
            return self._list_leads(context)
        if tipo == "posts":
            return self._list_posts(context)
        if tipo == "comentarios":
            return self._list_comentarios(context)
        return {"ok": False, "error": "tipo debe ser posts|leads|comentarios"}

    def _list_posts(self, context: dict) -> dict:
        ig_user_id = (context.get("ig_user_id") or os.getenv("IG_USER_ID") or "").strip()
        access_token = (context.get("access_token") or os.getenv("IG_ACCESS_TOKEN") or os.getenv("META_ACCESS_TOKEN") or "").strip()
        limit = min(int(context.get("limit") or 20), 100)

        if not ig_user_id:
            return {"ok": False, "error": "ig_user_id requerido (o IG_USER_ID en env)"}
        if not access_token:
            return {"ok": False, "error": "access_token requerido"}

        params = {
            "fields": "id,caption,timestamp,like_count,comments_count,media_type,permalink",
            "limit":  limit,
            "access_token": access_token,
        }
        qs = urllib.parse.urlencode(params)
        url = f"https://graph.facebook.com/{_VERSION}/{ig_user_id}/media?{qs}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode())
            if "error" in data:
                return {"ok": False, "error": data["error"].get("message", str(data["error"]))}
            posts = data.get("data", [])
            return {"ok": True, "data": {"tipo": "posts", "items": posts, "total": len(posts)}}
        except urllib.error.HTTPError as exc:
            try:
                err = json.loads(exc.read().decode())
                msg = err.get("error", {}).get("message", str(exc))
            except Exception:
                msg = str(exc)
            return {"ok": False, "error": msg}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def _list_leads(self, context: dict) -> dict:
        empresa_id = (context.get("empresa_id") or "").strip()
        if not empresa_id:
            return {"ok": False, "error": "empresa_id requerido para tipo=leads"}
        result = _run("vertical_sales/sales_list", {
            "empresa_id": empresa_id,
            "canal":      "instagram%",
            "estado":     context.get("estado"),
            "limit":      context.get("limit", 50),
        })
        if not result.get("ok"):
            return result
        items = result["data"].get("leads") or result["data"].get("items") or []
        return {"ok": True, "data": {"tipo": "leads", "items": items, "total": len(items)}}

    def _list_comentarios(self, context: dict) -> dict:
        media_id = (context.get("media_id") or "").strip()
        access_token = (context.get("access_token") or os.getenv("IG_ACCESS_TOKEN") or os.getenv("META_ACCESS_TOKEN") or "").strip()
        limit = min(int(context.get("limit") or 50), 200)

        if not media_id:
            return {"ok": False, "error": "media_id requerido para tipo=comentarios"}
        if not access_token:
            return {"ok": False, "error": "access_token requerido"}

        params = {
            "fields": "id,text,timestamp,from,like_count",
            "limit":  limit,
            "access_token": access_token,
        }
        qs = urllib.parse.urlencode(params)
        url = f"https://graph.facebook.com/{_VERSION}/{media_id}/comments?{qs}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": _UA})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = json.loads(r.read().decode())
            if "error" in data:
                return {"ok": False, "error": data["error"].get("message", str(data["error"]))}
            comments = data.get("data", [])
            return {"ok": True, "data": {"tipo": "comentarios", "media_id": media_id, "items": comments, "total": len(comments)}}
        except urllib.error.HTTPError as exc:
            try:
                err = json.loads(exc.read().decode())
                msg = err.get("error", {}).get("message", str(exc))
            except Exception:
                msg = str(exc)
            return {"ok": False, "error": msg}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
