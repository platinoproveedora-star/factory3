"""Pipeline automatico post-captura: evalua al candidato y notifica al manager."""

from __future__ import annotations

import os
from pathlib import Path

from factory.engine import SkillLoader, SkillRunner


_BASE = Path(__file__).parent.parent.parent.parent.parent


class RhPostScoreOrchestratorService:

    def __init__(self):
        self._runner: SkillRunner | None = None

    def _get_runner(self) -> SkillRunner:
        if self._runner is None:
            ext = _BASE / "factory" / "skills" / "externos"
            ext.mkdir(parents=True, exist_ok=True)
            loader = SkillLoader(
                internal_root=_BASE / "factory" / "skills" / "internos",
                external_root=ext,
            )
            self._runner = SkillRunner(loader)
        return self._runner

    def ejecutar(self, context: dict) -> dict:
        candidato_id: str = context.get("candidato_id") or ""
        vacante_id:   str = context.get("vacante_id") or ""
        empresa_id:   str = context.get("empresa_id") or ""
        manager_chat: str = context.get("manager_chat_id") or os.getenv("MANAGER_TELEGRAM_CHAT_ID", "")
        telegram_token: str = context.get("telegram_token") or os.getenv("FACTORY3_ADMIN_BOT_TOKEN", "")

        if not candidato_id or not vacante_id:
            return {"ok": False, "error": "candidato_id y vacante_id son requeridos"}

        runner  = self._get_runner()
        errores = []
        log     = []

        # 1. Profile builder
        r = runner.run("rh_candidate_profile_builder", {
            "candidato_id": candidato_id,
            "vacante_id":   vacante_id,
        }, source="internos")
        log.append({"step": "profile_builder", "ok": r.get("ok")})
        if not r.get("ok"):
            errores.append(f"profile_builder: {r.get('error')}")

        # 2. Basic validation
        r = runner.run("rh_basic_validation", {
            "candidato_id": candidato_id,
        }, source="internos")
        log.append({"step": "basic_validation", "ok": r.get("ok")})
        valido = (r.get("data") or {}).get("valido", True)

        # 3. Duplicate detector
        r = runner.run("rh_duplicate_detector", {
            "candidato_id": candidato_id,
            "vacante_id":   vacante_id,
            "empresa_id":   empresa_id,
        }, source="internos")
        log.append({"step": "duplicate_detector", "ok": r.get("ok")})
        es_duplicado = (r.get("data") or {}).get("es_duplicado", False)

        if es_duplicado:
            return {"ok": True, "data": {"log": log, "resultado": "duplicado", "score": None}}

        # 4. Knockout filter
        r = runner.run("rh_knockout_filter", {
            "candidato_id": candidato_id,
            "vacante_id":   vacante_id,
        }, source="internos")
        log.append({"step": "knockout_filter", "ok": r.get("ok")})
        pasa_ko = (r.get("data") or {}).get("pasa", True)

        # 5. Scoring
        r = runner.run("rh_candidate_scoring", {
            "candidato_id": candidato_id,
            "vacante_id":   vacante_id,
            "empresa_id":   empresa_id,
        }, source="internos")
        log.append({"step": "scoring", "ok": r.get("ok")})
        score = (r.get("data") or {}).get("score_total")

        # 6. Pipeline manager — asignar etapa según resultado
        etapa = self._calcular_etapa(pasa_ko, score)
        r = runner.run("rh_pipeline_manager", {
            "candidato_id": candidato_id,
            "vacante_id":   vacante_id,
            "etapa":        etapa,
            "notas":        "evaluacion automatica post-captura",
        }, source="internos")
        log.append({"step": "pipeline_manager", "ok": r.get("ok"), "etapa": etapa})

        # 7. Notificar al manager por Telegram
        if manager_chat and telegram_token:
            msg = self._build_notificacion(candidato_id, vacante_id, score, etapa, pasa_ko)
            runner.run("telegram_send_message", {
                "token":   telegram_token,
                "chat_id": manager_chat,
                "text":    msg,
                "parse_mode": "HTML",
            }, source="internos")
            log.append({"step": "telegram_notify", "ok": True})

        return {
            "ok": True,
            "data": {
                "candidato_id": candidato_id,
                "score":        score,
                "etapa":        etapa,
                "pasa_knockout": pasa_ko,
                "log":          log,
                "errores":      errores,
            },
        }

    def _calcular_etapa(self, pasa_ko: bool, score) -> str:
        if not pasa_ko:
            return "no_apto"
        if score is None:
            return "nuevo"
        if score >= 70:
            return "apto"
        if score >= 40:
            return "nuevo"
        return "no_apto"

    def _build_notificacion(
        self, candidato_id: str, vacante_id: str, score, etapa: str, pasa_ko: bool
    ) -> str:
        ko_txt    = "✓ Pasa KO" if pasa_ko else "✗ No pasa KO"
        score_txt = f"{score}pts" if score is not None else "—"
        return (
            f"<b>Nuevo candidato evaluado</b>\n"
            f"Candidato: <code>{candidato_id[:8]}</code>\n"
            f"Vacante: <code>{vacante_id[:8]}</code>\n"
            f"Score: <b>{score_txt}</b> | {ko_txt}\n"
            f"Etapa: <b>{etapa}</b>"
        )
