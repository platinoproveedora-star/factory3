# Módulo 18: Costeo4All v1.0
Generado por Factory3 coordinator — solo diseño.

## Objetivo
Dashboard de costeo y listas de precios por empresa, accesible desde Apps4All, con selector de empresas y cálculo automático de precios por listas.

## Acceso y auth
- Entrada por Apps4All (autorización general del módulo `costeo4all`).
- Integración con adminportal para pruebas: módulo visible para `admin_total`.
- Usuario autenticado ve selector de empresas según grants.
- `admin_total` ve todas las empresas disponibles.

## Contexto
- `company_id` / `schema` se setean desde el selector de empresa del usuario o por defecto admin_total.
- No hay selección manual de schema sin auth.

## Datos mínimos por producto
- `sku`
- `nombre`
- `costo_actual`
- `costo_promedio`
- `ultimo_costo`
- `lista_1_%`
- `lista_1_precio`
- `lista_2_%`
- `lista_2_precio`
- `lista_3_%`
- `lista_3_precio`

## Reglas de negocio v1.0
- Porcentajes por empresa: configurables, default `20 / 35 / 50`.
- Precio por lista = `costo_actual * (1 + porcentaje/100)`.
- Editable solo la columna `%` por lista.
- `precio` se calcula automáticamente.
- No hay historial ni auditoría en v1.0.
- No hay comparador de proveedores ni OCR.

## Skills requeridas
- `costeo4all_products`: listar productos por empresa/schema, con filtro texto y orden asc/desc.
- `costeo4all_prices`: leer/guardar los 3 porcentajes por empresa.
- `costeo4all_price_lookup`: calcular precios finales por producto y lista.

## Contratos
Todas las skills reciben:
```json
{
  "company_id": "",
  "schema": "",
  "project_code": "PROY-001",
  "module_code": "costeo4all",
  "action": "list | get | update",
  "dry_run": true
}
```

### costeo4all_products
- `list`: devuelve `products[]` con `sku`, `nombre`, `costo_actual`, `costo_promedio`, `ultimo_costo`, `lista_1_%`, `lista_2_%`, `lista_3_%`, `lista_1_precio`, `lista_2_precio`, `lista_3_precio`.
- Filtros: `q` (texto), `order_by`, `order_dir`.
- Sin escritura.

### costeo4all_prices
- `list`: devuelve `{ empresa, porcentaje_1, porcentaje_2, porcentaje_3 }`.
- `update`: guarda `{ empresa, porcentaje_1, porcentaje_2, porcentaje_3 }`.
- `dry_run=true` devuelve preview sin guardar.

### costeo4all_price_lookup
- Input: `sku`, `lista: 1|2|3`, `costo_actual`.
- Output: `{ sku, costo_actual, porcentaje, precio_final }`.

## Dashboard propsuesto
- Ruta: `/costeo`
- Header:
  - Selector de empresas (requerido).
  - Botón/admin: cambiar % globales por empresa.
- Tabla:
  - Filtro global por texto.
  - Columnas ordenables asc/desc.
  - 11 columnas: sku, nombre, costo_actual, costo_promedio, ultimo_costo, lista1_%, lista1_precio, lista2_%, lista2_precio, lista3_%, lista3_precio.
  - Editable solo `%` en cada lista.
- Guardado:
  - Porcentajes → skill `costeo4all_prices` update.
  - Precios calculados se actualizan al cambiar `%` o `costo_actual`.

## Checklist de cierre
- [ ] Alta de skills en `factory/skills/internos/vertical_costeo4all/`
- [ ] Registro en `factory/skills/registry.json`
- [ ] Módulo visible en adminportal para pruebas
- [ ] `dry_run=true` por defecto
- [ ] Prueba MCP visible en Hermes
- [ ] Prueba online: login Apps4All → selector empresa → tabla → editar % → guardar

## Riesgos
- Bajo: reusa Auth Apps4All y esquema Factory existente.
- Medio: manejo de edición concurrente de porcentajes por empresa.

## Decisión
Diseño aprobado para implementación posterior. No modifica otros módulos.
