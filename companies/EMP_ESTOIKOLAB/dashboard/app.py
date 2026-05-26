"""Dashboard operativo para Estoiko Lab chat agents."""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime

import pandas as pd
import streamlit as st


COMPANY_ID = "EMP_ESTOIKOLAB"


st.set_page_config(page_title="Estoiko Lab Agents", layout="wide")

st.markdown(
    """
    <style>
      .main .block-container { padding-top: 1.5rem; max-width: 1240px; }
      .metric-card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; background: #fff; }
      .muted { color: #6b7280; font-size: 13px; }
      .lead-box { border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; background: #fafafa; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


def _headers(schema: str | None = None) -> dict:
    key = _env("SUPABASE_SERVICE_ROLE_KEY")
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
    }
    if schema:
        headers["Accept-Profile"] = schema
    return headers


def _rest_get(table: str, params: dict, schema: str | None = None) -> list[dict]:
    base = _env("SUPABASE_URL").rstrip("/")
    if not base or not _env("SUPABASE_SERVICE_ROLE_KEY"):
        st.error("Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY en Render.")
        return []
    qs = urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(f"{base}/rest/v1/{table}?{qs}", headers=_headers(schema))
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode())
    except Exception as exc:
        st.warning(f"No se pudo leer {schema + '.' if schema else ''}{table}: {exc}")
        return []


def _leads() -> list[dict]:
    return _rest_get(
        "chat_leads",
        {
            "select": "id,folio,agent_id,canal,user_id,nombre,telefono,email,empresa,tipo_negocio,objetivo,status,created_at",
            "order": "created_at.desc",
            "limit": "500",
        },
        schema="estoikolab",
    )


def _all_recent_leads() -> list[dict]:
    return _rest_get(
        "chat_leads",
        {
            "select": "id,folio,agent_id,canal,user_id,nombre,telefono,email,status,created_at",
            "order": "created_at.desc",
            "limit": "50",
        },
        schema="estoikolab",
    )


def _states() -> list[dict]:
    return _rest_get(
        "bot_states",
        {
            "select": "chat_id,state,updated_at",
            "order": "updated_at.desc",
            "limit": "200",
        },
    )


def _messages_from_state(row: dict) -> list[dict]:
    state = row.get("state") or {}
    history = state.get("history") or []
    out = []
    for item in history:
        out.append({
            "chat_id": row.get("chat_id"),
            "agent_id": state.get("agent_id", ""),
            "lead_folio": state.get("lead_folio", ""),
            "role": item.get("role", ""),
            "content": item.get("content", ""),
            "updated_at": row.get("updated_at", ""),
        })
    return out


def _fmt_date(value: str) -> str:
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return value


st.title("Estoiko Lab - Chat Agents")
st.caption("Leads, conversaciones y analisis operativo de agentes.")

leads = _leads()
states = _states()
messages = [msg for row in states for msg in _messages_from_state(row)]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Leads Estoiko", len(leads))
c2.metric("Conversaciones", len([s for s in states if (s.get("state") or {}).get("agent_id")]))
c3.metric("Mensajes", len(messages))
c4.metric("Agentes activos", len(set((s.get("state") or {}).get("agent_id", "") for s in states if (s.get("state") or {}).get("agent_id"))))

tab_leads, tab_conversations, tab_analysis, tab_debug = st.tabs([
    "Leads", "Conversaciones", "Analisis", "Debug"
])

with tab_leads:
    st.subheader("Leads capturados")
    if leads:
        df = pd.DataFrame(leads)
        df["created_at"] = df["created_at"].map(_fmt_date)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("Todavia no hay leads reales para EMP_ESTOIKOLAB.")

    with st.expander("Ultimos 50 leads — estoikolab.chat_leads"):
        all_df = pd.DataFrame(_all_recent_leads())
        if not all_df.empty:
            st.dataframe(all_df, use_container_width=True, hide_index=True)

with tab_conversations:
    st.subheader("Conversaciones por chat")
    state_options = {
        f"{row.get('chat_id')} - {(row.get('state') or {}).get('lead_folio', 'sin folio')} - {_fmt_date(row.get('updated_at', ''))}": row
        for row in states
    }
    if state_options:
        selected = st.selectbox("Chat", list(state_options.keys()))
        row = state_options[selected]
        state = row.get("state") or {}
        st.write({
            "chat_id": row.get("chat_id"),
            "agent_id": state.get("agent_id"),
            "lead_id": state.get("lead_id"),
            "lead_folio": state.get("lead_folio"),
            "contact": state.get("contact"),
        })
        for item in state.get("history") or []:
            role = "Usuario" if item.get("role") == "user" else "Agente"
            st.markdown(f"**{role}:** {item.get('content', '')}")
    else:
        st.info("Sin conversaciones.")

with tab_analysis:
    st.subheader("Analisis rapido")
    if messages:
        msg_df = pd.DataFrame(messages)
        user_msgs = msg_df[msg_df["role"] == "user"]
        agent_msgs = msg_df[msg_df["role"] == "assistant"]
        a1, a2, a3 = st.columns(3)
        a1.metric("Mensajes usuario", len(user_msgs))
        a2.metric("Mensajes agente", len(agent_msgs))
        a3.metric("Chats con contacto", len([s for s in states if (s.get("state") or {}).get("contact")]))
        st.markdown("**Palabras frecuentes en mensajes de usuario**")
        words = {}
        for content in user_msgs["content"].fillna(""):
            for word in str(content).lower().replace(".", " ").replace(",", " ").split():
                if len(word) >= 5:
                    words[word] = words.get(word, 0) + 1
        top = sorted(words.items(), key=lambda x: x[1], reverse=True)[:20]
        st.dataframe(pd.DataFrame(top, columns=["palabra", "conteo"]), use_container_width=True, hide_index=True)
    else:
        st.info("Sin mensajes para analizar.")

with tab_debug:
    st.subheader("Estado crudo")
    st.json({"leads": leads[:5], "states": states[:3]})
