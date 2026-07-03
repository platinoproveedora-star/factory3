-- ============================================================
-- Tabla: fb_identity
-- Schema: public
-- Almacena la identidad visual generada por identidad_visual.
-- Una fila por empresa; estado_aprobacion=pendiente hasta
-- que el usuario aprueba manualmente.
--
-- NOTA: tabla en schema public para que supabase_query_table
-- pueda consultarla sin Content-Profile especial.
-- ============================================================

create table if not exists fb_identity (
    id               uuid primary key default gen_random_uuid(),
    empresa_id       text not null,

    logo_url         text,
    portada_fb_url   text,
    portada_ig_url   text,

    paleta_primaria  text,
    paleta_secundaria text,
    tono_marca       text,
    modelo_usado     text,

    estado_aprobacion text not null default 'pendiente'
        check (estado_aprobacion in ('pendiente', 'aprobado', 'rechazado')),

    created_at  timestamptz not null default now(),
    approved_at timestamptz
);

create index if not exists idx_fb_identity_empresa
    on fb_identity(empresa_id);

create index if not exists idx_fb_identity_estado
    on fb_identity(empresa_id, estado_aprobacion);

-- RLS off — acceso controlado por service_role_key + filtro empresa_id en service.py
alter table fb_identity disable row level security;
