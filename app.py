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
# IDENTIDADE VISUAL (PRESERVADA)
# ============================================================
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Amiko:wght@400;600;700&family=Annie+Use+Your+Telescope&family=Asap+Condensed:wght@400;600;700&family=Asap:wght@400;600;700&display=swap" rel="stylesheet">

<style>
:root{
  --blue-dark: #227C9D; --mint: #17C3B2; --yellow: #FFCB77; --cream: #FEF9EF; --coral: #FE6D73;
  --bg: var(--cream); --panel: #FFFFFF; --panel2: #FFF5E1; 
  --text-dark: #113F50; --muted: #4A7A8C;
  --shadow: 0 8px 24px rgba(34, 124, 157, 0.1); --radius: 20px;
}
html, body { background: var(--bg) !important; }
.stApp { background: var(--bg) !important; color: var(--text-dark) !important; }
* { font-family: "Asap", sans-serif; }
.qa-title-center{ font-family: "Amiko", sans-serif; font-weight: 700; font-size: 52px; text-align: center; color: var(--blue-dark); }
.qa-shell{ background: var(--panel); border: 1px solid rgba(23, 195, 178, 0.2); border-radius: var(--radius); box-shadow: var(--shadow); padding: 24px; transition: transform 0.2s ease; margin-bottom: 20px; }
.quote{ font-family: "Asap Condensed", sans-serif; font-style: italic; font-size: 16px; line-height: 1.6; border-left: 5px solid var(--yellow); padding-left: 15px; background: rgba(255, 203, 119, 0.1); padding-top: 8px; padding-bottom: 8px; border-radius: 0 12px 12px 0; }
.chip{ border-radius: 12px; padding: 6px 14px; font-size: 13px; font-weight: 700; color: #FFF; background-color: var(--mint); }
.stButton > button { background-color: var(--coral) !important; color: #fff !important; border-radius: 24px !important; font-weight: 700 !important; width: 100%; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# SESSION STATE
# ============================================================
if "analysis_done" not in st.session_state: st.session_state.analysis_done = False
if "result_data" not in st.session_state: st.session_state.result_data = None
if "ris_pdfs" not in st.session_state: st.session_state.ris_pdfs = []
if "ris_texts" not in st.session_state: st.session_state.ris_texts = []

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# ============================================================
# MODELOS PYDANTIC
# ============================================================
class UnidadeSentido(BaseModel):
    id_unidade: str
    documento: str
    pagina: int | None
    citacao_literal: str # IA incluirá a página aqui no texto formatado

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
    id_codigo: str
    documento: str
    pagina: int | None
    trecho: str
    codigo: str
    descricao_codigo: str

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
# FUNÇÕES AUXILIARES (RIS, UNPAYWALL, QUADROS)
# ============================================================
def parse_ris(ris_text: str):
    entries, current = [], {}
    for line in ris_text.splitlines():
        line = line.strip()
        if not line: continue
        if line.startswith('ER  -'):
            if current: entries.append(current)
            current = {}
        elif len(line) >= 6 and line[4:6] == '- ':
            key, val = line[:2], line[6:].strip()
            current[key] = current.get(key, "") + (" ; " if key in current else "") + val
    return entries

def fetch_oa_pdf(doi: str):
    try:
        res = requests.get(f"https://api.unpaywall.org/v2/{doi}?email=dobbylivreagora@gmail.com", timeout=10)
        if res.status_code == 200 and res.json().get('is_oa'):
            pdf_url = res.json()['best_oa_location'].get('url_for_pdf')
            if pdf_url:
                r = requests.get(pdf_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
                if r.status_code == 200: return r.content
    except: pass
    return None

def includes_phenom(m): return m in ["Fenomenológico", "Fenomenológico + Mapeamento", "Todos (3 modos)"]
def includes_thematic(m): return m in ["Temático (Braun & Clarke)", "Temático + Mapeamento", "Todos (3 modos)"]
def includes_systematic(m): return m in ["Mapeamento Sistemático", "Fenomenológico + Mapeamento", "Temático + Mapeamento", "Todos (3 modos)"]

def render_quadro_html(df):
    def esc(x): return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html = f"""<div style="overflow:auto; max-height:600px; border-radius:16px; border:1px solid #17C3B2; background:white;">
    <table style="width:100%; border-collapse:collapse; font-family:Asap; font-size:14px;">
    <thead><tr style="background:#227C9D; color:white;">{''.join([f'<th style="padding:16px; position:sticky; top:0;">{esc(c)}</th>' for c in df.columns])}</tr></thead>
    <tbody>{''.join([f'<tr>{" ".join([f"<td style=\'padding:12px; border:1px solid #eee; text-align:justify;\'>{esc(v)}</td>" for v in row])}</tr>' for row in df.values])}</tbody>
    </table></div>"""
    components.html(html, height=630, scrolling=True)

# ============================================================
# INTERFACE
# ============================================================
st.markdown('<div class="qa-title-center">Análise Qualitativa AI</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Configurações")
    mode = st.radio("Modo", ["Fenomenológico", "Temático (Braun & Clarke)", "Mapeamento Sistemático", "Todos (3 modos)"])
    
    phenom_q = st.text_area("Interrogação Fenomenológica") if includes_phenom(mode) else ""
    thematic_q = st.text_area("Questão Temática") if includes_thematic(mode) else ""
    sys_q = st.text_area("Mapeamento (1 por linha)") if includes_systematic(mode) else ""

    ris_file = st.file_uploader("Importar RIS", type=["ris", "txt"])
    if ris_file and st.button("Processar RIS"):
        ents = parse_ris(ris_file.getvalue().decode("utf-8", errors="ignore"))
        for e in ents:
            doi = e.get('DO', '').replace('https://doi.org/', '').strip()
            pdf = fetch_oa_pdf(doi) if doi else None
            if pdf: st.session_state.ris_pdfs.append({"name": e.get('TI', 'Doc')+'.pdf', "bytes": pdf})
            else: st.session_state.ris_texts.append({"name": e.get('TI', 'Resumo'), "text": e.get('AB', '')})

    uploaded_files = st.file_uploader("Upload PDFs", type="pdf", accept_multiple_files=True)
    total_docs = len(uploaded_files or []) + len(st.session_state.ris_pdfs) + len(st.session_state.ris_texts)
    run = st.button("🚀 Iniciar Análise", type="primary", disabled=(total_docs == 0))

# ============================================================
# EXECUÇÃO DA ANÁLISE (COM GEMINI-2.5-FLASH)
# ============================================================
if run:
    st.session_state.analysis_done = False
    timer = st.empty()
    stop_timer, start_time = False, time.time()

    def update_t():
        while not stop_timer:
            elapsed = int(time.time() - start_time)
            timer.markdown(f'<div style="background:#FFF; padding:15px; border-radius:15px; border:2px solid #17C3B2; text-align:center;">🧠 Analisando com Gemini 2.5... {elapsed}s</div>', unsafe_allow_html=True)
            time.sleep(1)

    t = threading.Thread(target=update_t); add_script_run_ctx(t); t.start()

    try:
        parts = [types.Part.from_bytes(data=f.getvalue(), mime_type="application/pdf") for f in (uploaded_files or [])]
        for p in st.session_state.ris_pdfs: parts.append(types.Part.from_bytes(data=p['bytes'], mime_type="application/pdf"))
        for txt in st.session_state.ris_texts: parts.append(types.Part.from_text(text=txt['text']))

        prompt = "Leia o corpus e analise.\n\n"
        if includes_phenom(mode):
            prompt += (
                f"FENOMENOLOGIA: {phenom_q}\n"
                "Extraia US com página. FORMATE 'citacao_literal' como: \"Trecho literal...\" (p. X).\n"
            )
        
        response = client.models.generate_content(
            model="gemini-2.5-flash", 
            contents=parts + [prompt],
            config=types.GenerateContentConfig(
                system_instruction="Assistente de Pesquisa. Responda em JSON conforme o esquema.",
                response_mime_type="application/json",
                response_schema=AnalysisResult,
                temperature=0.1,
            ),
        )
        st.session_state.result_data = json.loads(response.text)
        st.session_state.analysis_done = True
    except Exception as e: st.error(f"Erro: {e}")
    finally: stop_timer = True; t.join(); timer.empty()

# ============================================================
# RENDER RESULTADOS
# ============================================================
if st.session_state.analysis_done:
    res = st.session_state.result_data
    tabs = st.tabs(["☰ Unidades", "📄 Significados", "🏷️ Categorias", "🧭 Mapeamento"])
    
    with tabs[0]: # US com Página
        if res.get("fenomenologico"):
            for u in res["fenomenologico"]["unidades_sentido"]:
                st.markdown(f'<div class="qa-shell"><span class="chip">{u["id_unidade"]}</span> <span class="chip" style="background:#4A7A8C;">{u["documento"]}</span><div class="quote" style="margin-top:10px;">{u["citacao_literal"]}</div></div>', unsafe_allow_html=True)

    with tabs[2]: # Categorias (Estilo Roxo da imagem)
        if res.get("fenomenologico"):
            cats = res["fenomenologico"]["categorias"]
            cols = st.columns(len(cats) if cats else 1)
            for i, c in enumerate(cats):
                with cols[i]:
                    st.markdown(f"""<div class="qa-shell" style="height:100%; border-top:6px solid purple;">
                        <h4 style="color:purple; text-align:center;">{c['nome']}</h4>
                        <p style="font-size:14px; text-align:justify;">{c['descricao']}</p>
                        <hr><small>RELACIONADAS:</small><br>
                        {' '.join([f'<span class="chip" style="background:purple; font-size:10px;">{us}</span>' for us in c['unidades_relacionadas']])}
                    </div>""", unsafe_allow_html=True)

    with tabs[3]: # Mapeamento
        if res.get("sistematico"):
            rows = []
            for doc in res["sistematico"]["documentos"]:
                d = {"Documento": doc["documento"]}
                for a in doc["respostas"]: d[a["pergunta"]] = f"{a['evidencia_textual']} (p. {a['pagina']})"
                rows.append(d)
            render_quadro_html(pd.DataFrame(rows))
