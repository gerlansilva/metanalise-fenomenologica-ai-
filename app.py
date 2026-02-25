import streamlit as st
import pandas as pd
import json
import os
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Análise Qualitativa AI", page_icon="📖", layout="wide")

# =========================
# THEME (Sua paleta + tipografia)
# =========================
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Josefin+Sans:wght@600;700&family=Open+Sans:wght@400;600&family=Work+Sans:wght@600;700&display=swap" rel="stylesheet">

<style>
:root{
 --bg:#F4F8F8;          /* neutro suave (não usa aqua puro) */
 --card:#FFFFFF;        /* cards */
 --panel:#EDF4F5;       /* inputs/painéis */
 --border:#D6E2E3;      /* bordas */

 --text:#374B4A;        /* dark slate grey */
 --muted:#6B7C7C;

 --primary:#526760;     /* granite */
 --primaryHover:#3F5450;

 --accent:#88D9E6;      /* frosted blue */
 --category:#8B8BAE;    /* lavender grey */
}

html, body, .stApp{
 background:var(--bg) !important;
 color:var(--text) !important;
 font-family:"Open Sans", sans-serif !important;
}

.block-container{
 max-width: 1400px;
 padding-top: 18px;
 padding-bottom: 36px;
}

/* remove espaçamento do header default */
header[data-testid="stHeader"] { background: transparent; }

/* TÍTULO */
.qa-title-center{
 font-family:"Josefin Sans", sans-serif;
 font-size: 52px;
 font-weight: 700;
 text-align: center;
 margin: 8px 0 18px 0;
 color: var(--text);
}

/* “layout Atlas” */
.qa-layout{
 display: grid;
 grid-template-columns: 320px 1fr;
 gap: 16px;
 align-items: start;
}

.qa-panel{
 background: var(--card);
 border: 1px solid var(--border);
 border-radius: 16px;
 box-shadow: 0 4px 14px rgba(0,0,0,.07);
 padding: 14px;
}

.qa-panel-title{
 font-family:"Work Sans", sans-serif;
 font-weight: 700;
 font-size: 14px;
 letter-spacing: .02em;
 color: var(--muted);
 margin: 0 0 10px 0;
 text-transform: uppercase;
}

/* inputs */
textarea, input, .stTextInput > div > div > input{
 background: var(--panel) !important;
 border: 1px solid var(--border) !important;
 border-radius: 12px !important;
 color: var(--text) !important;
}
textarea:focus, input:focus{
 border-color: rgba(136,217,230,.95) !important;
 box-shadow: 0 0 0 4px rgba(136,217,230,.22) !important;
}

/* radios/labels */
label, .stRadio label, .stMarkdown, p, span, div { color: var(--text) !important; }

/* file uploader */
[data-testid="stFileUploader"]{
 border-radius: 16px !important;
 border: 1px dashed rgba(55,75,74,.28) !important;
 background: rgba(237,244,245,.75) !important;
}

/* botões (inclui download) */
.stButton > button, div[data-testid="stDownloadButton"] > button{
 background: var(--primary) !important;
 color: #fff !important;
 border: none !important;
 border-radius: 12px !important;
 padding: 10px 16px !important;
 font-family:"Work Sans", sans-serif !important;
 font-weight: 700 !important;
}
.stButton > button:hover, div[data-testid="stDownloadButton"] > button:hover{
 background: var(--primaryHover) !important;
}

/* tabs */
button[data-baseweb="tab"]{
 font-family:"Work Sans", sans-serif !important;
 font-weight: 700 !important;
 color: rgba(107,124,124,.95) !important;
}
button[data-baseweb="tab"][aria-selected="true"]{
 color: var(--text) !important;
}
div[data-baseweb="tab-highlight"]{
 background: var(--accent) !important;
 height: 3px !important;
 border-radius: 999px !important;
}

