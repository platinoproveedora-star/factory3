# vertical_bot

Skills portables reutilizables por cualquier bot de cualquier vertical.
No contienen logica de negocio — son infraestructura conversacional.

## Skills

| Skill | Descripcion | Estado |
|---|---|---|
| `bot_inbox_router` | Router generico de entrada — identifica canal, user_id, modo y deriva al flujo correcto | Pendiente |
| `bot_form_capture` | Ejecuta cuestionario paso a paso en cualquier canal (Telegram, IG, FB) con estado de conversacion | Pendiente |
| `bot_admin_tester` | Modo admin para probar vacantes, simular candidatos, ver scores y reiniciar flujos sin afectar produccion | Pendiente |

## Como se usan

El bot llama estos skills desde su `handle_update`:

```python
# ejemplo en bot.py
from factory.engine import SkillLoader, SkillRunner

result = runner.run("bot_inbox_router", {
    "canal": "telegram",
    "user_id": chat_id,
    "message_text": text,
    "empresa_id": "platino",
    "vacante_id": "vacante_001",
})
```

## Entradas de bot_inbox_router

```
canal           telegram | instagram | facebook | whatsapp | web
user_id         id unico del usuario en el canal
message_text    texto del mensaje
metadata        dict opcional con datos extra del canal
modo            normal | admin | prueba
empresa_id      identificador de la empresa
vacante_id      identificador de la vacante activa
```

## Salidas de bot_inbox_router

```
flujo_destino       rh_questionnaire | admin | soporte | desconocido
accion_siguiente    iniciar | continuar | finalizar | escalar
conversation_id     id de conversacion activa
candidate_id        id del candidato si ya existe
estado_conversacion sin_flujo | iniciando | haciendo_cuestionario | esperando_respuesta | finalizado
requiere_humano     bool
```

## Estados de conversacion

```
sin_flujo
iniciando
haciendo_cuestionario
esperando_respuesta
finalizado
modo_admin
modo_prueba
```

## Variables de entorno requeridas

Ninguna propias — usa las del canal (TELEGRAM_TOKEN, IG_ACCESS_TOKEN, etc.)
y las de Supabase para persistir estado de conversacion.

## Dependencias

- Supabase tabla `conversaciones` para estado persistente
- Skills de `vertical_rh` para el flujo de candidatos
- `telegram_send_message` o equivalente para responder
