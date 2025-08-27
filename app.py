import streamlit as st
import pandas as pd
import datetime
from io import BytesIO

st.set_page_config(page_title="Configurador de Pedidos", layout="wide")

# ===== Logo centralizada =====
import os
import streamlit as st

st.set_page_config(page_title="Configurador de Pedidos", layout="wide")

# Espaço negativo (empurra a logo mais pra cima)
st.markdown("\n\n", unsafe_allow_html=True)

LOGO_PATH = os.path.join(os.getcwd(), "logo_inicio.png")

if os.path.exists(LOGO_PATH):
    st.image(LOGO_PATH, width=400)
else:
    st.warning("Logo não encontrada.")

# ===== Título =====
st.title("Configurador de Pedidos")

st.markdown("""
Gera Excel com colunas:
**MATERIAL | TPVENDA | QTDE | VLRUNITARIO | DTPRAZO + dados do cliente**

Regras:
- TPVENDA = 2 (fixo)
- DTPRAZO = data de criação + 15 dias
""")

PLANILHA_FIXA = "tabelas_de_preço_nova.xlsx"
CLIENTES_ARQ = "clientes.xlsx"

# ====== Carregar tabela de preços ======
try:
    df = pd.read_excel(PLANILHA_FIXA, sheet_name="tabela")
    st.sidebar.success(f"Tabela carregada — {len(df)} registros")
except:
    st.error("Erro ao carregar tabela de preços.")
    st.stop()

# ====== Carregar tabela de clientes ======
try:
    df_clientes = pd.read_excel(CLIENTES_ARQ, sheet_name="sheet1")
    st.sidebar.success(f"Clientes carregados — {len(df_clientes)} registros")
except:
    st.error("Erro ao carregar clientes.")
    st.stop()

# ====== Padronização ======
df.columns = [c.strip().upper() for c in df.columns]
df_clientes.columns = [c.strip().upper() for c in df_clientes.columns]

if "CODIGO" in df.columns:
    df["CODIGO"] = df["CODIGO"].fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(8)
if "CODIGO_CM" in df.columns:
    df["CODIGO_CM"] = df["CODIGO_CM"].fillna("").astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(8)
df["CODIGO_STR"] = df.get("CODIGO", "").astype(str).str.strip()

def find_row_by_code(code):
    if code is None:
        return None
    s = str(code).strip()
    cand = {s, s.lstrip("0")}
    if s.isdigit():
        cand.add(str(int(s)))
    for c in cand:
        res = df[df["CODIGO_STR"] == c]
        if not res.empty:
            return res.iloc[0]
    for c in cand:
        res = df[df["CODIGO_STR"].str.endswith(c)]
        if not res.empty:
            return res.iloc[0]
    return None

# ====== Cliente ======
st.header("0) Selecione o cliente do pedido")

def exibir_cliente(row):
    codigo = str(row.get("CÓDIGO", "")).strip()
    fantasia = str(row.get("FANTASIA", "")).strip()
    razao = str(row.get("RAZÃO SOCIAL", "")).strip()
    cnpj = str(row.get("C.N.P.J.", "")).strip()
    cpf = str(row.get("C.P.F.", "")).strip()
    doc = cnpj if cnpj else cpf
    nome_base = fantasia if fantasia else razao
    return f"{codigo} - {nome_base} ({doc})" if doc else f"{codigo} - {nome_base}"

# Opção vazia primeiro para nascer limpo
opcoes_clientes = [""] + list(df_clientes.index)

idx_cliente = st.selectbox(
    "Cliente:",
    options=opcoes_clientes,
    format_func=lambda i: "— selecione —" if i == "" else exibir_cliente(df_clientes.loc[i]),
    index=0,
    key="select_cliente"
)

# Se vazio, cliente_info fica dict vazio
cliente_info = df_clientes.loc[idx_cliente].to_dict() if idx_cliente != "" else {}

