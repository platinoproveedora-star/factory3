from __future__ import annotations

from datetime import date
from html import escape
from pathlib import Path


class MarketingPrivacyNoticeBuilderService:
    """Builds a plain privacy notice for campaign landings."""

    def ejecutar(self, context: dict) -> dict:
        company_id = str(context.get("company_id") or context.get("empresa_id") or "").strip()
        if not company_id:
            return {"ok": False, "error": "company_id requerido"}

        root = Path(__file__).resolve().parents[5]
        business_name = str(context.get("business_name") or context.get("razon_social") or company_id).strip()
        contact_email = str(context.get("contact_email") or context.get("email") or "").strip()
        contact_phone = str(context.get("contact_phone") or context.get("phone") or "").strip()
        country = str(context.get("country") or "Mexico").strip()
        campaign_name = str(context.get("campaign_name") or context.get("campaign_slug") or "campana digital").strip()
        output_dir = Path(context.get("output_dir") or root / "companies" / company_id / "landing")
        if not output_dir.is_absolute():
            output_dir = root / output_dir
        dry_run = bool(context.get("dry_run", True))

        missing = []
        if not contact_email:
            missing.append("contact_email")
        if not contact_phone:
            missing.append("contact_phone")

        md = self._markdown(business_name, contact_email, contact_phone, country, campaign_name)
        html = self._html(business_name, md)
        files = {
            output_dir / "privacy.md": md,
            output_dir / "privacy.html": html,
        }

        if not dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)
            for path, content in files.items():
                path.write_text(content, encoding="utf-8")

        return {
            "ok": True,
            "data": {
                "company_id": company_id,
                "business_name": business_name,
                "output_dir": str(output_dir),
                "privacy_path": str(output_dir / "privacy.html"),
                "files": [str(path) for path in files],
                "missing_recommended_fields": missing,
                "dry_run": dry_run,
            },
        }

    def _markdown(self, business_name: str, contact_email: str, contact_phone: str, country: str, campaign_name: str) -> str:
        today = date.today().isoformat()
        contact_lines = []
        if contact_email:
            contact_lines.append(f"- Email: {contact_email}")
        if contact_phone:
            contact_lines.append(f"- Telefono/WhatsApp: {contact_phone}")
        contact_block = "\n".join(contact_lines) or "- Contacto pendiente de definir."
        return f"""# Aviso de privacidad

Fecha de ultima actualizacion: {today}

{business_name} es responsable del tratamiento de los datos personales recabados a traves de esta pagina y de los formularios asociados a la campana "{campaign_name}".

## Datos que podemos solicitar

Podemos solicitar nombre, telefono, correo electronico, interes comercial, preferencia de contacto y cualquier informacion que la persona comparta voluntariamente para recibir informacion, cotizacion, ficha comercial o seguimiento.

## Finalidades

Usaremos los datos para:

- Responder solicitudes de informacion.
- Dar seguimiento comercial.
- Agendar llamadas, visitas o reuniones.
- Enviar ficha, propuesta o informacion relacionada con la campana.
- Medir resultados de marketing y mejorar la atencion.

## Transferencias

Los datos pueden compartirse con asesores, brokers, personal comercial, proveedores de tecnologia, plataformas de publicidad y herramientas de almacenamiento necesarias para operar la campana. No vendemos datos personales a terceros.

## Derechos ARCO

La persona titular puede solicitar acceso, rectificacion, cancelacion u oposicion al uso de sus datos, asi como revocar su consentimiento, usando los medios de contacto indicados abajo.

## Contacto

{contact_block}

## Pais de operacion

Este aviso se preparo para una operacion comercial en {country}. Debe revisarse legalmente antes de usarlo como aviso definitivo.
"""

    def _html(self, business_name: str, md: str) -> str:
        body = []
        for line in md.splitlines():
            if line.startswith("# "):
                body.append(f"<h1>{escape(line[2:])}</h1>")
            elif line.startswith("## "):
                body.append(f"<h2>{escape(line[3:])}</h2>")
            elif line.startswith("- "):
                body.append(f"<li>{escape(line[2:])}</li>")
            elif line.strip():
                body.append(f"<p>{escape(line)}</p>")
        return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Aviso de privacidad | {escape(business_name)}</title>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; color: #172033; background: #f6f8fb; line-height: 1.6; }}
    main {{ max-width: 860px; margin: 0 auto; padding: 48px 20px 72px; }}
    h1, h2 {{ color: #111827; line-height: 1.2; }}
    h1 {{ font-size: 34px; }}
    h2 {{ margin-top: 32px; font-size: 22px; }}
    p, li {{ font-size: 16px; }}
  </style>
</head>
<body><main>
{chr(10).join(body)}
</main></body>
</html>
"""
