from app.core.br_formats import normalize_header

def test_normalize_header_whitespace_and_accents():
    assert normalize_header("Nome  \nEmpreendimento") == "nome empreendimento"
    assert normalize_header("Área privativa (m²)") == "area privativa (m2)"
