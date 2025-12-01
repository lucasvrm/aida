from __future__ import annotations

import io
import pandas as pd

from app.core.utils import normalize_whitespace
from app.extractors.base import ExtractResult
from app.extractors.mapping import map_dataframe_to_template_rows
from app.models.enums import DocType
from app.template.specs import RECEBIVEIS, TIPOLOGIA, LANDBANK, ENDIVIDAMENTO, VIABILIDADE, TableSpec

def _read_csv(content: bytes) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(content), dtype=str, encoding_errors="ignore")

def _read_xlsx(content: bytes) -> pd.DataFrame:
    return pd.read_excel(io.BytesIO(content), dtype=str)

def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [normalize_whitespace(str(c)) for c in df.columns]
    return df

def extract_tabular(doc_type: DocType, content: bytes, ext: str) -> ExtractResult:
    warnings: list[str] = []
    if ext == ".csv":
        df = _read_csv(content)
    else:
        df = _read_xlsx(content)

    df = _normalize_df(df)

    spec_map: dict[DocType, TableSpec] = {
        DocType.RECEBIVEIS: RECEBIVEIS,
        DocType.TIPOLOGIA: TIPOLOGIA,
        DocType.LANDBANK: LANDBANK,
        DocType.ENDIVIDAMENTO: ENDIVIDAMENTO,
        DocType.TABELA_VENDAS: RECEBIVEIS,
        DocType.FATURAMENTO: VIABILIDADE,
    }

    if doc_type in spec_map:
        spec = spec_map[doc_type]
        rows, map_meta = map_dataframe_to_template_rows(spec, df)
        warnings.extend(map_meta.get("warnings", []))
        return ExtractResult(
            payload={"table": spec.sheet, "rows": rows, "mapping": map_meta.get("mapping")},
            warnings=warnings,
        )

    sample = df.head(50).to_dict(orient="records")
    return ExtractResult(payload={"raw_rows": sample, "columns": list(df.columns)}, warnings=["DocType sem tabela alvo; retornando raw sample."])
