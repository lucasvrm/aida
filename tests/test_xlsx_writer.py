from pathlib import Path
import openpyxl

from app.template.bootstrap import ensure_template_ready
from app.models.payload import ConsolidatedPayload
from app.template.writer import write_filled_xlsx

def test_write_xlsx_basic(tmp_path: Path):
    ensure_template_ready()

    payload = ConsolidatedPayload()
    payload.Projeto.data["Data de Lançamento"] = "2025-12-31"
    payload.Recebíveis.rows = [
        {"C": "101", "F": "Cliente 1", "J": 100000.0, "U": 110000.0}
    ]

    out = tmp_path / "out.xlsx"
    write_filled_xlsx(payload, project_name="Projeto Teste", out_path=str(out))

    wb = openpyxl.load_workbook(out)
    ws_proj = wb["Projeto"]
    assert ws_proj["C27"].value == "2025-12-31"

    ws_rec = wb["Recebíveis"]
    assert ws_rec["C18"].value == "101"
    assert ws_rec["F18"].value == "Cliente 1"
    assert ws_rec["J18"].value == 100000.0
    assert ws_rec["U18"].value == 110000.0