/* cards de resultado */
.qa-card{
 background: var(--card);
 border: 1px solid var(--border);
 border-radius: 16px;
 box-shadow: 0 3px 12px rgba(0,0,0,.06);
 padding: 14px 14px 10px 14px;
 margin-bottom: 12px;
}
.qa-card-head{
 display:flex;
 justify-content:space-between;
 align-items:flex-start;
 gap:10px;
}
.qa-doc{
 font-weight: 700;
 font-size: 16px;
 line-height: 1.2;
}
.qa-meta{
 font-size: 12px;
 color: var(--muted) !important;
 margin-top: 4px;
}
.qa-pill{
 display:inline-block;
 background: rgba(139,139,174,.18);
 border: 1px solid rgba(139,139,174,.25);
 color: var(--text);
 padding: 4px 10px;
 border-radius: 999px;
 font-size: 12px;
 font-weight: 700;
 white-space: nowrap;
}
.qa-pill-accent{
 background: rgba(136,217,230,.22);
 border-color: rgba(136,217,230,.35);
}

/* quote */
.qa-quote{
 margin-top: 10px;
 padding: 10px 12px;
 border-left: 4px solid var(--accent);
 background: rgba(237,244,245,.75);
 border-radius: 12px;
 font-style: italic;
 white-space: pre-wrap;
}

/* bloco de texto */
.qa-block{
 margin-top: 10px;
 padding: 10px 12px;
 background: rgba(237,244,245,.75);
 border: 1px solid rgba(214,226,227,.9);
 border-radius: 12px;
}

/* tabela “mapeamento” estilo grid (colunas fixas) */
.qa-grid-header{
 display:grid;
 grid-template-columns: 240px 1fr 1fr 1fr;
 gap: 12px;
 padding: 8px 8px;
 color: var(--muted);
 font-weight: 800;
 font-family:"Work Sans";
 font-size: 12px;
 text-transform: uppercase;
}
.qa-grid-row{
 display:grid;
 grid-template-columns: 240px 1fr 1fr 1fr;
 gap: 12px;
 padding: 10px 8px;
 border-top: 1px solid rgba(214,226,227,.9);
 align-items:start;
}
.qa-cell{
 background: rgba(237,244,245,.65);
 border: 1px solid rgba(214,226,227,.9);
 border-radius: 14px;
 padding: 10px 12px;
 min-height: 74px;
}
.qa-doccell{
 background: transparent;
 border: none;
 padding: 0;
}
.qa-doctitle{
 font-weight: 800;
 font-size: 15px;
 line-height: 1.25;
}
.qa-ev{
 margin-top: 10px;
 font-style: italic;
 border-left: 4px solid rgba(139,139,174,.55);
 padding-left: 10px;
 color: var(--text);
 white-space: pre-wrap;
}
.qa-page{
 margin-top: 8px;
 color: var(--muted);
 font-size: 12px;
 font-weight: 700;
}

/* responsivo */
@media (max-width: 1100px){
  .qa-layout{ grid-template-columns: 1fr; }
  .qa-grid-header, .qa-grid-row{ grid-template-columns: 1fr; }
}

