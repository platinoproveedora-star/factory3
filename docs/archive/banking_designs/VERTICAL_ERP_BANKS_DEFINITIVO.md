# Vertical ERP Banks — DEFINITIVO para codificar

Documento unico. Sustituye a v1, v2, v3 y v4 — no hace falta volver a esos
archivos. Todo lo que Codex/Claude Code necesita para codificar sin adivinar
nada esta aqui, completo, sin remitir a otra seccion fuera de este documento.

---

## 0. Objetivo

`vertical_erp_banks` es el motor del dinero en Factory 3: cuentas, polizas de
movimiento, autorizacion y el punto de conexion para payables, billing y
conciliacion bancaria. Cada empresa vive en su propio schema de Supabase
(mismo patron que billing/inventario/ventas), nunca en un schema compartido.

---

## 1. Patron de aislamiento

Schema por empresa, resuelto via `vertical_erp/erp_project_context_resolve`
y materializado en banks via `resolve_banks_context` (`_banks_common.py`).
Ya implementado y correcto, no se toca.

```text
EMP_DURALON  -> companies/EMP_DURALON/projects/PROY-00X_BANKS/project.json
                 -> supabase_schema propio
Otra empresa -> su propio project.json, su propio schema
```

`empresa_id` se guarda en cada fila como segunda capa de integridad, pero el
aislamiento real es fisico (schema separado), no un `WHERE`.

La vista consolidada de varias empresas (seccion 7) es una capa de lectura
aparte; nunca hay tabla ni schema compartido.

---

## 2. Tablas — DDL completo final

### 2.1 `banks_accounts` (ya existe, sin cambios)

```sql
create table if not exists {schema}.banks_accounts (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,
  empresa_id text not null,
  project_code text not null,
  module_code text not null default 'banks',
  account_type text not null,
  account_name text not null,
  bank_name text,
  account_number text,
  account_number_mask text,
  holder_name text,
  currency text not null default 'MXN',
  responsible_user text,
  status text not null default 'active',
  current_balance numeric(14,2) not null default 0,
  opening_balance numeric(14,2) not null default 0,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz
);
```

### 2.2 `banks_movements` — version final con todas las columnas

```sql
create table if not exists {schema}.banks_movements (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,
  empresa_id text not null,
  project_code text not null,
  module_code text not null default 'banks',
  account_id uuid not null references {schema}.banks_accounts(id),
  account_folio text not null,
  movement_type text not null
    constraint banks_movements_movement_type_chk
    check (movement_type in ('entrada','salida')),
  source_type text not null
    constraint banks_movements_source_type_chk
    check (source_type in ('pago','transferencia','ajuste','corte','apertura','devolucion')),
  source_module text,                       -- 'billing' | 'gastos' | 'compras' | 'reconciliation' | 'manual'
  source_id text,
  source_folio text,
  amount numeric(14,2) not null,
  balance_before numeric(14,2),
  balance_after numeric(14,2),               -- nullable: no existe valor real mientras authorization_status='pendiente'
  movement_date date not null,
  transfer_group_id uuid,
  reversal_of_movement_id uuid references {schema}.banks_movements(id),
  authorization_status text not null default 'no_requerida'
    constraint banks_movements_authorization_status_chk
    check (authorization_status in ('no_requerida','pendiente','autorizado','rechazado')),
  authorization_id uuid,
  clave_rastreo text,
  value_date date,
  reconciliation_status text not null default 'pendiente'
    constraint banks_movements_reconciliation_status_chk
    check (reconciliation_status in ('pendiente','conciliado','en_disputa','no_aplica')),
  reconciled_at timestamptz,
  notes text,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz,
  constraint banks_movements_transfer_group_chk
    check (source_type <> 'transferencia' or transfer_group_id is not null)
);
```

`banks_movements_transfer_group_chk` es defensa en profundidad: el contrato
de la seccion 6.4 ya dice que `erp_banks_movement_record` debe rechazar una
transferencia sin `transfer_group_id` antes de insertar, pero esa
validacion vive en la funcion/skill. La constraint a nivel de tabla protege
contra cualquier insert que no pase por ahi (migracion de datos, fix manual,
bug futuro).

Para schemas que ya tengan `banks_movements` creada con la version vieja
(sin estas columnas), correr en su lugar:

