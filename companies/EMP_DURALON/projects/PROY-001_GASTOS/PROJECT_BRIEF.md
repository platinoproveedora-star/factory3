# PROY-001 - Telegram bot de gastos y dashboard empresarial

## Cliente

- Cliente: Luis Castillejos
- Empresa: COMERCIALIZADORA DURALON DE CHIAPAS SA DE CV
- Contacto: Luis Castillejos
- Email: alfredo82@hotmail.com
- Plataforma: interno

## Objetivo

Crear una herramienta interna para registrar, organizar y analizar gastos de la empresa usando Telegram y un dashboard central.

## Producto Inicial

El proyecto inicia con un modulo de gastos, pero el dashboard debe quedar preparado como base para otros proyectos internos de la empresa.

## Alcance MVP

1. Bot Telegram para captura de gastos.
2. Captura por imagen/ticket con AI/OCR.
3. Captura manual sin AI mediante flujo guiado.
4. Dashboard de gastos con analisis principal.
5. Base modular para futuros procesos/proyectos.

## Tiempo y Costo

- Tarifa: 40 USD/hora.
- Estimacion inicial: 16 horas.
- Costo estimado: 640 USD.
- Deadline operativo: 2026-05-29.
- Ritmo esperado: avance rapido en 2 dias para liberar MVP inicial y continuar con el siguiente proyecto.

## Nombre Tecnico

- Empresa: `EMP_DURALON`
- Legacy client: `UC-101`
- Proyecto: `PROY-001`
- Repo: `platinoproveedora-star/uc101-proy001`
- Repo URL: `https://github.com/platinoproveedora-star/uc101-proy001`
- Vercel sugerido: `uc101-proy001`
- Render: reservado para Factory API central, no para dashboard del proyecto.
- Bot Telegram: `@Duralon1_bot`
- Schema Supabase: `uc101_proy001`
- Bucket Storage: `uc101-proy001-assets`

## Usuarios Iniciales

- Tania
- Luis
- ACH (usuario inicial de pruebas)

## Identificacion de Usuarios

El bot debe identificar al usuario por el `telegram_chat_id` que envia el gasto.

Mapeo inicial:

| Usuario | Telegram chat_id | Uso |
|---|---|---|
| Luis | pendiente | captura |
| Tania | pendiente | captura |
| ACH | `8739777586` | pruebas iniciales |

## Categorias de Gastos

- combustible
- gastos varios
- taller mecanico
- papeleria
- telmex
- gas
- internet
- recargas celulares
- nomina
- gps
- imss
- sat

## Exportaciones

- Excel: requerido.
- PDF: pendiente/no confirmado.

## Datos Que Debe Pasar El Cliente

- Campos requeridos por gasto.
- Ejemplos de tickets/fotos.
- Reportes esperados.
- Chat IDs de Telegram para Tania, Luis y ACH.

## Riesgos

- Tickets con baja calidad de imagen.
- Variacion alta de formatos de ticket.
- Falta de reglas claras de categorias.
- Necesidad futura de permisos por usuario.

## Siguiente Paso

Confirmar campos del gasto y chat IDs de Telegram. No habra aprobacion de gastos en el MVP; solo captura por usuario.
