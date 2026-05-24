# rh_interview_scheduler

Agenda, cancela y lista entrevistas. Al agendar, notifica automáticamente al candidato y al reclutador por Telegram. Si no se especifica fecha, calcula el siguiente slot disponible (próximo día hábil a las 9am).

## Acciones

### agendar

```json
{
  "accion": "agendar",
  "candidato_id": "uuid",
  "reclutador_id": "uuid-opcional",
  "vacante_id": "uuid-opcional",
  "fecha_hora": "2026-05-12 10:00",
  "duracion_min": 30,
  "tipo": "presencial",
  "notas": "Llevar licencia y documentos",
  "notify_candidato": true,
  "notify_reclutador": true,
  "dry_run": false
}
```

- `candidato_id` — requerido
- `fecha_hora` — si omitido, se asigna automáticamente el próximo slot (día hábil 9am)
- `tipo` — `presencial` | `videollamada` | `telefonica`
- `dry_run` — si `true`, no guarda ni notifica, solo devuelve los datos que se usarían

### cancelar

```json
{
  "accion": "cancelar",
  "entrevista_id": "uuid"
}
```

### listar

```json
{
  "accion": "listar",
  "reclutador_id": "uuid-opcional",
  "candidato_id": "uuid-opcional",
  "estado": "agendada"
}
```

- `estado` — `agendada` | `cancelada` | `realizada`

## Output (agendar)

```json
{
  "ok": true,
  "data": {
    "entrevista_id": "uuid",
    "fecha_hora": "2026-05-12 10:00",
    "tipo": "presencial",
    "duracion_min": 30,
    "dry_run": false,
    "notificaciones": {
      "candidato": {"ok": true},
      "reclutador": {"ok": true}
    }
  }
}
```

## Dependencias

- `SUPABASE_URL` / `SUPABASE_KEY`
- Skill `telegram_send_message` (cargado dinámicamente para notificaciones)

## Tablas Supabase

- `entrevistas` (lectura/escritura) — `candidato_id`, `reclutador_id`, `vacante_id`, `fecha_hora`, `duracion_min`, `tipo`, `estado`, `notas`
- `candidatos` (lectura) — `nombre`, `telefono`, `canal_user_id`
- `reclutadores` (lectura) — `nombre`, `telegram_chat_id`