# ====== Estado ======
if "itens_principais" not in st.session_state:
    st.session_state.itens_principais = []
if "descontos" not in st.session_state:
    st.session_state.descontos = []

# ====== Itens ======
st.header("1) Selecione o(s) Item(ns) do pedido")
itens_display = df[["CODIGO", "DESCRICAO"]].copy()
opcoes_item_principal = [""] + list(itens_display.index)
idx_item_principal = st.selectbox(
    "Item principal:",
    options=opcoes_item_principal,
    format_func=lambda i: "— selecione —" if i == "" else f"{itens_display.loc[i,'CODIGO']} - {itens_display.loc[i,'DESCRICAO']}",
    key="item_principal"
)
qtde_item_principal = st.number_input("Quantidade (item principal)", min_value=1, value=1, step=1, key="qtde_principal")

if st.button("+ Adicionar mais itens", key="btn_add_extra"):
    st.session_state.itens_principais.append({"codigo": "", "qtde": 1})

for idx, extra in enumerate(st.session_state.itens_principais):
    c1, c2, c3 = st.columns([5, 2, 1])
    with c1:
        idx_atual = 0
        if extra["codigo"]:
            try:
                idx_atual = 1 + list(itens_display.index).index(extra["codigo"])
            except:
                idx_atual = 0
        escolha = st.selectbox(
            f"Item extra {idx+1}:",
            options=opcoes_item_principal,
            format_func=lambda i: "— selecione —" if i == "" else f"{itens_display.loc[i,'CODIGO']} - {itens_display.loc[i,'DESCRICAO']}",
            index=idx_atual,
            key=f"extra_select_{idx}"
        )
        st.session_state.itens_principais[idx]["codigo"] = escolha
    with c2:
        qtde = st.number_input("Qtde", min_value=1, value=int(extra["qtde"]), step=1, key=f"extra_qtde_{idx}")
        st.session_state.itens_principais[idx]["qtde"] = qtde
    with c3:
        if st.button("❌", key=f"rem_extra_{idx}"):
            st.session_state.itens_principais.pop(idx)
            st.experimental_rerun()

# ====== Casa de máquina ======
st.header("2) Escolha da casa de máquina")
casas_df = df[["CODIGO_CM", "DESCRICAO_CM"]].dropna().copy()
casas_df = casas_df[casas_df["CODIGO_CM"].astype(str).str.strip() != ""]
mask_casa = casas_df["DESCRICAO_CM"].astype(str).str.contains("casa de maquina", case=False, na=False)
casas_display = casas_df.loc[mask_casa]
opcoes_casa = [""] + list(casas_display.index)
idx_casa = st.selectbox(
    "Casa de máquina:",
    options=opcoes_casa,
    format_func=lambda i: "— selecione —" if i == "" else f"{casas_display.loc[i,'CODIGO_CM']} - {casas_display.loc[i,'DESCRICAO_CM']}",
    key="casa_maquina_select"
)
qtde_casa = st.number_input("Quantidade (casa de máquina)", min_value=1, value=1, step=1, key="qtde_casa")
selected_casa_codigo = casas_display.loc[idx_casa, "CODIGO_CM"] if idx_casa != "" else None
selected_casa_desc = casas_display.loc[idx_casa, "DESCRICAO_CM"] if idx_casa != "" else None

# ====== Componentes ======
st.markdown("---")
st.header("3) Componentes opcionais para casa de máquina")
componentes_codigos = {
    "Interruptor Bipolar": "07001001",
    "Kit By Pass": "07001002",
    "Kit Hidráulico": "07001003",
    "Kit Sucção": "07001008",
    "GC-2": "09001103",
    "GC-3": "09001084",
}
componentes_selecionados = []
for nome, codigo in componentes_codigos.items():
    if st.checkbox(f"Incluir {nome}", value=False, key=f"chk_{codigo}"):
        row = find_row_by_code(codigo)
        if row is not None:
            componentes_selecionados.append(row)

