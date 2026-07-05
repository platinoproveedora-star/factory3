from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

MODEL = "claude-haiku-4-5-20251001"
TONES = {"profesional", "casual", "urgente"}
INTENT_TYPES = {"informacional", "comparacion", "compra"}
FUNNEL_STAGES = {"awareness", "consideration", "decision"}
OBJECTIVES = {"conversions", "traffic", "leads"}
FORMATS = {"csv", "json", "both"}

_CLIENT = None


def load_dotenv_if_needed() -> None:
    if os.getenv("ANTHROPIC_API_KEY"):
        return
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def client():
    global _CLIENT
    load_dotenv_if_needed()
    if _CLIENT is None:
        import anthropic

        _CLIENT = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _CLIENT


def ai_json(prompt: str, system: str, max_tokens: int = 1800) -> tuple[dict | list | None, str | None]:
    try:
        msg = client().messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            temperature=0.2,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        return parse_json(raw), None
    except json.JSONDecodeError:
        return None, "ai_response_not_parseable"
    except KeyError:
        return None, "ANTHROPIC_API_KEY no configurada"
    except Exception as exc:
        return None, str(exc)


def parse_json(raw: str) -> dict | list:
    text = raw.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.strip().lower().startswith("json"):
            text = text.strip()[4:]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start_obj = text.find("{")
        start_arr = text.find("[")
        starts = [i for i in (start_obj, start_arr) if i >= 0]
        if not starts:
            raise
        start = min(starts)
        end = text.rfind("}") if text[start] == "{" else text.rfind("]")
        if end < start:
            raise
        return json.loads(text[start : end + 1])


def clamp_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        n = int(value)
    except Exception:
        n = default
    return max(minimum, min(maximum, n))


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def nullable_text(value: Any) -> str | None:
    text = clean_text(value)
    return text or None


def safe_priority(value: Any) -> int:
    return clamp_int(value, 3, 1, 5)


def seq(prefix: str, idx: int) -> str:
    return f"{prefix}_{idx:03d}"


def slug(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return text or "item"


def normalize_language(language: Any, country: Any) -> str:
    lang = clean_text(language).replace("_", "-")
    country_text = clean_text(country).upper()
    if not lang:
        return "es-MX" if country_text == "MX" else "en-US" if country_text == "US" else "es-MX"
    if "-" in lang:
        a, b = lang.split("-", 1)
        return f"{a.lower()}-{b.upper()}"
    if lang.lower() == "es":
        return f"es-{country_text or 'MX'}"
    if lang.lower() == "en":
        return f"en-{country_text or 'US'}"
    return lang


def ensure_market(raw: Any) -> dict:
    market = raw if isinstance(raw, dict) else {}
    country = clean_text(market.get("country") or "MX").upper()
    return {
        "country": country,
        "language": normalize_language(market.get("language"), country),
        "audience": nullable_text(market.get("audience")),
    }


def clip(value: Any, limit: int) -> str:
    text = clean_text(value)
    return text if len(text) <= limit else text[:limit].rstrip()


def safe_filename(value: str) -> str:
    safe = re.sub(r"[^a-z0-9_-]+", "_", value.lower()).strip("_")
    return safe or "gptads_export"
