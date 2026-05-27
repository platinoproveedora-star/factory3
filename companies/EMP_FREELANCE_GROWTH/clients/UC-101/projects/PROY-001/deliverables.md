# Deliverables - PROY-001 - Telegram bot de gastos y dashboard empresarial

Client: `UC-101`
Repo: `uc101-proy001`

## Scope
Crear un Telegram bot para registrar gastos de COMERCIALIZADORA DURALON DE CHIAPAS SA DE CV. El bot debe permitir captura de gastos desde tickets e imagenes usando AI/OCR, y tambien captura manual sin AI mediante formulario guiado.

El dashboard sera una base empresarial modular: inicia con gastos y analisis, pero debe quedar preparado para agregar futuros proyectos/procesos de la empresa.

## Checklist
- [ ] Telegram bot de captura de gastos
- [ ] Flujo de lectura de tickets e imagenes con AI/OCR
- [ ] Formulario de captura manual sin AI
- [ ] Dashboard empresarial modular
- [ ] Modulo de analisis de gastos
- [ ] Base de datos para gastos, categorias, usuarios y documentos
- [ ] Checklist de informacion que debe entregar el cliente
- [ ] README de uso y operacion
- [ ] Deploy inicial si se confirma Render necesario

## Preguntas Pendientes

- [ ] Campos obligatorios de captura manual.
- [ ] Chat IDs de Telegram para Tania, Luis y ACH.
- [x] Si requiere aprobacion de gastos o solo registro: solo registro por usuario.
- [x] Si requiere exportar Excel.
- [ ] Si requiere exportar PDF.
- [ ] Si los tickets se guardaran en Supabase Storage.

## Datos Confirmados

- Bot: `@Duralon1_bot`
- Usuarios iniciales: Tania, Luis, ACH
- Identificacion de usuario: por `telegram_chat_id`
- Aprobacion de gastos: no aplica en MVP
- Usuario de pruebas inicial: ACH (`8739777586`)
- Exportacion Excel: si
- Categorias: combustible, gastos varios, taller mecanico, papeleria, telmex, gas, internet, recargas celulares, nomina, gps, imss, sat