# ====== Bombas ======
st.markdown("---")
st.header("4) Bombas adicionais (até 2)")
bombas_list = [
    ("08004011", "HM-BOMBA AUX. 28 1/4 CV P/ CM"),
    ("08004012", "HM-BOMBA AUX. 35 1/3 CV P/ CM"),
    ("08004013", "HM-BOMBA AUX. 45 1/2 CV P/ CM"),
    ("08004014", "HM-BOMBA AUX. 55 1/2 CV P/ CM"),
    ("08004015", "HM-BOMBA AUX. 65 1/2 CV P/ CM"),
]
bombas_options = [f"{code} - {desc}" for code, desc in bombas_list]
sel_bombas = st.multiselect("Selecione até 2:", options=bombas_options, key="multi_bombas")
if len(sel_bombas) > 2:
    sel_bombas = sel_bombas[:2]

# ====== Condição de pagamento ======
st.markdown("---")
st.header("5) Condição de pagamento")
condicoes_map = {
    "À Vista": "A_VISTA",
    "30/60 dias": "30/60",
    "30/60/90 dias": "30/60/90"
}
condicao_escolhida = st.selectbox("Condição de pagamento:", list(condicoes_map.keys()), key="cond_pag_select")
coluna_preco_materiais = condicoes_map[condicao_escolhida]
coluna_preco_cm = {"A_VISTA": "A_VISTA_CM", "30/60": "30/60_CM", "30/60/90": "30/60/90_CM"}[coluna_preco_materiais]

# ====== Revisão ======
st.markdown("---")
st.header("6) Revisão do pedido")