```sql
alter table {schema}.banks_movements
  add column if not exists source_module text,
  add column if not exists balance_before numeric(14,2),
  add column if not exists transfer_group_id uuid,
  add column if not exists reversal_of_movement_id uuid references {schema}.banks_movements(id),
  add column if not exists authorization_status text not null default 'no_requerida',
  add constraint banks_movements_authorization_status_chk
    check (authorization_status in ('no_requerida','pendiente','autorizado','rechazado')),
  add column if not exists authorization_id uuid,
  add column if not exists clave_rastreo text,
  add column if not exists value_date date,
  add column if not exists reconciliation_status text not null default 'pendiente',
  add constraint banks_movements_reconciliation_status_chk
    check (reconciliation_status in ('pendiente','conciliado','en_disputa','no_aplica')),
  add column if not exists reconciled_at timestamptz;

-- balance_after ya existia como not null en instalaciones viejas; relajar:
alter table {schema}.banks_movements alter column balance_after drop not null;

-- movement_type/source_type ya existian sin CHECK; agregar las constraints
-- nombradas. Usar "not valid" + "validate constraint" por separado si la
-- tabla ya tiene filas que pudieran violar el check (evita un bloqueo largo
-- en produccion mientras valida fila por fila):
alter table {schema}.banks_movements
  add constraint banks_movements_movement_type_chk
    check (movement_type in ('entrada','salida')) not valid;
alter table {schema}.banks_movements
  validate constraint banks_movements_movement_type_chk;

alter table {schema}.banks_movements
  add constraint banks_movements_source_type_chk
    check (source_type in ('pago','transferencia','ajuste','corte','apertura','devolucion')) not valid;
alter table {schema}.banks_movements
  validate constraint banks_movements_source_type_chk;

alter table {schema}.banks_movements
  add constraint banks_movements_transfer_group_chk
    check (source_type <> 'transferencia' or transfer_group_id is not null) not valid;
alter table {schema}.banks_movements
  validate constraint banks_movements_transfer_group_chk;
```

### 2.3 `banks_authorization_rules` (nueva)

```sql
create table if not exists {schema}.banks_authorization_rules (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,
  empresa_id text not null,
  project_code text not null,
  module_code text not null default 'banks',
  rule_name text not null,
  active boolean not null default true,
  applies_to_account_id uuid references {schema}.banks_accounts(id),  -- null = todas las cuentas
  movement_type_filter text,        -- null = cualquier movement_type
  source_type_filter text,          -- null = cualquier source_type
  source_module_filter text,        -- null = cualquier source_module
  min_amount numeric(14,2) not null
    constraint banks_authorization_rules_min_amount_chk
    check (min_amount >= 0),
  authorizer_user_id uuid,          -- null = se resuelve via default_authorizer del company.config.json
  authorizer_role text,
  priority integer not null default 100,  -- numero menor = se evalua primero
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

create index if not exists banks_auth_rules_empresa_idx on {schema}.banks_authorization_rules(empresa_id, active);
```

### 2.4 `banks_authorizations` (nueva)

```sql
create table if not exists {schema}.banks_authorizations (
  id uuid primary key default gen_random_uuid(),
  folio text unique not null,
  empresa_id text not null,
  project_code text not null,
  module_code text not null default 'banks',
  movement_id uuid not null references {schema}.banks_movements(id),
  rule_id uuid references {schema}.banks_authorization_rules(id),
  requested_by uuid,
  requested_at timestamptz not null default now(),
  status text not null default 'pendiente'
    constraint banks_authorizations_status_chk
    check (status in ('pendiente','aprobado','rechazado')),
  decided_by uuid,
  decided_at timestamptz,
  decision_notes text,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz
);

create index if not exists banks_auth_status_idx on {schema}.banks_authorizations(empresa_id, status);
create index if not exists banks_movements_auth_idx on {schema}.banks_movements(authorization_status);
create index if not exists banks_movements_reconcile_idx on {schema}.banks_movements(account_id, reconciliation_status);
```

### 2.5 Indices adicionales en `banks_movements`

```sql
create index if not exists banks_movements_account_idx on {schema}.banks_movements(account_id);
create index if not exists banks_movements_source_idx on {schema}.banks_movements(source_type, source_id);
create index if not exists banks_movements_date_idx on {schema}.banks_movements(movement_date desc);
```

### 2.6 Indice de idempotencia (nuevo)

Evita duplicar saldo si billing/payables/reconciliation llaman dos veces por
error (reintento de red, doble click, doble evento):

```sql
create unique index if not exists banks_movements_source_unique_idx
on {schema}.banks_movements(source_module, source_type, source_id, movement_type)
where source_id is not null and reversal_of_movement_id is null;
```

Se agrega `movement_type` a la llave del indice (no solo
`source_module`+`source_type`+`source_id`). Motivo: una transferencia genera
2 filas que pueden compartir el mismo `source_id` (el id de la solicitud de
transferencia que las origino) pero con `movement_type` distinto
(`salida` en origen, `entrada` en destino). Sin `movement_type` en la
llave, la segunda pierna de cualquier transferencia que reuse `source_id`
violaria el indice unico y la operacion completa de transferencia
fallaria. Para `pago`/`ajuste`/`corte`/etc, que siempre generan una sola
fila por `source_id`, agregar `movement_type` no debilita la proteccion de
idempotencia en nada.

`erp_banks_movement_record` debe ademas, antes de insertar, buscar si ya
existe un movimiento con esa combinacion `source_module` + `source_type` +
`source_id` + `movement_type`. Si existe, **no truena**: regresa `{ok: true,
data: {movement: <el existente>, idempotent: true}}` en vez de insertar
duplicado o lanzar el error de constraint hacia el caller. El indice unico
es la red de seguridad a nivel de base de datos; el chequeo previo es la
experiencia normal sin depender de capturar la excepcion de Postgres.

El chequeo previo no es atomico por si solo: dos llamadas concurrentes con
el mismo `source_id` pueden pasar el chequeo antes de que ninguna haya
hecho commit. Por eso `banks_record_movement()` (seccion 5.0) debe envolver
el `insert` en un bloque `exception when unique_violation`: si el insert
choca contra `banks_movements_source_unique_idx`, la funcion debe atrapar
el error, volver a `select` el movimiento que si se inserto, y regresarlo
con `idempotent: true` — nunca debe propagar el error de constraint al
caller.

