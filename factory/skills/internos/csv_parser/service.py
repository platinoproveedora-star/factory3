"""Service for csv_parser - parses CSV text to rows."""

from __future__ import annotations

import csv
from io import StringIO


class CsvParserService:

    def ejecutar(self, context: dict) -> dict:
        text = context.get("text", "")
        if not isinstance(text, str):
            return {"ok": False, "error": "text debe ser texto CSV"}
        delimiter = context.get("delimiter", ",")
        if not isinstance(delimiter, str) or len(delimiter) != 1:
            return {"ok": False, "error": "delimiter debe ser un caracter"}
        has_header = bool(context.get("header", True))
        try:
            reader = csv.reader(StringIO(text), delimiter=delimiter)
            rows = list(reader)
        except csv.Error as exc:
            return {"ok": False, "error": str(exc)}
        if not rows:
            return {"ok": True, "data": {"rows": [], "count": 0}}
        if not has_header:
            return {"ok": True, "data": {"rows": rows, "count": len(rows)}}
        headers = [header.strip() for header in rows[0]]
        objects = [dict(zip(headers, row)) for row in rows[1:]]
        return {"ok": True, "data": {"headers": headers, "rows": objects, "count": len(objects)}}
