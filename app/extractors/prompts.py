from app.models.enums import DocType

def get_prompt_for_doc_type(doc_type: DocType, text: str) -> str:
    """
    Gera o prompt especializado para o Gemini com base no tipo de documento.
    Refinado com base em exemplos reais de:
    - Recebíveis (MEA, T3, Broker)
    - Endividamento (ARIE, Goldsztein)
    - Viabilidade (Planilhas e PDFs)
    - Cronogramas (Curva de Obra Físico-Financeira)
    - Jurídico (Contratos Sociais/Estatutos)
    """
    
    base_head = (
        "Você é um especialista em extração de dados imobiliários e financeiros (pt-BR). "
        "Analise o TEXTO extraído do documento e gere um JSON estruturado seguindo rigorosamente as chaves solicitadas."
    )

    # =========================================================================
    # 1. RECEBÍVEIS / TABELA DE VENDAS
    # =========================================================================
    if doc_type in (DocType.RECEBIVEIS, DocType.TABELA_VENDAS):
        return f"""{base_head}

CONTEXTO: 
Relatório de Contas a Receber, Tabela de Vendas ou Estoque.
Pode ser uma lista consolidada (ex: MEA - Resumo) ou fichas financeiras por cliente (ex: T3 - R-01).

OBJETIVO:
Preencher a tabela 'Recebíveis' com uma linha por Unidade/Contrato.

MAPEAMENTO DE COLUNAS (Keys Obrigatórias):
- 'C': Nº Unidade (Procure: "Unidade", "U-xxxx", "Apto", "Loja", "1204B")
- 'D': Torre/Bloco (Se houver)
- 'E': Situação (Ex: "Vendido", "Estoque", "Reservado", "Quitado")
- 'F': Nome Cliente (Em relatórios financeiros, está associado ao contrato)
- 'G': CPF/CNPJ do Cliente
- 'J': Valor de Tabela / Valor Original (R$)
- 'K': Valor de Venda / Valor Contrato (R$)
- 'L': Recebido / Pago / Valor Baixa (R$)
      -> Dica: Procure por "Total Pago", "Valor Baixa", "Total Recebido".
      -> Em fichas financeiras (T3), some os valores de "Valor baixa".
- 'M': A Receber / Saldo Devedor (R$)
      -> Dica: Procure por "Total a Pagar", "Saldo Atual", "Saldo Devedor".
- 'Q': Área Total (m²)
- 'R': Área Privativa (m²)

REGRAS DE EXTRAÇÃO:
1. Ignore linhas de totais gerais (somas do empreendimento).
2. Converta valores monetários para float (ex: "1.200,50" -> 1200.50).
3. Se o documento for "Tabela de Vendas" (espelho), foque em Unidade, Área e Valor de Tabela.

SAÍDA ESPERADA (JSON):
{{
  "tables": [
    {{
      "table": "Recebíveis",
      "rows": [
        {{ "C": "101", "F": "MARIA SILVA", "L": 50000.00, "M": 250000.00, "E": "Vendido" }}
      ]
    }}
  ]
}}

TEXTO DO DOCUMENTO:
<<<
{text[:190000]}
>>>
"""

    # =========================================================================
    # 2. ENDIVIDAMENTO
    # =========================================================================
    if doc_type == DocType.ENDIVIDAMENTO:
        return f"""{base_head}

CONTEXTO:
Relatório de Endividamento Bancário, Extrato de CCB, CRI ou Debêntures.
Exemplos: "Relatório de Endividamento ARIE", "Giro Caixa".

OBJETIVO:
Listar as dívidas ativas na tabela 'Endividamento'.

MAPEAMENTO DE COLUNAS:
- 'B': CNPJ do Tomador (Procure no cabeçalho, ex: "ARIE PROPERTIES", "GOLDSZTEIN")
- 'C': Razão Social Tomador
- 'D': Instituição Financeira / Credor
      -> Dica: Muitas vezes está na coluna "Credor/Banco" ou implícito no nome do produto (ex: "GIRO CAIXA").
      -> Se for Debênture, use o nome do Agente Fiduciário ou genericamente "Debenturistas".
- 'E': Modalidade / Produto (Ex: "CCB", "CRI", "Debênture", "Plano Empresário")
- 'F': Taxa de Juros (Ex: "1,44% a.m", "CDI + 2%")
- 'G': Indexador (Ex: "CDI", "IPCA", "TR")
- 'K': Valor Contratado / Valor Original (R$)
- 'L': Saldo Devedor Atual (Valor Principal + Juros Acumulados)
      -> Dica: Coluna "Saldo Devedor", "Valor Presente" ou "Total".
- 'N': Vencimento Final (Data)

SAÍDA ESPERADA (JSON):
{{
  "tables": [
    {{
      "table": "Endividamento",
      "rows": [
        {{ "D": "CAIXA", "E": "GIRO CAIXA", "F": "1.44% a.m", "L": 3000000.00, "N": "2029-02-01" }}
      ]
    }}
  ]
}}

TEXTO DO DOCUMENTO:
<<<
{text[:190000]}
>>>
"""

    # =========================================================================
    # 3. LANDBANK
    # =========================================================================
    if doc_type == DocType.LANDBANK:
        return f"""{base_head}

CONTEXTO:
Planilha de controle de Terrenos (Landbank).

OBJETIVO:
Preencher a tabela 'Landbank'.

MAPEAMENTO DE COLUNAS:
- 'C': Bairro
- 'D': Cidade
- 'E': UF
- 'F': Área do Terreno (m²)
- 'G': Valor de Mercado / VGV Estimado
- 'J': Valor de Aquisição (Custo histórico)
- 'I': Modelo de Aquisição (Permuta, Dinheiro, Parceria)
- 'K': Saldo a Pagar (se houver parcelas pendentes do terreno)
- 'O': Nome do Empreendimento (se já definido)

SAÍDA ESPERADA (JSON):
{{
  "tables": [
    {{
      "table": "Landbank",
      "rows": [
        {{ "C": "Pompeia", "D": "São Paulo", "F": 1401.00, "J": 19042800.00 }}
      ]
    }}
  ]
}}

TEXTO DO DOCUMENTO:
<<<
{text[:190000]}
>>>
"""

    # =========================================================================
    # 4. VIABILIDADE / FATURAMENTO
    # =========================================================================
    if doc_type in (DocType.VIABILIDADE, DocType.FATURAMENTO):
        return f"""{base_head}

CONTEXTO:
Estudo de Viabilidade Econômica, DRE Projetado ou Resumo do Empreendimento.
Pode ser PDF (Relatório Visual) ou Excel (Tabela).

OBJETIVO:
Extrair as grandes linhas de Receita e Custo para a tabela 'Viabilidade Financeira'.

MAPEAMENTO DE COLUNAS:
- 'A': Descritivo Financeiro (Nome da linha)
- 'B': Valor (R$)
- 'C': Valor (%)

ITENS CHAVE PARA BUSCAR:
- "(+) Receita VGV" ou "VGV Total"
- "(-) Custo de Obra" ou "Obras Totais"
- "(-) Terreno" ou "Aquisição Terreno"
- "(-) Impostos" ou "Tributos"
- "(-) Marketing" ou "Despesas Comerciais"
- "(=) Resultado Líquido" ou "Margem Líquida"

SAÍDA ESPERADA (JSON):
{{
  "tables": [
    {{
      "table": "Viabilidade Financeira",
      "rows": [
        {{ "A": "Receita VGV", "B": 56279500.00 }},
        {{ "A": "Terreno", "B": 19042800.00 }}
      ]
    }}
  ]
}}

TEXTO DO DOCUMENTO:
<<<
{text[:190000]}
>>>
"""

    # =========================================================================
    # 5. CRONOGRAMA / CURVA DE OBRA
    # =========================================================================
    if doc_type == DocType.CRONOGRAMA:
        return f"""{base_head}

CONTEXTO:
Cronograma Físico-Financeiro, Curva de Obra ou Planejamento.
Muitas vezes apresenta uma sequência de meses (1, 2, 3...) e custos associados.

OBJETIVO:
Extrair datas chave para o planejamento do projeto (Aba 'Projeto').

CAMPOS ALVO (Preencher em "kv" -> "Projeto"):
1. "Data de Início das Obras": 
   - Procure por "Data Base", "Início Previsto" ou a data correspondente ao "Mês 1".
2. "Previsão Término de Obras": 
   - Procure a data do último mês com custo relevante ou "Data Entrega".
3. "Habite-se (previsão)":
   - Geralmente 1 a 2 meses após o término da obra.

IMPORTANTE SOBRE DATAS RELATIVAS:
Se o documento listar apenas "Mês 1", "Mês 2", procure no cabeçalho a "Data de Referência" ou "Data Atualização" (ex: "03.10" ou "out/2024") e tente estimar a data de início real.

SAÍDA ESPERADA (JSON):
{{
  "kv": {{
    "Projeto": {{
      "Data de Início das Obras": "2024-10-01",
      "Previsão Término de Obras": "2026-10-01"
    }}
  }}
}}

TEXTO DO DOCUMENTO:
<<<
{text[:190000]}
>>>
"""

    # =========================================================================
    # 6. CONTRATO SOCIAL / ESTATUTO
    # =========================================================================
    if doc_type == DocType.CONTRATO_SOCIAL:
        return f"""{base_head}

CONTEXTO:
Contrato Social, Estatuto ou Alteração Contratual (Jurídico).

OBJETIVO:
Identificar a entidade legal e seus sócios para cadastro geral.

CAMPOS ALVO (Preencher em "kv" -> "Geral"):
- "Razão Social SPE": Nome completo da empresa (Ex: "ARIE PROPERTIES S.A.").
- "CNPJ SPE": Número do CNPJ.
- "Sócios": Lista de nomes dos sócios ou diretores citados no preâmbulo ou assinaturas.

SAÍDA ESPERADA (JSON):
{{
  "kv": {{
    "Geral": {{
      "Razão Social SPE": "ARIE PROPERTIES S.A.",
      "CNPJ SPE": "50.448.249/0001-32",
      "Sócios": "Paulo Silva Rutman Goldsztejn, Aline Silva Rutman Goldsztejn"
    }}
  }}
}}

TEXTO DO DOCUMENTO:
<<<
{text[:190000]}
>>>
"""

    # =========================================================================
    # GENÉRICO (Fallback)
    # =========================================================================
    return f"""{base_head}

TIPO DOCUMENTO: {doc_type.value}
INSTRUÇÃO:
Tente identificar tabelas ou dados relevantes para um projeto imobiliário.
Se encontrar dados de Vendas, mapeie para 'Recebíveis'.
Se encontrar dados de Dívida, mapeie para 'Endividamento'.
Se encontrar dados Gerais (Datas, Nomes), coloque em 'kv'.

TEXTO DO DOCUMENTO:
<<<
{text[:190000]}
>>>
"""