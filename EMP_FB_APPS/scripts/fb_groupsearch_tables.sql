-- FB Group Search — tablas Fase 1
-- Ejecutar en Supabase SQL Editor

CREATE TABLE IF NOT EXISTS fb_gs_searches (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  search_id      text UNIQUE NOT NULL,
  empresa_id     text,
  usuario_id     text,
  tema_busqueda  text NOT NULL,
  fuente         text DEFAULT 'ia_sugerido',
  estado         text DEFAULT 'procesando',
  total_grupos   integer DEFAULT 0,
  created_at     timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS fb_gs_groups (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  search_id           text NOT NULL,
  empresa_id          text,
  grupo_nombre        text,
  grupo_url           text,
  descripcion         text,
  miembros_estimados  integer,
  ubicacion_detectada text,
  fuente              text DEFAULT 'ia_sugerido',
  created_at          timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_fb_gs_groups_search ON fb_gs_groups(search_id);
CREATE INDEX IF NOT EXISTS idx_fb_gs_searches_emp  ON fb_gs_searches(empresa_id);
