# RLS runtime patch - erp_kardex

Fecha: 2026-06-29

## Motivo

Los flujos operativos de compras y remisiones fallaban al insertar movimientos en
`uc101_proy004.erp_kardex` con:

```text
HTTP 401 / 42501: new row violates row-level security policy for table "erp_kardex"
```

La lectura de inventario ya funcionaba, pero las escrituras de `erp_kardex`
quedaban bloqueadas por RLS cuando Factory3 ejecutaba el flujo desde Render.

## Parche aplicado

Se agrego una policy temporal y restringida de `INSERT` sobre
`uc101_proy004.erp_kardex` para los flujos ERP de Duralon:

```sql
alter table uc101_proy004.erp_kardex enable row level security;

drop policy if exists erp_kardex_insert_erp_apps on uc101_proy004.erp_kardex;
create policy erp_kardex_insert_erp_apps
on uc101_proy004.erp_kardex
for insert
to anon, authenticated
with check (
  empresa_id = 'EMP_DURALON'
  and project_code = 'PROY-004'
  and module_code in ('inventario', 'compras')
  and source_type in ('compra', 'remision', 'ajuste')
  and movement_type in ('entrada', 'salida', 'ajuste')
);

grant insert on uc101_proy004.erp_kardex to anon, authenticated;
notify pgrst, 'reload schema';
```

## Pruebas realizadas

- Remision real minima: creo documento, item, evento y salida de kardex.
- Compra real minima: creo entrada de kardex.
- Ambos registros de prueba se borraron inmediatamente.
- Verificacion final de limpieza:
  - `sales_documents` con `CODEX_TEST_REMISION`: 0
  - `sales_document_items` con `PRUEBA CODEX BORRAR`: 0
  - `sales_events` de la remision de prueba: 0
  - `erp_kardex` con `CODEX_TEST_COMPRA` / `CODEX_TEST_REMISION`: 0

## Riesgo

Riesgo operativo bajo para desbloqueo inmediato. La policy no concede update ni
delete, y solo permite insertar movimientos de Duralon/PROY-004 con tipos
operativos esperados.

## Cierre futuro

Este parche debe reemplazarse por una solucion estructural:

1. Confirmar que Factory3 en Render escribe con `SUPABASE_SERVICE_ROLE_KEY`.
2. Hacer restart/redeploy controlado de Factory3 cuando Render tenga pipeline
   disponible.
3. Mover las escrituras criticas de ERP a endpoints server-side con credencial
   de servicio si se decide reducir dependencia de Render.
4. Quitar o endurecer `erp_kardex_insert_erp_apps` cuando el runtime use service
   role correctamente.
