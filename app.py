import streamlit as st
import pandas as pd
import json
import os
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
    initial_sidebar_state="collapsed",
)

# ============================================================
# IDENTIDADE VISUAL (PALETA + FONTES)
# ============================================================
st.markdown(
    """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Josefin+Sans:wght@400;600;700&family=Open+Sans:wght@300;400;600;700&family=Roboto:wght@300;400;500;700&family=Work+Sans:wght@400;600;700&display=swap" rel="stylesheet">

<style>
  :root{
    --brown:#5E412F;
    --cream:#FCEBB6;
    --mint:#78C0A8;
    --orange:#F07818;
    --gold:#F0A830;

    --text:#111827;
    --muted:#6b7280;
    --line:#e5e7eb;
    --line2:#eef2f7;
    --panel:#ffffff;
    --shadow: 0 10px 25px rgba(17,24,39,0.06);
    --shadow2: 0 2px 10px rgba(17,24,39,0.05);
    --radius: 18px;
  }

  /* ====== FUNDO GERAL ====== */
  html, body { background: var(--cream) !important; }
  .stApp { background: var(--cream) !important; color: var(--text) !important; }
  * { font-family: "Open Sans", system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; }

  /* ====== REMOVE TOPO DEFAULT / AJUSTA CONTAINER ====== */
  section.main > div { padding-top: 24px !important; }
  .block-container { max-width: 1320px; padding-top: 16px; padding-bottom: 40px; }

  /* ====== PAINEL PRINCIPAL (CARD GIGANTE) ====== */
  .qa-shell{
    background: var(--panel);
    border: 1px solid rgba(17,24,39,0.06);
    border-radius: calc(var(--radius) + 6px);
    box-shadow: var(--shadow);
    padding: 26px 26px 18px 26px;
  }

  /* ====== CABEÇALHO ====== */
  .qa-title{
    font-family: "Josefin Sans", sans-serif;
    font-weight: 700;
    font-size: 44px;
    line-height: 1.05;
    color: var(--brown);
    letter-spacing: -0.02em;
    margin: 0 0 10px 0;
  }
  .qa-subtitle{
    color: var(--muted);
    font-size: 15px;
    margin: 0 0 18px 0;
  }
  .qa-badge{
    display:inline-flex;
    gap:10px;
    align-items:center;
    border: 1px solid rgba(17,24,39,0.08);
    background: rgba(120,192,168,0.16);
    color: var(--brown);
    padding: 8px 12px;
    border-radius: 999px;
    font-weight: 700;
    font-family: "Work Sans", sans-serif;
    font-size: 12px;
  }

  /* ====== INPUTS ====== */
  textarea, input, .stTextInput > div > div > input {
    background: #fff !important;
    color: var(--text) !important;
    border-radius: 14px !important;
    border: 1px solid rgba(17,24,39,0.10) !important;
  }
  textarea:focus, input:focus {
    border-color: rgba(240,120,24,0.55) !important;
    box-shadow: 0 0 0 4px rgba(240,120,24,0.12) !important;
  }

  /* ====== RADIO ====== */
  .stRadio label {
    font-family: "Work Sans", sans-serif !important;
    font-weight: 600 !important;
    color: var(--text) !important;
  }

  /* ====== FILE UPLOADER ====== */
  [data-testid="stFileUploader"]{
    border-radius: var(--radius) !important;
    border: 1px dashed rgba(17,24,39,0.18) !important;
    background: rgba(252,235,182,0.35) !important;
    padding: 14px !important;
  }

  /* ====== BOTÃO PRINCIPAL ====== */
  .stButton > button {
    background: linear-gradient(135deg, var(--orange), var(--gold)) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 14px !important;
    padding: 12px 18px !important;
    font-family: "Work Sans", sans-serif !important;
    font-weight: 800 !important;
    letter-spacing: .01em !important;
    box-shadow: 0 12px 18px rgba(240,120,24,0.18) !important;
    transition: transform .08s ease, box-shadow .12s ease;
  }
  .stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 16px 22px rgba(240,120,24,0.22) !important;
  }
  .stButton > button:disabled { opacity: 0.55 !important; }

  /* ====== DOWNLOAD BUTTON ====== */
  div[data-testid="stDownloadButton"] > button {
    border: 1px solid rgba(17,24,39,0.10) !important;
    background: #fff !important;
    color: var(--brown) !important;
    border-radius: 14px !important;
    padding: 10px 14px !important;
    font-weight: 800 !important;
    font-family: "Work Sans", sans-serif !important;
    box-shadow: var(--shadow2) !important;
  }
  div[data-testid="stDownloadButton"] > button:hover {
    border-color: rgba(240,120,24,0.35) !important;
    box-shadow: 0 10px 20px rgba(17,24,39,0.08) !important;
  }

  /* ====== TABS ====== */
  button[data-baseweb="tab"]{
    font-family: "Work Sans", sans-serif !important;
    font-weight: 800 !important;
    color: var(--muted) !important;
  }
  button[data-baseweb="tab"][aria-selected="true"]{
    color: var(--brown) !important;
  }
  div[data-baseweb="tab-highlight"]{
    background: linear-gradient(90deg, var(--orange), var(--gold)) !important;
    height: 3px !important;
    border-radius: 999px !important;
  }

  /* ====== SCROLLBOX + STICKY HEADER ====== */
  .scrollbox{
    max-height: 72vh;
    overflow-y: auto;
    padding-right: 10px;
  }
  .sticky-header{
    position: sticky;
    top: 0;
    z-index: 50;
    background: var(--panel);
    padding-top: 6px;
  }

  /* ====== GRID “QUADRO” ====== */
  .grid-header{
    display:grid;
    grid-template-columns: 220px 1.25fr 1.1fr;
    gap: 18px;
    padding: 14px 0 10px 0;
    border-bottom: 1px solid var(--line);
  }
  .grid-header .h{
    font-weight: 900;
    font-size: 12px;
    letter-spacing: .10em;
    color: var(--muted);
    text-transform: uppercase;
    font-family: "Work Sans", sans-serif;
  }
  .grid-row{
    display:grid;
    grid-template-columns: 220px 1.25fr 1.1fr;
    gap: 18px;
    padding: 18px 0;
    border-bottom: 1px solid var(--line2);
  }

  .idblock{
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-weight: 800;
    color: var(--brown);
    margin-bottom: 6px;
    word-break: break-word;
  }
  .docblock{
    color: var(--text);
    font-weight: 700;
    margin-bottom: 6px;
    word-break: break-word;
  }
  .pagblock{ color: var(--muted); font-size: 12px; }

  .quote{
    font-style: italic;
    color: var(--text);
    line-height: 1.62;
    white-space: pre-wrap;
    border-left: 4px solid rgba(120,192,168,0.95);
    padding-left: 12px;
  }

  .cj-title{
    font-weight: 900;
    font-size: 12px;
    letter-spacing: .08em;
    color: var(--muted);
    text-transform: uppercase;
    margin-top: 4px;
    margin-bottom: 6px;
    font-family: "Work Sans", sans-serif;
  }
  .cj-text{ color: var(--text); line-height: 1.62; white-space: pre-wrap; }

  .synth-card{
    background: rgba(252,235,182,0.30);
    border: 1px solid rgba(17,24,39,0.06);
    padding: 16px;
    border-radius: 16px;
    font-weight: 700;
    color: var(--text);
    line-height: 1.6;
    white-space: pre-wrap;
  }

  /* ====== CARDS (Categorias / Temas) ====== */
  .cat-grid{ display:grid; grid-template-columns: 1fr 1fr; gap: 18px; }
  .cat-card{
    border: 1px solid rgba(17,24,39,0.08);
    border-radius: 20px;
    padding: 18px;
    background: var(--panel);
    box-shadow: var(--shadow2);
  }
  .cat-title{
    font-family: "Josefin Sans", sans-serif;
    font-weight: 800;
    font-size: 28px;
    line-height: 1.15;
    margin: 0 0 10px 0;
    color: var(--brown);
  }
  .cat-desc{
    color: var(--text);
    line-height: 1.65;
    margin-bottom: 14px;
    white-space: pre-wrap;
  }
  .cat-sub{
    font-weight: 900;
    font-size: 12px;
    letter-spacing: .10em;
    color: var(--muted);
    text-transform: uppercase;
    margin-bottom: 10px;
    font-family: "Work Sans", sans-serif;
  }
  .chips{ display:flex; flex-wrap: wrap; gap: 10px; }
  .chip{
    border: 1px solid rgba(17,24,39,0.08);
    border-radius: 12px;
    padding: 6px 10px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
    font-size: 13px;
    color: var(--brown);
    background: rgba(120,192,168,0.18);
  }

  .muted{ color: #9ca3af; font-size: 13px; }

  /* ====== SCROLLBAR ====== */
  ::-webkit-scrollbar { width: 10px; }
  ::-webkit-scrollbar-thumb { background: rgba(120,192,168,0.9); border-radius: 999px; }
  ::-webkit-scrollbar-track { background: rgba(17,24,39,0.04); }

  /* Responsivo */
  @media (max-width: 1100px){
    .grid-header, .grid-row{ grid-template-columns: 1fr; }
    .cat-grid{ grid-template-columns: 1fr; }
    .qa-title{ font-size: 36px; }
  }
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# SESSION STATE
# ============================================================
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False
if "result_data" not in st.session_state:
    st.session_state.result_data = None
if "df_sys_long" not in st.session_state:
    st.session_state.df_sys_long = None
if "last_mode" not in st.session_state:
    st.session_state.last_mode = None
if "cross_synthesis" not in st.session_state:
    st.session_state.cross_synthesis = {}
if "cross_synthesis_mode_tag" not in st.session_state:
    st.session_state.cross_synthesis_mode_tag = None

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


# ===== Temática (Braun & Clarke) =====
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


# ===== Mapeamento =====
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


# ===== Agregado =====
class AnalysisResult(BaseModel):
    fenomenologico: PhenomenologicalResult | None = None
    tematico: ThematicResult | None = None
    sistematico: SystematicResult | None = None


# ============================================================
# FUNÇÃO: SÍNTESE TRANSVERSAL POR PERGUNTA (sem reprocessar PDFs)
# ============================================================
def gerar_sintese_transversal(pergunta: str, df_sub: pd.DataFrame) -> str:
    linhas = []
    for _, r in df_sub.iterrows():
        doc = str(r.get("Documento", "")).strip()
        resp = str(r.get("Resposta", "")).strip()
        evid = str(r.get("Evidência", "")).strip()
        pag = r.get("Página", None)
        pag_str = f"{pag}" if (pag is not None and str(pag).strip() != "") else "null"
        linhas.append(
            f"- DOCUMENTO: {doc}\n"
            f"  RESPOSTA: {resp}\n"
            f"  EVIDÊNCIA: \"{evid}\"\n"
            f"  PÁGINA: {pag_str}\n"
        )

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

REGRAS:
- Não invente informação.
- Não cite nada que não esteja nas respostas/evidências.
- Se houver contradição, explicite como divergência.
"""
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt],
        config=types.GenerateContentConfig(temperature=0.2),
    )
    return resp.text


