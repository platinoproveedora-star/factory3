# Deliverables - PROY-001 - Telegram bot de gastos y dashboard empresarial

Company: `EMP_DURALON`
Legacy client: `UC-101`
Repo: `uc101-proy001`

## Scope
Crear un Telegram bot para registrar gastos de COMERCIALIZADORA DURALON DE CHIAPAS SA DE CV. El bot debe permitir captura de gastos desde tickets e imagenes usando AI/OCR, y tambien captura manual sin AI mediante formulario guiado.

El dashboard sera una base empresarial modular: inicia con gastos y analisis, pero debe quedar preparado para agregar futuros proyectos/procesos de la empresa.

## Checklist
- [x] Telegram bot de captura de gastos (@Duralon1_bot) — corriendo en factory3
- [ ] Flujo de lectura de tickets e imagenes con AI/OCR — siguiente sprint
- [x] Formulario de captura manual sin AI — forma 1 (cantidad,fecha,concepto) + forma 2 (/nuevo paso a paso)
- [ ] Dashboard empresarial modular en Vercel — pendiente de deploy final
- [x] Modulo de analisis — Overview KPIs+alertas, Analisis (barras/pie/tendencia/treemap/comparacion), Detalle filtrable, Exportar Excel+PDF configurable
- [x] Base de datos — schema uc101_proy001 creado y expuesto en Supabase (5 tablas + 12 categorias seed)
- [x] Informacion del cliente recopilada (categorias, usuarios, politica, exportaciones)
- [x] README de uso y operacion — repo platinoproveedora-star/uc101-proy001
- [ ] Deploy dashboard en Vercel — `uc101-proy001`
- [x] PDF export configurable — secciones, membrete, columnas, filtros en el PDF
- [x] Manual de prueba enviado a ACH (para reenviar a Tania y Luis)
- [x] Tania pre-registrada en Supabase USR-002 — se vincula automaticamente en su primer /start

## Preguntas Pendientes

- [x] Tania: +529612970916 — pre-registrada, pendiente que haga /start para vincular chat_id
- [ ] Luis: numero de telefono / chat_id pendiente
- [x] PDF export: implementado como configurable en el dashboard
- [ ] Si los tickets se guardaran en Supabase Storage (bucket uc101-proy001-assets ya nombrado).
- [x] Campos obligatorios: categoria, monto, fecha, descripcion (opcional), usuario.
- [x] Si requiere aprobacion de gastos: no, solo registro por usuario.
- [x] Si requiere exportar Excel: si.

## Datos Confirmados

- Bot: `@Duralon1_bot`
- Dashboard: pendiente Vercel (`https://uc101-proy001.vercel.app` esperado)
- Usuarios iniciales: Tania (USR-002, +529612970916), Luis (pendiente), ACH (USR-001, 8739777586)
- Identificacion de usuario: por `telegram_chat_id`
- Aprobacion de gastos: no aplica en MVP
- Exportacion Excel: si
- Exportacion PDF: si (configurable en dashboard)
- Categorias: combustible, gastos varios, taller mecanico, papeleria, telmex, gas, internet, recargas celulares, nomina, gps, imss, sat
