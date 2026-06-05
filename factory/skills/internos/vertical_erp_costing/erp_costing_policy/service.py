from __future__ import annotations


class ErpCostingPolicyService:
    def ejecutar(self, context: dict) -> dict:
        return {
            "ok": True,
            "data": {
                "policy": "lot_last_weighted_average",
                "currency": context.get("currency") or "MXN",
                "costs": {
                    "lot_unit_cost": "Costo unitario real de la compra o entrada del lote. No se modifica desde ventas.",
                    "last_purchase_cost": "Ultimo costo unitario comprado por producto. Se deriva de la ultima compra.",
                    "weighted_avg_cost": "Costo promedio ponderado del inventario existente por producto y lote.",
                },
                "source_of_truth": "erp_kardex",
                "tax_rule": "Los costos de inventario son netos de IVA; IVA y total comercial viven separados en metadata.",
            },
        }
