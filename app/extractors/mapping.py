from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

from app.core.br_formats import normalize_header, parse_brl_money, parse_date_br, parse_int, parse_float
from app.core.utils import normalize_whitespace
from app.extractors.gemini import GeminiClient
from app.template.specs import TableSpec

class TransformKind(str):
    NONE = "none"
    PARSE_BRL_MONEY = "parse_brl_money"
    PARSE_DATE = "parse_date_ddmmyyyy"
    PARSE_INT = "parse_int"
    PARSE_FLOAT = "parse_float"

class ColumnMapItem(BaseModel):
    source: str
    target_col: str | None = None
    transform: str = Field(default=TransformKind.NONE)

class ColumnMappingResponse(BaseModel):
    mapping: list[ColumnMapItem]
    notes: str | None = None

def _score(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

def _heuristic_match(columns: list[str], spec: TableSpec) -> dict[str, str | None]:
    target = [(col_letter, normalize_header(name)) for col_letter, name in spec.columns]
    out: dict[str, str | None] = {}
    for src in columns:
        sn = normalize_header(src)
        best = (None, 0.0)
        for (t_letter, tn) in target:
            sc = _score(sn, tn)
            if sc > best[1]:
                best = (t_letter, sc)
        letter, sc = best
        out[src] = letter if (letter and sc >= 0.86) else None
    return out

def _apply_transform(value: Any, transform: str) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        value = normalize_whitespace(value)
        if value == "":
            return None

    if transform == TransformKind.PARSE_BRL_MONEY:
        return parse_brl_money(value)
    if transform == TransformKind.PARSE_DATE:
        d = parse_date_br(value)
        return d.isoformat() if d else None
    if transform == TransformKind.PARSE_INT:
        return parse_int(value)
    if transform == TransformKind.PARSE_FLOAT:
        return parse_float(value)
    return value

def _infer_transform(target_name: str) -> str:
    tn = normalize_header(target_name)
    if "data" in tn or "vencimento" in tn or "previsao" in tn:
        return TransformKind.PARSE_DATE
    if "valor" in tn or "vgv" in tn or "saldo" in tn or "pmt" in tn or "(r$)" in tn:
        return TransformKind.PARSE_BRL_MONEY
    if "parcelas" in tn or "prazo" in tn or "unidades" in tn or "dormitorios" in tn or "vagas" in tn:
        return TransformKind.PARSE_INT
    if "area" in tn or "m2" in tn or "taxa" in tn or "%" in tn:
        return TransformKind.PARSE_FLOAT
    return TransformKind.NONE

def map_dataframe_to_template_rows(spec: TableSpec, df: pd.DataFrame) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    columns = list(df.columns)
    mapping = _heuristic_match(columns, spec)
    warnings: list[str] = []

    hit_rate = sum(1 for v in mapping.values() if v) / max(1, len(columns))
    if hit_rate < 0.50:
        client = GeminiClient()
        sample_rows = df.head(5).fillna("").to_dict(orient="records")
        prompt = _build_mapping_prompt(spec, columns, sample_rows)
        resp = client.generate_structured(prompt, ColumnMappingResponse)
        llm_map: dict[str, str | None] = {}
        llm_transform: dict[str, str] = {}
        for item in resp["mapping"]:
            llm_map[item["source"]] = item.get("target_col")
            llm_transform[item["source"]] = item.get("transform") or TransformKind.NONE
        mapping = llm_map
        warnings.append("Mapping via LLM (colunas não bateram 1:1).")

        rows = []
        for _, row in df.iterrows():
            out: dict[str, Any] = {}
            for src_col, target_letter in mapping.items():
                if not target_letter:
                    continue
                v = row.get(src_col)
                out[target_letter] = _apply_transform(v, llm_transform.get(src_col, TransformKind.NONE))
            if any(v is not None and v != "" for v in out.values()):
                rows.append(out)
        return rows, {"mapping": resp, "warnings": warnings}

    name_by_letter = {letter: name for letter, name in spec.columns}
    rows = []
    for _, row in df.iterrows():
        out: dict[str, Any] = {}
        for src_col, target_letter in mapping.items():
            if not target_letter:
                continue
            transform = _infer_transform(name_by_letter.get(target_letter, ""))
            out[target_letter] = _apply_transform(row.get(src_col), transform)
        if any(v is not None and v != "" for v in out.values()):
            rows.append(out)

    return rows, {"mapping": mapping, "warnings": warnings}

def _build_mapping_prompt(spec: TableSpec, columns: list[str], sample_rows: list[dict[str, Any]]) -> str:
    template_cols = [{"col": c, "name": n} for c, n in spec.columns]
    return f"""
Você é um parser de planilhas pt-BR. Mapeie colunas de origem para colunas do template.

REGRAS:
- O ID do destino é SEMPRE a letra da coluna do template (ex.: "J", "U").
- Se não tiver correspondência, use null em target_col.
- Sugira transformações: "parse_brl_money", "parse_date_ddmmyyyy", "parse_int", "parse_float", ou "none".
- Não invente colunas inexistentes.

TEMPLATE (colunas):
{template_cols}

ORIGEM (colunas detectadas):
{columns}

AMOSTRA (até 5 linhas):
{sample_rows}
""".strip()