---

## 3. Orden de migracion exacto

Todo corre dentro del mismo schema de empresa, parametrizado por `{schema}`
— **es un script generico, no uno distinto por empresa**. Se ejecuta una vez
por cada empresa que active banks (igual mecanismo que hoy usa
`erp_banks_schema_plan`: genera el SQL con `{schema}` resuelto y se corre en
el Supabase SQL Editor de esa empresa).

Para empresas que **todavia no han corrido nada de banks**: usar el DDL
completo de la seccion 2 tal cual (CREATE con todas las columnas desde el
dia uno). Para empresas que **ya corrieron la version vieja** (solo
`banks_accounts`/`banks_movements` basicos): usar el orden siguiente.

1. `ALTER TABLE banks_movements ...` (seccion 2.2, variante ALTER, incluye
   ahora los `CHECK` de `movement_type`/`source_type`/`transfer_group_id`).
   No rompe nada existente porque todas las columnas nuevas son nullable o
   tienen default, y los `CHECK` se agregan con `not valid` +
   `validate constraint` por separado para no bloquear la tabla.
2. `CREATE TABLE banks_authorization_rules ...` (seccion 2.3).
3. `CREATE TABLE banks_authorizations ...` (seccion 2.4). Depende de
   `banks_authorization_rules` por el FK `rule_id`, por eso va despues.
4. Indices de las secciones 2.3, 2.4, 2.5 **y 2.6** (el indice unico de
   idempotencia tambien va aqui, antes de que cualquier movimiento real se
   inserte).
5. `INSERT` de la regla default de reconciliacion (seccion 6.2), usando la
   funcion `reserve_erp_folio()` que ya existe en el schema para generar el
   folio dentro del mismo `INSERT`:

```sql
insert into {schema}.banks_authorization_rules (
  folio, empresa_id, project_code, module_code, rule_name, active,
  applies_to_account_id, movement_type_filter, source_type_filter,
  source_module_filter, min_amount, authorizer_user_id, priority
) values (
  {schema}.reserve_erp_folio('banks_authorization_rules', 'BAR', 5, '{empresa_id}', '{project_code}', 'banks'),
  '{empresa_id}', '{project_code}', 'banks',
  'Forzar autorizacion en ajustes de reconciliacion', true,
  null, null, null, 'reconciliation', 0, null, 1
);
```

Este `INSERT` (paso 5) si requiere que `{empresa_id}` y `{project_code}` ya
esten resueltos como valores literales (no son DDL generico como los pasos
1-4), porque la regla es una fila de datos especifica de esa empresa.

6. `CREATE OR REPLACE FUNCTION banks_record_movement(...)` y
   `banks_decide_authorization(...)` (seccion 5.0). Van despues de que
   existan todas las tablas que referencian, no antes.
7. `CREATE OR REPLACE FUNCTION banks_movements_protect()` +
   `CREATE TRIGGER banks_movements_protect_trg` (seccion 7.1). Debe ir
   **al final**, despues del paso 6: si el trigger se activa antes de que
   existan las funciones de negocio, cualquier prueba manual de insercion/
   actualizacion durante la migracion se comporta igual que en produccion
   desde el primer momento, lo cual es justamente el objetivo, pero
   conviene confirmar que los pasos 1-6 ya insertaron/ajustaron lo que
   necesitaban antes de que el trigger empiece a vigilar.

---

## 4. Prefijos de folio

| Prefijo | Tabla | Estado |
|---|---|---|
| `BAC` | `banks_accounts` | ya en uso |
| `BAM` | `banks_movements` | ya en uso |
| `BAR` | `banks_authorization_rules` | nuevo, sin choque confirmado |
| `BAU` | `banks_authorizations` | nuevo, sin choque confirmado |

Verificado contra todos los prefijos ya usados en el repo: `BCUT`
(`billing_cash_cuts`), `BCF` (`billing_collection_folios`), `BMA`
(`billing_money_accounts`), `BAPP` (`billing_payment_applications`), `BPAY`
(`billing_payments`), `COM`/`COT`/`PED`/`REM`/`REMI`/`FAC`/`KAR`/`AJU`/`EVT`
(ventas/inventario). `BAR` y `BAU` no chocan con ninguno.

---

## 5. Skills nuevos — contrato completo

### 5.0 Requisito de atomicidad (aplica a 5.1 y a `erp_banks_movement_record`)

El patron actual de `_banks_common.py`/`SupabaseClient` (un `rest_select`
seguido de un `rest_update` por separado, como ya hace
`erp_banks_movement_record` hoy) **no es atomico**: entre el select y el
update puede entrar otro movimiento y pisar el saldo. Esto es inaceptable en
el motor de dinero.

**Obligatorio:** tanto `erp_banks_movement_record` (creacion de movimiento)
como `erp_banks_authorization_decide` (aprobar/rechazar) deben ejecutar su
logica de lectura-de-saldo + escritura como una sola transaccion de
Postgres con bloqueo de fila, no como llamadas REST secuenciales desde
Python. Esto requiere una funcion `plpgsql` por operacion (mismo patron que
ya usa `reserve_erp_folio()`), invocada via RPC de Supabase en vez de
`rest_select`/`rest_update` sueltos:

