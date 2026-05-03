"""Service for markdown_table - renders rows as a Markdown table."""

from __future__ import annotations


class MarkdownTableService:

    def ejecutar(self, context: dict) -> dict:
        rows = context.get("rows", [])
        if not isinstance(rows, list):
            return {"ok": False, "error": "rows debe ser lista"}
        if not rows:
            return {"ok": True, "data": {"markdown": ""}}
        headers = context.get("headers")
        if headers is None and all(isinstance(row, dict) for row in rows):
            headers = list(dict.fromkeys(key for row in rows for key in row.keys()))
        if headers is None:
            headers = [f"col_{idx + 1}" for idx in range(max(len(row) if isinstance(row, list) else 1 for row in rows))]
        if not isinstance(headers, list) or not all(isinstance(header, str) for header in headers):
            return {"ok": False, "error": "headers debe ser lista de textos"}
        body = [self._row_values(row, headers) for row in rows]
        table = [self._format_row(headers), self._format_row(["---"] * len(headers))]
        table.extend(self._format_row(row) for row in body)
        return {"ok": True, "data": {"markdown": "\n".join(table)}}

    def _row_values(self, row: object, headers: list[str]) -> list[str]:
        if isinstance(row, dict):
            return [str(row.get(header, "")) for header in headers]
        if isinstance(row, list):
            values = [str(value) for value in row]
            return values + [""] * (len(headers) - len(values))
        return [str(row)] + [""] * (len(headers) - 1)

    def _format_row(self, values: list[str]) -> str:
        escaped = [value.replace("|", "\\|").replace("\n", " ") for value in values]
        return "| " + " | ".join(escaped) + " |"
