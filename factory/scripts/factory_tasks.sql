-- factory_tasks — cola universal de tareas para meta skills
-- Ejecutar en Supabase SQL Editor

CREATE TABLE IF NOT EXISTS factory_tasks (
  id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id        text UNIQUE NOT NULL,
  empresa_id     text,
  skill_name     text NOT NULL,
  skill_source   text NOT NULL DEFAULT 'internos',
  context        jsonb NOT NULL DEFAULT '{}',
  status         text NOT NULL DEFAULT 'pendiente',
  resultado      jsonb,
  error_msg      text,
  prioridad      int DEFAULT 5,
  parent_task_id text,
  generated_by   text,
  costo_tokens   int DEFAULT 0,
  latencia_ms    int DEFAULT 0,
  created_by     text,
  created_at     timestamptz DEFAULT now(),
  started_at     timestamptz,
  finished_at    timestamptz
);

CREATE INDEX IF NOT EXISTS idx_factory_tasks_status  ON factory_tasks(status);
CREATE INDEX IF NOT EXISTS idx_factory_tasks_empresa ON factory_tasks(empresa_id);
CREATE INDEX IF NOT EXISTS idx_factory_tasks_parent  ON factory_tasks(parent_task_id);
CREATE INDEX IF NOT EXISTS idx_factory_tasks_created ON factory_tasks(created_at DESC);
