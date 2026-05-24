from __future__ import annotations
import json
from pathlib import Path


class ActivitySkillPlanService:

    def ejecutar(self, context: dict) -> dict:
        actividad = (context.get("actividad") or context.get("activity") or "").strip()
        if not actividad:
            return {"ok": False, "error": "actividad requerido"}

        registry = self._registry()
        activity_type = self._classify(actividad, context)
        plan = self._build_plan(activity_type, actividad, context, registry)
        return {"ok": True, "data": plan}

    def _build_plan(self, activity_type: str, actividad: str, context: dict, registry: dict) -> dict:
        if activity_type == "meta_lead_ads_campaign":
            return self._meta_lead_ads_plan(actividad, context, registry)

        matches = self._search_registry(registry, actividad)
        return {
            "actividad": actividad,
            "tipo_detectado": activity_type,
            "resumen": "Plan generico basado en skills encontrados por texto.",
            "skills_sugeridos": matches[:20],
            "credenciales_requeridas": [],
            "datos_requeridos": ["objetivo", "audiencia", "oferta", "canales", "presupuesto", "fecha_inicio"],
            "orden_ejecucion": [
                {"paso": 1, "accion": "Definir objetivo y resultado esperado", "skills": []},
                {"paso": 2, "accion": "Buscar o crear skills faltantes", "skills": [m["nombre"] for m in matches[:5]]},
                {"paso": 3, "accion": "Ejecutar dry_run y revisar gaps", "skills": [m["nombre"] for m in matches[:5]]},
            ],
            "gaps": ["No hay plantilla especifica para esta actividad todavia."],
        }

    def _meta_lead_ads_plan(self, actividad: str, context: dict, registry: dict) -> dict:
        objetivo = context.get("objetivo") or context.get("goal") or "generar leads desde formulario instantaneo"
        vertical_destino = context.get("vertical_destino") or context.get("lead_destination") or self._lead_destination(actividad)
        preset = context.get("preset") or self._preset_for_activity(actividad)

        core_skills = [
            "vertical_meta_ads/meta_ads_connection_check",
            "vertical_meta_ads/meta_lead_form_create",
            "vertical_meta_ads/meta_ads_lead_campaign_flow",
            "vertical_ads/ads_approval_queue_create",
            "vertical_meta_ads/meta_ads_update_campaign",
            "vertical_meta_ads/meta_ads_get_insights",
        ]
        if vertical_destino == "rh":
            core_skills.append("vertical_meta_ads/meta_leads_sync_to_rh")
            core_skills.extend(["rh_basic_validation", "rh_duplicate_detector", "rh_candidate_scoring", "rh_pipeline_manager"])
        elif vertical_destino == "sales":
            core_skills.extend(["vertical_instagram/ig_leads_sync", "vertical_sales/lead_pipeline_system"])
        else:
            core_skills.append("vertical_meta_ads/meta_leads_sync_to_rh")

        existing, missing = self._split_existing(core_skills, registry)
        return {
            "actividad": actividad,
            "tipo_detectado": "meta_lead_ads_campaign",
            "objetivo": objetivo,
            "preset_formulario_sugerido": preset,
            "destino_leads": vertical_destino,
            "resumen": "Plan para crear una campana Meta Lead Ads: validar cuenta, crear formulario, crear campana pausada, aprobar, activar y sincronizar leads.",
            "credenciales_requeridas": [
                "META_ACCESS_TOKEN",
                "META_AD_ACCOUNT_ID",
                "META_PAGE_ID o IG_PAGE_ID",
                "META_PRIVACY_URL",
                "SUPABASE_URL",
                "SUPABASE_SERVICE_ROLE_KEY",
            ],
            "datos_requeridos": [
                "campaign_name",
                "message",
                "title",
                "daily_budget",
                "targeting",
                "privacy_url",
                "form_id despues de crear formulario",
                "imagen o asset creativo opcional",
            ],
            "skills_existentes": existing,
            "skills_faltantes": missing,
            "orden_ejecucion": [
                {"paso": 1, "accion": "Validar conexion Meta Ads y cuenta publicitaria", "skills": ["vertical_meta_ads/meta_ads_connection_check"], "salida": "ad_account_id valido"},
                {"paso": 2, "accion": "Crear formulario de leads en dry_run y luego real", "skills": ["vertical_meta_ads/meta_lead_form_create"], "salida": "form_id"},
                {"paso": 3, "accion": "Crear campana Lead Ads generica en PAUSED", "skills": ["vertical_meta_ads/meta_ads_lead_campaign_flow"], "salida": "campaign_id, adset_id, creative_id, ad_id"},
                {"paso": 4, "accion": "Crear aprobacion humana antes de gastar", "skills": ["vertical_ads/ads_approval_queue_create"], "salida": "decision aprobar/rechazar"},
                {"paso": 5, "accion": "Activar campana si fue aprobada", "skills": ["vertical_meta_ads/meta_ads_update_campaign"], "salida": "campaign ACTIVE"},
                {"paso": 6, "accion": "Sincronizar leads al destino operativo", "skills": self._sync_skills(vertical_destino), "salida": "leads/candidatos creados"},
                {"paso": 7, "accion": "Medir performance y optimizar", "skills": ["vertical_meta_ads/meta_ads_get_insights", "vertical_ads/ads_performance_analyzer", "vertical_ads/ads_optimizer"], "salida": "recomendaciones"},
            ],
            "payloads_minimos": {
                "meta_lead_form_create": {
                    "preset": preset,
                    "privacy_url": "https://.../privacidad",
                    "dry_run": True,
                },
                "meta_ads_lead_campaign_flow": {
                    "campaign_name": context.get("campaign_name") or "Campana Lead Ads - Prueba",
                    "form_id": "<FORM_ID>",
                    "message": context.get("message") or "Deja tus datos y te contactamos.",
                    "title": context.get("title") or "Solicita informacion",
                    "daily_budget": context.get("daily_budget") or 100,
                    "targeting": context.get("targeting") or {"geo_locations": {"countries": ["MX"]}},
                    "dry_run": True,
                },
            },
            "gaps": self._meta_gaps(registry, vertical_destino),
        }

    def _classify(self, actividad: str, context: dict) -> str:
        text = f"{actividad} {context.get('tipo', '')} {context.get('plataforma', '')}".lower()
        if ("meta" in text or "facebook" in text or "instagram" in text) and ("lead" in text or "form" in text or "campana" in text or "campaña" in text or "anuncio" in text):
            return "meta_lead_ads_campaign"
        if "campana" in text or "campaña" in text or "marketing" in text:
            return "marketing_campaign"
        return "generic"

    def _lead_destination(self, actividad: str) -> str:
        text = actividad.lower()
        if any(word in text for word in ("chofer", "vacante", "reclut", "candidato", "trabajo")):
            return "rh"
        if any(word in text for word in ("venta", "inmobiliaria", "propiedad", "cliente", "cotiza", "cotizacion")):
            return "sales"
        return "leads"

    def _preset_for_activity(self, actividad: str) -> str:
        text = actividad.lower()
        if any(word in text for word in ("chofer", "torton", "vacante", "trabajo")):
            return "reclutamiento_chofer_torton"
        if any(word in text for word in ("inmobiliaria", "propiedad", "casa", "departamento")):
            return "inmobiliaria_venta_propiedades"
        return "custom"

    def _sync_skills(self, destino: str) -> list[str]:
        if destino == "rh":
            return ["vertical_meta_ads/meta_leads_sync_to_rh", "rh_basic_validation", "rh_duplicate_detector"]
        if destino == "sales":
            return ["vertical_instagram/ig_leads_sync", "vertical_sales/lead_pipeline_system"]
        return ["vertical_meta_ads/meta_leads_sync_to_rh"]

    def _meta_gaps(self, registry: dict, destino: str) -> list[str]:
        gaps = []
        if "vertical_meta_ads/meta_webhook_lead_receive" not in registry:
            gaps.append("Falta webhook realtime generico para recibir leads sin sync manual.")
        if destino == "sales" and "vertical_meta_ads/meta_leads_sync_to_sales" not in registry:
            gaps.append("Falta sync directo Meta Leads -> Sales; hoy se puede adaptar con pipeline existente o crear skill dedicado.")
        if "asset_upload_public_url" not in registry:
            gaps.append("Falta skill generico para subir assets y obtener URL publica para creativos.")
        return gaps

    def _split_existing(self, names: list[str], registry: dict) -> tuple[list[dict], list[str]]:
        existing = []
        missing = []
        for name in names:
            item = registry.get(name)
            if item:
                existing.append({"nombre": name, "descripcion": item.get("descripcion", ""), "path": item.get("path", "")})
            else:
                missing.append(name)
        return existing, missing

    def _search_registry(self, registry: dict, text: str) -> list[dict]:
        terms = [t for t in text.lower().replace("/", " ").replace("_", " ").split() if len(t) > 3]
        scored = []
        for name, item in registry.items():
            haystack = f"{name} {item.get('descripcion', '')} {item.get('vertical', '')}".lower()
            score = sum(1 for term in terms if term in haystack)
            if score:
                scored.append((score, {"nombre": name, "descripcion": item.get("descripcion", ""), "path": item.get("path", "")}))
        scored.sort(key=lambda row: row[0], reverse=True)
        return [item for _, item in scored]

    def _registry(self) -> dict:
        root = Path(__file__).resolve().parents[4]
        path = root / "factory" / "skills" / "registry.json"
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
