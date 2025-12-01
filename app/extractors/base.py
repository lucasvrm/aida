from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass
class ExtractResult:
    payload: dict[str, Any]
    warnings: list[str]
