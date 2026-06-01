# Notes - PROY-001

## Arranque

Cliente: Luis Castillejos  
Empresa: COMERCIALIZADORA DURALON DE CHIAPAS SA DE CV  
Contacto: Luis Castillejos  
Email: alfredo82@hotmail.com  
Plataforma: interno

## Objetivo General

Mejorar procesos internos con AI.

## Proyecto Inicial

Crear el primer modulo operativo para la empresa: registro y analisis de gastos.

Este proyecto debe tener dos piezas:

1. Telegram bot para captura de gastos.
2. Dashboard empresarial modular para visualizar y analizar informacion.

El dashboard no debe quedar limitado a gastos. Debe ser la base para futuros proyectos internos de la empresa.

## Requerimientos Iniciales

- Bot Telegram para registrar gastos.
- Lectura de tickets e imagenes de gastos con AI/OCR.
- Captura manual sin AI mediante formulario guiado.
- Dashboard completo para analisis de gastos.
- Estructura modular para agregar futuros proyectos/procesos de la empresa.
- Analisis principal de la informacion que posteriormente entregara el cliente.

## Pendientes por Confirmar

- Campos obligatorios para captura manual.
- Chat IDs de Telegram de Tania, Luis y ACH.
- Si habra roles/permisos por usuario.
- Si requiere exportacion a PDF.
- Si el proyecto requiere repo propio desde el inicio: recomendado si.
- Dashboard nuevo debe ir a Vercel; Render queda reservado para Factory API central.

## Tiempo y Costo

- Tarifa acordada/base: 40 USD/hora.
- Estimacion inicial: 16 horas.
- Costo estimado: 640 USD.
- Deadline: 2026-05-29.
- Prioridad: alta, liberar MVP rapido porque ya existe un siguiente proyecto del cliente listo para iniciar.

## Datos Confirmados

- Bot Telegram dedicado: `@Duralon1_bot`.
- Usuarios iniciales: Tania, Luis y ACH.
- Captura: sin aprobacion de gastos; solo registro por usuario.
- Identificacion: por `telegram_chat_id`/numero de Telegram que envia el gasto.
- Usuario de pruebas inicial: ACH (`8739777586`).
- Exportacion a Excel: requerida.
- Categorias: combustible, gastos varios, taller mecanico, papeleria, telmex, gas, internet, recargas celulares, nomina, gps, imss, sat.

