-- vertical_sales — schema y tablas MVP
-- Ejecutar en Supabase vía supabase_run_sql o SQL Editor

CREATE SCHEMA IF NOT EXISTS sales;

CREATE TABLE sales.communication_events (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    folio       text UNIQUE NOT NULL,
    empresa_id  text NOT NULL,
    canal       text NOT NULL,
    user_id     text NOT NULL,
    chat_id     text,
    texto       text,
    intent      text,
    raw_payload jsonb,
    created_at  timestamptz DEFAULT now()
);

CREATE TABLE sales.leads (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    folio       text UNIQUE NOT NULL,
    empresa_id  text NOT NULL,
    canal       text NOT NULL,
    user_id     text NOT NULL,
    nombre      text,
    telefono    text,
    email       text,
    estado      text NOT NULL DEFAULT 'nuevo',
    fuente      text,
    score       integer DEFAULT 0,
    created_at  timestamptz DEFAULT now(),
    updated_at  timestamptz DEFAULT now()
);

CREATE TABLE sales.followup_tasks (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    folio             text UNIQUE NOT NULL,
    empresa_id        text NOT NULL,
    lead_id           uuid REFERENCES sales.leads(id),
    mensaje_sugerido  text,
    fecha_seguimiento date,
    estado            text NOT NULL DEFAULT 'pendiente',
    created_at        timestamptz DEFAULT now(),
    updated_at        timestamptz DEFAULT now()
);

CREATE TABLE sales.automation_logs (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    folio         text UNIQUE NOT NULL,
    empresa_id    text NOT NULL,
    lead_id       uuid REFERENCES sales.leads(id),
    accion        text,
    skill_destino text,
    estado        text NOT NULL DEFAULT 'encolado',
    created_at    timestamptz DEFAULT now()
);

CREATE TABLE sales.conversation_messages (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    folio       text UNIQUE NOT NULL,
    empresa_id  text NOT NULL,
    lead_id     uuid REFERENCES sales.leads(id),
    canal       text,
    direccion   text NOT NULL,
    texto       text,
    created_at  timestamptz DEFAULT now()
);

-- Índices
CREATE INDEX ON sales.leads (empresa_id, estado);
CREATE INDEX ON sales.leads (user_id, canal, empresa_id);
CREATE INDEX ON sales.followup_tasks (lead_id, estado);
CREATE INDEX ON sales.conversation_messages (lead_id);
CREATE INDEX ON sales.communication_events (empresa_id, canal);
