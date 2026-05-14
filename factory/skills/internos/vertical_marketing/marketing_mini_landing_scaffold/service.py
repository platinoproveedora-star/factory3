from __future__ import annotations

import json
from html import escape
from pathlib import Path
from urllib.parse import quote


class MarketingMiniLandingScaffoldService:
    """Creates a deterministic static mini landing for a campaign."""

    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        if not company_id:
            return {"ok": False, "error": "company_id requerido"}

        root = Path(__file__).resolve().parents[5]
        campaign_slug = str(context.get("campaign_slug") or "first_campaign").strip()
        campaign = self._load_campaign(root, company_id, campaign_slug)
        brief = campaign.get("brief", {})
        prop = brief.get("property", {})

        title = str(context.get("title") or campaign.get("title") or prop.get("property_name") or "Oferta disponible").strip()
        description = str(context.get("description") or campaign.get("description") or campaign.get("message") or "").strip()
        offer = str(context.get("offer") or self._offer_from_property(prop) or description).strip()
        bullets = context.get("bullets") or prop.get("main_benefits") or []
        facts = context.get("facts") or self._facts_from_property(prop)
        image_url = str(context.get("image_url") or campaign.get("image_url") or "").strip()
        privacy_url = str(context.get("privacy_url") or "privacy.html").strip()
        whatsapp_number = self._digits(str(context.get("whatsapp_number") or context.get("phone") or "").strip())
        whatsapp_message = str(context.get("whatsapp_message") or f"Hola, quiero informacion de {title}.").strip()
        business_name = str(context.get("business_name") or company_id).strip()
        service_name = str(context.get("render_service_name") or f"{company_id.lower().replace('_', '-')}-landing").strip()
        output_dir = Path(context.get("output_dir") or root / "companies" / company_id / "landing")
        if not output_dir.is_absolute():
            output_dir = root / output_dir
        dry_run = bool(context.get("dry_run", True))

        missing = []
        if not image_url:
            missing.append("image_url")
        if not whatsapp_number:
            missing.append("whatsapp_number")
        if not privacy_url:
            missing.append("privacy_url")

        cta_url = self._whatsapp_url(whatsapp_number, whatsapp_message) if whatsapp_number else "#contacto"
        html = self._html(
            business_name=business_name,
            title=title,
            description=description,
            offer=offer,
            bullets=[str(x) for x in bullets],
            facts={str(k): str(v) for k, v in facts.items()},
            image_url=image_url,
            cta_url=cta_url,
            privacy_url=privacy_url,
        )
        render_yaml = self._render_yaml(service_name)
        files = {
            output_dir / "index.html": html,
            output_dir / "render.yaml": render_yaml,
        }

        if not dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)
            for path, content in files.items():
                path.write_text(content, encoding="utf-8")

        return {
            "ok": True,
            "data": {
                "company_id": company_id,
                "campaign_slug": campaign_slug,
                "output_dir": str(output_dir),
                "landing_path": str(output_dir / "index.html"),
                "files": [str(path) for path in files],
                "cta_url": cta_url,
                "privacy_url": privacy_url,
                "missing_recommended_fields": missing,
                "dry_run": dry_run,
            },
        }

    def _load_campaign(self, root: Path, company_id: str, campaign_slug: str) -> dict:
        path = root / "companies" / company_id / f"{campaign_slug}.json"
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _offer_from_property(self, prop: dict) -> str:
        if not prop:
            return ""
        pieces = [
            prop.get("property_name"),
            prop.get("location"),
            prop.get("price_range"),
        ]
        return " | ".join(str(x) for x in pieces if x)

    def _facts_from_property(self, prop: dict) -> dict:
        keys = [
            ("Tipo", "property_type"),
            ("Ubicacion", "location"),
            ("Superficie", "size_m2"),
            ("Capacidad", "capacity"),
            ("Precio", "price_range"),
            ("Entrega", "occupancy_options"),
            ("Renta actual", "current_rent"),
        ]
        facts = {}
        for label, key in keys:
            value = prop.get(key)
            if value not in (None, ""):
                facts[label] = f"{value} m2" if key == "size_m2" else value
        return facts

    def _digits(self, value: str) -> str:
        return "".join(ch for ch in value if ch.isdigit())

    def _whatsapp_url(self, number: str, message: str) -> str:
        return f"https://wa.me/{number}?text={quote(message)}"

    def _html(self, business_name: str, title: str, description: str, offer: str, bullets: list[str], facts: dict, image_url: str, cta_url: str, privacy_url: str) -> str:
        hero_media = (
            f'<img src="{escape(image_url)}" alt="{escape(title)}">'
            if image_url
            else '<div class="placeholder">Agregar foto principal</div>'
        )
        bullet_html = "\n".join(f"<li>{escape(item)}</li>" for item in bullets)
        fact_html = "\n".join(f"<div><span>{escape(k)}</span><strong>{escape(v)}</strong></div>" for k, v in facts.items())
        return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)} | {escape(business_name)}</title>
  <meta name="description" content="{escape(description)}">
  <style>
    :root {{ color-scheme: light; --ink: #101827; --muted: #526070; --line: #d9e1ec; --accent: #0f766e; --soft: #f3f7f6; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Arial, sans-serif; color: var(--ink); background: #ffffff; }}
    header, section, footer {{ width: 100%; }}
    .wrap {{ max-width: 1080px; margin: 0 auto; padding: 0 20px; }}
    .hero {{ min-height: 88vh; display: grid; align-items: center; background: var(--soft); border-bottom: 1px solid var(--line); }}
    .hero-grid {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(320px, 460px); gap: 40px; align-items: center; padding: 56px 0; }}
    .eyebrow {{ margin: 0 0 14px; font-size: 13px; letter-spacing: 0; text-transform: uppercase; color: var(--accent); font-weight: 700; }}
    h1 {{ margin: 0; font-size: clamp(36px, 7vw, 72px); line-height: 1.02; letter-spacing: 0; }}
    .lead {{ margin: 20px 0 0; font-size: 20px; line-height: 1.5; color: var(--muted); max-width: 650px; }}
    .offer {{ margin-top: 22px; font-size: 18px; font-weight: 700; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 12px; margin-top: 30px; }}
    .btn {{ display: inline-flex; min-height: 48px; align-items: center; justify-content: center; padding: 0 20px; border-radius: 8px; text-decoration: none; font-weight: 700; }}
    .btn.primary {{ background: var(--accent); color: #ffffff; }}
    .btn.secondary {{ border: 1px solid var(--line); color: var(--ink); background: #ffffff; }}
    .media img, .placeholder {{ width: 100%; aspect-ratio: 4 / 3; object-fit: cover; border-radius: 8px; border: 1px solid var(--line); background: #e6ecef; }}
    .placeholder {{ display: grid; place-items: center; color: var(--muted); font-weight: 700; }}
    .band {{ padding: 56px 0; }}
    .facts {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }}
    .facts div {{ border: 1px solid var(--line); border-radius: 8px; padding: 16px; background: #ffffff; }}
    .facts span {{ display: block; color: var(--muted); font-size: 13px; margin-bottom: 8px; }}
    .facts strong {{ font-size: 18px; }}
    .bullets {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(280px, 420px); gap: 34px; align-items: start; }}
    h2 {{ margin: 0 0 16px; font-size: 32px; }}
    li {{ margin: 0 0 12px; color: var(--muted); font-size: 18px; line-height: 1.45; }}
    footer {{ border-top: 1px solid var(--line); padding: 28px 0; color: var(--muted); }}
    footer a {{ color: var(--accent); }}
    @media (max-width: 820px) {{
      .hero-grid, .bullets {{ grid-template-columns: 1fr; }}
      .facts {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .hero {{ min-height: auto; }}
    }}
  </style>
</head>
<body>
  <header class="hero">
    <div class="wrap hero-grid">
      <div>
        <p class="eyebrow">{escape(business_name)}</p>
        <h1>{escape(title)}</h1>
        <p class="lead">{escape(description)}</p>
        <p class="offer">{escape(offer)}</p>
        <div class="actions">
          <a class="btn primary" href="{escape(cta_url)}">Solicitar informacion</a>
          <a class="btn secondary" href="#detalles">Ver detalles</a>
        </div>
      </div>
      <div class="media">{hero_media}</div>
    </div>
  </header>
  <section class="band" id="detalles">
    <div class="wrap facts">{fact_html}</div>
  </section>
  <section class="band">
    <div class="wrap bullets">
      <div><h2>Por que puede interesarte</h2></div>
      <ul>{bullet_html}</ul>
    </div>
  </section>
  <section class="band" id="contacto">
    <div class="wrap">
      <h2>Solicita informacion</h2>
      <p class="lead">Comparte tus datos con el asesor asignado para recibir ficha, resolver dudas o agendar visita.</p>
      <div class="actions">
        <a class="btn primary" href="{escape(cta_url)}">Contactar ahora</a>
      </div>
    </div>
  </section>
  <footer>
    <div class="wrap">
      <span>{escape(business_name)}</span> · <a href="{escape(privacy_url)}">Aviso de privacidad</a>
    </div>
  </footer>
</body>
</html>
"""

    def _render_yaml(self, service_name: str) -> str:
        return f"""services:
  - type: web
    name: {service_name}
    runtime: static
    staticPublishPath: .
    pullRequestPreviewsEnabled: false
"""
