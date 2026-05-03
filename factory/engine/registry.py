"""Generic JSON registry access.

The registry stores metadata only. It does not know how a skill works.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class Registry:
    """Small JSON-backed registry helper."""

    def __init__(self, path: Path):
        self.path = Path(path)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}

        raw = self._read_text().strip()
        if not raw:
            return {}

        return json.loads(raw)

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def get(self, name: str) -> dict[str, Any] | None:
        return self.load().get(name)

    def set(self, name: str, metadata: dict[str, Any]) -> None:
        data = self.load()
        data[name] = metadata
        self.save(data)

    def remove(self, name: str) -> bool:
        data = self.load()
        if name not in data:
            return False

        del data[name]
        self.save(data)
        return True

    def list(self) -> dict[str, Any]:
        return self.load()

    def _read_text(self) -> str:
        for encoding in ("utf-8", "utf-8-sig", "utf-16"):
            try:
                return self.path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue

        return self.path.read_text()