```sql
create or replace function {schema}.banks_record_movement(...)
returns jsonb language plpgsql security definer set search_path = {schema}, public as $$
declare
  v_current_balance numeric(14,2);
begin
  select current_balance into v_current_balance
  from {schema}.banks_accounts
  where id = p_account_id
  for update;
  -- ... resto de la logica: evaluar reglas, insertar movimiento,
  -- actualizar cuenta solo si no requiere autorizacion, todo dentro
  -- de esta misma transaccion.
end;
$$;
```

Mismo principio para `banks_decide_authorization(...)`: el `select ... for
update` sobre `banks_accounts` y la actualizacion de
`banks_movements`/`banks_authorizations` ocurren dentro de la misma funcion,
nunca como pasos sueltos desde `service.py`. El `skill.py`/`service.py` de
cada skill se convierte en un wrapper delgado que llama a la funcion via RPC
y formatea la respuesta — la logica de negocio critica vive en la funcion
de Postgres, no en Python, precisamente para que el bloqueo de fila (`for
update`) sea real.

### 5.1 `erp_banks_authorization_decide`

**Input:**
```text
movement_id    uuid, requerido
decision       text, requerido. Valores: 'aprobado' | 'rechazado'
decided_by     uuid, requerido
decision_notes text, opcional
```

**Logica (ejecutada dentro de `banks_decide_authorization()`, ver 5.0):**
1. Resolver contexto via `resolve_banks_context`.
2. **Lockear primero el movimiento**: `select * from banks_movements where
   id = movement_id and empresa_id = ctx.empresa_id for update`. Si no
   existe o no pertenece a la empresa -> error. Este lock es obligatorio y
   va antes que cualquier otra lectura: sin el, dos llamadas concurrentes a
   `erp_banks_authorization_decide` sobre el mismo `movement_id` podrian
   pasar ambas el chequeo del paso 3 antes de que ninguna hiciera commit,
   resultando en doble aplicacion de saldo. El lock sobre el movimiento
   serializa cualquier decision concurrente sobre la misma fila.
3. Con el movimiento ya lockeado, si `authorization_status != 'pendiente'`
   -> error ("movimiento ya decidido o no requiere autorizacion"). Una
   segunda llamada concurrente que llegue aqui despues de que la primera
   ya hizo commit va a ver el estado actualizado y fallar limpiamente en
   este paso, no va a duplicar nada.
4. Si la decision va a ser `'aprobado'`, lockear tambien la cuenta:
   `select current_balance from banks_accounts where id = account_id for
   update`. Orden de lock fijo en todo el modulo: primero
   `banks_movements`, despues `banks_accounts` — el mismo orden que debe
   respetar `banks_record_movement()` (seccion 5.0) si en algun punto
   futuro llegara a tocar ambas tablas, para evitar deadlocks por orden de
   lock cruzado entre las dos funciones.
5. Resolver el autorizador correcto, en este orden: si la regla que generó
   la autorizacion (`banks_authorizations.rule_id` ->
   `banks_authorization_rules.authorizer_user_id`) trae un valor explicito
   (no null), ese gana. Si es `null`, se usa `default_authorizer` de
   `company.config.json` (via `erp_project_context_resolve`, seccion 8.2).
   Si `decided_by` no coincide exactamente con el autorizador resuelto ->
   error ("usuario no autorizado para decidir"), no se mueve nada.
6. Si `decision = 'rechazado'`: actualizar `banks_authorizations.status =
   'rechazado'`, `decided_by`, `decided_at`, `decision_notes`. Actualizar
   `banks_movements.authorization_status = 'rechazado'`. No se toca
   `current_balance`, ni `balance_before`, ni `balance_after`.
7. Si `decision = 'aprobado'`: con el lock de cuenta ya tomado en el paso 4,
   leer `current_balance` **vigente en ese momento** de `banks_accounts`
   (no el que existia cuando se creo el movimiento) y guardarlo en
   `banks_movements.balance_before`. Calcular `balance_after =
   current_balance + amount` (si `movement_type='entrada'`) o
   `current_balance - amount` (si `'salida'`) y guardarlo en
   `banks_movements.balance_after`. Actualizar
   `banks_movements.authorization_status = 'autorizado'`. Actualizar
   `banks_accounts.current_balance = balance_after`. Actualizar
   `banks_authorizations.status='aprobado'`, `decided_by`, `decided_at`,
   `decision_notes`.

**Output:** `{ok, data: {movement, authorization, balance_before,
balance_after}}`.

### 5.2 `erp_banks_mark_reconciled`

**Input:**
```text
movement_id            uuid, requerido
reconciliation_status  text, requerido. Valores: 'conciliado' | 'en_disputa' | 'no_aplica'
reconciled_at          timestamptz, opcional (default now() si status='conciliado')
```

**Logica:**
1. Resolver contexto via `resolve_banks_context`.
2. Buscar movimiento por `id` + `empresa_id`. No existe/no pertenece ->
   error.
