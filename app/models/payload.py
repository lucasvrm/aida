from pydantic import BaseModel, Field
from typing import Any

class SectionKV(BaseModel):
    data: dict[str, Any] = Field(default_factory=dict)

class SectionTable(BaseModel):
    rows: list[dict[str, Any]] = Field(default_factory=list)

class ConsolidatedPayload(BaseModel):
    Geral: SectionKV = Field(default_factory=SectionKV)
    Projeto: SectionKV = Field(default_factory=SectionKV)
    Recebíveis: SectionTable = Field(default_factory=SectionTable)
    Tipologia: SectionTable = Field(default_factory=SectionTable)
    Landbank: SectionTable = Field(default_factory=SectionTable)
    Endividamento: SectionTable = Field(default_factory=SectionTable)
    Viabilidade_Financeira: SectionTable = Field(default_factory=SectionTable)

    def to_public_dict(self) -> dict[str, Any]:
        d = self.model_dump()
        d["Viabilidade Financeira"] = d.pop("Viabilidade_Financeira")
        return d