</style>
""", unsafe_allow_html=True)

# =========================
# GEMINI CLIENT
# =========================
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.warning("⚠️ Variável de ambiente GEMINI_API_KEY não encontrada. Configure-a para continuar.")
    st.stop()
client = genai.Client(api_key=api_key)

# =========================
# Pydantic Schemas
# =========================
class UnidadeSentido(BaseModel):
    id_unidade: str = Field(description="ID único automático, ex: DOC01_P087_US03")
    documento: str = Field(description="Nome do arquivo PDF")
    pagina: int | None = Field(description="Número da página onde o trecho aparece, null se não encontrado")
    citacao_literal: str = Field(description="Trecho exato do texto, sem alterações")
    contexto_resumido: str | None = None
    justificativa_fenomenologica: str | None = None

class UnidadeSignificado(BaseModel):
    id_unidade: str
    documento: str
    trecho_original: str
    sintese: str

class Categoria(BaseModel):
    nome: str
    descricao: str
    unidades_relacionadas: list[str]

class PhenomenologicalResult(BaseModel):
    unidades_sentido: list[UnidadeSentido]
    unidades_significado: list[UnidadeSignificado]
    categorias: list[Categoria]

class SystematicAnswer(BaseModel):
    pergunta: str
    resposta: str
    evidencia_textual: str
    pagina: int | None = None

class SystematicDocument(BaseModel):
    documento: str
    respostas: list[SystematicAnswer]

class SystematicResult(BaseModel):
    documentos: list[SystematicDocument]

class AnalysisResult(BaseModel):
    fenomenologico: PhenomenologicalResult | None = None
    sistematico: SystematicResult | None = None

# =========================
# Helpers
# =========================
def parse_questions(multiline: str) -> list[str]:
    qs = []
    for line in (multiline or "").splitlines():
        l = line.strip()
        if not l:
            continue
        # remove "1. " etc
        if len(l) > 2 and l[0].isdigit() and l[1] in [".", ")"]:
            l = l[2:].strip()
        qs.append(l)
    return qs

def safe_get(d, key, default):
    if isinstance(d, dict) and key in d:
        return d[key]
    return default

# guarda resultado em sessão para baixar CSV sem reprocessar
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "last_mode" not in st.session_state:
    st.session_state.last_mode = None

# =========================
# HEADER
# =========================
st.markdown('<div class="qa-title-center">📖 Análise Qualitativa AI</div>', unsafe_allow_html=True)

# =========================
# LAYOUT (estilo Atlas: sidebar + conteúdo)
# =========================
left, right = st.columns([0.32, 0.68], gap="large")

with left:
    st.markdown('<div class="qa-panel"><div class="qa-panel-title">Configurações</div>', unsafe_allow_html=True)

    mode = st.radio(
        "Modo de Análise",
        [
            "Fenomenológico",
            "Temático (Braun & Clarke)",
            "Mapeamento Sistemático",
            "Fenomenológico + Mapeamento",
            "Temático + Mapeamento",
            "Todos (3 modos)",
        ],
        index=0,
        help="Escolha o modo. Para mapeamento, insira perguntas (1 por linha)."
    )

    phenom_q = ""
    thematic_q = ""
    sys_q = ""

    if mode in ["Fenomenológico", "Fenomenológico + Mapeamento", "Todos (3 modos)"]:
        phenom_q = st.text_area(
            "Interrogação Fenomenológica",
            placeholder="Ex: Como o fenômeno X se constitui nos textos analisados?",
            height=110
        )

    if mode in ["Temático (Braun & Clarke)", "Temático + Mapeamento", "Todos (3 modos)"]:
        thematic_q = st.text_area(
            "Questão orientadora (Temática) — opcional",
            placeholder="Ex: Quais padrões se repetem sobre objetivos, métodos e resultados?",
            height=90
        )

    if mode in ["Mapeamento Sistemático", "Fenomenológico + Mapeamento", "Temático + Mapeamento", "Todos (3 modos)"]:
        sys_q = st.text_area(
            "Perguntas para Mapeamento (1 por linha)",
            placeholder="1. Qual é o objetivo do estudo?\n2. Qual metodologia é utilizada?\n3. Quais softwares foram utilizados?",
            height=130
        )

    uploaded_files = st.file_uploader("Corpus Documental (PDFs)", type="pdf", accept_multiple_files=True)

    # validações rápidas
    needs_phenom = mode in ["Fenomenológico", "Fenomenológico + Mapeamento", "Todos (3 modos)"]
    needs_sys = mode in ["Mapeamento Sistemático", "Fenomenológico + Mapeamento", "Temático + Mapeamento", "Todos (3 modos)"]
    needs_thematic = mode in ["Temático (Braun & Clarke)", "Temático + Mapeamento", "Todos (3 modos)"]

    can_run = bool(uploaded_files) and (not needs_phenom or phenom_q.strip()) and (not needs_sys or sys_q.strip() or mode.startswith("Temático"))

    run = st.button("Iniciar Análise do Corpus", type="primary", disabled=not bool(uploaded_files))

    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="qa-panel"><div class="qa-panel-title">Resultados</div>', unsafe_allow_html=True)

    if run:
        if needs_phenom and not phenom_q.strip():
            st.warning("Preencha a Interrogação Fenomenológica.")
        elif needs_sys and mode != "Temático (Braun & Clarke)" and not sys_q.strip() and "Mapeamento" in mode:
            st.warning("Preencha as Perguntas para Mapeamento (1 por linha).")
        else:
            total_size = sum([f.size for f in uploaded_files]) if uploaded_files else 0
            if total_size > 15 * 1024 * 1024:
                st.error(f"Tamanho total {total_size/1024/1024:.2f} MB excede limite seguro de 15 MB.")
            else:
                with st.spinner("Analisando o corpus..."):
                    try:
                        gemini_files = [
                            types.Part.from_bytes(data=f.getvalue(), mime_type="application/pdf")
                            for f in uploaded_files
                        ]

                        prompt_text = "Leia todos os PDFs anexados.\n\n"

                        # Fenomenológico
                        if needs_phenom:
                            prompt_text += "=== MODO FENOMENOLÓGICO ===\n"
                            prompt_text += f"INTERROGAÇÃO:\n\"{phenom_q}\"\n\n"
                            prompt_text += (
                                "ETAPA 1: Extraia unidades de sentido (documento, página, citação literal exata, contexto e justificativa).\n"
                                "ETAPA 2: Transforme cada unidade em unidade de significado.\n"
                                "ETAPA 3: Agrupe convergências.\n"
                                "ETAPA 4: Sugira categorias fenomenológicas.\n"
                                "Regras: NÃO parafrasear a citação, NÃO inventar páginas. Se não souber, página = null.\n\n"
                            )

                        # Temático (Braun & Clarke) — implementação mínima: códigos + temas
                        # Para manter compatibilidade, reaproveitamos estrutura fenomenológica como "unidades_sentido"
                        # e "categorias" como "temas". (Você pode refinar depois com schema próprio.)
                        if needs_thematic:
                            prompt_text += "=== MODO TEMÁTICO (BRAUN & CLARKE) ===\n"
                            if thematic_q.strip():
                                prompt_text += f"QUESTÃO ORIENTADORA:\n\"{thematic_q.strip()}\"\n\n"
                            prompt_text += (
                                "Produza: (1) uma lista de CÓDIGOS com trechos literais (doc/página) "
                                "e (2) TEMAS com descrição e lista de códigos associados.\n"
                                "Se não conseguir página com certeza, use null.\n\n"
                            )

                        # Mapeamento Sistemático
                        if "Mapeamento" in mode or mode == "Mapeamento Sistemático" or mode == "Todos (3 modos)":
                            qs = parse_questions(sys_q)
                            if qs:
                                prompt_text += "=== MODO MAPEAMENTO SISTEMÁTICO ===\n"
                                prompt_text += "Responda às perguntas abaixo PARA CADA documento:\n"
                                prompt_text += "\n".join(qs) + "\n\n"
                                prompt_text += "Regras: resposta objetiva + evidência textual literal + página.\n\n"

                        contents = gemini_files + [prompt_text]

                        # escolhe schema
                        schema = AnalysisResult
                        if mode == "Fenomenológico":
                            schema = PhenomenologicalResult
                        elif mode == "Mapeamento Sistemático":
                            schema = SystematicResult

                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=contents,
                            config=types.GenerateContentConfig(
                                system_instruction=(
                                    "Você é um assistente de análise qualitativa de corpus documental. "
                                    "Siga o prompt e preencha o JSON de saída. "
                                    "Nunca invente conteúdo. Se página não for certa, use null."
                                ),
                                response_mime_type="application/json",
                                response_schema=schema,
                                temperature=0.2,
                            ),
                        )

                        result_data = json.loads(response.text)
                        st.session_state.analysis_result = result_data
                        st.session_state.last_mode = mode
                        st.success("Análise concluída!")

                    except Exception as e:
                        st.error(f"Erro durante a análise: {e}")

    # Render dos resultados (sem reprocessar)
    result_data = st.session_state.analysis_result
    if result_data:
        mode_used = st.session_state.last_mode or mode

        # Normaliza
        phenom_data = result_data if mode_used == "Fenomenológico" else safe_get(result_data, "fenomenologico", None)
        sys_data = result_data if mode_used == "Mapeamento Sistemático" else safe_get(result_data, "sistematico", None)

        tabs = []
        if phenom_data:
            tabs.extend(["Unidades de Sentido", "Unidades de Significado", "Categorias"])
        if sys_data:
            tabs.append("Mapeamento")

        if tabs:
            t = st.tabs(tabs)

            ti = 0
            # Fenomenológico: cards estilo “mapeamento”
            if phenom_data:
                # CSV topo (por aba)
                with t[ti]:
                    us = pd.DataFrame(phenom_data.get("unidades_sentido", []))
                    csv = us.to_csv(index=False).encode("utf-8")
                    st.download_button("Exportar CSV", csv, "unidades_sentido.csv", "text/csv")

                    for _, row in us.iterrows():
                        doc = row.get("documento", "-")
                        pid = row.get("id_unidade", "-")
                        pag = row.get("pagina", None)
                        pag_txt = f"Pág. {pag}" if pd.notna(pag) and pag is not None else "Pág. —"
                        cit = row.get("citacao_literal", "")
                        ctx = row.get("contexto_resumido", "")
                        jus = row.get("justificativa_fenomenologica", "")

                        st.markdown(f"""
                        <div class="qa-card">
                          <div class="qa-card-head">
                            <div>
                              <div class="qa-doc">{doc}</div>
                              <div class="qa-meta">{pid} • {pag_txt}</div>
                            </div>
                            <span class="qa-pill qa-pill-accent">Unidade de Sentido</span>
                          </div>

                          <div class="qa-quote">"{cit}"</div>

                          <div class="qa-block">
                            <div style="font-weight:800; font-family:'Work Sans'; margin-bottom:6px; color:var(--muted); text-transform:uppercase; font-size:12px;">
                              Contexto
                            </div>
                            <div>{ctx if ctx else "-"}</div>

                            <div style="height:10px"></div>

                            <div style="font-weight:800; font-family:'Work Sans'; margin-bottom:6px; color:var(--muted); text-transform:uppercase; font-size:12px;">
                              Justificativa
                            </div>
                            <div>{jus if jus else "-"}</div>
                          </div>
                        </div>
                        """, unsafe_allow_html=True)
                ti += 1

                with t[ti]:
                    um = pd.DataFrame(phenom_data.get("unidades_significado", []))
                    csv = um.to_csv(index=False).encode("utf-8")
                    st.download_button("Exportar CSV", csv, "unidades_significado.csv", "text/csv")

                    for _, row in um.iterrows():
                        doc = row.get("documento", "-")
                        pid = row.get("id_unidade", "-")
                        trecho = row.get("trecho_original", "")
                        sintese = row.get("sintese", "")

                        st.markdown(f"""
                        <div class="qa-card">
                          <div class="qa-card-head">
                            <div>
                              <div class="qa-doc">{doc}</div>
                              <div class="qa-meta">{pid}</div>
                            </div>
                            <span class="qa-pill">Unidade de Significado</span>
                          </div>

                          <div class="qa-quote">"{trecho}"</div>

                          <div class="qa-block">
                            <div style="font-weight:800; font-family:'Work Sans'; margin-bottom:6px; color:var(--muted); text-transform:uppercase; font-size:12px;">
                              Síntese de significado
                            </div>
                            <div style="font-weight:700;">{sintese if sintese else "-"}</div>
                          </div>
                        </div>
                        """, unsafe_allow_html=True)
                ti += 1

                with t[ti]:
                    cats = phenom_data.get("categorias", [])
                    # CSV
                    cats_rows = []
                    for c in cats:
                        cats_rows.append({
                            "nome": c.get("nome"),
                            "descricao": c.get("descricao"),
                            "unidades_relacionadas": ", ".join(c.get("unidades_relacionadas", []))
                        })
                    df_cats = pd.DataFrame(cats_rows)
                    csv = df_cats.to_csv(index=False).encode("utf-8")
                    st.download_button("Exportar CSV", csv, "categorias.csv", "text/csv")

                    # cards de categorias
                    for c in cats:
                        nome = c.get("nome", "Categoria")
                        desc = c.get("descricao", "")
                        units = c.get("unidades_relacionadas", [])
                        chips = " ".join([f'<span class="qa-pill">{u}</span>' for u in units]) if units else "<span class='qa-pill'>—</span>"

                        st.markdown(f"""
                        <div class="qa-card">
                          <div class="qa-card-head">
                            <div class="qa-doc">{nome}</div>
                            <span class="qa-pill qa-pill-accent">Categoria</span>
                          </div>

                          <div class="qa-block">{desc if desc else "-"}</div>

                          <div style="margin-top:10px; font-weight:800; font-family:'Work Sans'; color:var(--muted); text-transform:uppercase; font-size:12px;">
                            Unidades relacionadas
                          </div>
                          <div style="margin-top:8px;">{chips}</div>
                        </div>
                        """, unsafe_allow_html=True)
                ti += 1

            # Mapeamento: grid estilo print
            if sys_data:
                with t[ti]:
                    docs = sys_data.get("documentos", [])

                    # extrair perguntas únicas
                    unique_qs = []
                    for d in docs:
                        for a in d.get("respostas", []):
                            q = a.get("pergunta")
                            if q and q not in unique_qs:
                                unique_qs.append(q)

                    # CSV topo
                    rows = []
                    for d in docs:
                        row = {"Documento": d.get("documento", "-")}
                        for q in unique_qs:
                            ans = next((x for x in d.get("respostas", []) if x.get("pergunta") == q), None)
                            if ans:
                                p = ans.get("pagina")
                                ptxt = f" (Pág. {p})" if p is not None else ""
                                row[q] = f"{ans.get('resposta','')}\n\nEvidência: \"{ans.get('evidencia_textual','')}\"{ptxt}"
                            else:
                                row[q] = "-"
                        rows.append(row)

                    df_sys = pd.DataFrame(rows)
                    csv = df_sys.to_csv(index=False).encode("utf-8")
                    st.download_button("Exportar CSV", csv, "mapeamento_sistematico.csv", "text/csv")

                    # grid (até 3 perguntas por linha no layout mostrado)
                    show_qs = unique_qs[:3] if len(unique_qs) >= 3 else unique_qs
                    while len(show_qs) < 3:
                        show_qs.append("—")

                    st.markdown(f"""
                    <div class="qa-grid-header">
                      <div>Documento</div>
                      <div>{show_qs[0]}</div>
                      <div>{show_qs[1]}</div>
                      <div>{show_qs[2]}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    for d in docs:
                        docname = d.get("documento", "-")
                        answers = d.get("respostas", [])

                        def cell_for(q):
                            if q == "—":
                                return "<div class='qa-cell'>—</div>"
                            ans = next((x for x in answers if x.get("pergunta") == q), None)
                            if not ans:
                                return "<div class='qa-cell'>—</div>"
                            resp = ans.get("resposta", "-")
                            ev = ans.get("evidencia_textual", "")
                            pg = ans.get("pagina", None)
                            pg_html = f"<div class='qa-page'>PÁG. {pg}</div>" if pg is not None else "<div class='qa-page'>PÁG. —</div>"
                            ev_html = f"<div class='qa-ev'>\"{ev}\"</div>" if ev else ""
                            return f"<div class='qa-cell'><div>{resp}</div>{ev_html}{pg_html}</div>"

                        st.markdown(f"""
                        <div class="qa-grid-row">
                          <div class="qa-doccell">
                            <div class="qa-doctitle">{docname}</div>
                          </div>
                          {cell_for(show_qs[0])}
                          {cell_for(show_qs[1])}
                          {cell_for(show_qs[2])}
                        </div>
                        """, unsafe_allow_html=True)

    else:
        st.info("Envie PDFs e rode a análise. Os resultados aparecerão aqui (não reinicia ao exportar CSV).")

    st.markdown("</div>", unsafe_allow_html=True)
