from __future__ import annotations
import os
from pathlib import Path

_TIPO_SKILL = {
    "post":     "vertical_instagram/ig_post_image",
    "reel":     "vertical_instagram/ig_post_reel",
    "carousel": "vertical_instagram/ig_post_carousel",
}


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


class IgContentOrchestratorService:

    def ejecutar(self, context: dict) -> dict:
        tipo = (context.get("tipo") or "post").strip().lower()
        tema = (context.get("tema") or "").strip()
        empresa_id = (context.get("empresa_id") or "").strip()
        publicar = context.get("publicar", False)
        dry_run = context.get("dry_run", True)
        tono = context.get("tono", "profesional")
        objetivo = context.get("objetivo", "engagement")
        audiencia = context.get("audiencia", "compradores de inmuebles")

        if not tema:
            return {"ok": False, "error": "tema requerido"}
        if tipo not in ("post", "reel", "carousel", "story"):
            return {"ok": False, "error": "tipo debe ser post|reel|carousel|story"}

        base_ctx = {
            "tema":      tema,
            "tono":      tono,
            "objetivo":  objetivo,
            "audiencia": audiencia,
            "dry_run":   dry_run,
        }

        # 1. Caption
        r_caption = _run("vertical_instagram/ig_caption_generator", {
            **base_ctx,
            "formato": tipo,
        })
        caption = r_caption.get("data", {}).get("caption", "") if r_caption.get("ok") else ""

        # 2. Hashtags
        r_hash = _run("vertical_instagram/ig_hashtag_generator", {
            **base_ctx,
            "caption": caption,
        })
        hashtags = r_hash.get("data", {}).get("hashtags", []) if r_hash.get("ok") else []
        hashtags_str = " ".join(hashtags) if hashtags else ""

        # 3. Alt text (solo para posts con imagen)
        alt_text = ""
        if tipo in ("post", "carousel"):
            r_alt = _run("vertical_instagram/ig_alt_text_generator", {
                "tema":    tema,
                "caption": caption,
            })
            alt_text = r_alt.get("data", {}).get("alt_text", "") if r_alt.get("ok") else ""

        caption_final = f"{caption}\n\n{hashtags_str}".strip() if hashtags_str else caption

        resultado = {
            "tipo":          tipo,
            "tema":          tema,
            "caption":       caption,
            "hashtags":      hashtags,
            "alt_text":      alt_text,
            "caption_final": caption_final,
            "publicado":     False,
            "post_id":       None,
        }

        if not publicar or dry_run:
            resultado["dry_run"] = dry_run
            return {"ok": True, "data": resultado}

        # 4. Publicar si se solicita y hay imagen/video en contexto
        skill_pub = _TIPO_SKILL.get(tipo)
        if not skill_pub:
            resultado["publicado"] = False
            resultado["publish_note"] = f"tipo={tipo} no tiene skill de publicación disponible"
            return {"ok": True, "data": resultado}

        access_token = context.get("access_token") or os.getenv("IG_ACCESS_TOKEN") or os.getenv("META_ACCESS_TOKEN") or ""
        ig_user_id = context.get("ig_user_id") or os.getenv("IG_USER_ID") or ""

        pub_ctx = {
            "ig_user_id":   ig_user_id,
            "access_token": access_token,
            "caption":      caption_final,
            "dry_run":      False,
        }
        if tipo == "post":
            pub_ctx["image_url"] = context.get("image_url", "")
        elif tipo == "reel":
            pub_ctx["video_url"] = context.get("video_url", "")
        elif tipo == "carousel":
            pub_ctx["media_urls"] = context.get("media_urls", [])

        r_pub = _run(skill_pub, pub_ctx)
        resultado["publicado"] = r_pub.get("ok", False)
        resultado["post_id"] = r_pub.get("data", {}).get("post_id") or r_pub.get("data", {}).get("media_id")
        resultado["publish_error"] = r_pub.get("error") if not r_pub.get("ok") else None

        return {"ok": True, "data": resultado}
