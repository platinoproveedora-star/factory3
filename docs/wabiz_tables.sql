-- vertical_wabiz: tablas Supabase (schema public, prefijo wabiz_)
-- Ejecutar en: Supabase Dashboard → SQL Editor

-- 1. Configuración WhatsApp Business por empresa
CREATE TABLE IF NOT EXISTS public.wabiz_config (
    id                   uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id           text        UNIQUE NOT NULL,
    phone_number_id      text        NOT NULL,
    business_account_id  text        NOT NULL DEFAULT '',
    access_token         text        NOT NULL,
    verify_token         text        NOT NULL,
    graph_version        text        NOT NULL DEFAULT 'v24.0',
    created_at           timestamptz NOT NULL DEFAULT now(),
    updated_at           timestamptz NOT NULL DEFAULT now()
);

-- 2. Log de mensajes entrantes y salientes
CREATE TABLE IF NOT EXISTS public.wabiz_messages (
    id             uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    empresa_id     text        NOT NULL,
    from_phone     text        NOT NULL,
    direction      text        NOT NULL CHECK (direction IN ('in', 'out')),
    type           text        NOT NULL DEFAULT 'text',
    body           text,
    wa_message_id  text,
    timestamp      timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wabiz_messages_lookup
    ON public.wabiz_messages (empresa_id, from_phone, timestamp DESC);
