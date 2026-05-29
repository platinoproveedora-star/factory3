from __future__ import annotations


class DashboardDataSourceMapperService:
    def ejecutar(self, context: dict) -> dict:
        schema = context.get("schema") or context.get("supabase_schema") or ""
        tables = context.get("tables") or []
        if schema == "uc101_proy001" and not tables:
            tables = self._duralon_tables(schema)
        data_sources = []
        for table in tables:
            if isinstance(table, str):
                data_sources.append({"id": table, "kind": "supabase_table", "schema": schema, "name": table, "fields": []})
            elif isinstance(table, dict):
                item = {
                    "id": table.get("id") or table.get("name"),
                    "kind": table.get("kind", "supabase_table"),
                    "schema": table.get("schema", schema),
                    "name": table.get("name"),
                    "fields": table.get("fields", []),
                }
                data_sources.append(item)
        return {"ok": True, "data": {"data_sources": data_sources, "relationships": context.get("relationships", [])}}

    def _duralon_tables(self, schema: str) -> list[dict]:
        return [
            {
                "id": "gastos",
                "kind": "supabase_table",
                "schema": schema,
                "name": "gastos",
                "fields": ["id", "folio", "usuario_id", "categoria_id", "monto", "descripcion", "fecha", "metodo_captura", "estado", "created_at"],
            },
            {
                "id": "categorias_gasto",
                "kind": "supabase_table",
                "schema": schema,
                "name": "categorias_gasto",
                "fields": ["id", "folio", "nombre", "activo"],
            },
            {
                "id": "usuarios",
                "kind": "supabase_table",
                "schema": schema,
                "name": "usuarios",
                "fields": ["id", "folio", "nombre", "telegram_chat_id", "rol", "activo"],
            },
        ]

