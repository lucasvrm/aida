from __future__ import annotations
from typing import Any
from app.models.payload import ConsolidatedPayload

def consolidate(extracted_docs: list[dict[str, Any]]) -> ConsolidatedPayload:
    payload = ConsolidatedPayload()

    for doc in extracted_docs:
        if doc.get("table") and doc.get("rows") is not None:
            table = doc["table"]
            rows = doc["rows"]
            if table == "Recebíveis":
                payload.Recebíveis.rows.extend(rows)
            elif table == "Tipologia":
                payload.Tipologia.rows.extend(rows)
            elif table == "Landbank":
                payload.Landbank.rows.extend(rows)
            elif table == "Endividamento":
                payload.Endividamento.rows.extend(rows)
            elif table == "Viabilidade Financeira":
                payload.Viabilidade_Financeira.rows.extend(rows)
            continue

        kv = doc.get("kv")
        if isinstance(kv, dict):
            g = kv.get("Geral") or {}
            p = kv.get("Projeto") or {}
            if isinstance(g, dict):
                payload.Geral.data.update(g)
            if isinstance(p, dict):
                payload.Projeto.data.update(p)

    for row in payload.Landbank.rows:
        if "O" in row and isinstance(row["O"], str):
            row["O"] = " ".join(str(row["O"]).split())

    return payload