# Função BRL para formatação
def brl(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

# Cliente layout tabela
st.subheader("Cliente selecionado")

if not cliente_info:
    st.info("Nenhum cliente selecionado.")
    # Caso queira bloquear tudo sem cliente, descomente:
    # st.stop()
else:
    c1, c2 = st.columns([1, 3])
    c1.markdown("**Código**")
    c1.markdown(cliente_info.get("CÓDIGO", "-"))
    c2.markdown("**Razão social | CNPJ**")
    razao_cnpj = f"{cliente_info.get('RAZÃO SOCIAL','')}  |  {cliente_info.get('C.N.P.J.','')}" if cliente_info.get("C.N.P.J.") else cliente_info.get("RAZÃO SOCIAL", "")
    c2.markdown(razao_cnpj if (razao_cnpj or '').strip() else "-")

    c3, c4 = st.columns([1, 3])
    c3.markdown("**Fantasia**")
    c3.markdown(cliente_info.get("FANTASIA", "-"))
    c4.markdown("**CPF**")
    c4.markdown(cliente_info.get("C.P.F.", "-"))

st.markdown("---")

# ===== Montagem do pedido =====
order_lines = []
if idx_item_principal != "":
    row = df.loc[idx_item_principal]
    order_lines.append({
        "MATERIAL": row["CODIGO"],
        "DESCRICAO": row["DESCRICAO"],
        "TPVENDA": 2,
        "QTDE": int(qtde_item_principal),
        "VLRUNITARIO": float(row[coluna_preco_materiais]),
    })

for extra in st.session_state.itens_principais:
    if extra["codigo"]:
        row = df.loc[extra["codigo"]]
        order_lines.append({
            "MATERIAL": row["CODIGO"],
            "DESCRICAO": row["DESCRICAO"],
            "TPVENDA": 2,
            "QTDE": int(extra["qtde"]),
            "VLRUNITARIO": float(row[coluna_preco_materiais]),
        })

if selected_casa_codigo:
    precos_casa = pd.to_numeric(df.loc[df["CODIGO_CM"] == selected_casa_codigo, coluna_preco_cm], errors="coerce").dropna()
    preco_casa = float(precos_casa.iloc[0]) if not precos_casa.empty else 0.0
    order_lines.append({
        "MATERIAL": selected_casa_codigo,
        "DESCRICAO": selected_casa_desc,
        "TPVENDA": 2,
        "QTDE": qtde_casa,
        "VLRUNITARIO": preco_casa,
    })

for comp in componentes_selecionados:
    order_lines.append({
        "MATERIAL": comp["CODIGO"],
        "DESCRICAO": comp["DESCRICAO"],
        "TPVENDA": 2,
        "QTDE": 1,
        "VLRUNITARIO": float(comp[coluna_preco_materiais]),
    })

for sel in sel_bombas:
    code = sel.split(" - ")[0]
    row = find_row_by_code(code)
    if row is not None:
        order_lines.append({
            "MATERIAL": row["CODIGO"],
            "DESCRICAO": row["DESCRICAO"],
            "TPVENDA": 2,
            "QTDE": 1,
            "VLRUNITARIO": float(row[coluna_preco_materiais]),
        })

df_order_display = pd.DataFrame(order_lines)

if df_order_display.empty:
    st.info("Nenhum item no pedido.")
else:
    # Regra de descontos
    def permite_5(cod):
        return str(cod)[:2] in {"01", "02", "03"}

    if len(st.session_state.descontos) != len(df_order_display):
        st.session_state.descontos = [
            {"d1":0.0,"d2":0.0,"d3":0.0,"d4":0.0,"d5":0.0}
            for _ in range(len(df_order_display))
        ]

    bruto_total = 0.0
    liquido_total = 0.0

    st.markdown("### Itens do pedido e descontos")
    for i, row in df_order_display.iterrows():
        st.markdown(f"**{row['MATERIAL']} - {row['DESCRICAO']}**")
        st.write(f"Qtde: {int(row['QTDE'])} | Preço unit. bruto: {brl(row['VLRUNITARIO'])}")

        if permite_5(row["MATERIAL"]):
            cols = st.columns(5)
            for j, campo in enumerate(["d1","d2","d3","d4","d5"]):
                st.session_state.descontos[i][campo] = cols[j].number_input(
                    f"Desc{j+1} %",
                    min_value=0.0, max_value=100.0, step=0.1,
                    value=st.session_state.descontos[i][campo],
                    key=f"{campo}_{i}"
                )
        else:
            st.session_state.descontos[i]["d1"] = st.number_input(
                "Desc %", min_value=0.0, max_value=100.0, step=0.1,
                value=st.session_state.descontos[i]["d1"],
                key=f"d1_unico_{i}"
            )
            for campo in ["d2","d3","d4","d5"]:
                st.session_state.descontos[i][campo] = 0.0

        # Cálculo líquido
        valor_unit_liq = float(row["VLRUNITARIO"])
        for campo in ["d1", "d2", "d3", "d4", "d5"]:
            valor_unit_liq *= (1 - st.session_state.descontos[i][campo] / 100.0)

        valor_bruto_linha = float(row["VLRUNITARIO"]) * int(row["QTDE"])
        valor_liquido_linha = valor_unit_liq * int(row["QTDE"])
        bruto_total += valor_bruto_linha
        liquido_total += valor_liquido_linha

        cb, cl = st.columns(2)
        cb.markdown(f"**Valor bruto (linha):** {brl(valor_bruto_linha)}")
        cl.markdown(f"**Valor líquido (linha):** {brl(valor_liquido_linha)}")

        df_order_display.at[i, "VLRUNITARIO"] = valor_unit_liq

    # Monta df para Excel
    df_order = df_order_display.drop(columns=["DESCRICAO"], errors="ignore")
    for col in ["CÓDIGO", "RAZÃO SOCIAL", "FANTASIA", "C.N.P.J.", "C.P.F."]:
        df_order[col] = cliente_info.get(col, "")

    hoje = datetime.date.today()
    prazo = hoje + datetime.timedelta(days=15)
    df_order_display["DTPRAZO"] = prazo
    df_order["DTPRAZO"] = prazo

    st.write("### Resumo final")
    st.dataframe(df_order_display)
    t1, t2 = st.columns(2)
    t1.metric("Total bruto", brl(bruto_total))
    t2.metric("Total líquido", brl(liquido_total))

    # ====== Função para gerar PDF do Orçamento ======
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def gerar_pdf_orcamento(buffer_bytesio, cliente_info, df_itens, total_bruto, total_liquido, condicao_pagamento):
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle("TitleBoldCenter", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18, alignment=1, spaceAfter=6)
    style_h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13, spaceBefore=8, spaceAfter=4)
    style_text = styles["BodyText"]

    doc = SimpleDocTemplate(buffer_bytesio, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm, topMargin=15*mm, bottomMargin=15*mm)
    elems = []

    # Título
    elems.append(Paragraph("ORÇAMENTO DE VENDA", style_title))
    elems.append(Spacer(1, 4))

    # Cabeçalho com cliente e data
    cliente_nome = (cliente_info.get("FANTASIA") or "").strip() or (cliente_info.get("RAZÃO SOCIAL") or "").strip()
    cliente_nome = cliente_nome if cliente_nome else "-"
    data_str = datetime.date.today().strftime("%d/%m/%Y")

    header_tbl = Table(
        [["CLIENTE", "ORÇAMENTO DE VENDA", "DATA"],
         [cliente_nome, "", data_str]],
        colWidths=[75*mm, 50*mm, 40*mm]
    )
    header_tbl.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (1,0), (1,0), "CENTER"),
        ("ALIGN", (2,0), (2,0), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    elems.append(header_tbl)
    elems.append(Spacer(1, 8))

    # Dados do cliente
    codigo = str(cliente_info.get("CÓDIGO", "") or "")
    razao = str(cliente_info.get("RAZÃO SOCIAL", "") or "")
    cnpj = str(cliente_info.get("C.N.P.J.", "") or "")
    fantasia = str(cliente_info.get("FANTASIA", "") or "")
    cpf = str(cliente_info.get("C.P.F.", "") or "")

    cliente_tbl = Table(
        [["Código", codigo, "Razão Social | CNPJ", f"{razao}" + (f" | {cnpj}" if cnpj else "")],
         ["Fantasia", fantasia, "CPF", cpf]],
        colWidths=[25*mm, 60*mm, 35*mm, 55*mm]
    )
    cliente_tbl.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.lightgrey),
        ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    elems.append(cliente_tbl)
    elems.append(Spacer(1, 10))

    # RESUMO DO PEDIDO
    elems.append(Paragraph("RESUMO DO PEDIDO", style_h2))
    elems.append(Spacer(1, 2))

    header = ["Código", "Descrição", "Qtde", "Unit Bruto", "Desc(%)", "Unit Líquido", "Total Bruto", "Total Líquido"]
    data = [header]

    def fmt(v):
        try:
            return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except:
            return "-"

    for _, r in df_itens.iterrows():
        data.append([
            str(r.get("MATERIAL", "")),
            str(r.get("DESCRICAO", "")),
            str(int(r.get("QTDE", 0) or 0)),
            fmt(r.get("UNIT_BRUTO")),
            str(r.get("DESCONTOS_TXT", "") or "-"),
            fmt(r.get("VLRUNITARIO")),
            fmt(r.get("TOTAL_BRUTO")),
            fmt(r.get("TOTAL_LIQ")),
        ])

    itens_tbl = Table(data, colWidths=[22*mm, 60*mm, 12*mm, 22*mm, 22*mm, 22*mm, 24*mm, 24*mm], repeatRows=1)
    itens_tbl.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.25, colors.lightgrey),
        ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (2,1), (2,-1), "CENTER"),
        ("ALIGN", (3,1), (-1,-1), "RIGHT"),
    ]))
    elems.append(itens_tbl)
    elems.append(Spacer(1, 8))

    # Totais e pagamento
    totals_tbl = Table(
        [["Total bruto", fmt(total_bruto)],
         ["Total líquido", fmt(total_liquido)],
         ["Condição de pagamento", str(condicao_pagamento or "")],
         ["Validade do orçamento", "15 dias a partir da emissão"]],
        colWidths=[60*mm, 100*mm]
    )
    totals_tbl.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.25, colors.lightgrey),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
    ]))
    elems.append(totals_tbl)

    doc.build(elems)

