"""Service for onboard_new_account — orchestrates digital identity onboarding."""
from __future__ import annotations

from pathlib import Path


def _runner():
    from factory.engine import SkillLoader, SkillRunner
    root = Path(__file__).parent.parent.parent
    ext_root = root.parent / "externos"
    ext_root.mkdir(parents=True, exist_ok=True)
    loader = SkillLoader(internal_root=root, external_root=ext_root)
    return SkillRunner(loader)


def _run(name: str, ctx: dict) -> dict:
    return _runner().run(name, ctx, source="internos")


_PASOS_MANUALES_SIEMPRE = [
    "Crear cuenta de Instagram Business / Página de Facebook (Meta no permite creación vía API)",
    "Subir foto de perfil de Instagram (API de Instagram es solo lectura para este campo)",
    "Escribir bio de Instagram (API de Instagram es solo lectura para este campo)",
]


class OnboardNewAccountService:

    def ejecutar(self, context: dict) -> dict:
        company_id = (context.get("company_id") or "").strip()
        user_id = (context.get("user_id") or "").strip()
        modulo_code = (context.get("modulo_code") or "").strip()

        if not company_id:
            return {"ok": False, "error": "company_id requerido"}
        if not user_id:
            return {"ok": False, "error": "user_id requerido"}
        if not modulo_code:
            return {"ok": False, "error": "modulo_code requerido"}

        plataformas = context.get("plataformas") or []
        if not plataformas:
            return {"ok": False, "error": "plataformas requerido (instagram|facebook_page)"}

        tipo_negocio = (context.get("tipo_negocio") or "").strip()
        nombre = (context.get("nombre_negocio") or "").strip()
        if not tipo_negocio:
            return {"ok": False, "error": "tipo_negocio requerido"}
        if not nombre:
            return {"ok": False, "error": "nombre_negocio requerido"}

        dry_run = context.get("dry_run", False)
        pasos_completados: list[str] = []
        pasos_pendientes: list[str] = []
        errores: list[dict] = []
        posts_publicados: list[dict] = []

        # Paso -1: validar acceso — aborta si falla
        r_grant = _run("vertical_auth_security/security_access_grant", {
            "action": "check",
            "user_id": user_id,
            "company_id": company_id,
            "modulo_code": modulo_code,
        })
        if not r_grant.get("ok") or not r_grant.get("data", {}).get("has_access"):
            msg = r_grant.get("error") or "sin grant activo"
            return {"ok": False, "error": f"Acceso denegado a '{modulo_code}' para {user_id}@{company_id}: {msg}"}
        pasos_completados.append("paso_-1_validar_acceso")

        # Registrar onboarding en Supabase
        onboarding_id = None
        if not dry_run:
            r_ins = _run("vertical_supabase/supabase_insert_row", {
                "table": "digital_identity_onboarding",
                "row": {
                    "company_id": company_id,
                    "plataformas": plataformas,
                    "tipo_negocio": tipo_negocio,
                    "nombre_negocio": nombre,
                    "estado": "en_progreso",
                    "ig_business_account_id": context.get("ig_business_account_id"),
                    "fb_page_id": context.get("fb_page_id"),
                },
                "dry_run": False,
            })
            if r_ins.get("ok"):
                data = r_ins.get("data")
                if isinstance(data, list) and data:
                    onboarding_id = data[0].get("id")
                elif isinstance(data, dict):
                    onboarding_id = data.get("id")

        # Paso 1: verificar conexión Meta
        r_conn = _run("vertical_meta/meta_connection_check", {
            "access_token": context.get("access_token"),
            "page_id": context.get("fb_page_id"),
            "ig_user_id": context.get("ig_business_account_id"),
        })
        if r_conn.get("ok"):
            pasos_completados.append("paso_1_meta_connection_check")
        else:
            errores.append({"paso": "meta_connection_check", "error": r_conn.get("error")})

        # Paso 1b: identidad visual (solo si no hay logo aprobado)
        r_query = _run("vertical_supabase/supabase_query_table", {
            "table": "fb_identity",
            "filters": {"empresa_id": company_id, "estado_aprobacion": "aprobado"},
            "limit": 1,
            "dry_run": False,
        })
        identity_data = r_query.get("data") if r_query.get("ok") else None
        identity_exists = bool(isinstance(identity_data, list) and identity_data)

        if identity_exists:
            pasos_completados.append("paso_1b_identidad_visual_ya_aprobada")
        else:
            r_id_vis = _run("vertical_media_gen/identidad_visual", {
                "empresa_id": company_id,
                "nombre_empresa": nombre,
                "productos_o_servicios": context.get("productos_o_servicios") or [],
                "ubicacion": context.get("ubicacion") or "",
                "paleta_primaria": context.get("paleta_primaria") or "",
                "paleta_secundaria": context.get("paleta_secundaria") or "",
                "tono_marca": context.get("tono_marca") or "",
                "dry_run": dry_run,
            })
            if r_id_vis.get("ok"):
                pasos_completados.append("paso_1b_identidad_visual_generada")
                pasos_pendientes.append(
                    "Aprobar identidad visual antes de publicar — estado_aprobacion=pendiente en tabla fb_identity"
                )
            else:
                errores.append({"paso": "identidad_visual", "error": r_id_vis.get("error")})

        # Paso 2: contenido
        if tipo_negocio == "propiedad":
            r_content = _run("vertical_marketing/property_landing_content_generator", {
                "empresa_id": company_id,
                "nombre": nombre,
                "descripcion": context.get("descripcion") or "",
                "ubicacion": context.get("ubicacion") or "",
                "dry_run": dry_run,
            })
            if r_content.get("ok"):
                pasos_completados.append("paso_2_property_landing_content")
            else:
                errores.append({"paso": "property_landing_content_generator", "error": r_content.get("error")})
        else:
            r_cal = _run("vertical_marketing/content_calendar_generator", {
                "empresa_id": company_id,
                "nombre": nombre,
                "descripcion": context.get("descripcion") or "",
                "dry_run": dry_run,
            })
            if r_cal.get("ok"):
                pasos_completados.append("paso_2_content_calendar")
            else:
                errores.append({"paso": "content_calendar_generator", "error": r_cal.get("error")})

            r_copy = _run("vertical_marketing/copy_generator", {
                "empresa_id": company_id,
                "nombre": nombre,
                "descripcion": context.get("descripcion") or "",
                "tono": context.get("tono_marca") or "profesional",
                "dry_run": dry_run,
            })
            if r_copy.get("ok"):
                pasos_completados.append("paso_2_copy_generator")
            else:
                errores.append({"paso": "copy_generator", "error": r_copy.get("error")})

        # Paso 3: publicación Instagram
        if "instagram" in plataformas:
            ig_user_id = context.get("ig_business_account_id") or ""
            access_token = context.get("access_token") or ""
            fotos = context.get("fotos") or []
            videos = context.get("videos") or []
            descripcion = (context.get("descripcion") or "")[:2200]

            if len(fotos) >= 2:
                r_carousel = _run("vertical_instagram/ig_post_carousel", {
                    "ig_user_id": ig_user_id,
                    "access_token": access_token,
                    "media_items": [{"type": "IMAGE", "url": u} for u in fotos[:10]],
                    "caption": descripcion,
                    "dry_run": dry_run,
                })
                if r_carousel.get("ok"):
                    pasos_completados.append("paso_3_ig_carousel")
                    posts_publicados.append({"plataforma": "instagram", "tipo": "carousel", **(r_carousel.get("data") or {})})
                else:
                    errores.append({"paso": "ig_post_carousel", "error": r_carousel.get("error")})
            elif len(fotos) == 1:
                r_img = _run("vertical_instagram/ig_post_image", {
                    "ig_user_id": ig_user_id,
                    "access_token": access_token,
                    "image_url": fotos[0],
                    "caption": descripcion,
                    "dry_run": dry_run,
                })
                if r_img.get("ok"):
                    pasos_completados.append("paso_3_ig_post_image")
                    posts_publicados.append({"plataforma": "instagram", "tipo": "imagen", **(r_img.get("data") or {})})
                else:
                    errores.append({"paso": "ig_post_image", "error": r_img.get("error")})

            if videos:
                r_reel = _run("vertical_instagram/ig_post_reel", {
                    "ig_user_id": ig_user_id,
                    "access_token": access_token,
                    "video_url": videos[0],
                    "caption": descripcion,
                    "dry_run": dry_run,
                })
                if r_reel.get("ok"):
                    pasos_completados.append("paso_3_ig_reel")
                    posts_publicados.append({"plataforma": "instagram", "tipo": "reel", **(r_reel.get("data") or {})})
                else:
                    errores.append({"paso": "ig_post_reel", "error": r_reel.get("error")})

        # Paso 3: publicación Facebook Page
        if "facebook_page" in plataformas:
            fb_page_id = context.get("fb_page_id") or ""
            access_token = context.get("access_token") or ""
            fotos = context.get("fotos") or []
            descripcion = (context.get("descripcion") or "")[:63206]

            try:
                tipo_post = "foto" if fotos else "texto"
                fb_ctx: dict = {
                    "fb_page_id": fb_page_id,
                    "access_token": access_token,
                    "tipo_post": tipo_post,
                    "mensaje": descripcion,
                    "dry_run": dry_run,
                }
                if fotos:
                    fb_ctx["media_url"] = fotos[0]

                r_fb = _run("vertical_meta/meta_page_post", fb_ctx)
                if r_fb.get("ok"):
                    pasos_completados.append("paso_3_fb_page_post")
                    posts_publicados.append({"plataforma": "facebook_page", **(r_fb.get("data") or {})})
                else:
                    errores.append({"paso": "meta_page_post", "error": r_fb.get("error")})
            except Exception as exc:
                pasos_pendientes.append(
                    f"Publicar en Facebook Page manualmente — meta_page_post no disponible: {exc}"
                )

        # Paso 4: auto-respuesta Instagram
        if "instagram" in plataformas:
            ig_user_id = context.get("ig_business_account_id") or ""
            access_token = context.get("access_token") or ""

            r_ar = _run("vertical_instagram/ig_auto_responder", {
                "ig_user_id": ig_user_id,
                "access_token": access_token,
                "dry_run": dry_run,
            })
            if r_ar.get("ok"):
                pasos_completados.append("paso_4_ig_auto_responder")
            else:
                errores.append({"paso": "ig_auto_responder", "error": r_ar.get("error")})

            r_lead = _run("vertical_instagram/ig_comment_lead_detect", {
                "ig_user_id": ig_user_id,
                "access_token": access_token,
                "dry_run": dry_run,
            })
            if r_lead.get("ok"):
                pasos_completados.append("paso_4_ig_comment_lead_detect")
            else:
                errores.append({"paso": "ig_comment_lead_detect", "error": r_lead.get("error")})

        # Paso 5: sincronizar leads al pipeline de ventas
        access_token = context.get("access_token") or ""
        empresa_id_leads = context.get("empresa_id") or company_id

        ig_form_id = (context.get("ig_form_id") or "").strip()
        if "instagram" in plataformas:
            if ig_form_id:
                r_ig_leads = _run("vertical_instagram/ig_leads_sync", {
                    "form_id": ig_form_id,
                    "access_token": access_token,
                    "empresa_id": empresa_id_leads,
                    "dry_run": dry_run,
                })
                if r_ig_leads.get("ok"):
                    pasos_completados.append("paso_5_ig_leads_sync")
                else:
                    errores.append({"paso": "ig_leads_sync", "error": r_ig_leads.get("error")})
            else:
                pasos_pendientes.append(
                    "Sincronizar leads IG al pipeline — falta ig_form_id en context"
                )

        fb_form_id = (context.get("fb_form_id") or context.get("meta_form_id") or "").strip()
        if "facebook_page" in plataformas:
            if fb_form_id:
                r_meta_leads = _run("vertical_meta_ads/meta_leads_sync_to_sales", {
                    "form_id": fb_form_id,
                    "access_token": access_token,
                    "company_id": company_id,
                    "dry_run": dry_run,
                })
                if r_meta_leads.get("ok"):
                    pasos_completados.append("paso_5_meta_leads_sync_to_sales")
                else:
                    errores.append({"paso": "meta_leads_sync_to_sales", "error": r_meta_leads.get("error")})
            else:
                pasos_pendientes.append(
                    "Sincronizar leads FB al pipeline — falta fb_form_id en context"
                )

        auto_respuesta_activa = "paso_4_ig_auto_responder" in pasos_completados
        estado_final = "completo" if not errores else "parcial"
        pasos_pendientes_final = pasos_pendientes + _PASOS_MANUALES_SIEMPRE

        # Actualizar estado en Supabase
        if not dry_run and onboarding_id:
            _run("vertical_supabase/supabase_update_row", {
                "table": "digital_identity_onboarding",
                "values": {
                    "estado": estado_final,
                    "pasos_completados": pasos_completados,
                    "pasos_pendientes_manuales": pasos_pendientes_final,
                    "posts_publicados": posts_publicados,
                    "errores": errores,
                },
                "filters": {"id": onboarding_id},
                "dry_run": False,
            })

        return {
            "ok": True,
            "data": {
                "pasos_completados": pasos_completados,
                "pasos_pendientes_manuales": pasos_pendientes_final,
                "posts_publicados": posts_publicados,
                "auto_respuesta_activa": auto_respuesta_activa,
                "errores": errores,
            },
        }