3. Si `authorization_status != 'autorizado'` -> error ("solo movimientos
   autorizados pueden conciliarse").
4. Update exclusivo de `reconciliation_status`, `reconciled_at`,
   `updated_at`. Ningun otro campo se toca.

**Output:** `{ok, data: {movement}}`.

Unico punto de entrada que `vertical_erp_reconciliation` puede llamar contra
banks para escritura. Lectura de `banks_movements` es libre (select directo),
pero escritura solo por aqui.

### 5.3 `erp_banks_consolidated_dashboard`

**Input:**
```text
contexts   array de objetos, requerido. Cada objeto:
           { company_id: text, project_code: text, schema: text }
```

**Logica:**
1. Para cada elemento de `contexts`, llamar `erp_project_context_resolve`
   con esos 3 campos para confirmar que la empresa/schema existen.
2. Si un contexto falla al resolverse (empresa o schema invalido): **se
   omite con warning, no falla la llamada completa**. Se acumula en
   `data.warnings` y se sigue con los demas.
3. Para cada contexto valido, llamar `erp_banks_account_list` con ese
   schema/empresa.
4. Agregar resultados en memoria (Python, sin join SQL entre schemas).

**Output:**
```json
{
  "ok": true,
  "data": {
    "by_empresa": [
      {
        "company_id": "EMP_DURALON",
        "total_by_currency": { "MXN": 125000.50 },
        "accounts": [ { "folio": "BAC-00001", "account_name": "...", "current_balance": 50000.0, "currency": "MXN", "account_type": "bank" } ]
      }
    ],
    "total_by_currency": { "MXN": 340000.75 },
    "total_by_account_type": { "bank": 300000.0, "cash": 40000.75 },
    "warnings": [ "schema invalido para EMP_X: no existe companies/EMP_X/" ]
  }
}
```

Estructura anidada: `by_empresa` (lista, una entrada por empresa) +
totales globales (`total_by_currency`, `total_by_account_type`) calculados
sobre todas las empresas que si resolvieron. `warnings` siempre presente
(lista vacia si no hubo fallos). Skill de solo lectura, nunca escribe.

---

## 6. Reglas de autorizacion (motor completo)

### 6.1 Evaluacion al crear un movimiento (en `erp_banks_movement_record` / `banks_record_movement()`, ver 5.0)

Al recibir un movimiento nuevo, dentro de la misma transaccion que toma
`select ... for update` sobre la cuenta (seccion 5.0), antes de tocar
`current_balance`:

0. Verificar idempotencia: si ya existe un movimiento con la misma
   combinacion `source_module`+`source_type`+`source_id` (seccion 2.6),
   regresar ese movimiento existente, no insertar otro.
1. Buscar en `banks_authorization_rules` (de esa empresa, `active=true`)
   las reglas donde: (`applies_to_account_id` es null O coincide con la
   cuenta) Y (`movement_type_filter` es null O coincide) Y
   (`source_type_filter` es null O coincide) Y (`source_module_filter` es
   null O coincide) Y `min_amount <= amount`.
2. Si hay mas de una regla que matchea, gana la de menor `priority`
   (numero mas chico = mayor precedencia). El `select` que trae las reglas
   candidatas debe ordenar explicitamente por `priority asc, created_at
   asc, id asc` y tomar la primera fila (`limit 1`) — sin este `order by`
   explicito, dos reglas con el mismo `priority` dan un resultado
   no determinista (el orden de retorno de Postgres sin `order by` no esta
   garantizado), lo que significaria que el mismo movimiento podria quedar
   `pendiente` una vez y `no_requerida` otra vez en llamadas distintas,
   dependiendo del plan de ejecucion.
3. Si ninguna regla matchea -> `authorization_status = 'no_requerida'`,
   se aplica el movimiento de inmediato (comportamiento actual, sin
   cambios). `balance_before`/`balance_after` se llenan de una vez con el
   saldo recien leido bajo el lock.
4. Si una regla matchea -> `authorization_status = 'pendiente'`,
   `balance_before`/`balance_after` quedan `null` (no hay saldo real
   todavia), **no se toca `current_balance`**. Se inserta la fila en
   `banks_authorizations` con `status='pendiente'`, `rule_id` apuntando a
   la regla que gano, y de inmediato se actualiza
   `banks_movements.authorization_id` con el `id` de esa fila recien
   creada — el movimiento y su autorizacion quedan enlazados en ambos
   sentidos desde el primer instante.

### 6.2 Regla default obligatoria por empresa (reconciliacion)

Cuando se activa banks para una empresa, se inserta automaticamente (paso 5
de la seccion 3):

```text
rule_name: 'Forzar autorizacion en ajustes de reconciliacion'
source_module_filter: 'reconciliation'
movement_type_filter: null
source_type_filter: null
applies_to_account_id: null
min_amount: 0
authorizer_user_id: null   (se resuelve via default_authorizer)
priority: 1
```

Esto garantiza que **cualquier** movimiento que
`vertical_erp_reconciliation` intente crear (vía su propio skill
`erp_recon_missing_movement_create`, que llama a `erp_banks_movement_record`
con `source_module='reconciliation'`) quede `pendiente` sin importar el
monto, porque `priority=1` le gana a cualquier otra regla mas generica.

### 6.3 Resolucion del autorizador

No existe tabla de roles. `authorizer_user_id` en una regla puede ser
`null`, en cuyo caso se resuelve via `default_authorizer`, campo nuevo en
`company.config.json` de cada empresa (seccion 8). El gate valida que
`decided_by` (que llega en el input de `erp_banks_authorization_decide`)
coincida exactamente con ese valor. Si la regla si trae un
`authorizer_user_id` explicito, ese gana sobre `default_authorizer`.

### 6.4 Transferencias incompletas

Una transferencia genera 2 filas (`salida` en origen, `entrada` en
destino) ligadas por `transfer_group_id`. Cada fila evalua autorizacion de
forma independiente, asi que puede quedar una `autorizado` y la otra
`pendiente` o `rechazado` — un estado intermedio inconsistente para el
negocio aunque cada fila individualmente sea correcta.

Reglas de contrato:

- `source_type='transferencia'` **exige** `transfer_group_id` no nulo. Un
  movimiento con `source_type='transferencia'` y `transfer_group_id` null
  debe ser rechazado por `erp_banks_movement_record` antes de insertar.
- Una transferencia se considera **cerrada** unicamente cuando ambas filas
  de su `transfer_group_id` tienen `authorization_status='autorizado'`, o
  ambas tienen `authorization_status='rechazado'`/fueron revertidas. Un
  estado mixto (una autorizada, otra pendiente o rechazada) es una
  transferencia **incompleta** y debe quedar visible como tal.
- Se deja como pendiente para `erp_banks_consolidated_dashboard` o un
  futuro skill de solo lectura (`erp_banks_transfer_status`) agregar un
  reporte de transferencias incompletas: agrupar `banks_movements` por
  `transfer_group_id` y senalar los grupos donde las 2 filas no comparten
  el mismo `authorization_status` final. No se codifica en este cierre,
  pero el contrato de datos (`transfer_group_id` obligatorio cuando
  `source_type='transferencia'`) si debe quedar validado desde el dia uno.

---

## 7. Inmutabilidad y reversa

- Una vez insertada, una fila de `banks_movements` **nunca se edita ni se
  borra**, con dos excepciones explicitas:
  - La transicion de `authorization_status` (`pendiente` -> `autorizado` o
    `rechazado`), hecha exclusivamente por `erp_banks_authorization_decide`.
  - El llenado de `reconciliation_status`/`reconciled_at`, hecho
    exclusivamente por `erp_banks_mark_reconciled`.
- Para corregir un movimiento ya `autorizado`: se inserta un movimiento
  nuevo con `reversal_of_movement_id` apuntando al original y
  `movement_type`/efecto invertido (si el original fue `entrada`, la
  reversa es `salida` por el mismo monto, y viceversa). El original
  permanece intacto para siempre.
- Transferencias entre cuentas: siempre 2 filas (`salida` en cuenta origen,
  `entrada` en cuenta destino), ligadas por un `transfer_group_id` comun.
  Cada una evalua autorizacion de forma independiente — puede requerir
  aprobar solo una de las dos.

### 7.1 Enforcement real de inmutabilidad (no solo convencion)

Lo de arriba es una regla de negocio que hoy solo respetan las funciones
`banks_record_movement()`/`banks_decide_authorization()`/
`erp_banks_mark_reconciled`. Nada impide hoy un `UPDATE` directo desde el
SQL Editor de Supabase o un futuro skill que no siga el patron. Agregar un
trigger que la haga cumplir a nivel de base de datos:

```sql
create or replace function {schema}.banks_movements_protect()
returns trigger language plpgsql as $$
declare
  v_old jsonb;
  v_new jsonb;
begin
  -- Lista de permitidos (las unicas columnas que pueden transicionar
  -- despues del insert original). Cualquier otra diferencia entre OLD y
  -- NEW se rechaza. Enfoque de lista permitida, no lista bloqueada: evita
  -- el error de bloquear por accidente una columna que si debe poder
  -- cambiar (balance_before/balance_after transicionan de null a su valor
  -- real exactamente cuando se aprueba la autorizacion).
  v_old := to_jsonb(old) - 'authorization_status' - 'authorization_id'
                          - 'balance_before' - 'balance_after'
                          - 'reconciliation_status' - 'reconciled_at'
                          - 'updated_at';
  v_new := to_jsonb(new) - 'authorization_status' - 'authorization_id'
                          - 'balance_before' - 'balance_after'
                          - 'reconciliation_status' - 'reconciled_at'
                          - 'updated_at';
  if v_old is distinct from v_new then
    raise exception 'banks_movements es inmutable salvo authorization_status/authorization_id/balance_before/balance_after/reconciliation_status/reconciled_at';
  end if;
  return new;
end;
$$;

create trigger banks_movements_protect_trg
before update on {schema}.banks_movements
for each row execute function {schema}.banks_movements_protect();
```

El trigger corre para cualquier `UPDATE`, venga de donde venga (incluidas
las funciones `security definer`); por eso la lista de columnas permitidas
debe incluir exactamente las que las funciones legitimas si necesitan
tocar — `balance_before`/`balance_after` al aprobar, `authorization_id` al
crear la autorizacion pendiente, `reconciliation_status`/`reconciled_at`
al conciliar. Cualquier otro intento de `UPDATE` (manual, de otro skill, de
un bug futuro) queda bloqueado por el trigger sin excepcion.

---

## 8. Cierre de `company.config.json` / `erp_project_context_resolve`

### 8.1 Migracion `EMP_DURALON`

Renombrar `companies/EMP_DURALON/company.json` ->
`companies/EMP_DURALON/company.config.json`, sin borrar datos existentes,
agregando los campos faltantes del contrato (`COMPANY_PATTERN.md`) mas
`default_authorizer`:

```json
{
  "company_id": "EMP_DURALON",
  "company_name": "COMERCIALIZADORA DURALON DE CHIAPAS SA DE CV",
  "short_name": "Duralon",
  "company_type": "internal_client",
  "industry": "construction_materials_distribution",
  "status": "active",
  "relationship": "internal_client",
  "primary_contact": {
    "name": "Luis Castillejos",
    "email": "alfredo82@hotmail.com"
  },
  "objective": "Mejorar procesos internos con AI, iniciando con captura y analisis de gastos.",
  "legacy_ids": { "client_id": "UC-101" },
  "dashboards": [],
  "skill_stack": [],
  "channels": [],
  "storage": { "supabase_schema": "", "buckets": [] },
  "default_authorizer": "<uuid de Ach, pendiente de definir>",
  "created_at": "2026-05-27T16:39:25.087322Z",
  "updated_at": "<fecha de la migracion>"
}
```

### 8.2 Validacion real en `erp_project_context_resolve`

Agregar, antes de devolver `ok: true`:

1. Construir `repo_root / "companies" / company_id`. Si la carpeta no
   existe -> agregar a `issues`: `"company_id invalido: no existe
   companies/<id>/"`.
2. Si existe la carpeta pero no `company.config.json` dentro -> agregar a
   `issues`: `"company_id sin company.config.json"`.
3. Si existe el archivo pero no es JSON valido, o su `company_id` no
   coincide con el solicitado -> agregar a `issues`: `"company.config.json
   invalido o company_id no coincide"`.
4. Exponer `default_authorizer` en la respuesta `data`, leido de ese mismo
   archivo (mismo patron que ya usa para `schema`/`sales_schema`/etc).

Estos issues se acumulan en la lista que el resolver ya retorna; el shape
de la respuesta (`{ok, data, error}`) no cambia.

### 8.3 Dato pendiente real

El valor de `default_authorizer` para EMP_DURALON (el UUID de Ach) sigue sin
definirse — es lo unico que falta para que el gate de la seccion 5.1/6.3
funcione con un dato real en vez de un placeholder.

---

## 9. Casos de prueba minimos del gate (checklist verificable)

- [ ] **a.** Movimiento sin regla aplicable -> `authorization_status =
  'no_requerida'`, `current_balance` se actualiza en la misma llamada a
  `erp_banks_movement_record`.
- [ ] **b.** Movimiento con regla aplicable -> `authorization_status =
  'pendiente'`, `current_balance` NO cambia, se crea fila en
  `banks_authorizations` con `status='pendiente'`.
- [ ] **c.** `erp_banks_authorization_decide` con `decided_by` correcto y
  `decision='aprobado'` -> recalcula `balance_after` contra el
  `current_balance` vigente en el momento de la decision (no el que existia
  cuando se creo el movimiento), actualiza la cuenta.
- [ ] **d.** `erp_banks_authorization_decide` con `decided_by` correcto y
  `decision='rechazado'` -> no toca `current_balance`, cierra el ciclo
  (`authorization_status='rechazado'`).
- [ ] **e.** `erp_banks_authorization_decide` con `decided_by` que NO
  coincide con `default_authorizer` -> error, no se mueve nada (ni saldo ni
  estado del movimiento).
- [ ] **f.** Reversa de un movimiento ya `autorizado` -> se inserta uno
  nuevo con `reversal_of_movement_id`, el original permanece sin cambios.
- [ ] **g.** Movimiento con `source_module='reconciliation'` -> siempre
  `pendiente`, sin importar el monto, por la regla default de `priority=1`.
- [ ] **h.** Dos llamadas a `erp_banks_movement_record` con el mismo
  `source_module`+`source_type`+`source_id` -> la segunda regresa el
  movimiento existente (`idempotent: true`), no inserta duplicado, no
  duplica el efecto en `current_balance`.
- [ ] **i.** Dos movimientos concurrentes sobre la misma cuenta (simulado
  con dos llamadas paralelas) -> el segundo espera el lock (`for update`)
  del primero; ningun escenario debe terminar con `current_balance`
  incorrecto por carrera de lectura-escritura.
- [ ] **j.** Movimiento con `source_type='transferencia'` y
  `transfer_group_id` null -> rechazado antes de insertar.

---

## 10. Ganchos de conexion con otros modulos

### 10.1 Payables (compras / `vertical_erp_compras`)

Al pagar una compra: llamar `erp_banks_movement_record` con
`source_type='pago'`, `source_module='compras'`, `source_id=<id de la
compra>`, `source_folio=<folio de la compra>`. Esperar a que quede
`autorizado` (puede ser inmediato o requerir aprobacion). Solo entonces,
compras actualiza `paid_amount`/`balance_amount`/`payment_status` en su
propia tabla. Banks no sabe nada de la estructura de compras.

### 10.2 Billing (cobros a clientes)

`erp_billing_payment_create`/`erp_billing_payment_apply` dejan de tocar
`billing_money_accounts.current_balance` directo y llaman a
`erp_banks_movement_record` con `source_type='pago'`,
`source_module='billing'`, `source_id=<payment_id de billing>`.
`billing_money_accounts` queda como decision del Cerebro (espejo de lectura
o se elimina a favor de `banks_accounts`).

### 10.3 Conciliacion bancaria (`vertical_erp_reconciliation`)

Vertical propio y separado, vendible por si solo. Lee `banks_movements`
libremente (select). Escribe exclusivamente via `erp_banks_mark_reconciled`
(seccion 5.2). Cuando detecta un movimiento en el extracto sin contraparte
en `banks_movements`, lo crea via su propio skill
`erp_recon_missing_movement_create`, que internamente llama a
`erp_banks_movement_record` con `source_module='reconciliation'` — ese
movimiento siempre nace `pendiente` por la regla de la seccion 6.2. Su
propia tabla `bank_statement_lines` vive en el schema de
`vertical_erp_reconciliation`, no en el de banks. Match sugerido entre
extracto y poliza: `clave_rastreo` + `value_date` + `amount`.

---

## 11. Patron de archivos por skill nuevo (correccion)

**No se va a usar `SKILL.md` por skill.** Se reviso el repo completo: de 392
skills internos, 94 tienen `SKILL.md` (verticales viejos como Instagram),
pero **ningun skill de los verticales ERP actuales** (`vertical_erp_billing`,
`vertical_erp_inventory`, `vertical_erp_ventas`, `vertical_erp_banks`,
`vertical_erp`) usa ese archivo. El patron real y consistente de la familia
ERP, confirmado en cada skill existente de banks, es:

```text
<skill_name>/
  manifest.json   -> name, vertical, version, description, entrypoint
  skill.py        -> wrapper delgado que carga service.py y llama .ejecutar(context)
  service.py       -> logica real, clase Erp...Service con metodo ejecutar(context)
```

Los 3 skills nuevos (`erp_banks_authorization_decide`,
`erp_banks_mark_reconciled`, `erp_banks_consolidated_dashboard`) deben seguir
exactamente este patron de 3 archivos, mas su entrada correspondiente en
`factory/skills/registry.json` (mismo formato que las entradas ya existentes
de `vertical_erp_banks`).

---

## 12. Checklist final de codificacion

1. Migracion SQL (seccion 3): ALTER/CREATE de `banks_movements`,
   `banks_authorization_rules`, `banks_authorizations`, indices, INSERT de
   regla default.
2. Logica de gate en `erp_banks_movement_record` (seccion 6.1).
3. Skill nuevo `erp_banks_authorization_decide` (seccion 5.1).
4. Skill nuevo `erp_banks_mark_reconciled` (seccion 5.2).
5. Skill nuevo `erp_banks_consolidated_dashboard` (seccion 5.3).
6. Renombrar/migrar `company.json` -> `company.config.json` con
   `default_authorizer` (seccion 8.1) — falta el UUID real de Ach.
7. Validacion real de `empresa_id` + exposicion de `default_authorizer` en
   `erp_project_context_resolve` (seccion 8.2).
8. Conectar payables y billing para que dejen de tocar saldo directo
   (seccion 10.1, 10.2).
9. Registrar los 3 skills nuevos en `factory/skills/registry.json` (seccion
   11).
10. Validar contra los 10 casos de prueba de la seccion 9 antes de dar por
    cerrado (incluye idempotencia, concurrencia y transferencias
    incompletas).
11. Implementar `banks_record_movement()` y `banks_decide_authorization()`
    como funciones `plpgsql` con `select ... for update` (seccion 5.0),
    invocadas via RPC — no como `rest_select`/`rest_update` sueltos desde
    Python.
12. Confirmar `balance_after` nullable y constraints CHECK nombradas
    (`banks_movements_authorization_status_chk`,
    `banks_movements_reconciliation_status_chk`) en la migracion real.
13. Confirmar indice unico de idempotencia (seccion 2.6, con `movement_type`
    incluido en la llave) creado antes de exponer el modulo a cualquier
    llamada real.
14. Confirmar manejo de `exception when unique_violation` dentro de
    `banks_record_movement()` (seccion 2.6) para que una carrera de
    llamadas concurrentes con el mismo `source_id` regrese el movimiento
    existente en vez de propagar el error.
15. Confirmar que `banks_decide_authorization()` lockea primero
    `banks_movements` (`for update`) y solo despues `banks_accounts`, en
    ese orden, en ambas funciones (seccion 5.1, 5.0).
16. Confirmar `order by priority asc, created_at asc, id asc` en la query
    de evaluacion de reglas (seccion 6.1 paso 2), para tie-break
    determinista.
17. Crear el trigger `banks_movements_protect_trg` (seccion 7.1) antes de
    considerar el modulo listo para produccion.

Diseno aprobado v1->v4, auditado funcionalmente y ahora auditado a nivel de
implementacion (concurrencia, idempotencia, constraints, integridad
referencial). No se reabre nada de negocio; este documento es la unica
referencia para codificar.