# ====== Botões de exportação ======
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import os

# Caminho da logo (ajuste se necessário)
LOGO_PATH = os.path.join(os.getcwd(), "logo.png")

def gerar_pdf_orcamento_paisagem(buffer_bytesio, cliente_info, df_itens, total_bruto, total_liquido, condicao_pagamento):
    styles = getSampleStyleSheet()
    style_title = ParagraphStyle("TitleBoldCenter", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=18, alignment=1, spaceAfter=6)
    style_h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13, spaceBefore=8, spaceAfter=4)
    style_body = ParagraphStyle("Body", parent=styles["BodyText"], fontName="Helvetica", fontSize=10)

    # Documento horizontal
    doc = SimpleDocTemplate(
        buffer_bytesio,
        pagesize=landscape(A4),
        leftMargin=12*mm, rightMargin=12*mm, topMargin=10*mm, bottomMargin=10*mm
    )
    elems = []

    # Topo com logo (esquerda) e título (centro)
    top_row = []
    if os.path.exists(LOGO_PATH):
        img = Image(LOGO_PATH, width=35*mm, height=12*mm)
        img.hAlign = "LEFT"
        top_row.append(img)
    else:
        top_row.append(Paragraph(" ", style_body))
    top_row.append(Paragraph("ORÇAMENTO DE VENDA", style_title))

    top_tbl = Table([top_row], colWidths=[45*mm, 230*mm])
    top_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (1,0), (1,0), "CENTER"),
    ]))
    elems.append(top_tbl)
    elems.append(Spacer(1, 4))

    # Cabeçalho com cliente e data
    cliente_nome = (cliente_info.get("FANTASIA") or "").strip() or (cliente_info.get("RAZÃO SOCIAL") or "").strip() or "-"
    data_str = datetime.date.today().strftime("%d/%m/%Y")

    header_tbl = Table(
        [["CLIENTE", "ORÇAMENTO DE VENDA", "DATA"],
         [cliente_nome, "", data_str]],
        colWidths=[140*mm, 60*mm, 75*mm]
    )
    header_tbl.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (1,0), (1,0), "CENTER"),
        ("ALIGN", (2,0), (2,0), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    elems.append(header_tbl)
    elems.append(Spacer(1, 6))

    # Bloco de identificação do cliente
    codigo = str(cliente_info.get("CÓDIGO", "") or "")
    razao = str(cliente_info.get("RAZÃO SOCIAL", "") or "")
    cnpj = str(cliente_info.get("C.N.P.J.", "") or "")
    fantasia = str(cliente_info.get("FANTASIA", "") or "")
    cpf = str(cliente_info.get("C.P.F.", "") or "")

    cliente_tbl = Table(
        [["Código", codigo, "Razão Social | CNPJ", f"{razao}" + (f" | {cnpj}" if cnpj else "")],
         ["Fantasia", fantasia, "CPF", cpf]],
        colWidths=[20*mm, 70*mm, 35*mm, 150*mm]
    )
    cliente_tbl.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.4, colors.lightgrey),
        ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    elems.append(cliente_tbl)
    elems.append(Spacer(1, 6))

    # Título do resumo
    elems.append(Paragraph("RESUMO DO PEDIDO", style_h2))
    elems.append(Spacer(1, 2))

    # Helper moeda
    def fmt(v):
        try:
            return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except:
            return "-"

    # Garante colunas auxiliares no df para o PDF
    itens_pdf = df_itens.copy()
    for col_aux in ["UNIT_BRUTO", "DESCONTOS_TXT", "TOTAL_BRUTO", "TOTAL_LIQ"]:
        if col_aux not in itens_pdf.columns:
            itens_pdf[col_aux] = ""

    headers = ["Código", "Descrição", "Qtde", "Unit Bruto", "Desc(%)", "Unit Líq", "Total Bruto", "Total Líq"]
    data = [headers]
    for _, r in itens_pdf.iterrows():
        data.append([
            str(r.get("MATERIAL", "")),
            str(r.get("DESCRICAO", "")),
            str(int(r.get("QTDE", 0) or 0)),
            fmt(r.get("UNIT_BRUTO")),
            str(r.get("DESCONTOS_TXT", "") or "-"),
            fmt(r.get("VLRUNITARIO")),
            fmt(r.get("TOTAL_BRUTO")),
            fmt(r.get("TOTAL_LIQ")),
        ])

    itens_tbl = Table(
        data,
        colWidths=[25*mm, 115*mm, 12*mm, 22*mm, 22*mm, 22*mm, 25*mm, 25*mm],
        repeatRows=1
    )
    itens_tbl.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.25, colors.lightgrey),
        ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (2,1), (2,-1), "CENTER"),
        ("ALIGN", (3,1), (-1,-1), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    elems.append(KeepTogether([itens_tbl]))
    elems.append(Spacer(1, 6))

    # Totais e condição
    totals_tbl = Table(
        [["Total bruto", fmt(total_bruto)],
         ["Total líquido", fmt(total_liquido)],
         ["Condição de pagamento", str(condicao_pagamento or "")],
         ["Validade do orçamento", "15 dias a partir da emissão"]],
        colWidths=[60*mm, 160*mm]
    )
    totals_tbl.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.25, colors.lightgrey),
        ("BACKGROUND", (0,0), (1,0), colors.whitesmoke),
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("ALIGN", (1,0), (1,-1), "RIGHT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))
    elems.append(totals_tbl)

    doc.build(elems)

# Área de exportação
st.markdown("---")
st.header("7) Gerar arquivos")

# Bloqueios simples: precisa ter itens
if df_order_display.empty:
    st.info("Adicione itens ao pedido para habilitar a geração de arquivos.")
else:
    col_pdf, col_xlsx = st.columns(2)

    with col_pdf:
        habilita_pdf = True
        if not cliente_info:
            st.warning("Selecione um cliente para gerar o PDF do orçamento.")
            habilita_pdf = False

        if st.button("Gerar PDF (Orçamento)", key="btn_export_pdf", disabled=not habilita_pdf):
            pdf_buffer = BytesIO()
            gerar_pdf_orcamento_paisagem(
                buffer_bytesio=pdf_buffer,
                cliente_info=cliente_info,
                df_itens=df_order_display,  # já contém VLRUNITARIO líquido; unit bruto/descontos podem ter sido adicionados na etapa de cálculo
                total_bruto=bruto_total,
                total_liquido=liquido_total,
                condicao_pagamento=condicao_escolhida
            )
            pdf_buffer.seek(0)
            st.download_button(
                "Download PDF do Orçamento",
                data=pdf_buffer,
                file_name=f"orcamento_{datetime.date.today().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                key="btn_download_pdf"
            )

    with col_xlsx:
        st.caption("Após validação do orçamento pelo cliente, gere o Excel:")
        if st.button("Gerar arquivo Excel (.xlsx)", key="btn_export_xlsx"):
            towrite = BytesIO()
            with pd.ExcelWriter(towrite, engine="openpyxl") as writer:
                df_order.to_excel(writer, index=False, sheet_name="pedido")
            towrite.seek(0)
            st.download_button(
                "Download Excel",
                data=towrite,
                file_name="pedido_simulado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_download_xlsx"
            )
