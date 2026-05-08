"""Run RH schema migrations: folio triggers, tipo column, bot_states table."""
import os, sys
from pathlib import Path

root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

# Load .env
env_file = root / ".env"
for line in env_file.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    k = k.strip(); v = v.strip().strip('"').strip("'")
    if k and k not in os.environ:
        os.environ[k] = v

from factory.engine import SupabaseClient
db = SupabaseClient({})

STATEMENTS = [
    # folio en vacantes
    "ALTER TABLE vacantes ADD COLUMN IF NOT EXISTS folio TEXT",
    "CREATE SEQUENCE IF NOT EXISTS vacantes_folio_seq START 1",
    """
    CREATE OR REPLACE FUNCTION generate_vacante_folio()
    RETURNS TRIGGER AS $$
    BEGIN
      IF NEW.folio IS NULL THEN
        NEW.folio := 'VAC-' || LPAD(nextval('vacantes_folio_seq')::text, 3, '0');
      END IF;
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql
    """,
    "DROP TRIGGER IF EXISTS trg_vacante_folio ON vacantes",
    """
    CREATE TRIGGER trg_vacante_folio
    BEFORE INSERT ON vacantes
    FOR EACH ROW EXECUTE FUNCTION generate_vacante_folio()
    """,
    # folio en candidatos
    "ALTER TABLE candidatos ADD COLUMN IF NOT EXISTS folio TEXT",
    "CREATE SEQUENCE IF NOT EXISTS candidatos_folio_seq START 1",
    """
    CREATE OR REPLACE FUNCTION generate_candidato_folio()
    RETURNS TRIGGER AS $$
    BEGIN
      IF NEW.folio IS NULL THEN
        NEW.folio := 'CAND-' || LPAD(nextval('candidatos_folio_seq')::text, 3, '0');
      END IF;
      RETURN NEW;
    END;
    $$ LANGUAGE plpgsql
    """,
    "DROP TRIGGER IF EXISTS trg_candidato_folio ON candidatos",
    """
    CREATE TRIGGER trg_candidato_folio
    BEFORE INSERT ON candidatos
    FOR EACH ROW EXECUTE FUNCTION generate_candidato_folio()
    """,
    # tipo en vacantes
    "ALTER TABLE vacantes ADD COLUMN IF NOT EXISTS tipo TEXT DEFAULT 'real'",
    # bot_states para persistir estado del bot
    """
    CREATE TABLE IF NOT EXISTS bot_states (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      chat_id TEXT UNIQUE NOT NULL,
      state JSONB DEFAULT '{}',
      updated_at TIMESTAMPTZ DEFAULT NOW()
    )
    """,
    # unique index para bot_states
    "CREATE UNIQUE INDEX IF NOT EXISTS bot_states_chat_id_idx ON bot_states(chat_id)",
]

print(f"Ejecutando {len(STATEMENTS)} sentencias...\n")
ok = 0
for i, sql in enumerate(STATEMENTS, 1):
    sql = sql.strip()
    label = sql.split('\n')[0][:60]
    r = db.management_query(sql)
    if r.get("ok"):
        print(f"  [{i:02d}] OK  — {label}")
        ok += 1
    else:
        print(f"  [{i:02d}] ERR — {label}")
        print(f"         {r.get('error') or r}")

print(f"\n{ok}/{len(STATEMENTS)} sentencias exitosas.")