# ============================================================
# HELPERS: modo -> quais análises incluir
# ============================================================
def includes_phenom(m: str) -> bool:
    return m in ["Fenomenológico", "Fenomenológico + Mapeamento", "Todos (3 modos)"]


def includes_thematic(m: str) -> bool:
    return m in ["Temático (Braun & Clarke)", "Temático + Mapeamento", "Todos (3 modos)"]


def includes_systematic(m: str) -> bool:
    return m in [
        "Mapeamento Sistemático",
        "Fenomenológico + Mapeamento",
        "Temático + Mapeamento",
        "Todos (3 modos)",
    ]


# ============================================================
# UI — CABEÇALHO PROFISSIONAL
# ============================================================
st.markdown(
    """
<div class="qa-shell">
  <div style="display:flex; justify-content:space-between; gap:14px; align-items:flex-start; flex-wrap:wrap;">
    <div>
      <div class="qa-title">📖 Análise Qualitativa AI</div>
      <div class="qa-subtitle">Fenomenológica • Temática (Braun & Clarke) • Mapeamento • Rastreamento por documento/página • Export CSV</div>
    </div>
    <div class="qa-badge">Identidade visual • Paleta + Tipografia</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

st.write("")  # espaçamento

# ============================================================
# CONTROLES
# ============================================================
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
    horizontal=False,
)

phenom_q = ""
thematic_q = ""
sys_q = ""

if includes_phenom(mode):
    phenom_q = st.text_area(
        "Interrogação Fenomenológica",
        placeholder="Ex: Como o fenômeno X se constitui nos textos analisados?",
        height=110,
    )

if includes_thematic(mode):
    thematic_q = st.text_area(
        "Questão orientadora (Análise Temática – opcional)",
        placeholder="Ex: Quais padrões se repetem sobre métodos, ferramentas, objetivos e resultados?",
        height=90,
    )

if includes_systematic(mode):
    sys_q = st.text_area(
        "Perguntas para Mapeamento Sistemático (1 por linha)",
        placeholder="1. Qual é o objetivo do estudo?\n2. Qual metodologia é utilizada?\n3. Quais softwares foram utilizados?",
        height=150,
    )

uploaded_files = st.file_uploader("Corpus Documental (PDFs)", type="pdf", accept_multiple_files=True)

run = st.button("Iniciar Análise do Corpus", type="primary", disabled=not uploaded_files)

# ============================================================
# EXECUTAR ANÁLISE
# ============================================================
if run:
    st.session_state.analysis_done = False
    st.session_state.result_data = None
    st.session_state.df_sys_long = None
    st.session_state.last_mode = mode
    st.session_state.cross_synthesis = {}
    st.session_state.cross_synthesis_mode_tag = None

    if includes_phenom(mode) and not phenom_q.strip():
        st.warning("Por favor, preencha a Interrogação Fenomenológica.")
        st.stop()

    if includes_systematic(mode) and not sys_q.strip():
        st.warning("Por favor, preencha as Perguntas para Mapeamento Sistemático.")
        st.stop()

    total_size = sum([f.size for f in uploaded_files])
    if total_size > 15 * 1024 * 1024:
        st.error(f"O tamanho total ({total_size / 1024 / 1024:.2f} MB) excede 15 MB. Reduza a quantidade de PDFs.")
        st.stop()

    with st.spinner("Analisando o corpus documental..."):
        try:
            gemini_files = [
                types.Part.from_bytes(data=f.getvalue(), mime_type="application/pdf")
                for f in uploaded_files
            ]

            prompt_text = "Leia todos os PDFs anexados como um corpus único.\n\n"

            if includes_phenom(mode):
                prompt_text += "=== MODO FENOMENOLÓGICO ===\n"
                prompt_text += f"INTERROGAÇÃO FENOMENOLÓGICA:\n\"{phenom_q}\"\n\n"
                prompt_text += (
                    "ETAPA 1: Extraia unidades de sentido (documento, página, citação literal exata, contexto e justificativa).\n"
                    "REGRAS: NÃO parafrasear a citação; NÃO inventar páginas; NÃO omitir documento.\n"
                    "ETAPA 2: Transforme cada unidade em unidade de significado.\n"
                    "ETAPA 3: Agrupe convergências.\n"
                    "ETAPA 4: Sugira categorias fenomenológicas.\n\n"
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
                prompt_text += "=== MODO MAPEAMENTO SISTEMÁTICO ===\n"
                prompt_text += "Responda às perguntas abaixo para CADA documento:\n"
                prompt_text += f"{sys_q}\n\n"
                prompt_text += (
                    "REGRAS: Respostas objetivas (máx. 3 frases). Cite evidência textual literal e página.\n"
                    "Se página não puder ser identificada com certeza, retorne null.\n\n"
                )

            contents = gemini_files + [prompt_text]

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=(
                        "Você é um assistente de análise qualitativa de corpus documental.\n"
                        "Nunca invente conteúdo. Preserve rastreabilidade.\n"
                        "Se o número da página não puder ser identificado com certeza, use null.\n"
                        "Respeite o schema JSON estritamente."
                    ),
                    response_mime_type="application/json",
                    response_schema=AnalysisResult,
                    temperature=0.2,
                ),
            )

            st.session_state.result_data = json.loads(response.text)
            st.session_state.analysis_done = True
            st.session_state.cross_synthesis_mode_tag = f"{mode}|{len(uploaded_files)}|{total_size}"
            st.success("Análise concluída com sucesso!")

        except Exception as e:
            if "exceeds the maximum number of tokens allowed" in str(e):
                st.error("O corpus excede o limite de tokens. Reduza a quantidade de PDFs.")
            else:
                st.error(f"Erro durante a análise: {e}")

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

    st.markdown(
        """
<div class="qa-shell" style="padding:18px 22px;">
  <div class="qa-badge">Resultados prontos — exporte CSV em cada aba</div>
</div>
""",
        unsafe_allow_html=True,
    )

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
        # Unidades de Sentido
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
                        use_container_width=True,
                    )

                st.markdown(
                    """
                    <div class="scrollbox">
                      <div class="sticky-header">
                        <div class="grid-header">
                          <div class="h">ID / DOC / PÁG</div>
                          <div class="h">CITAÇÃO LITERAL</div>
                          <div class="h">CONTEXTO &amp; JUSTIFICATIVA</div>
                        </div>
                      </div>
                    """,
                    unsafe_allow_html=True,
                )

                for _, r in df_us.iterrows():
                    uid = r.get("id_unidade", "")
                    doc = r.get("documento", "")
                    pag = r.get("pagina", None)
                    pag_txt = f"Pág. {pag}" if (pag is not None and str(pag).strip() != "") else "Pág. null"
                    cit = r.get("citacao_literal", "")
                    ctx = (r.get("contexto_resumido", "") or "").strip()
                    jus = (r.get("justificativa_fenomenologica", "") or "").strip()

                    cj_html = ""
                    if ctx:
                        cj_html += f'<div class="cj-title">CONTEXTO</div><div class="cj-text">{ctx}</div><br/>'
                    if jus:
                        cj_html += f'<div class="cj-title">JUSTIFICATIVA</div><div class="cj-text">{jus}</div>'
                    if not cj_html:
                        cj_html = '<div class="muted">-</div>'

                    st.markdown(
                        f"""
                        <div class="grid-row">
                          <div>
                            <div class="idblock">{uid}</div>
                            <div class="docblock">{doc}</div>
                            <div class="pagblock">{pag_txt}</div>
                          </div>
                          <div class="quote">"{cit}"</div>
                          <div>{cj_html}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                st.markdown("</div>", unsafe_allow_html=True)
        tab_idx += 1

        # Unidades de Significado
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
                        use_container_width=True,
                    )

                st.markdown(
                    """
                    <div class="scrollbox">
                      <div class="sticky-header">
                        <div class="grid-header">
                          <div class="h">ID / DOCUMENTO</div>
                          <div class="h">TRECHO ORIGINAL</div>
                          <div class="h">SÍNTESE</div>
                        </div>
                      </div>
                    """,
                    unsafe_allow_html=True,
                )

                for _, r in df_um.iterrows():
                    uid = r.get("id_unidade", "")
                    doc = r.get("documento", "")
                    tre = r.get("trecho_original", "")
                    syn = r.get("sintese", "")
                    st.markdown(
                        f"""
                        <div class="grid-row">
                          <div>
                            <div class="idblock">{uid}</div>
                            <div class="docblock">{doc}</div>
                          </div>
                          <div class="quote">"{tre}"</div>
                          <div class="synth-card">{syn}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                st.markdown("</div>", unsafe_allow_html=True)
        tab_idx += 1

        # Categorias
        with st_tabs[tab_idx]:
            categorias = (phenom_data or {}).get("categorias", [])
            if not categorias:
                st.warning("Nenhuma categoria foi retornada.")
            else:
                df_cat = pd.DataFrame(
                    [
                        {
                            "nome": c.get("nome"),
                            "descricao": c.get("descricao"),
                            "unidades_relacionadas": ", ".join(c.get("unidades_relacionadas", [])),
                        }
                        for c in categorias
                    ]
                )

                c1, c2 = st.columns([6, 1.6], vertical_alignment="center")
                with c1:
                    st.caption("Categorias fenomenológicas (cards)")
                with c2:
                    st.download_button(
                        "Exportar CSV",
                        df_cat.to_csv(index=False).encode("utf-8"),
                        "categorias.csv",
                        "text/csv",
                        use_container_width=True,
                    )

                st.markdown('<div class="cat-grid">', unsafe_allow_html=True)
                for c in categorias:
                    nome = c.get("nome", "(sem nome)")
                    desc = c.get("descricao", "")
                    rel = c.get("unidades_relacionadas", [])
                    chips_html = (
                        '<div class="chips">' + "".join([f'<span class="chip">{u}</span>' for u in rel]) + "</div>"
                        if rel
                        else '<div class="muted">-</div>'
                    )
                    st.markdown(
                        f"""
                        <div class="cat-card">
                          <div class="cat-title">{nome}</div>
                          <div class="cat-desc">{desc}</div>
                          <div class="cat-sub">UNIDADES RELACIONADAS</div>
                          {chips_html}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                st.markdown("</div>", unsafe_allow_html=True)
        tab_idx += 1

    # ===================== Temática (Braun & Clarke) =====================
    if includes_thematic(render_mode):
        # Códigos
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
                        "codigos_tematicos.csv",
                        "text/csv",
                        use_container_width=True,
                    )

                st.markdown(
                    """
                    <div class="scrollbox">
                      <div class="sticky-header">
                        <div class="grid-header">
                          <div class="h">ID / DOC / PÁG</div>
                          <div class="h">TRECHO LITERAL</div>
                          <div class="h">CÓDIGO &amp; DEFINIÇÃO</div>
                        </div>
                      </div>
                    """,
                    unsafe_allow_html=True,
                )

                for _, r in df_cod.iterrows():
                    cid = r.get("id_codigo", "")
                    doc = r.get("documento", "")
                    pag = r.get("pagina", None)
                    pag_txt = f"Pág. {pag}" if (pag is not None and str(pag).strip() != "") else "Pág. null"
                    trecho = r.get("trecho", "")
                    codigo = r.get("codigo", "")
                    desc = r.get("descricao_codigo", "")

                    cj_html = (
                        f'<div class="cj-title">CÓDIGO</div><div class="cj-text">{codigo}</div><br/>'
                        f'<div class="cj-title">DEFINIÇÃO</div><div class="cj-text">{desc}</div>'
                        if (codigo or desc)
                        else '<div class="muted">-</div>'
                    )

                    st.markdown(
                        f"""
                        <div class="grid-row">
                          <div>
                            <div class="idblock">{cid}</div>
                            <div class="docblock">{doc}</div>
                            <div class="pagblock">{pag_txt}</div>
                          </div>
                          <div class="quote">"{trecho}"</div>
                          <div>{cj_html}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                st.markdown("</div>", unsafe_allow_html=True)
        tab_idx += 1

        # Temas
        with st_tabs[tab_idx]:
            temas = (them_data or {}).get("temas", [])
            if not temas:
                st.warning("Nenhum tema foi retornado.")
            else:
                df_temas = pd.DataFrame(
                    [
                        {
                            "nome": t.get("nome"),
                            "descricao": t.get("descricao"),
                            "interpretacao": t.get("interpretacao"),
                            "codigos_relacionados": ", ".join(t.get("codigos_relacionados", [])),
                        }
                        for t in temas
                    ]
                )

                c1, c2 = st.columns([6, 1.6], vertical_alignment="center")
                with c1:
                    st.caption("Temas (cards) • descrição • interpretação • códigos relacionados")
                with c2:
                    st.download_button(
                        "Exportar CSV",
                        df_temas.to_csv(index=False).encode("utf-8"),
                        "temas_tematicos.csv",
                        "text/csv",
                        use_container_width=True,
                    )

                st.markdown('<div class="cat-grid">', unsafe_allow_html=True)
                for t in temas:
                    nome = t.get("nome", "(sem nome)")
                    desc = t.get("descricao", "")
                    interp = t.get("interpretacao", "")
                    rel = t.get("codigos_relacionados", [])

                    chips_html = (
                        '<div class="chips">' + "".join([f'<span class="chip">{u}</span>' for u in rel]) + "</div>"
                        if rel
                        else '<div class="muted">-</div>'
                    )

                    st.markdown(
                        f"""
                        <div class="cat-card">
                          <div class="cat-title">{nome}</div>
                          <div class="cat-desc">{desc}</div>
                          <div class="cat-sub">INTERPRETAÇÃO</div>
                          <div class="cat-desc">{interp}</div>
                          <div class="cat-sub">CÓDIGOS RELACIONADOS</div>
                          {chips_html}
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                st.markdown("</div>", unsafe_allow_html=True)
        tab_idx += 1

    # ===================== Mapeamento Sistemático =====================
    if includes_systematic(render_mode):
        with st_tabs[tab_idx]:
            docs = (sys_data or {}).get("documentos", [])
            if not docs:
                st.warning("O mapeamento sistemático não foi retornado.")
            else:
                rows_long = []
                for doc in docs:
                    for ans in doc.get("respostas", []):
                        rows_long.append(
                            {
                                "Documento": doc.get("documento"),
                                "Pergunta": ans.get("pergunta"),
                                "Resposta": ans.get("resposta"),
                                "Evidência": ans.get("evidencia_textual"),
                                "Página": ans.get("pagina"),
                            }
                        )
                df_long = pd.DataFrame(rows_long)
                st.session_state.df_sys_long = df_long

                st.download_button(
                    "Exportar CSV",
                    df_long.to_csv(index=False).encode("utf-8"),
                    "mapeamento_sistematico.csv",
                    "text/csv",
                )
                st.caption("Comparação por pergunta + síntese transversal (usa apenas respostas já extraídas).")

                perguntas = df_long["Pergunta"].dropna().unique().tolist()
                st.subheader("Comparação transversal (por pergunta)")

                for pergunta in perguntas:
                    sub = df_long[df_long["Pergunta"] == pergunta].copy()

                    with st.expander(f"🔎 {pergunta}", expanded=False):
                        st.dataframe(
                            sub[["Documento", "Resposta", "Página", "Evidência"]],
                            use_container_width=True,
                            height=260,
                            column_config={
                                "Documento": st.column_config.TextColumn("Documento", width="medium"),
                                "Resposta": st.column_config.TextColumn("Resposta", width="large"),
                                "Página": st.column_config.TextColumn("Página", width="small"),
                                "Evidência": st.column_config.TextColumn("Evidência", width="large"),
                            },
                        )

                        colA, _ = st.columns([1.4, 3.6])
                        with colA:
                            if st.button("Gerar síntese transversal", key=f"sintese_{hash(pergunta)}"):
                                with st.spinner("Gerando síntese (sem reprocessar PDFs)..."):
                                    texto = gerar_sintese_transversal(pergunta, sub)
                                    st.session_state.cross_synthesis[pergunta] = texto

                        if pergunta in st.session_state.cross_synthesis:
                            st.markdown("### Síntese transversal")
                            st.write(st.session_state.cross_synthesis[pergunta])

                        st.markdown("### Evidências por documento")
                        for _, r in sub.iterrows():
                            doc = str(r.get("Documento", "(sem doc)"))
                            resp = str(r.get("Resposta", "")).strip()
                            evid = str(r.get("Evidência", "")).strip()
                            pag = r.get("Página", None)
                            pag_txt = f"PÁG. {pag}" if (pag is not None and str(pag).strip() != "") else "PÁG. null"

                            st.markdown(
                                f"""
                                <div class="grid-row" style="grid-template-columns: 220px 1.25fr 1.1fr;">
                                  <div>
                                    <div class="docblock">{doc}</div>
                                    <div class="pagblock">{pag_txt}</div>
                                  </div>
                                  <div class="synth-card">{resp}</div>
                                  <div class="quote">"{evid}"</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
