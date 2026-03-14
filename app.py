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
  --bg: var(--cream); --panel: #FFFFFF; --text-dark: #113F50; --muted: #4A7A8C;
  --shadow: 0 8px 24px rgba(34, 124, 157, 0.1); --radius: 20px;
}
html, body { background: var(--bg) !important; }
.stApp { background: var(--bg) !important; color: var(--text-dark) !important; }
* { font-family: "Asap", sans-serif; }
.qa-title-center{ font-family: "Amiko", sans-serif; font-weight: 700; font-size: 52px; text-align: center; color: var(--blue-dark); }
.qa-shell{ background: var(--panel); border: 1px solid rgba(23, 195, 178, 0.2); border-radius: var(--radius); box-shadow: var(--shadow); padding: 24px; margin-bottom: 20px; transition: transform 0.2s ease; }
.quote{ font-family: "Asap Condensed", sans-serif; font-style: italic; font-size: 16px; line-height: 1.6; border-left: 5px solid var(--yellow); padding: 8px 15px; background: rgba(255, 203, 119, 0.1); border-radius: 0 12px 12px 0; }
.chip{ border-radius: 12px; padding: 6px 14px; font-size: 13px; font-weight: 700; color: #FFF; background-color: var(--mint); }
.stButton > button { background-color: var(--coral) !important; color: #fff !important; border-radius: 24px !important; font-weight: 700 !important; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# MODELOS PYDANTIC (CORRIGIDOS PARA EVITAR CLIENTERROR)
# ============================================================
class UnidadeSentido(BaseModel):
    id_unidade: str | None = None
    documento: str | None = None
    pagina: int | None = None
    citacao_literal: str | None = None
    citacao_formatada: str | None = Field(None, description="Citação e página: 'Texto...' (p. X).")

class UnidadeSignificado(BaseModel):
    id_unidade: str | None = None
    documento: str | None = None
    trecho_original: str | None = None
    sintese: str | None = None

class Categoria(BaseModel):
    nome: str | None = None
    descricao: str | None = None
    unidades_relacionadas: list[str] = []

class PhenomenologicalResult(BaseModel):
    unidades_sentido: list[UnidadeSentido] = []
    unidades_significado: list[UnidadeSignificado] = []
    categorias: list[Categoria] = []

class ThematicCode(BaseModel):
    id_codigo: str | None = None
    documento: str | None = None
    pagina: int | None = None
    trecho: str | None = None
    codigo: str | None = None

class ThematicTheme(BaseModel):
    nome: str | None = None
    descricao: str | None = None
    codigos_relacionados: list[str] = []

class ThematicResult(BaseModel):
    codigos: list[ThematicCode] = []
    temas: list[ThematicTheme] = []

class SystematicAnswer(BaseModel):
    pergunta: str | None = None
    resposta: str | None = None
    evidencia_textual: str | None = None
    pagina: int | None = None

class SystematicDocument(BaseModel):
    documento: str | None = None
    respostas: list[SystematicAnswer] = []

class SystematicResult(BaseModel):
    documentos: list[SystematicDocument] = []

class AnalysisResult(BaseModel):
    fenomenologico: PhenomenologicalResult | None = None
    tematico: ThematicResult | None = None
    sistematico: SystematicResult | None = None

# ============================================================
# LOGICA DE SESSÃO E API
# ============================================================
if "analysis_done" not in st.session_state: st.session_state.analysis_done = False
if "result_data" not in st.session_state: st.session_state.result_data = None
if "ris_pdfs" not in st.session_state: st.session_state.ris_pdfs = []
if "ris_texts" not in st.session_state: st.session_state.ris_texts = []

# Tenta pegar a chave do Secrets (Streamlit Cloud) ou Environment (Local)
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ Configure a GEMINI_API_KEY nos Secrets ou Variáveis de Ambiente.")
    st.stop()
client = genai.Client(api_key=api_key)

# ============================================================
# FUNÇÕES AUXILIARES (RIS E TABELAS)
# ============================================================
def parse_ris(ris_text):
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

def fetch_oa_pdf(doi):
    try:
        res = requests.get(f"https://api.unpaywall.org/v2/{doi}?email=dobbylivreagora@gmail.com", timeout=10)
        if res.status_code == 200 and res.json().get('is_oa'):
            url = res.json()['best_oa_location'].get('url_for_pdf')
            if url:
                r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
                if r.status_code == 200: return r.content
    except: pass
    return None

def render_quadro_html(df):
    def esc(x): return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html = f"""<div style="overflow-x:auto; border-radius:15px; border:1px solid #17C3B2; background:white;">
    <table style="width:100%; border-collapse:collapse; font-family:Asap; font-size:14px;">
    <thead><tr style="background:#227C9D; color:white;">{''.join([f'<th style="padding:15px;">{esc(c)}</th>' for c in df.columns])}</tr></thead>
    <tbody>{''.join([f'<tr>{" ".join([f"<td style=\'padding:12px; border:1px solid #eee; text-align:justify;\'>{esc(v)}</td>" for v in row])}</tr>' for row in df.values])}</tbody>
    </table></div>"""
    components.html(html, height=500, scrolling=True)

# ============================================================
# INTERFACE
# ============================================================
st.markdown('<div class="qa-title-center">Análise Qualitativa AI</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Configurações")
    mode = st.radio("Modo", ["Fenomenológico", "Temático", "Mapeamento", "Todos (3 modos)"])
    phenom_q = st.text_area("Interrogação Fenomenológica", "Como o fenômeno é descrito?")
    thematic_q = st.text_area("Questão Temática", "Quais os principais temas?")
    sys_q = st.text_area("Mapeamento (1 por linha)", "Objetivo?\nMetodologia?")
    
    st.subheader("📚 Corpus")
    ris_file = st.file_uploader("Importar RIS", type=["ris", "txt"])
    if ris_file and st.button("Processar RIS"):
        with st.spinner("Baixando PDFs..."):
            ents = parse_ris(ris_file.getvalue().decode("utf-8", errors="ignore"))
            for e in ents:
                doi = e.get('DO', '').replace('https://doi.org/', '').strip()
                pdf = fetch_oa_pdf(doi) if doi else None
                if pdf: st.session_state.ris_pdfs.append({"name": e.get('TI', 'Doc')+'.pdf', "bytes": pdf})
                else: st.session_state.ris_texts.append({"name": e.get('TI', 'Resumo'), "text": e.get('AB', '')})

    uploaded_files = st.file_uploader("Envio Manual", type="pdf", accept_multiple_files=True)
    total_docs = len(uploaded_files or []) + len(st.session_state.ris_pdfs) + len(st.session_state.ris_texts)
    run = st.button("🚀 Iniciar Análise", type="primary", disabled=(total_docs == 0))

# ============================================================
# EXECUÇÃO (CORREÇÃO DO MODELO)
# ============================================================
if run:
    st.session_state.analysis_done = False
    timer = st.empty()
    stop_timer, start_time = False, time.time()
    
    def update_t():
        while not stop_timer:
            elapsed = int(time.time() - start_time)
            timer.markdown(f'<div style="text-align:center; padding:10px; background:#fff; border:2px solid #17C3B2; border-radius:15px;">🧠 Processando... {elapsed}s</div>', unsafe_allow_html=True)
            time.sleep(1)
    
    thread = threading.Thread(target=update_t); add_script_run_ctx(thread); thread.start()

    try:
        parts = [types.Part.from_bytes(data=f.getvalue(), mime_type="application/pdf") for f in (uploaded_files or [])]
        for p in st.session_state.ris_pdfs: parts.append(types.Part.from_bytes(data=p['bytes'], mime_type="application/pdf"))
        for t_doc in st.session_state.ris_texts: parts.append(types.Part.from_text(text=t_doc['text']))
        
        prompt = f"Realize a análise qualitativa.\n"
        if "Fenomenológico" in mode or "Todos" in mode:
            prompt += f"FENOMENOLOGIA: {phenom_q}. Extraia US com página. Formato 'citacao_formatada': 'Trecho...' (p. X).\n"
        if "Temático" in mode or "Todos" in mode:
            prompt += f"TEMÁTICA: {thematic_q}.\n"
        if "Mapeamento" in mode or "Todos" in mode:
            prompt += f"MAPEAMENTO: {sys_q}.\n"

        response = client.models.generate_content(
            model="gemini-1.5-flash", # Troca para modelo estável
            contents=parts + [prompt],
            config=types.GenerateContentConfig(
                system_instruction="Assistente de Pesquisa. Use JSON conforme o esquema.",
                response_mime_type="application/json",
                response_schema=AnalysisResult,
                temperature=0.1
            )
        )
        st.session_state.result_data = json.loads(response.text)
        st.session_state.analysis_done = True
    except Exception as e:
        st.error(f"Erro na API: {e}")
    finally:
        stop_timer = True; thread.join(); timer.empty()

# ============================================================
# RESULTADOS (VISUAL DA FENOMENOLOGIA)
# ============================================================
if st.session_state.analysis_done:
    res = st.session_state.result_data
    tabs = st.tabs(["☰ Unidades (US)", "📄 Significados", "🏷️ Categorias", "🧩 Temas", "🧭 Mapeamento"])
    
    with tabs[0]: # US com Citação Formatada
        if res.get("fenomenologico"):
            for u in res["fenomenologico"].get("unidades_sentido", []):
                st.markdown(f'<div class="qa-shell" style="border-left:6px solid var(--blue-dark);"><span class="chip">{u.get("id_unidade")}</span> <span class="chip" style="background:var(--muted);">{u.get("documento")}</span><div class="quote" style="margin-top:10px;">{u.get("citacao_formatada")}</div></div>', unsafe_allow_html=True)

    with tabs[2]: # Categorias (VISUAL ROXO DA IMAGEM)
        if res.get("fenomenologico"):
            cats = res["fenomenologico"].get("categorias", [])
            cols = st.columns(len(cats) if cats else 1)
            for i, c in enumerate(cats):
                with cols[i]:
                    st.markdown(f'<div class="qa-shell" style="height:100%; border-top:6px solid purple;"><h4 style="color:purple; text-align:center;">{c.get("nome")}</h4><p style="font-size:14px; text-align:justify;">{c.get("descricao")}</p><hr><small>US RELACIONADAS:</small><br>{" ".join([f'<span class="chip" style="background:purple; font-size:10px;">{us}</span>' for us in c.get("unidades_relacionadas", [])])}</div>', unsafe_allow_html=True)

    with tabs[4]: # Mapeamento Sistemático
        if res.get("sistematico"):
            rows = []
            for doc in res["sistematico"].get("documentos", []):
                d = {"Documento": doc.get("documento")}
                for a in doc.get("respostas", []): d[a.get("pergunta")] = f"{a.get('evidencia_textual')} (p. {a.get('pagina')})"
                rows.append(d)
            if rows:
                df = pd.DataFrame(rows)
                render_quadro_html(df)
