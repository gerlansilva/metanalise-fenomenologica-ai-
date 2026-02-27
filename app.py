import streamlit as st
import pandas as pd
import json
import os
import time
import threading
import requests
from streamlit.runtime.scriptrunner import add_script_run_ctx
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
import streamlit.components.v1 as components
import io, csv

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
  --bg:#E7DFC9;
  --panel:#F1E9D8;
  --panel2:#EDE4D1;
  --line:#C9BFA6;
  --text:#2F241C;
  --muted:#6E6A5E;
  --accent:#C26A2E;
  --accent2:#A35422;
  --moss:#6F8A73;
  --shadow: 0 10px 26px rgba(47,36,28,0.10);
  --shadow2: 0 2px 10px rgba(47,36,28,0.08);
  --radius: 20px;
}

html, body { background: var(--bg) !important; }
.stApp { background: var(--bg) !important; color: var(--text) !important; }
* { font-family: "Open Sans", system-ui, -apple-system, Segoe UI, Arial, sans-serif; }

.block-container { max-width: 1320px; padding-top: 36px; padding-bottom: 36px; }

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

.qa-shell{
  background: var(--panel);
  border: 1px solid rgba(47,36,28,0.12);
  border-radius: calc(var(--radius) + 6px);
  box-shadow: var(--shadow);
  padding: 18px 20px;
}

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

.stRadio label, .stMarkdown, label, p, span, div { color: var(--text); }
.stRadio [data-testid="stMarkdownContainer"] p { color: var(--text) !important; }

[data-testid="stFileUploader"]{
  border-radius: var(--radius) !important;
  border: 1px dashed rgba(47,36,28,0.25) !important;
  background: rgba(241,233,216,0.55) !important;
}

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

div[data-testid="stDownloadButton"] > button {
  border: 1px solid rgba(47,36,28,0.16) !important;
  background: var(--panel2) !important;
  color: var(--text) !important;
  border-radius: 14px !important;
  font-weight: 800 !important;
  box-shadow: var(--shadow2) !important;
}

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

.quote{
  font-style: italic;
  line-height: 1.62;
  white-space: pre-wrap;
  border-left: 4px solid rgba(111,138,115,0.95);
  padding-left: 12px;
  color: var(--text);
}

.chip{
  border: 1px solid rgba(47,36,28,0.14);
  border-radius: 12px;
  padding: 6px 10px;
  font-size: 13px;
  color: var(--text);
  background: rgba(111,138,115,0.22);
}

::-webkit-scrollbar { width: 10px; }
::-webkit-scrollbar-thumb { background: rgba(111,138,115,0.75); border-radius: 999px; }
::-webkit-scrollbar-track { background: rgba(47,36,28,0.06); }

/* ==========================
   QUADRO (cards) com scroll
   ========================== */
.qa-table-wrap{
  background: rgba(241,233,216,0.55);
  border: 1px solid rgba(47,36,28,0.14);
  border-radius: calc(var(--radius) + 6px);
  box-shadow: var(--shadow2);
  overflow: auto;
  max-height: 72vh;
}

/* tabela */
.qa-table{
  border-collapse: separate;
  border-spacing: 0;
  width: max-content;     /* permite ficar mais larga que a tela (scroll horizontal) */
  min-width: 100%;
}

/* cabeçalho fixo */
.qa-table thead th{
  position: sticky;
  top: 0;
  z-index: 5;
  background: var(--panel);
  color: var(--text);
  text-align: left;
  font-family: "Work Sans", sans-serif;
  font-weight: 800;
  font-size: 14px;
  border-bottom: 1px solid rgba(47,36,28,0.16);
  padding: 14px 14px;
  white-space: nowrap;
}

/* primeira coluna fixa */
.qa-table .sticky-col{
  position: sticky;
  left: 0;
  z-index: 6;
  background: var(--panel);
  border-right: 1px solid rgba(47,36,28,0.10);
}

/* células */
.qa-table td{
  vertical-align: top;
  padding: 14px 14px;
  border-bottom: 1px solid rgba(47,36,28,0.10);
  min-width: 360px;      /* garante espaço para texto longo */
}

/* coluna Documento (mais estreita) */
.qa-table td.doccell{
  min-width: 260px;
  max-width: 260px;
}

/* card dentro da célula */
.cell-card{
  background: rgba(255,255,255,0.45);
  border: 1px solid rgba(47,36,28,0.14);
  border-radius: 14px;
  box-shadow: var(--shadow2);
  padding: 12px 12px;
}

/* texto dentro do card (não cortar) */
.cell-text{
  white-space: pre-wrap;     /* mantém quebras e permite wrap */
  word-break: break-word;    /* quebra palavras enormes */
  overflow-wrap: anywhere;
  line-height: 1.55;
  font-size: 13.5px;
  color: var(--text);
}

