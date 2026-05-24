# Knowledge base de agentes — Estoiko Lab

Cada agente puede tener un archivo de conocimiento en texto plano.
El contenido se inyecta directamente en el system prompt del agente.

## Formato

Un archivo `.txt` por agente. Contenido libre: FAQs, descripción de servicios,
políticas, catálogo, horarios, datos de contacto, etc.

## Convención de nombres

```
knowledge/
  cliente_abc.txt     ← conocimiento para el agente de Cliente ABC
  cliente_xyz.txt     ← conocimiento para el agente de Cliente XYZ
```

## Cómo vincular al agente

En `agents/<nombre>.json`, campo `knowledge_file`:

```json
"knowledge_file": "knowledge/cliente_abc.txt"
```

## Ejemplo de contenido

```
EMPRESA: Clínica Dental Sonrisa
SERVICIOS: Limpieza, blanqueamiento, ortodoncia, implantes
HORARIOS: Lunes a viernes 9am-7pm, Sábado 9am-2pm
UBICACIÓN: Av. Insurgentes 123, CDMX
TELÉFONO: 55-1234-5678
PRECIO LIMPIEZA: $800 MXN
PRECIO CONSULTA: $500 MXN (se descuenta si se hace tratamiento)

PREGUNTAS FRECUENTES:
¿Aceptan seguro? → No, solo pago directo o financiamiento propio.
¿Cuánto dura una limpieza? → Aproximadamente 45 minutos.
¿Dan factura? → Sí, se solicita al momento del pago.
```
