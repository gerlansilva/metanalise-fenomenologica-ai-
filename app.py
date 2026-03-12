import streamlit as st
import pandas as pd
import json
import os
import time
import threading
import requests
import io, csv
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
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# IDENTIDADE VISUAL (DESIGN DOPAMINA)
# ============================================================
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Josefin+Sans:wght@400;700;900&family=Nunito:wght@400;600;700;800&display=swap" rel="stylesheet">

<style>
:root{
  /* Fundo super claro e limpo para as cores brilharem */
  --bg: #F4F7FE; 
  /* Painéis brancos para contraste */
  --panel: #FFFFFF;
  --panel2: #E8EEF2;
  --line: #E2E8F0;
  /* Texto escuro com um tom de azul para ficar mais suave que o preto */
  --text: #1E293B;
  --muted: #64748B;
  
  /* CORES DOPAMINA */
  --accent: #FF007F; /* Rosa Choque Vibrante */
  --accent2: #FF8C00; /* Laranja Energético */
  --moss: #00E5FF; /* Ciano Elétrico (para destaques secundários) */
  --purple: #8A2BE2; /* Roxo para as tags */
  
  /* Sombras coloridas e suaves */
  --shadow: 0 10px 30px rgba(255, 0, 127, 0.08);
  --shadow2: 0 4px 15px rgba(0, 0, 0, 0.05);
  --radius: 24px; /* Bordas bem redondinhas */
}

/* Alterando a fonte global para Nunito */
html, body { background: var(--bg) !important; }
.stApp { background: var(--bg) !important; color: var(--text) !important; }
* { font-family: "Nunito", system-ui, -apple-system, sans-serif; }

.block-container { max-width: 1320px; padding-top: 28px; padding-bottom: 32px; }

/* Título com Gradiente Vibrante */
.qa-title-center{
  font-family: "Josefin Sans", sans-serif;
  font-weight: 900;
  font-size: 54px;
  letter-spacing: -0.02em;
  text-align: center;
  margin: 0 0 6px 0;
  background: -webkit-linear-gradient(45deg, var(--accent), var(--accent2));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  filter: drop-shadow(0px 4px 6px rgba(255,0,127,0.15));
}
.qa-subtitle-center {
  text-align: center;
  color: var(--muted);
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 35px;
}

/* Caixas de conteúdo (Shells) brancas flutuantes */
.qa-shell{
  background: var(--panel);
  border: none;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 24px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.qa-shell:hover {
  transform: translateY(-2px);
  box-shadow: 0 15px 35px rgba(255, 0, 127, 0.12);
}

/* Inputs e Textareas mais "fofos" */
textarea, input, .stTextInput > div > div > input {
  background: var(--panel2) !important;
  color: var(--text) !important;
  border-radius: 16px !important;
  border: 2px solid transparent !important;
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.02) !important;
  transition: all 0.3s ease;
}
textarea:focus, input:focus {
  border-color: var(--moss) !important;
  box-shadow: 0 0 0 4px rgba(0, 229, 255, 0.2) !important;
  background: #FFFFFF !important;
}

.stRadio label, .stMarkdown, label, p, span, div { color: var(--text); }
.stRadio [data-testid="stMarkdownContainer"] p { color: var(--text) !important; font-weight: 600; }

[data-testid="stFileUploader"]{
  border-radius: var(--radius) !important;
  border: 2px dashed var(--moss) !important;
  background: rgba(0, 229, 255, 0.05) !important;
}

/* BOTÃO PRINCIPAL (A injeção de dopamina!) */
.stButton > button {
  background: linear-gradient(45deg, var(--accent), var(--accent2)) !important;
  color: #fff !important;
  border: none !important;
  border-radius: 30px !important;
  padding: 14px 24px !important;
  font-weight: 800 !important;
  font-size: 16px !important;
  box-shadow: 0 10px 20px rgba(255, 0, 127, 0.3) !important;
  width: 100%;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}
.stButton > button:hover { 
  transform: translateY(-3px) scale(1.02); 
  box-shadow: 0 15px 25px rgba(255, 140, 0, 0.4) !important; 
}

/* Download botão padrão */
div[data-testid="stDownloadButton"] > button {
  background: #FFFFFF !important;
  color: var(--accent) !important;
  border: 2px solid var(--accent) !important;
  border-radius: 24px !important;
  font-weight: 800 !important;
  box-shadow: var(--shadow2) !important;
}
div[data-testid="stDownloadButton"] > button:hover {
  background: var(--accent) !important;
  color: #FFFFFF !important;
}

