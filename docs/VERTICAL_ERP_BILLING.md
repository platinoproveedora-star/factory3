# Vertical ERP Billing

## Objetivo

`vertical_erp_billing` gestiona cobranza, pagos, cuentas por cobrar ligeras, cuentas de dinero y cortes de caja. Es generica y vendible: no pertenece a una empresa, schema o dashboard especifico.

## Modulos MVP

| Modulo | Funcion |
|---|---|
| Cobranza | Registrar pagos y aplicar pagos a documentos de venta. |
| Folios de cobranza | Emitir folio imprimible para cobranza manual, efectivo o transferencia. |
| Cuentas de dinero | Bancos, cajas de efectivo, cajas de cobrador, terminales y otros destinos de dinero. |
| Corte de caja | Abrir/cerrar cortes de efectivo y depositar lo contado en una cuenta de dinero. |
| Dashboard billing | KPIs y bandejas para una UI operativa. |

## Tablas

| Tabla | Uso |
|---|---|
| `billing_money_accounts` | Cuentas de banco, efectivo, caja, cobrador o terminal. |
| `billing_collection_folios` | Folios de cobranza ligados a documentos comerciales. |
| `billing_payments` | Pagos capturados con metodo, importe, cuentas, banco y comprobante. |
| `billing_payment_applications` | Aplicaciones de pago contra documentos de ventas. |
| `billing_cash_cuts` | Cortes de caja/cobrador. |
| `billing_events` | Auditoria ligera de eventos sensibles. |

## Skills iniciales

| Skill | Funcion |
|---|---|
| `vertical_erp_billing/erp_billing_schema_plan` | Genera SQL de tablas billing. |
| `vertical_erp_billing/erp_billing_money_account_create` | Crea/actualiza cuenta de dinero. |
| `vertical_erp_billing/erp_billing_money_account_list` | Lista cuentas de dinero. |
| `vertical_erp_billing/erp_billing_collection_folio_create` | Crea folio de cobranza desde documento comercial. |
| `vertical_erp_billing/erp_billing_collection_folio_pdf` | Genera HTML imprimible del folio. |
| `vertical_erp_billing/erp_billing_payment_create` | Registra pago manual/bancario/efectivo. |
| `vertical_erp_billing/erp_billing_payment_apply` | Aplica pago y actualiza saldos de ventas. |
| `vertical_erp_billing/erp_billing_cash_cut_open` | Abre corte de efectivo. |
| `vertical_erp_billing/erp_billing_cash_cut_close` | Cierra corte y deposita a cuenta de dinero. |
| `vertical_erp_billing/erp_billing_dashboard_data` | Datos para dashboard operativo. |

## Flujo operativo

1. Ventas emite remision/factura.
2. Billing crea `billing_collection_folios` y PDF de cobranza.
3. Cobrador recibe efectivo o transferencia.
4. Usuario registra pago con `erp_billing_payment_create`.
5. Si el pago corresponde a un documento, se aplica con `erp_billing_payment_apply`.
6. Para efectivo, el corte se abre/cierra con `cash_cut_open/close`.
7. Dashboard consume `erp_billing_dashboard_data`.

## Archivos y OCR

La fase 1 deja campos para comprobantes:

- `receipt_file_url`
- `receipt_file_path`
- `receipt_file_bucket`
- `ocr_status`
- `validation_status`

La fase 2 debe conectar `vertical_finance_document_intake` para leer PDF/imagen de banco o folio firmado.

## Reglas

- Ningun skill asume empresa, schema o proyecto por default.
- Toda escritura usa `dry_run=True` por defecto.
- Billing puede leer/escribir su schema propio y, para aplicar pagos, requiere `sales_schema`.
- El dashboard no debe tocar Supabase directo; consume data skills.

## Manual de usuario pendiente

Cuando el dashboard este listo, documentar manuales por modulo:

- Registro de pago.
- Aplicacion de pago a remision/factura.
- Impresion y foto de folio de cobranza.
- Corte de caja.
- Alta de cuentas de dinero.
- Revision de saldos y bandejas del dashboard.
