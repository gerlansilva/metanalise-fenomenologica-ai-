import streamlit as st
import pandas as pd
import json
import os
import time
import threading
import requests
import hashlib
import html
import streamlit.components.v1 as components

from streamlit.runtime.scriptrunner import add_script_run_ctx
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# ============================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================
st.set_page_config(
    page_title="Análise Qualitativa AI",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# IDENTIDADE VISUAL (PALETA + FONTES)
# ============================================================
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Josefin+Sans:wght@400;600;700&family=Open+Sans:wght@300;400;600;700&family=Work+Sans:wght@400;600;700&display=swap" rel="stylesheet">

<style>
:root{
  --bg:#E7DFC9;          /* pergaminho médio */
  --panel:#F1E9D8;       /* creme médio */
  --panel2:#EDE4D1;      /* creme mais fechado */
  --line:#C9BFA6;        /* bordas */
  --text:#2F241C;        /* texto */
  --muted:#6E6A5E;       /* texto secundário */
  --accent:#C26A2E;      /* terracota */
  --accent2:#A35422;     /* terracota escuro */
  --moss:#6F8A73;        /* musgo */
  --shadow: 0 10px 26px rgba(47,36,28,0.10);
  --shadow2: 0 2px 10px rgba(47,36,28,0.08);
  --radius: 20px;
}

/* FUNDO */
html, body { background: var(--bg) !important; }
.stApp { background: var(--bg) !important; color: var(--text) !important; }
* { font-family: "Open Sans", system-ui, -apple-system, Segoe UI, Arial, sans-serif; }

/* CONTAINER PRINCIPAL */
.block-container { max-width: 1320px; padding-top: 36px; padding-bottom: 36px; }

/* TÍTULO CENTRALIZADO */
.qa-title-center{
  font-family: "Josefin Sans", sans-serif;
  font-weight: 800;
  font-size: 52px;
  letter-spacing: -0.02em;
  color: var(--text);
  text-align: center;
  margin: 0 0 10px 0;
  background: -webkit-linear-gradient(135deg, var(--accent), var(--accent2));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.qa-subtitle-center {
  text-align: center;
  color: var(--muted);
  font-size: 16px;
  margin-bottom: 40px;
}

/* CARD/PAINÉIS */
.qa-shell{
  background: var(--panel);
  border: 1px solid rgba(47,36,28,0.12);
  border-radius: calc(var(--radius) + 6px);
  box-shadow: var(--shadow);
  padding: 18px 20px;
}

/* INPUTS */
textarea, input, .stTextInput > div > div > input {
  background: var(--panel2) !important;
  color: var(--text) !important;
  border-radius: 14px !important;
  border: 1px solid rgba(47,36,28,0.18) !important;
}
textarea::placeholder, input::placeholder { color: rgba(110,106,94,0.85) !important; }
textarea:focus, input:focus {
  border-color: rgba(194,106,46,0.70) !important;
  box-shadow: 0 0 0 4px rgba(194,106,46,0.18) !important;
}

/* RADIO / LABELS */
.stRadio label, .stMarkdown, label, p, span, div { color: var(--text); }
.stRadio [data-testid="stMarkdownContainer"] p { color: var(--text) !important; }

/* FILE UPLOADER */
[data-testid="stFileUploader"]{
  border-radius: var(--radius) !important;
  border: 1px dashed rgba(47,36,28,0.25) !important;
  background: rgba(241,233,216,0.55) !important;
}

/* BOTÃO PRINCIPAL */
.stButton > button {
  background: linear-gradient(135deg, var(--accent), var(--accent2)) !important;
  color: #fff !important;
  border: none !important;
  border-radius: 14px !important;
  padding: 12px 18px !important;
  font-family: "Work Sans", sans-serif !important;
  font-weight: 800 !important;
  box-shadow: 0 14px 22px rgba(194,106,46,0.18) !important;
  width: 100%;
}
.stButton > button:hover { filter: saturate(1.05); transform: translateY(-1px); }

/* DOWNLOAD BUTTON */
div[data-testid="stDownloadButton"] > button {
  border: 1px solid rgba(47,36,28,0.16) !important;
  background: var(--panel2) !important;
  color: var(--text) !important;
  border-radius: 14px !important;
  font-weight: 800 !important;
  box-shadow: var(--shadow2) !important;
}

/* TABS */
button[data-baseweb="tab"]{
  font-family: "Work Sans", sans-serif !important;
  font-weight: 800 !important;
  color: rgba(110,106,94,0.95) !important;
}
button[data-baseweb="tab"][aria-selected="true"]{ color: var(--text) !important; }
div[data-baseweb="tab-highlight"]{
  background: linear-gradient(90deg, var(--accent), var(--accent2)) !important;
  height: 3px !important;
  border-radius: 999px !important;
}

/* QUOTE */
.quote{
  font-style: italic;
  line-height: 1.62;
  white-space: pre-wrap;
  border-left: 4px solid rgba(111,138,115,0.95);
  padding-left: 12px;
  color: var(--text);
}

/* CHIPS */
.chip{
  border: 1px solid rgba(47,36,28,0.14);
  border-radius: 12px;
  padding: 6px 10px;
  font-size: 13px;
  color: var(--text);
  background: rgba(111,138,115,0.22);
}

/* SCROLLBAR */
::-webkit-scrollbar { width: 10px; }
::-webkit-scrollbar-thumb { background: rgba(111,138,115,0.75); border-radius: 999px; }
::-webkit-scrollbar-track { background: rgba(47,36,28,0.06); }
</style>
""", unsafe_allow_html=True)

# ============================================================
# SESSION STATE
# ============================================================
if "analysis_done" not in st.session_state: st.session_state.analysis_done = False
if "result_data" not in st.session_state: st.session_state.result_data = None
if "df_sys_long" not in st.session_state: st.session_state.df_sys_long = None
if "last_mode" not in st.session_state: st.session_state.last_mode = None
if "cross_synthesis" not in st.session_state: st.session_state.cross_synthesis = {}
if "ris_pdfs" not in st.session_state: st.session_state.ris_pdfs = []
if "ris_texts" not in st.session_state: st.session_state.ris_texts = []

# ============================================================
# GEMINI CLIENT
# ============================================================
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ Variável de ambiente GEMINI_API_KEY não encontrada. Configure-a para continuar.")
    st.stop()
client = genai.Client(api_key=api_key)

# ============================================================
# MODELOS PYDANTIC
# ============================================================
class UnidadeSentido(BaseModel):
    id_unidade: str
    documento: str
    pagina: int | None
    citacao_literal: str
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

class ThematicCode(BaseModel):
    id_codigo: str = Field(description="ID único, ex: DOC01_P014_COD03")
    documento: str
    pagina: int | None
    trecho: str = Field(description="Trecho literal exato (sem parafrasear)")
    codigo: str = Field(description="Nome curto do código")
    descricao_codigo: str = Field(description="Definição operacional do código")

class ThematicTheme(BaseModel):
    nome: str
    descricao: str
    codigos_relacionados: list[str]
    interpretacao: str

class ThematicResult(BaseModel):
    codigos: list[ThematicCode]
    temas: list[ThematicTheme]

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
    tematico: ThematicResult | None = None
    sistematico: SystematicResult | None = None

# ============================================================
# FUNÇÕES AUXILIARES (IA / RIS / PDF)
# ============================================================
def gerar_sintese_transversal(pergunta: str, df_sub: pd.DataFrame) -> str:
    linhas = []
    for _, r in df_sub.iterrows():
        doc = str(r.get("Documento", "")).strip()
        resp = str(r.get("Resposta", "")).strip()
        evid = str(r.get("Evidência", "")).strip()
        pag = r.get("Página", None)
        pag_str = f"{pag}" if (pag is not None and str(pag).strip() != "") else "null"
        linhas.append(f"- DOCUMENTO: {doc}\n  RESPOSTA: {resp}\n  EVIDÊNCIA: \"{evid}\"\n  PÁGINA: {pag_str}\n")

    prompt = f"""
Você está comparando resultados entre documentos para a MESMA pergunta, com base apenas nas respostas e evidências abaixo.

PERGUNTA:
{pergunta}

RESPOSTAS POR DOCUMENTO:
{chr(10).join(linhas)}

TAREFAS (nesta ordem):
1) CONVERGÊNCIAS (bullets)
2) DIVERGÊNCIAS (bullets)
3) DISTRIBUIÇÃO/CONTAGEM (Item — Nº de documentos). Use "não informado" quando apropriado.
4) SÍNTESE INTERPRETATIVA (6–10 linhas), em português acadêmico claro.
"""
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt],
        config=types.GenerateContentConfig(temperature=0.2),
    )
    return resp.text

def parse_ris(ris_text):
    entries = []
    current = {}
    for line in ris_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('ER  -'):
            if current:
                entries.append(current)
            current = {}
        elif len(line) >= 6 and line[4:6] == '- ':
            key = line[:2]
            val = line[6:].strip()
            if key in current:
                current[key] = current[key] + " ; " + val
            else:
                current[key] = val
    return entries

def fetch_oa_pdf(doi):
    try:
        url = f"https://api.unpaywall.org/v2/{doi}?email=dobbylivreagora@gmail.com"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if data.get('is_oa') and data.get('best_oa_location'):
                pdf_url = data['best_oa_location'].get('url_for_pdf')
                if pdf_url:
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                    pdf_res = requests.get(pdf_url, headers=headers, timeout=15)
                    if pdf_res.status_code == 200 and pdf_res.content.startswith(b'%PDF'):
                        return pdf_res.content
    except Exception:
        pass
    return None

def includes_phenom(m: str) -> bool:
    return m in ["Fenomenológico", "Fenomenológico + Mapeamento", "Todos (3 modos)"]

def includes_thematic(m: str) -> bool:
    return m in ["Temático (Braun & Clarke)", "Temático + Mapeamento", "Todos (3 modos)"]

def includes_systematic(m: str) -> bool:
    return m in ["Mapeamento Sistemático", "Fenomenológico + Mapeamento", "Temático + Mapeamento", "Todos (3 modos)"]

# ============================================================
# FUNÇÕES AUXILIARES (MAPEAMENTO: PIVOT + TABELA STICKY)
# ============================================================
def build_sys_pivot_table(df_long: pd.DataFrame) -> pd.DataFrame:
    """
    Pivot: linhas=Documento (vertical), colunas=Pergunta (horizontal).
    Cada célula contém Resposta + Evidência + Página (tudo na célula).
    """
    df = df_long.copy()
    df["Documento"] = df["Documento"].fillna("Sem documento").astype(str)
    df["Pergunta"] = df["Pergunta"].fillna("Sem pergunta").astype(str)

    def fmt_cell(r):
        resp = (r.get("Resposta") or "").strip()
        evid = (r.get("Evidência") or "").strip()
        pag = r.get("Página", None)
        pag_txt = f"{pag}" if (pag is not None and str(pag).strip() != "") else "null"

        parts = []
        parts.append(f"**Resposta:** {resp}" if resp else "**Resposta:** —")
        parts.append(f"**Evidência:** “{evid}”" if evid else "**Evidência:** —")
        parts.append(f"**Página:** {pag_txt}")
        return "\n".join(parts).strip()

    df["Celula"] = df.apply(fmt_cell, axis=1)

    # Se tiver duplicatas (mesmo doc+pergunta), junta
    agg = (
        df.groupby(["Documento", "Pergunta"])["Celula"]
          .apply(lambda s: "\n\n---\n\n".join([x for x in s if x]))
          .reset_index()
    )

    pivot = agg.pivot(index="Documento", columns="Pergunta", values="Celula").fillna("")
    pivot = pivot.reset_index()
    return pivot

def render_sticky_table(pivot_df: pd.DataFrame, height_px: int = 560):
    """
    Tabela HTML com scroll e sticky header + sticky primeira coluna.
    """
    cols = pivot_df.columns.tolist()
    first_col = cols[0]  # "Documento"

    css = f"""
    <style>
      .tbl-wrap {{
        border: 1px solid rgba(47,36,28,0.18);
        border-radius: 14px;
        overflow: auto;
        height: {height_px}px;
        background: rgba(241,233,216,0.65);
        box-shadow: 0 2px 10px rgba(47,36,28,0.06);
      }}

      table.sys {{
        border-collapse: separate;
        border-spacing: 0;
        width: max-content;
        min-width: 100%;
        font-family: "Open Sans", system-ui, -apple-system, Segoe UI, Arial, sans-serif;
        color: var(--text);
      }}

      thead th {{
        position: sticky;
        top: 0;
        z-index: 5;
        background: var(--panel);
        border-bottom: 1px solid rgba(47,36,28,0.18);
        padding: 10px 12px;
        font-size: 13px;
        text-align: left;
        white-space: nowrap;
      }}

      tbody td {{
        border-bottom: 1px solid rgba(47,36,28,0.10);
        border-right: 1px solid rgba(47,36,28,0.08);
        padding: 10px 12px;
        vertical-align: top;
        font-size: 13px;
        line-height: 1.45;
        background: rgba(237,228,209,0.55);
        min-width: 360px;
        max-width: 640px;
        white-space: pre-wrap;
      }}

      tbody tr:hover td {{
        background: rgba(194,106,46,0.07);
      }}

      /* 1ª coluna sticky */
      th.sticky-col, td.sticky-col {{
        position: sticky;
        left: 0;
        z-index: 6;
        background: var(--panel2);
        border-right: 1px solid rgba(47,36,28,0.18);
        min-width: 260px;
        max-width: 320px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        font-weight: 800;
      }}

      /* canto superior esquerdo */
      thead th.sticky-col {{
        z-index: 10;
        background: var(--panel);
      }}

      .cell-strong b {{
        color: var(--accent2);
      }}

      .muted {{
        color: var(--muted);
      }}

      .divider {{
        margin: 10px 0;
        height: 1px;
        background: rgba(47,36,28,0.12);
      }}
    </style>
    """

    def md_bold_to_html(text: str) -> str:
        out = html.escape(text)
        # negrito simples **...**
        while "**" in out:
            out = out.replace("**", "<b>", 1).replace("**", "</b>", 1)
        out = out.replace("\n\n---\n\n", "<div class='divider'></div>")
        out = out.replace("\n", "<br>")
        return f"<div class='cell-strong'>{out}</div>"

    thead = "<thead><tr>"
    for c in cols:
        if c == first_col:
            thead += f"<th class='sticky-col'>{html.escape(c)}</th>"
        else:
            thead += f"<th>{html.escape(c)}</th>"
    thead += "</tr></thead>"

    tbody = "<tbody>"
    for _, row in pivot_df.iterrows():
        tbody += "<tr>"
        for c in cols:
            val = row.get(c, "")
            if c == first_col:
                tbody += f"<td class='sticky-col'>{html.escape(str(val))}</td>"
            else:
                cell = str(val).strip()
                cell_html = md_bold_to_html(cell) if cell else "<span class='muted'>—</span>"
                tbody += f"<td>{cell_html}</td>"
        tbody += "</tr>"
    tbody += "</tbody>"

    html_table = f"""
    {css}
    <div class="tbl-wrap">
      <table class="sys">
        {thead}
        {tbody}
      </table>
    </div>
    """

    components.html(html_table, height=height_px + 60, scrolling=False)

# ============================================================
# TÍTULO CENTRALIZADO
# ============================================================
st.markdown('<div class="qa-title-center">Análise Qualitativa AI</div>', unsafe_allow_html=True)
st.markdown('<div class="qa-subtitle-center">Fenomenológica • Temática (Braun & Clarke) • Mapeamento • Integração RIS (Scopus/OpenAlex)</div>', unsafe_allow_html=True)

# ============================================================
# BARRA LATERAL (SIDEBAR)
# ============================================================
with st.sidebar:
    st.header("Configurações")
    mode = st.radio(
        "Modo de Análise",
        [
            "Fenomenológico",
            "Temático (Braun & Clarke)",
            "Mapeamento Sistemático",
            "Fenomenológico + Mapeamento",
            "Temático + Mapeamento",
            "Todos (3 modos)"
        ],
        horizontal=False,
    )

    phenom_q = ""
    thematic_q = ""
    sys_q = ""

    if includes_phenom(mode):
        phenom_q = st.text_area(
            "Interrogação Fenomenológica",
            placeholder="Ex: Como o fenômeno X se constitui nos textos analisados?",
            height=110
        )

    if includes_thematic(mode):
        thematic_q = st.text_area(
            "Questão orientadora (Análise Temática)",
            placeholder="Ex: Quais padrões se repetem sobre métodos, ferramentas, objetivos e resultados?",
            height=90
        )

    if includes_systematic(mode):
        sys_q = st.text_area(
            "Perguntas para Mapeamento Sistemático (1 por linha)",
            placeholder="1. Qual é o objetivo do estudo?\n2. Qual metodologia é utilizada?",
            height=150
        )

    st.markdown("---")
    st.subheader("📚 Corpus Documental")

    # 1. RIS UPLOADER
    with st.expander("📥 Importar arquivo .RIS (Scopus/OpenAlex)", expanded=False):
        st.markdown(
            "<p style='font-size:13px; color:var(--muted);'>Faz o download automático de PDFs Open Access a partir do DOI. Artigos fechados terão o resumo extraído.</p>",
            unsafe_allow_html=True
        )
        ris_file = st.file_uploader("Arquivo .ris", type=["ris", "txt"])

        if ris_file and st.button("Processar e Baixar PDFs"):
            with st.spinner("Lendo arquivo RIS..."):
                ris_text = ris_file.getvalue().decode("utf-8", errors="ignore")
                entries = parse_ris(ris_text)

                st.session_state.ris_pdfs = []
                st.session_state.ris_texts = []

                progress_bar = st.progress(0.0)
                status_text = st.empty()

                for i, entry in enumerate(entries):
                    title = entry.get('TI', 'Sem título')
                    doi = entry.get('DO', '').replace('https://doi.org/', '').strip()
                    abstract = entry.get('AB', '')

                    status_text.text(f"Buscando ({i+1}/{len(entries)}): {title[:30]}...")

                    pdf_bytes = None
                    if doi:
                        pdf_bytes = fetch_oa_pdf(doi)

                    if pdf_bytes:
                        st.session_state.ris_pdfs.append({"name": f"RIS: {title[:30]}.pdf", "bytes": pdf_bytes})
                    elif abstract:
                        content = f"Título: {title}\nDOI: {doi}\n\nResumo:\n{abstract}"
                        st.session_state.ris_texts.append({"name": f"RIS (Resumo): {title[:30]}", "text": content})

                    progress_bar.progress((i + 1) / max(1, len(entries)))

                status_text.success(
                    f"Concluído! {len(st.session_state.ris_pdfs)} PDFs baixados, {len(st.session_state.ris_texts)} resumos extraídos."
                )

    # 2. FILE UPLOADER MANUAL
    uploaded_files = st.file_uploader("Ou envie seus PDFs manualmente", type="pdf", accept_multiple_files=True)

    # Mostrar corpus atual
    total_docs = len(uploaded_files or []) + len(st.session_state.ris_pdfs) + len(st.session_state.ris_texts)
    if total_docs > 0:
        st.markdown(f"**Documentos prontos para análise ({total_docs}):**")
        for f in (uploaded_files or []):
            st.markdown(f"- 📄 {f.name}")
        for d in st.session_state.ris_pdfs:
            st.markdown(f"- 📥 {d['name']}")
        for d in st.session_state.ris_texts:
            st.markdown(f"- 📝 {d['name']}")
        if st.button("Limpar Corpus Importado"):
            st.session_state.ris_pdfs = []
            st.session_state.ris_texts = []
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    run = st.button("▶ Iniciar Análise do Corpus", type="primary", disabled=(total_docs == 0))

# ============================================================
# EXECUTAR ANÁLISE COM CRONÔMETRO
# ============================================================
if run:
    st.session_state.analysis_done = False
    st.session_state.result_data = None
    st.session_state.last_mode = mode

    if includes_phenom(mode) and not phenom_q.strip():
        st.error("Por favor, preencha a Interrogação Fenomenológica.")
        st.stop()
    if includes_systematic(mode) and not sys_q.strip():
        st.error("Por favor, preencha as Perguntas para Mapeamento Sistemático.")
        st.stop()

    total_size = sum([f.size for f in (uploaded_files or [])]) + sum([len(p['bytes']) for p in st.session_state.ris_pdfs])
    if total_size > 15 * 1024 * 1024:
        st.error("O tamanho total excede 15 MB. Reduza a quantidade de PDFs.")
        st.stop()

    timer_placeholder = st.empty()
    stop_timer = False
    start_time = time.time()

    def update_timer():
        while not stop_timer:
            elapsed = int(time.time() - start_time)
            mins, secs = divmod(elapsed, 60)
            timer_placeholder.info(f"⏳ **Analisando documentos... Tempo decorrido: {mins:02d}:{secs:02d}**")
            time.sleep(1)

    t = threading.Thread(target=update_timer)
    add_script_run_ctx(t)
    t.start()

    try:
        # Prepara PDFs manuais
        gemini_files = [types.Part.from_bytes(data=f.getvalue(), mime_type="application/pdf") for f in (uploaded_files or [])]

        # Prepara PDFs baixados do RIS
        for pdf_doc in st.session_state.ris_pdfs:
            gemini_files.append(types.Part.from_bytes(data=pdf_doc['bytes'], mime_type="application/pdf"))

        # Prepara Resumos do RIS
        for doc in st.session_state.ris_texts:
            gemini_files.append(types.Part.from_text(text=f"DOCUMENTO: {doc['name']}\n\n{doc['text']}"))

        prompt_text = "Leia todos os documentos anexados como um corpus único.\n\n"

        if includes_phenom(mode):
            prompt_text += (
                f"=== MODO FENOMENOLÓGICO ===\n"
                f"INTERROGAÇÃO FENOMENOLÓGICA:\n\"{phenom_q}\"\n\n"
                f"ETAPA 1: Extraia unidades de sentido (documento, página, citação literal exata, contexto e justificativa).\n"
                f"REGRAS: NÃO parafrasear a citação; NÃO inventar páginas; NÃO omitir documento.\n"
                f"ETAPA 2: Transforme cada unidade em unidade de significado.\n"
                f"ETAPA 3: Agrupe convergências.\n"
                f"ETAPA 4: Sugira categorias fenomenológicas.\n\n"
            )

        if includes_thematic(mode):
            prompt_text += "=== MODO ANÁLISE TEMÁTICA (Braun & Clarke) ===\n"
            if thematic_q.strip():
                prompt_text += f"QUESTÃO ORIENTADORA (OPCIONAL):\n\"{thematic_q}\"\n\n"
            prompt_text += (
                "Execute as fases 2–5:\n"
                "FASE 2 (Códigos iniciais): extraia códigos com TRECHO literal, documento, página, nome do código e descrição operacional.\n"
                "FASE 3–5 (Temas): agrupe códigos em temas; para cada tema: nome, descrição, lista de IDs de códigos relacionados e interpretação.\n"
                "REGRAS: Trechos devem ser literais; não inventar páginas; se página não identificável, use null.\n\n"
            )

        if includes_systematic(mode):
            prompt_text += (
                f"=== MODO MAPEAMENTO SISTEMÁTICO ===\n"
                f"Responda às perguntas abaixo para CADA documento:\n{sys_q}\n\n"
                f"REGRAS: Respostas objetivas (máx. 3 frases). Cite evidência textual literal e página.\n"
                f"Se página não puder ser identificada com certeza, retorne null.\n\n"
            )

        contents = gemini_files + [prompt_text]

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=(
                    "Você é um assistente de análise qualitativa de corpus documental. "
                    "Nunca invente conteúdo. Preserve rastreabilidade. "
                    "Se o número da página não puder ser identificado com certeza, use null. "
                    "Respeite o schema JSON estritamente."
                ),
                response_mime_type="application/json",
                response_schema=AnalysisResult,
                temperature=0.2,
            ),
        )

        st.session_state.result_data = json.loads(response.text)
        st.session_state.analysis_done = True
        st.success("✨ Análise concluída com sucesso!")

    except Exception as e:
        st.error(f"Erro durante a análise: {e}")
    finally:
        stop_timer = True
        t.join()
        timer_placeholder.empty()

# ============================================================
# RENDER RESULTADOS
# ============================================================
if st.session_state.analysis_done and st.session_state.result_data:
    result_data = st.session_state.result_data
    render_mode = st.session_state.last_mode or mode

    phenom_data = (result_data.get("fenomenologico") or {}) if includes_phenom(render_mode) else {}
    them_data = (result_data.get("tematico") or {}) if includes_thematic(render_mode) else {}
    sys_data = (result_data.get("sistematico") or {}) if includes_systematic(render_mode) else {}

    n_us = len((phenom_data or {}).get("unidades_sentido", [])) if includes_phenom(render_mode) else 0
    n_um = len((phenom_data or {}).get("unidades_significado", [])) if includes_phenom(render_mode) else 0
    n_cat = len((phenom_data or {}).get("categorias", [])) if includes_phenom(render_mode) else 0
    n_cod = len((them_data or {}).get("codigos", [])) if includes_thematic(render_mode) else 0
    n_temas = len((them_data or {}).get("temas", [])) if includes_thematic(render_mode) else 0

    tabs = []
    if includes_phenom(render_mode):
        tabs.extend([f"☰ Unidades de Sentido ({n_us})", f"📄 Unidades de Significado ({n_um})", f"🏷️ Categorias ({n_cat})"])
    if includes_thematic(render_mode):
        tabs.extend([f"🧩 Códigos ({n_cod})", f"🗂️ Temas ({n_temas})"])
    if includes_systematic(render_mode):
        tabs.append("🧭 Mapeamento")

    st_tabs = st.tabs(tabs)
    tab_idx = 0

    # ===================== Fenomenológico =====================
    if includes_phenom(render_mode):
        with st_tabs[tab_idx]:
            unidades = (phenom_data or {}).get("unidades_sentido", [])
            if not unidades:
                st.warning("Nenhuma unidade de sentido foi retornada.")
            else:
                df_us = pd.DataFrame(unidades)
                c1, c2 = st.columns([6, 1.6], vertical_alignment="center")
                with c1:
                    st.caption("ID/DOC/PÁG • Citação literal • Contexto & Justificativa")
                with c2:
                    st.download_button(
                        "Exportar CSV",
                        df_us.to_csv(index=False).encode("utf-8"),
                        "unidades_sentido.csv",
                        "text/csv",
                        use_container_width=True
                    )

                for _, r in df_us.iterrows():
                    uid, doc, pag = r.get("id_unidade", ""), r.get("documento", ""), r.get("pagina", None)
                    pag_txt = f"Pág. {pag}" if pag is not None else "Pág. null"
                    cit = r.get("citacao_literal", "")
                    ctx = (r.get("contexto_resumido", "") or "").strip()
                    jus = (r.get("justificativa_fenomenologica", "") or "").strip()
                    cj_html = ""
                    if ctx:
                        cj_html += f'<div style="font-size:12px; font-weight:bold; color:var(--muted);">CONTEXTO</div><div style="margin-bottom:10px;">{ctx}</div>'
                    if jus:
                        cj_html += f'<div style="font-size:12px; font-weight:bold; color:var(--muted);">JUSTIFICATIVA</div><div>{jus}</div>'

                    st.markdown(f"""
                        <div class="qa-shell" style="margin-bottom: 15px;">
                          <div style="display:flex; gap:10px; margin-bottom:10px;">
                            <span class="chip">{uid}</span><span class="chip">{doc}</span><span class="chip">{pag_txt}</span>
                          </div>
                          <div class="quote" style="margin-bottom:15px;">"{cit}"</div>
                          <div style="background: rgba(255,255,255,0.4); padding: 12px; border-radius: 10px;">{cj_html}</div>
                        </div>
                    """, unsafe_allow_html=True)
        tab_idx += 1

        with st_tabs[tab_idx]:
            unidades_sig = (phenom_data or {}).get("unidades_significado", [])
            if not unidades_sig:
                st.warning("Nenhuma unidade de significado foi retornada.")
            else:
                df_um = pd.DataFrame(unidades_sig)
                c1, c2 = st.columns([6, 1.6], vertical_alignment="center")
                with c1:
                    st.caption("ID/Documento • Trecho original • Síntese de significado")
                with c2:
                    st.download_button(
                        "Exportar CSV",
                        df_um.to_csv(index=False).encode("utf-8"),
                        "unidades_significado.csv",
                        "text/csv",
                        use_container_width=True
                    )

                for _, r in df_um.iterrows():
                    st.markdown(f"""
                        <div class="qa-shell" style="margin-bottom: 15px;">
                          <div style="display:flex; gap:10px; margin-bottom:10px;">
                            <span class="chip">{r.get("id_unidade", "")}</span><span class="chip">{r.get("documento", "")}</span>
                          </div>
                          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                            <div><div style="font-size:12px; font-weight:bold; color:var(--muted); margin-bottom:5px;">TRECHO ORIGINAL</div><div class="quote">"{r.get("trecho_original", "")}"</div></div>
                            <div><div style="font-size:12px; font-weight:bold; color:var(--muted); margin-bottom:5px;">SÍNTESE</div><div style="background: rgba(194,106,46,0.1); padding: 12px; border-radius: 10px; color: var(--accent2); font-weight: 600;">{r.get("sintese", "")}</div></div>
                          </div>
                        </div>
                    """, unsafe_allow_html=True)
        tab_idx += 1

        with st_tabs[tab_idx]:
            categorias = (phenom_data or {}).get("categorias", [])
            if not categorias:
                st.warning("Nenhuma categoria foi retornada.")
            else:
                df_cat = pd.DataFrame([{
                    "nome": c.get("nome"),
                    "descricao": c.get("descricao"),
                    "unidades_relacionadas": ", ".join(c.get("unidades_relacionadas", []))
                } for c in categorias])

                c1, c2 = st.columns([6, 1.6], vertical_alignment="center")
                with c1:
                    st.caption("Categorias fenomenológicas")
                with c2:
                    st.download_button(
                        "Exportar CSV",
                        df_cat.to_csv(index=False).encode("utf-8"),
                        "categorias.csv",
                        "text/csv",
                        use_container_width=True
                    )

                cols3 = st.columns(3)
                for i, c in enumerate(categorias):
                    with cols3[i % 3]:
                        rel = c.get("unidades_relacionadas", [])
                        chips_html = (
                            '<div style="display:flex; flex-wrap:wrap; gap:5px;">'
                            + "".join([f'<span class="chip" style="font-size:11px;">{u}</span>' for u in rel])
                            + "</div>"
                        ) if rel else '-'

                        st.markdown(f"""
                            <div class="qa-shell" style="height: 100%; margin-bottom: 15px;">
                              <h3 style="color: var(--accent2); margin-top:0;">{c.get("nome", "")}</h3>
                              <p style="font-size: 14px;">{c.get("descricao", "")}</p>
                              <div style="font-size:11px; font-weight:bold; color:var(--muted); margin-bottom:5px; margin-top:15px;">UNIDADES RELACIONADAS</div>
                              {chips_html}
                            </div>
                        """, unsafe_allow_html=True)
        tab_idx += 1

    # ===================== Temática =====================
    if includes_thematic(render_mode):
        with st_tabs[tab_idx]:
            codigos = (them_data or {}).get("codigos", [])
            if not codigos:
                st.warning("Nenhum código foi retornado.")
            else:
                df_cod = pd.DataFrame(codigos)
                c1, c2 = st.columns([6, 1.6], vertical_alignment="center")
                with c1:
                    st.caption("ID/DOC/PÁG • Trecho literal • Código & definição")
                with c2:
                    st.download_button(
                        "Exportar CSV",
                        df_cod.to_csv(index=False).encode("utf-8"),
                        "codigos.csv",
                        "text/csv",
                        use_container_width=True
                    )

                for _, r in df_cod.iterrows():
                    pag = r.get("pagina", None)
                    pag_txt = f"Pág. {pag}" if pag is not None else "Pág. null"
                    st.markdown(f"""
                        <div class="qa-shell" style="margin-bottom: 15px;">
                          <div style="display:flex; gap:10px; margin-bottom:10px;">
                            <span class="chip">{r.get("id_codigo", "")}</span><span class="chip">{r.get("documento", "")}</span><span class="chip">{pag_txt}</span>
                          </div>
                          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                            <div><div style="font-size:12px; font-weight:bold; color:var(--muted); margin-bottom:5px;">TRECHO LITERAL</div><div class="quote">"{r.get("trecho", "")}"</div></div>
                            <div style="background: rgba(255,255,255,0.4); padding: 12px; border-radius: 10px;">
                              <div style="font-size:12px; font-weight:bold; color:var(--muted);">CÓDIGO</div><div style="font-weight:bold; color:var(--accent2); margin-bottom:10px;">{r.get("codigo", "")}</div>
                              <div style="font-size:12px; font-weight:bold; color:var(--muted);">DEFINIÇÃO</div><div>{r.get("descricao_codigo", "")}</div>
                            </div>
                          </div>
                        </div>
                    """, unsafe_allow_html=True)
        tab_idx += 1

        with st_tabs[tab_idx]:
            temas = (them_data or {}).get("temas", [])
            if not temas:
                st.warning("Nenhum tema foi retornado.")
            else:
                df_temas = pd.DataFrame([{
                    "nome": t.get("nome"),
                    "descricao": t.get("descricao"),
                    "interpretacao": t.get("interpretacao"),
                    "codigos_relacionados": ", ".join(t.get("codigos_relacionados", []))
                } for t in temas])

                c1, c2 = st.columns([6, 1.6], vertical_alignment="center")
                with c1:
                    st.caption("Temas (cards)")
                with c2:
                    st.download_button(
                        "Exportar CSV",
                        df_temas.to_csv(index=False).encode("utf-8"),
                        "temas.csv",
                        "text/csv",
                        use_container_width=True
                    )

                cols2 = st.columns(2)
                for i, t in enumerate(temas):
                    with cols2[i % 2]:
                        rel = t.get("codigos_relacionados", [])
                        chips_html = (
                            '<div style="display:flex; flex-wrap:wrap; gap:5px;">'
                            + "".join([f'<span class="chip" style="font-size:11px;">{u}</span>' for u in rel])
                            + "</div>"
                        ) if rel else '-'

                        st.markdown(f"""
                            <div class="qa-shell" style="height: 100%; margin-bottom: 15px;">
                              <h3 style="color: var(--accent2); margin-top:0;">{t.get("nome", "")}</h3>
                              <p>{t.get("descricao", "")}</p>
                              <div style="background: rgba(255,255,255,0.5); padding: 10px; border-radius: 8px; margin-bottom: 15px;">
                                <div style="font-size:11px; font-weight:bold; color:var(--muted); margin-bottom:3px;">INTERPRETAÇÃO</div>
                                <div style="font-size:14px;">{t.get("interpretacao", "")}</div>
                              </div>
                              <div style="font-size:11px; font-weight:bold; color:var(--muted); margin-bottom:5px;">CÓDIGOS RELACIONADOS</div>
                              {chips_html}
                            </div>
                        """, unsafe_allow_html=True)
        tab_idx += 1

    # ===================== Mapeamento (NOVO: pivot + sticky) =====================
    if includes_systematic(render_mode):
        with st_tabs[tab_idx]:
            docs = (sys_data or {}).get("documentos", [])
            if not docs:
                st.warning("O mapeamento sistemático não foi retornado.")
            else:
                rows_long = []
                for doc in docs:
                    for ans in doc.get("respostas", []):
                        rows_long.append({
                            "Documento": doc.get("documento"),
                            "Pergunta": ans.get("pergunta"),
                            "Resposta": ans.get("resposta"),
                            "Evidência": ans.get("evidencia_textual"),
                            "Página": ans.get("pagina"),
                        })
                df_long = pd.DataFrame(rows_long)

                # Export long (rastreabilidade)
                st.download_button(
                    "Exportar CSV (long)",
                    df_long.to_csv(index=False).encode("utf-8"),
                    "mapeamento_long.csv",
                    "text/csv",
                    use_container_width=True
                )

                # Pivot
                pivot_df = build_sys_pivot_table(df_long)

                # Export pivot
                st.download_button(
                    "Exportar CSV (pivot)",
                    pivot_df.to_csv(index=False).encode("utf-8"),
                    "mapeamento_pivot.csv",
                    "text/csv",
                    use_container_width=True
                )

                # Opções de visualização
                c1, c2, c3 = st.columns([1.2, 1.2, 2.6], vertical_alignment="center")
                with c1:
                    height = st.slider("Altura", 360, 900, 560, 20)
                with c2:
                    max_docs = st.number_input("Máx. docs na tela", min_value=5, max_value=500, value=150, step=5)
                with c3:
                    filtro = st.text_input("Filtrar documentos (contém)", placeholder="Ex: Silva, 2022 / título / DOI...")

                view_df = pivot_df.copy()
                if filtro.strip():
                    view_df = view_df[view_df["Documento"].astype(str).str.contains(filtro.strip(), case=False, na=False)]
                view_df = view_df.head(int(max_docs))

                st.markdown(
                    f"<div class='qa-shell' style='margin: 14px 0;'><b>Documentos:</b> {len(view_df)} &nbsp;•&nbsp; <b>Perguntas:</b> {len(view_df.columns)-1}</div>",
                    unsafe_allow_html=True
                )

                # Render
                render_sticky_table(view_df, height_px=int(height))