/* label pequeno */
.cell-label{
  font-size: 11px;
  font-weight: 800;
  color: var(--muted);
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
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
# FUNÇÕES AUXILIARES
# ============================================================
def gerar_sintese_transversal(pergunta: str, df_sub: pd.DataFrame) -> str:
    linhas = []
    for _, r in df_sub.iterrows():
        doc = str(r.get("Documento", "")).strip()
        evid = str(r.get("Evidência", "")).strip()
        pag = r.get("Página", None)
        pag_str = f"{pag}" if (pag is not None and str(pag).strip() != "") else "null"
        linhas.append(f"- DOCUMENTO: {doc}\n  EVIDÊNCIA: \"{evid}\"\n  PÁGINA: {pag_str}\n")

    prompt = f"""
Você está comparando resultados entre documentos para a MESMA pergunta, com base apenas nas evidências abaixo.

PERGUNTA:
{pergunta}

EVIDÊNCIAS POR DOCUMENTO:
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
            padding:10px 14px;
            border-radius:14px;
            border:1px solid rgba(47,36,28,0.16);
            background: #EDE4D1;
            color: #2F241C;
            font-weight: 800;
            cursor: pointer;
            box-shadow: 0 2px 10px rgba(47,36,28,0.08);
        ">{label}</button>

        <script>
          const btn = document.getElementById("{key}");
          btn.addEventListener("click", async () => {{
            try {{
              const text = `{safe}`;
              await navigator.clipboard.writeText(text);
              btn.innerText = "✅ Copiado!";
              setTimeout(() => btn.innerText = "{label}", 1400);
            }} catch (e) {{
              btn.innerText = "⚠️ Não consegui copiar (use a caixa abaixo)";
              setTimeout(() => btn.innerText = "{label}", 2200);
            }}
          }});
        </script>
        """,
        height=55,
    )

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
    run = st.button("▶ Iniciar Análise do Corpus", type="primary", disabled=(total_docs == 0))

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

    # (Fenomenológico / Temático iguais ao seu; omitidos aqui por brevidade)
    # ---------------------------------------------------------------------
    if includes_phenom(render_mode):
        with st_tabs[tab_idx]:
            st.info("Aba Fenomenológico mantida (sem alterações nesta versão).")
        tab_idx += 1
        with st_tabs[tab_idx]:
            st.info("Aba Fenomenológico mantida (sem alterações nesta versão).")
        tab_idx += 1
        with st_tabs[tab_idx]:
            st.info("Aba Fenomenológico mantida (sem alterações nesta versão).")
        tab_idx += 1

    if includes_thematic(render_mode):
        with st_tabs[tab_idx]:
            st.info("Aba Temática mantida (sem alterações nesta versão).")
        tab_idx += 1
        with st_tabs[tab_idx]:
            st.info("Aba Temática mantida (sem alterações nesta versão).")
        tab_idx += 1

    # ===================== Mapeamento (QUADRO EM CARDS) =====================
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
                            "Resposta": ans.get("resposta"),
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

                df_long["Célula"] = df_long.apply(fmt_evid, axis=1)

                # wide (para export/cópia)
                df_wide = (
                    df_long
                    .pivot_table(index="Documento", columns="Pergunta", values="Célula", aggfunc="first")
                    .reset_index()
                )

                st.markdown(
                    '<div class="qa-shell" style="margin-top: 10px; margin-bottom: 12px;">'
                    '<h4 style="margin:0; color:var(--accent2);">🧾 Quadro do Mapeamento (cards, texto completo)</h4>'
                    '<p style="margin:6px 0 0 0; color:var(--muted); font-size:13px;">Cada célula é um card com a citação literal + (p. X). Scroll horizontal e vertical habilitados.</p>'
                    '</div>',
                    unsafe_allow_html=True
                )

                # Exportações
                st.download_button(
                    "Exportar CSV (quadro)",
                    df_wide.to_csv(index=False).encode("utf-8"),
                    "quadro_mapeamento_evidencias.csv",
                    "text/csv",
                    use_container_width=True
                )

                tsv_wide = df_to_tsv(df_wide)

                c1, c2 = st.columns([1.3, 1.7], vertical_alignment="center")
                with c1:
                    copy_button_tsv(tsv_wide, "📋 Copiar quadro (TSV)", key="copy_quadro_tsv")
                with c2:
                    st.download_button(
                        "Baixar TSV (quadro)",
                        tsv_wide.encode("utf-8"),
                        "quadro_mapeamento_evidencias.tsv",
                        "text/tab-separated-values",
                        use_container_width=True
                    )

                with st.expander("Abrir TSV (se o copiar falhar)", expanded=False):
                    st.text_area(
                        "Selecione tudo (Ctrl/Cmd + A), copie e cole na planilha.",
                        value=tsv_wide,
                        height=220,
                        key="tsv_quadro_text"
                    )

                # --------- render em HTML (cards) para NÃO suprimir texto ---------
                perguntas = [c for c in df_wide.columns if c != "Documento"]

                # cabeçalho HTML
                thead = "<thead><tr>"
                thead += '<th class="sticky-col">Documento</th>'
                for p in perguntas:
                    thead += f"<th>{p}</th>"
                thead += "</tr></thead>"

                # corpo HTML
                tbody = "<tbody>"
                for _, row in df_wide.iterrows():
                    doc = (row.get("Documento") or "")
                    tbody += "<tr>"
                    tbody += f'<td class="sticky-col doccell"><div class="cell-card"><div class="cell-label">Documento</div><div class="cell-text">{doc}</div></div></td>'
                    for p in perguntas:
                        val = row.get(p, "")
                        val = "" if pd.isna(val) else str(val)
                        tbody += (
                            "<td>"
                            f'<div class="cell-card"><div class="cell-label">Evidência</div><div class="cell-text">{val}</div></div>'
                            "</td>"
                        )
                    tbody += "</tr>"
                tbody += "</tbody>"

                html = f"""
                <div class="qa-table-wrap">
                  <table class="qa-table">
                    {thead}
                    {tbody}
                  </table>
                </div>
                """

                st.markdown(html, unsafe_allow_html=True)

                # (Opcional) também manter o LONG para auditoria
                with st.expander("Exportar formato LONG (auditoria)", expanded=False):
                    st.download_button(
                        "Exportar CSV (long)",
                        df_long[["Documento", "Pergunta", "Resposta", "Evidência", "Página"]].to_csv(index=False).encode("utf-8"),
                        "mapeamento_long.csv",
                        "text/csv",
                        use_container_width=True
                    )