/* Quotes mais coloridos */
.quote{
  font-style: italic;
  font-weight: 600;
  line-height: 1.62;
  white-space: pre-wrap;
  border-left: 5px solid var(--accent);
  padding-left: 15px;
  color: var(--text);
  background: linear-gradient(90deg, rgba(255,0,127,0.05) 0%, rgba(255,255,255,0) 100%);
  padding-top: 8px;
  padding-bottom: 8px;
  border-radius: 0 12px 12px 0;
}

/* Chips coloridos parecendo "stickers" */
.chip{
  border: none;
  border-radius: 20px;
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 700;
  color: #FFF;
  background: linear-gradient(135deg, var(--purple), #B829EA);
  box-shadow: 0 2px 8px rgba(138, 43, 226, 0.3);
}

/* Tabs do Streamlit */
button[data-baseweb="tab"]{
  font-weight: 800 !important;
  color: var(--muted) !important;
  font-size: 16px !important;
}
button[data-baseweb="tab"][aria-selected="true"]{ color: var(--accent) !important; }
div[data-baseweb="tab-highlight"]{
  background: linear-gradient(90deg, var(--accent), var(--accent2)) !important;
  height: 4px !important;
  border-radius: 999px !important;
}

/* Barra de rolagem mais amigável */
::-webkit-scrollbar { width: 8px; }
::-webkit-scrollbar-thumb { background: var(--moss); border-radius: 999px; }
::-webkit-scrollbar-track { background: transparent; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# SESSION STATE
# ============================================================
if "analysis_done" not in st.session_state: st.session_state.analysis_done = False
if "result_data" not in st.session_state: st.session_state.result_data = None
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
# FUNÇÕES AUXILIARES
# ============================================================
def parse_ris(ris_text: str):
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

def fetch_oa_pdf(doi: str):
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

def df_to_tsv(df: pd.DataFrame) -> str:
    output = io.StringIO()
    writer = csv.writer(output, delimiter="\t", quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    writer.writerow(df.columns.tolist())
    for row in df.itertuples(index=False):
        writer.writerow(list(row))
    return output.getvalue()

def copy_button_tsv(tsv_text: str, label: str, key: str):
    safe = tsv_text.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    components.html(
        f"""
        <button id="{key}" style="
            width:100%;
            padding:12px 14px;
            border-radius:24px;
            border:2px solid #00E5FF;
            background:#FFFFFF;
            color:#00BCD4;
            font-weight:800;
            font-family: 'Nunito', sans-serif;
            cursor:pointer;
            box-shadow: 0 4px 15px rgba(0,229,255,0.15);
            transition: all 0.3s ease;
        "
        onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 8px 20px rgba(0,229,255,0.25)';"
        onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 15px rgba(0,229,255,0.15)';"
        >{label}</button>

        <script>
          const btn = document.getElementById("{key}");
          btn.addEventListener("click", async () => {{
            try {{
              const text = `{safe}`;
              await navigator.clipboard.writeText(text);
              btn.innerText = "✨ Copiado!";
              setTimeout(() => btn.innerText = "{label}", 1400);
            }} catch (e) {{
              btn.innerText = "⚠️ Falhou (use o TSV abaixo)";
              setTimeout(() => btn.innerText = "{label}", 2200);
            }}
          }});
        </script>
        """,
        height=65,
    )

# ✅ QUADRO HTML: Atualizado para a estética super clean Dopamina
def render_quadro_html(df: pd.DataFrame, max_height_px: int = 650):
    def esc(x: str) -> str:
        return (x.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;")
                 .replace('"', "&quot;"))

    # Largura da primeira coluna (Documento)
    doc_w = 320

    html = f"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap');
      
      .qa-wrap {{
        overflow:auto;
        max-height:{max_height_px}px;
        border-radius:24px;
        border:none;
        box-shadow: 0 10px 30px rgba(255,0,127,0.08);
        background: #FFFFFF;
        font-family: 'Nunito', sans-serif;
      }}
      table.qa-table {{
        border-collapse: collapse;
        width:100%;
        font-size:14px;
        color:#1E293B;
      }}

      thead th {{
        position: sticky;
        top: 0;
        z-index: 5;
        background: #F4F7FE;
        color: #FF007F;
        padding: 16px;
        border-bottom: 2px solid #E2E8F0;
        text-align: left;
        font-weight: 800;
        min-width: 420px;
      }}

      /* header da coluna Documento: sticky left + sticky top */
      thead th.doc {{
        left: 0;
        z-index: 8;
        min-width: {doc_w}px;
        max-width: {doc_w}px;
        width: {doc_w}px;
      }}

      tbody td {{
        padding: 16px;
        border-bottom: 1px solid #E2E8F0;
        vertical-align: top;
        line-height: 1.55;
        white-space: pre-wrap;
        min-width: 420px;
      }}

      /* coluna Documento: sticky left */
      tbody td.doc {{
        position: sticky;
        left: 0;
        z-index: 3;
        font-weight: 800;
        background: #FFFFFF;
        min-width: {doc_w}px;
        max-width: {doc_w}px;
        width: {doc_w}px;
        color: #8A2BE2;
      }}

      /* zebra */
      tbody tr:nth-child(even) td {{
        background: #F8FAFC;
      }}
      tbody tr:nth-child(even) td.doc {{
        background: #F8FAFC;
      }}

      .qa-wrap::-webkit-scrollbar {{ width: 8px; height: 8px; }}
      .qa-wrap::-webkit-scrollbar-thumb {{ background: #00E5FF; border-radius: 999px; }}
      .qa-wrap::-webkit-scrollbar-track {{ background: transparent; }}
    </style>

    <div class="qa-wrap">
      <table class="qa-table">
        <thead><tr>
    """

    for i, col in enumerate(df.columns):
        if i == 0:
            html += f'<th class="doc">{esc(str(col))}</th>'
        else:
            html += f'<th>{esc(str(col))}</th>'

    html += "</tr></thead><tbody>"

    for _, row in df.iterrows():
        html += "<tr>"
        for i, col in enumerate(df.columns):
            cell = "" if pd.isna(row[col]) else str(row[col])
            if i == 0:
                html += f'<td class="doc">{esc(cell)}</td>'
            else:
                html += f"<td>{esc(cell)}</td>"
        html += "</tr>"

    html += "</tbody></table></div>"

    components.html(html, height=max_height_px + 30, scrolling=True)

# ============================================================
# TÍTULO CENTRALIZADO
# ============================================================
st.markdown('<div class="qa-title-center">Análise Qualitativa AI</div>', unsafe_allow_html=True)
st.markdown('<div class="qa-subtitle-center">Fenomenológica • Temática (Braun & Clarke) • Mapeamento • Integração RIS</div>', unsafe_allow_html=True)

# ============================================================
# BARRA LATERAL (SIDEBAR)
# ============================================================
with st.sidebar:
    st.header("✨ Configurações")
    mode = st.radio(
        "Modo de Análise",
        ["Fenomenológico", "Temático (Braun & Clarke)", "Mapeamento Sistemático",
         "Fenomenológico + Mapeamento", "Temático + Mapeamento", "Todos (3 modos)"],
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

                progress_bar = st.progress(0)
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

                    progress_bar.progress((i + 1) / len(entries))

                status_text.success(
                    f"Concluído! {len(st.session_state.ris_pdfs)} PDFs baixados, {len(st.session_state.ris_texts)} resumos extraídos."
                )

    uploaded_files = st.file_uploader("Ou envie seus PDFs manualmente", type="pdf", accept_multiple_files=True)

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
    run = st.button("🚀 Iniciar Análise do Corpus", type="primary", disabled=(total_docs == 0))

# ============================================================
# EXECUTAR ANÁLISE
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
        gemini_files = [types.Part.from_bytes(data=f.getvalue(), mime_type="application/pdf") for f in (uploaded_files or [])]

        for pdf_doc in st.session_state.ris_pdfs:
            gemini_files.append(types.Part.from_bytes(data=pdf_doc['bytes'], mime_type="application/pdf"))

        for doc in st.session_state.ris_texts:
            gemini_files.append(types.Part.from_text(text=f"DOCUMENTO: {doc['name']}\n\n{doc['text']}"))

        prompt_text = "Leia todos os documentos anexados como um corpus único.\n\n"

        if includes_phenom(mode):
            prompt_text += (
                f"=== MODO FENOMENOLÓGICO ===\nINTERROGAÇÃO FENOMENOLÓGICA:\n\"{phenom_q}\"\n\n"
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
            prompt_text += (
                "=== MODO MAPEAMENTO SISTEMÁTICO ===\n"
                "Responda às perguntas abaixo para CADA documento:\n"
                f"{sys_q}\n\n"
                "REGRAS OBRIGATÓRIAS:\n"
                "1) 'resposta' deve ser curta (máx. 2–3 frases).\n"
                "2) 'evidencia_textual' deve ser uma CITAÇÃO LITERAL do artigo (copiada exatamente do texto, sem traduzir/parafrasear).\n"
                "3) A evidência deve ser suficiente para justificar a resposta.\n"
                "4) 'pagina' deve ser o número da página onde a citação aparece. Se não tiver certeza, use null.\n\n"
            )

        contents = gemini_files + [prompt_text]

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=(
                    "Você é um assistente de análise qualitativa de corpus documental. Nunca invente conteúdo. "
                    "Preserve rastreabilidade. Para o mapeamento sistemático: 'evidencia_textual' deve ser citação literal do documento. "
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
        st.success("🎉 Análise concluída com sucesso! Explore os resultados abaixo.")

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
                    st.download_button("Exportar CSV", df_us.to_csv(index=False).encode("utf-8"), "unidades_sentido.csv", "text/csv", use_container_width=True)

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
                        <div class="qa-shell" style="margin-bottom: 20px;">
                          <div style="display:flex; gap:10px; margin-bottom:15px;">
                            <span class="chip">{uid}</span><span class="chip">{doc}</span><span class="chip">{pag_txt}</span>
                          </div>
                          <div class="quote" style="margin-bottom:15px;">"{cit}"</div>
                          <div style="background: var(--panel2); padding: 16px; border-radius: 16px;">{cj_html}</div>
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
                    st.download_button("Exportar CSV", df_um.to_csv(index=False).encode("utf-8"), "unidades_significado.csv", "text/csv", use_container_width=True)

                for _, r in df_um.iterrows():
                    st.markdown(f"""
                        <div class="qa-shell" style="margin-bottom: 20px;">
                          <div style="display:flex; gap:10px; margin-bottom:15px;">
                            <span class="chip">{r.get("id_unidade", "")}</span><span class="chip">{r.get("documento", "")}</span>
                          </div>
                          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                            <div><div style="font-size:12px; font-weight:bold; color:var(--muted); margin-bottom:8px;">TRECHO ORIGINAL</div><div class="quote">"{r.get("trecho_original", "")}"</div></div>
                            <div><div style="font-size:12px; font-weight:bold; color:var(--muted); margin-bottom:8px;">SÍNTESE</div><div style="background: rgba(255, 140, 0, 0.1); padding: 16px; border-radius: 16px; color: var(--accent2); font-weight: 700;">{r.get("sintese", "")}</div></div>
                          </div>
                        </div>
                        """, unsafe_allow_html=True)
        tab_idx += 1

        with st_tabs[tab_idx]:
            categorias = (phenom_data or {}).get("categorias", [])
            if not categorias:
                st.warning("Nenhuma categoria foi retornada.")
            else:
                cols = st.columns(3)
                for i, c in enumerate(categorias):
                    with cols[i % 3]:
                        rel = c.get("unidades_relacionadas", [])
                        chips_html = (
                            '<div style="display:flex; flex-wrap:wrap; gap:8px;">'
                            + "".join([f'<span class="chip" style="font-size:11px;">{u}</span>' for u in rel])
                            + "</div>"
                        ) if rel else "-"

                        st.markdown(f"""
                            <div class="qa-shell" style="height: 100%; margin-bottom: 20px;">
                              <h3 style="color: var(--accent); font-weight: 800; margin-top:0;">{c.get("nome", "")}</h3>
                              <p style="font-size: 15px; color: var(--text);">{c.get("descricao", "")}</p>
                              <div style="font-size:12px; font-weight:bold; color:var(--muted); margin-bottom:10px; margin-top:20px;">UNIDADES RELACIONADAS</div>
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
                    st.download_button("Exportar CSV", df_cod.to_csv(index=False).encode("utf-8"), "codigos.csv", "text/csv", use_container_width=True)

                for _, r in df_cod.iterrows():
                    pag = r.get("pagina", None)
                    pag_txt = f"Pág. {pag}" if pag is not None else "Pág. null"
                    st.markdown(f"""
                        <div class="qa-shell" style="margin-bottom: 20px;">
                          <div style="display:flex; gap:10px; margin-bottom:15px;">
                            <span class="chip">{r.get("id_codigo", "")}</span><span class="chip">{r.get("documento", "")}</span><span class="chip">{pag_txt}</span>
                          </div>
                          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                            <div><div style="font-size:12px; font-weight:bold; color:var(--muted); margin-bottom:8px;">TRECHO LITERAL</div><div class="quote">"{r.get("trecho", "")}"</div></div>
                            <div style="background: var(--panel2); padding: 16px; border-radius: 16px;">
                              <div style="font-size:12px; font-weight:bold; color:var(--muted);">CÓDIGO</div><div style="font-weight:800; font-size: 18px; color:var(--accent); margin-bottom:15px;">{r.get("codigo", "")}</div>
                              <div style="font-size:12px; font-weight:bold; color:var(--muted);">DEFINIÇÃO</div><div style="font-weight: 600;">{r.get("descricao_codigo", "")}</div>
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
                cols = st.columns(2)
                for i, t in enumerate(temas):
                    with cols[i % 2]:
                        rel = t.get("codigos_relacionados", [])
                        chips_html = (
                            '<div style="display:flex; flex-wrap:wrap; gap:8px;">'
                            + "".join([f'<span class="chip" style="font-size:11px;">{u}</span>' for u in rel])
                            + "</div>"
                        ) if rel else "-"

                        st.markdown(f"""
                            <div class="qa-shell" style="height: 100%; margin-bottom: 20px;">
                              <h3 style="color: var(--accent2); font-weight: 800; margin-top:0;">{t.get("nome", "")}</h3>
                              <p style="font-weight: 600;">{t.get("descricao", "")}</p>
                              <div style="background: var(--panel2); padding: 14px; border-radius: 12px; margin-bottom: 15px;">
                                <div style="font-size:12px; font-weight:bold; color:var(--muted); margin-bottom:5px;">INTERPRETAÇÃO</div>
                                <div style="font-size:14px; font-weight: 600;">{t.get("interpretacao", "")}</div>
                              </div>
                              <div style="font-size:12px; font-weight:bold; color:var(--muted); margin-bottom:10px;">CÓDIGOS RELACIONADOS</div>
                              {chips_html}
                            </div>
                            """, unsafe_allow_html=True)
        tab_idx += 1

    # ===================== Mapeamento =====================
    if includes_systematic(render_mode):
        with st_tabs[tab_idx]:
            docs = (sys_data or {}).get("documentos", [])
            if not docs:
                st.warning("O mapeamento sistemático não foi retornado.")
            else:
                rows_long = []
                for doc in docs:
                    doc_name = doc.get("documento")
                    for ans in doc.get("respostas", []):
                        rows_long.append({
                            "Documento": doc_name,
                            "Pergunta": ans.get("pergunta"),
                            "Evidência": ans.get("evidencia_textual"),
                            "Página": ans.get("pagina"),
                        })
                df_long = pd.DataFrame(rows_long)

                def fmt_evid(row):
                    evid = (row.get("Evidência") or "").strip()
                    pag = row.get("Página", None)
                    pag_txt = f"{pag}" if (pag is not None and str(pag).strip() != "") else "null"
                    if evid:
                        return f'{evid} (p. {pag_txt})'
                    return f'(p. {pag_txt})'

                df_long["Evidência (citação + página)"] = df_long.apply(fmt_evid, axis=1)

                df_wide = (
                    df_long
                    .pivot_table(
                        index="Documento",
                        columns="Pergunta",
                        values="Evidência (citação + página)",
                        aggfunc="first"
                    )
                    .reset_index()
                )

                tsv_wide = df_to_tsv(df_wide)

                # Cabeçalho central minimalista
                st.markdown(
                    """
                    <div style="text-align:center; margin: 8px 0 24px 0;">
                      <div style="
                        font-family: 'Josefin Sans', sans-serif;
                        font-weight: 900;
                        font-size: 46px;
                        letter-spacing: -0.02em;
                        color: var(--text);
                      ">Mapeamento Sistemático</div>
                      <div style="color: var(--muted); font-size: 15px; font-weight: 600; margin-top:6px;">
                        Quadro consolidado (evidência literal + página)
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # Só dois botões (copiar/baixar)
                c1, c2 = st.columns([1, 1], vertical_alignment="center")
                with c1:
                    copy_button_tsv(tsv_wide, "📋 Copiar quadro (TSV)", key="copy_quadro_tsv_clean")
                with c2:
                    st.download_button(
                        "⬇️ Baixar quadro (TSV)",
                        tsv_wide.encode("utf-8"),
                        "quadro_mapeamento.tsv",
                        "text/tab-separated-values",
                        use_container_width=True
                    )

                # Quadro
                render_quadro_html(df_wide, max_height_px=650)
