-- Schema y tablas de EMP_ESTOIKOLAB — chat agents
-- Ejecutar en Supabase SQL Editor una sola vez
-- IMPORTANTE: exponer schema 'estoikolab' en Supabase → Settings → Data API → Exposed schemas

CREATE SCHEMA IF NOT EXISTS estoikolab;

CREATE TABLE IF NOT EXISTS estoikolab.chat_leads (
  id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  folio        text        UNIQUE NOT NULL,                        -- LEAD-001
  agent_id     text        NOT NULL DEFAULT 'AGT-001',
  canal        text        DEFAULT 'telegram',
  user_id      text,                                               -- chat_id Telegram o phone WA
  nombre       text,
  telefono     text,
  email        text,
  empresa      text,
  tipo_negocio text,
  objetivo     text,
  status       text        DEFAULT 'nuevo',                        -- nuevo / contactado / calificado
  created_at   timestamptz DEFAULT now(),
  updated_at   timestamptz DEFAULT now()
);

-- Índices útiles
CREATE INDEX IF NOT EXISTS idx_estoikolab_leads_agent  ON estoikolab.chat_leads (agent_id);
CREATE INDEX IF NOT EXISTS idx_estoikolab_leads_status ON estoikolab.chat_leads (status);
CREATE INDEX IF NOT EXISTS idx_estoikolab_leads_date   ON estoikolab.chat_leads (created_at DESC);
