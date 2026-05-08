"""
Fase 1 — Prueba RH completa via SkillRunner.
Corre skills en orden, escribe a Supabase, visible en dashboard.

Uso:
    python tests/test_fase1_rh.py
"""
from __future__ import annotations
import os, sys, json
from pathlib import Path

# ── Env ───────────────────────────────────────────────────────────────────────
for line in open(".env"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()

# ── Engine ────────────────────────────────────────────────────────────────────
sys.path.insert(0, ".")
from factory.engine.skill_loader import SkillLoader
from factory.engine.skill_runner import SkillRunner

_INTERNOS = Path("factory/skills/internos")
loader    = SkillLoader(internal_root=_INTERNOS)
runner    = SkillRunner(loader)

# ── Helpers ───────────────────────────────────────────────────────────────────
_resultados: list[dict] = []

def run(skill: str, ctx: dict, esperado_ok: bool = True) -> dict:
    result = runner.run(skill, ctx)
    ok     = result.get("ok", False)
    status = "PASS" if ok == esperado_ok else "FAIL"
    _resultados.append({"skill": skill, "status": status, "ok": ok})
    datos  = json.dumps(result.get("data", result.get("error", "")), ensure_ascii=False)[:120]
    print(f"  [{status}] {skill:40s} {datos}")
    return result

def seccion(titulo: str):
    print(f"\n{'='*60}")
    print(f"  {titulo}")
    print(f"{'='*60}")

# ══════════════════════════════════════════════════════════════════════════════
# 1. Datos base — seed
# ══════════════════════════════════════════════════════════════════════════════
seccion("1. SEED — crear datos de prueba")

seed = run("rh_seed_generator", {
    "empresa_id":              "test_fase1",
    "n_vacantes":              1,
    "n_candidatos_por_vacante": 5,
    "puestos":                 ["Operador de tracto"],
    "seed_label":              "seed_fase1_rh",
    "dry_run":                 False,
})

# El seed no devuelve IDs — consultamos Supabase directamente
vacante_id    = None
candidato_ids = []

sys.path.insert(0, "dashboard")
from db import select as db_select

vacs = db_select("vacantes", "select=id,titulo&empresa_id=eq.test_fase1&tipo=eq.seed&order=created_at.desc&limit=1")
if vacs:
    vacante_id = vacs[0]["id"]
    print(f"    vacante_id:  {vacante_id}  ({vacs[0].get('titulo','?')})")

if vacante_id:
    cands = db_select("candidatos", f"select=id,nombre&vacante_id=eq.{vacante_id}")
    candidato_ids = [c["id"] for c in cands if c.get("id")]
    print(f"    candidatos:  {len(candidato_ids)}")

if not vacante_id or not candidato_ids:
    print("\n  ERROR: sin datos de seed. Abortando.")
    sys.exit(1)

cand_id = candidato_ids[0]

# ══════════════════════════════════════════════════════════════════════════════
# 2. Pipeline individual — primer candidato
# ══════════════════════════════════════════════════════════════════════════════
seccion("2. PIPELINE INDIVIDUAL — candidato 1")

r_perfil = run("rh_candidate_profile_builder", {"candidato_id": cand_id})
perfil   = (r_perfil.get("data") or {}).get("perfil", {})

run("rh_basic_validation", {
    "candidato_id": cand_id,
    "perfil":       perfil,
})

run("rh_duplicate_detector", {
    "candidato_id": cand_id,
    "vacante_id":   vacante_id,
})

run("rh_knockout_filter", {
    "candidato_id": cand_id,
    "vacante_id":   vacante_id,
    "perfil":       perfil,
})

run("rh_candidate_scoring", {
    "candidato_id": cand_id,
    "vacante_id":   vacante_id,
    "perfil":       perfil,
})

# ══════════════════════════════════════════════════════════════════════════════
# 3. Skills nuevos AI — mismo candidato
# ══════════════════════════════════════════════════════════════════════════════
seccion("3. SKILLS AI NUEVOS")

run("rh_dimension_analyzer", {
    "candidato_id": cand_id,
    "dimension":    "maquinaria",
    "puesto":       "Operador de tracto",
})

run("rh_dimension_analyzer", {
    "candidato_id": cand_id,
    "dimension":    "compromiso",
    "puesto":       "Operador de tracto",
})

run("rh_shift_zone_validator", {
    "candidato_id":   cand_id,
    "turno_requerido": "noche",
    "zona_trabajo":   "Zona Industrial Merida Norte",
})

run("rh_retention_predictor", {
    "candidato_id": cand_id,
    "puesto":       "Operador de tracto",
})

run("rh_contractor_interview", {
    "puesto":       "Operador de tracto",
    "contratista":  "Transportes del Norte SA",
    "requisitos":   ["doble remolque", "licencia tipo E"],
    "equipo":       ["Kenworth T800"],
    "zona":         "Merida - CDMX",
    "num_preguntas": 5,
})

# ══════════════════════════════════════════════════════════════════════════════
# 4. Pipeline manager + ranking
# ══════════════════════════════════════════════════════════════════════════════
seccion("4. PIPELINE Y RANKING")

run("rh_pipeline_manager", {
    "candidato_id": cand_id,
    "vacante_id":   vacante_id,
    "etapa":        "apto",
    "notas":        "Pasa Fase 1 pruebas",
})

run("rh_candidate_ranking", {"vacante_id": vacante_id})

run("rh_candidate_search", {
    "vacante_id": vacante_id,
    "estado":     "apto",
})

# ══════════════════════════════════════════════════════════════════════════════
# 5. Orquestador completo — segundo candidato
# ══════════════════════════════════════════════════════════════════════════════
seccion("5. ORQUESTADOR COMPLETO — candidato 2")

if len(candidato_ids) > 1:
    run("rh_post_score_orchestrator", {
        "candidato_id": candidato_ids[1],
        "vacante_id":   vacante_id,
    })
else:
    print("  [SKIP] solo 1 candidato en seed")

# ══════════════════════════════════════════════════════════════════════════════
# 6. Entrevista + oferta — dry run
# ══════════════════════════════════════════════════════════════════════════════
seccion("6. ENTREVISTA Y OFERTA (dry_run)")

run("rh_interview_scheduler", {
    "accion":       "agendar",
    "candidato_id": cand_id,
    "tipo":         "presencial",
    "dry_run":      True,
})

run("rh_offer_sender", {
    "candidato_id": cand_id,
    "vacante_id":   vacante_id,
    "oferta": {
        "puesto":       "Operador de tracto",
        "salario":      "$18,000 mensuales",
        "horario":      "Lunes a Viernes 6am-3pm",
        "fecha_inicio": "2026-05-15",
        "lugar":        "Merida, Yucatan",
    },
    "dry_run": True,
})

# ══════════════════════════════════════════════════════════════════════════════
# 7. Reportes y KPIs
# ══════════════════════════════════════════════════════════════════════════════
seccion("7. REPORTES Y KPIS")

run("rh_report_generator", {"vacante_id": vacante_id})

run("rh_stats", {})

run("rh_pipeline_view", {"vacante_id": vacante_id})

run("rh_candidate_history", {"candidato_id": cand_id})

# ══════════════════════════════════════════════════════════════════════════════
# Resumen final
# ══════════════════════════════════════════════════════════════════════════════
total  = len(_resultados)
passed = sum(1 for r in _resultados if r["status"] == "PASS")
failed = sum(1 for r in _resultados if r["status"] == "FAIL")

print(f"\n{'='*60}")
print(f"  RESULTADO FINAL: {passed}/{total} PASS  |  {failed} FAIL")
print(f"{'='*60}")

if failed:
    print("\n  Skills con falla:")
    for r in _resultados:
        if r["status"] == "FAIL":
            print(f"    - {r['skill']}")

print(f"\n  Datos escritos en Supabase bajo seed_label: seed_fase1_rh")
print(f"  Vacante ID: {vacante_id}")
print(f"  Candidato 1 ID: {cand_id}")
print(f"\n  Abre el dashboard y busca empresa 'test_fase1' para ver los resultados.")
