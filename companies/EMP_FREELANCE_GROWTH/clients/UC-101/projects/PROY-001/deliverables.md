# Deliverables - PROY-001 - Telegram bot de gastos y dashboard empresarial

Client: `UC-101`
Repo: `uc101-proy001`

## Scope
Crear un Telegram bot para registrar gastos de COMERCIALIZADORA DURALON DE CHIAPAS SA DE CV. El bot debe permitir captura de gastos desde tickets e imagenes usando AI/OCR, y tambien captura manual sin AI mediante formulario guiado.

El dashboard sera una base empresarial modular: inicia con gastos y analisis, pero debe quedar preparado para agregar futuros proyectos/procesos de la empresa.

## Checklist
- [x] Telegram bot de captura de gastos (@Duralon1_bot) — corriendo en factory3
- [ ] Flujo de lectura de tickets e imagenes con AI/OCR — siguiente sprint
- [x] Formulario de captura manual sin AI — forma 1 (cantidad,fecha,concepto) + forma 2 (/nuevo paso a paso)
- [x] Dashboard empresarial modular (Streamlit) — https://uc101-proy001.onrender.com
- [x] Modulo de analisis de gastos — KPIs, barras por categoria, pastel por usuario, tendencia mensual, tabla filtrable, export Excel
- [x] Base de datos — schema uc101_proy001 creado y expuesto en Supabase (5 tablas + 12 categorias seed)
- [x] Informacion del cliente recopilada (categorias, usuarios, politica, exportaciones)
- [x] README de uso y operacion — repo platinoproveedora-star/uc101-proy001
- [x] Deploy dashboard en Render — srv-d8bjgbel51nc73db9t30 (uc101-proy001, auto-deploy ON)

## Preguntas Pendientes

- [ ] Chat IDs de Telegram para Tania y Luis (ACH = 8739777586 ya confirmado).
- [ ] Si requiere exportar PDF.
- [ ] Si los tickets se guardaran en Supabase Storage (bucket uc101-proy001-assets ya nombrado).
- [x] Campos obligatorios: categoria, monto, fecha, descripcion (opcional), usuario.
- [x] Si requiere aprobacion de gastos: no, solo registro por usuario.
- [x] Si requiere exportar Excel: si.

## Datos Confirmados

- Bot: `@Duralon1_bot`
- Usuarios iniciales: Tania, Luis, ACH
- Identificacion de usuario: por `telegram_chat_id`
- Aprobacion de gastos: no aplica en MVP
- Usuario de pruebas inicial: ACH (`8739777586`)
- Exportacion Excel: si
- Categorias: combustible, gastos varios, taller mecanico, papeleria, telmex, gas, internet, recargas celulares, nomina, gps, imss, sat
