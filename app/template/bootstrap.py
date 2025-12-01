from __future__ import annotations

from pathlib import Path

from app.core.config import settings
from app.template.kv_spec import ensure_kv_spec

def _looks_like_xlsx_binary(p: Path) -> bool:
    try:
        with p.open("rb") as f:
            head = f.read(2)
        return head == b"PK"
    except Exception:
        return False

def ensure_template_ready() -> None:
    p = Path(settings.TEMPLATE_PATH)
    if not p.exists():
        raise RuntimeError(f"Template ausente: {p}")

    if not _looks_like_xlsx_binary(p):
        raise RuntimeError(
            f"Template inválido (não parece XLSX/ZIP). Troque resources/template.xlsx pelo arquivo KOA real. path={p}"
        )

    ensure_kv_spec()
