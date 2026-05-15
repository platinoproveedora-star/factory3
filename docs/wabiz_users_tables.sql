-- factory_users: usuarios globales de la fábrica (todos los canales)
CREATE TABLE IF NOT EXISTS public.factory_users (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre     text NOT NULL,
    empresa_id text NOT NULL,
    role       text NOT NULL DEFAULT 'user',
    user_mode  text[] NOT NULL DEFAULT '{}',
    phone      text UNIQUE,
    telegram_id text UNIQUE,
    activo     boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- wabiz_access_codes: claves de registro para WhatsApp
CREATE TABLE IF NOT EXISTS public.wabiz_access_codes (
    codigo     text PRIMARY KEY,
    empresa_id text NOT NULL,
    user_mode  text[] NOT NULL DEFAULT '{}',
    role       text NOT NULL DEFAULT 'user',
    activo     boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Claves iniciales
INSERT INTO public.wabiz_access_codes (codigo, empresa_id, user_mode, role) VALUES
    ('logplat26', 'logplat', ARRAY['logplat'], 'chofer'),
    ('admin2026',  'logplat', ARRAY['logplat'], 'admin')
ON CONFLICT (codigo) DO NOTHING;
