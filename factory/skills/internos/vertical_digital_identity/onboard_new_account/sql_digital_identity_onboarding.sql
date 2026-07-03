-- ============================================================
-- Tabla: digital_identity_onboarding
-- Vertical: vertical_digital_identity
-- Registra el estado de cada onboarding de identidad digital
-- (InstaStart4all / FBstart4all). Usada exclusivamente por el
-- skill onboard_new_account vía vertical_supabase.
--
-- Verificado contra el SQL real de la plataforma:
-- companies/EMP_APPS4ALL/projects/PROY-001_PORTAL/sql/
-- 001_platform_sales_ready.sql — platform.companies.company_id
-- es TEXT, no uuid. access_grants (no company_users) es la
-- tabla real que valida acceso user×company×modulo_code
-- (confirmado en lib/platform.ts del portal).
-- ============================================================

create table if not exists digital_identity_onboarding (
    id              uuid primary key default gen_random_uuid(),
    company_id      text not null,
    -- FK a platform.companies omitida: esa tabla vive en PLATFORM_SUPABASE (proyecto distinto).
    -- La validez de company_id la garantiza security_access_grant antes de cada insert.

    plataformas     text[] not null,        -- ej. {'instagram','facebook_page'}
    tipo_negocio    text not null,          -- 'producto' | 'propiedad' | 'servicio'
    nombre_negocio  text not null,

    estado          text not null default 'en_progreso'
                    check (estado in ('en_progreso','completo','parcial','fallido')),

    pasos_completados          jsonb not null default '[]'::jsonb,
    pasos_pendientes_manuales  jsonb not null default '[]'::jsonb,
    posts_publicados           jsonb not null default '[]'::jsonb,
    errores                    jsonb not null default '[]'::jsonb,

    ig_business_account_id     text,
    fb_page_id                 text,

    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

create index if not exists idx_digital_identity_onboarding_company
    on digital_identity_onboarding(company_id);

create index if not exists idx_digital_identity_onboarding_estado
    on digital_identity_onboarding(estado);

-- Trigger para mantener updated_at al día en cada UPDATE
create or replace function set_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists trg_digital_identity_onboarding_updated_at
    on digital_identity_onboarding;

create trigger trg_digital_identity_onboarding_updated_at
    before update on digital_identity_onboarding
    for each row execute function set_updated_at();

-- ============================================================
-- ACCESO — este proyecto NO usa Supabase Auth nativo ni RLS
-- basado en auth.jwt(). El modelo real es JWT propio firmado
-- con PLATFORM_JWT_SECRET. Los skills corren con
-- SUPABASE_SERVICE_ROLE_KEY, que salta RLS. El filtro por
-- company_id se hace a mano en cada service.py.
-- ============================================================

alter table digital_identity_onboarding disable row level security;
-- (explícito: RLS off a propósito, no es un olvido)
