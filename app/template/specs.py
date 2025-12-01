from dataclasses import dataclass

@dataclass(frozen=True)
class TableSpec:
    sheet: str
    header_row: int
    data_start_row: int
    start_col: str
    columns: list[tuple[str, str]]  # (letter, name)

RECEBIVEIS = TableSpec(
    sheet="Recebíveis",
    header_row=17,
    data_start_row=18,
    start_col="B",
    columns=[
        ("B","-"),
        ("C","Nº Unidade"),
        ("D","Torre"),
        ("E","Situação"),
        ("F","Nome cliente"),
        ("G","CPF"),
        ("H","Profissão"),
        ("I","Data de venda"),
        ("J","Valor de tabela"),
        ("K","Valor de venda"),
        ("L","Recebido (período de obras)"),
        ("M","A receber (período de obras)"),
        ("N","A receber Chaves"),
        ("O","A receber Repasse / Financiamento"),
        ("P","A receber Financiamento Direto"),
        ("Q","Área total"),
        ("R","Área privativa"),
        ("S","Total dormitórios"),
        ("T","Total vagas"),
        ("U","Valor de tabela"),
        ("V","Valor de venda"),
        ("W","Valor de estoque"),
    ],
)

TIPOLOGIA = TableSpec(
    sheet="Tipologia",
    header_row=7,
    data_start_row=8,
    start_col="B",
    columns=[
        ("B","-"),
        ("C","Nº da Unidade"),
        ("D","Torre"),
        ("E","Situação"),
        ("F","Padrão"),
        ("G","Uso da unidade"),
        ("H","Tipo (residencial)"),
        ("I","Área total (m²)"),
        ("J","Área privativa (m²)"),
        ("K","Dormitórios"),
        ("L","Vagas"),
        ("M","Valor de tabela"),
        ("N","Valor de venda"),
        ("O","Valor m²"),
    ],
)

LANDBANK = TableSpec(
    sheet="Landbank",
    header_row=9,
    data_start_row=10,
    start_col="C",
    columns=[
        ("C","Bairro"),
        ("D","Cidade"),
        ("E","UF"),
        ("F","Área (m²)"),
        ("G","Valor de Mercado"),
        ("H","Data de aquisição"),
        ("I","Modelo de Aquisição"),
        ("J","Valor de Aquisição"),
        ("K","Saldo a Pagar"),
        ("L","Vencimento Final"),
        ("M","Forma de Pagamento"),
        ("N","Area Permutada"),
        ("O","Nome Empreendimento"),
        ("P","Tipo (Residencial/ Comercial/Loteamento)"),
        ("Q","Unidades"),
        ("R","VGV"),
        ("S","Previsão aprovação projeto"),
        ("T","Previsão lançamento"),
        ("U","Previsão início obras"),
    ],
)

ENDIVIDAMENTO = TableSpec(
    sheet="Endividamento",
    header_row=7,
    data_start_row=8,
    start_col="B",
    columns=[
        ("B","CNPJ tomador"),
        ("C","Razão social tomador"),
        ("D","Instituição financeira"),
        ("E","Modalidade do crédito"),
        ("F","Taxa (a.a.)"),
        ("G","Indexador"),
        ("H","Garantia"),
        ("I","Valor da PMT"),
        ("J","Parcelas restantes"),
        ("K","Valor contratado"),
        ("L","Saldo devedor atual"),
        ("M","Prazo (meses)"),
        ("N","Vencimento"),
    ],
)

VIABILIDADE = TableSpec(
    sheet="Viabilidade Financeira",
    header_row=7,
    data_start_row=8,
    start_col="A",
    columns=[
        ("A","Descritivo financeiro"),
        ("B","Valor (R$)"),
        ("C","Valor (%)"),
    ],
)

PROJETO_CELLS = {
    "Data de Lançamento": "C27",
    "Data de Início das Obras": "C28",
    "Previsão Término de Obras": "C29",
    "Habite-se (previsão)": "C30",
    "Outorga onerosa": "F30",
    "Empreendimento Faseado?": "C33",
    "Modelo aquisição terreno": "C46",
    "Status aquisição terreno": "C49",
}
