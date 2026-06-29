# Vertical Multi Shopper

## Objetivo

`vertical_multi_shopper` es la vertical reusable para Purchasing IA Engine: cotizaciones de venta, productos a cotizar, proveedores, solicitudes de cotizacion de compra, documentos y precios historicos.

## Dashboard

Ruta fuente:

```text
companies/EMP_MULTI_SHOPPER/projects/PROY-001_DASHBOARD
```

Deploy objetivo: Vercel.

El dashboard sigue el patron de Conta4All:

- Next.js.
- Auth con `vertical_auth_security`.
- Cookie JWT httpOnly.
- Middleware de rutas protegidas.
- API routes/server components llamando Factory API.
- Sin credenciales Supabase en frontend.

## Contexto Obligatorio

Todo skill debe recibir:

```json
{
  "company_id": "EMP_MULTI_SHOPPER",
  "project_code": "PROY-001",
  "module_code": "vertical_multi_shopper",
  "schema": "multi_shopper"
}
```

## Etapa 1

Pantallas:

- Dashboard.
- Cotizaciones de venta.
- Productos.
- Proveedores.
- Cotizaciones compra.
- Add documentos.
- Documentos.
- Configuracion.

Reglas:

- No escribe inventario.
- No modifica kardex.
- No envia WhatsApp/correo automaticamente.
- ERP solo lectura/referencia mediante IDs opcionales.
