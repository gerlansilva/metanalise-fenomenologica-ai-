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
# IDENTIDADE VISUAL (CSS)
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
.qa-title-center{ font-family: "Amiko", sans-serif; font-weight: 700; font-size: 52px; text-align: center; color: var(--blue-dark); margin-bottom: 20px;}
.qa-shell{ background: var(--panel); border: 1px solid rgba(23, 195, 178, 0.2); border-radius: var(--radius); box-shadow: var(--shadow); padding: 24px; margin-bottom: 20px; }
.quote{ font-family: "Asap Condensed", sans-serif; font-style: italic; font-size: 15px; line-height: 1.6; border-left: 5px solid var(--yellow); padding-left: 15px; background: rgba(255, 203, 119, 0.1); padding: 10px 15px; border-radius: 0 12px 12px 0; }
.chip{ border-radius: 12px; padding: 6px 14px; font-size: 12px; font-weight: 700; color: #FFF; background-color: var(--mint); margin-right: 5px;}
.stButton > button { background-color: var(--coral) !important; color: #fff !important; border-radius: 24px !important; font-weight: 700 !important; }

/* Custom Download Button */
div[data-testid="stDownloadButton"] > button {
    width: 45px !important; height: 45px !important; border-radius: 12px !important;
    background-color: var(--mint) !important; border: none !important; font-size: 20px !important;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# SESSION STATE E MODELOS
# ============================================================
for key in ["analysis_done", "result_data", "ris_pdfs", "ris_texts"]:
    if key not in st.session_state: st.session_state[key] = [] if "ris" in key else (None if key=="result_data" else False)

class UnidadeSentido(BaseModel):
    id_unidade: str; documento: str; pagina: int | None; citacao_literal: str

class UnidadeSignificado(BaseModel):
    id_unidade: str; documento: str; trecho_original: str; sintese: str

class Categoria(BaseModel):
    nome: str; descricao: str; unidades_relacionadas: list[str]

class PhenomenologicalResult(BaseModel):
    unidades_sentido: list[UnidadeSentido] = []; unidades_significado: list[UnidadeSignificado] = []; categorias: list[Categoria] = []

class SystematicAnswer(BaseModel):
    pergunta: str; resposta: str; evidencia_textual: str; pagina: int | None = None

class SystematicDocument(BaseModel):
    documento: str; respostas: list[SystematicAnswer] = []

class SystematicResult(BaseModel):
    documentos: list[SystematicDocument] = []

class AnalysisResult(BaseModel):
    fenomenologico: PhenomenologicalResult | None = None; sistematico: SystematicResult | None = None

# ============================================================
# FUNÇÕES DE UTILIDADE (COPIAR, BAIXAR, RIS)
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

def df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8-sig')

def copy_button(text, key):
    safe = text.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    components.html(f"""<button id="{key}" style="width:45px; height:45px; border-radius:12px; border:none; background-color:#FFCB77; color:#113F50; font-size:20px; cursor:pointer;">📋</button>
    <script>const btn=document.getElementById("{key}"); btn.onclick=async()=>{{await navigator.clipboard.writeText(`{safe}`); btn.innerText="✔️"; setTimeout(()=>btn.innerText="📋",1500);}}</script>""", height=55)

def render_quadro_html(df):
    def esc(x): return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    html = f"""<div style="overflow:auto; max-height:550px; border-radius:15px; border:1px solid #17C3B2; background:white; font-family:Asap;">
    <table style="width:100%; border-collapse:collapse; font-size:14px;">
    <thead><tr style="background:#227C9D; color:white;">{''.join([f'<th style="padding:15px; position:sticky; top:0; z-index:2;">{esc(c)}</th>' for c in df.columns])}</tr></thead>
    <tbody>{''.join([f'<tr>{" ".join([f"<td style=\'padding:12px; border:1px solid #eee; text-align:justify;\'>{esc(v)}</td>" for v in row])}</tr>' for row in df.values])}</tbody>
    </table></div>"""
    components.html(html, height=580, scrolling=True)

# ============================================================
# LÓGICA PRINCIPAL
# ============================================================
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

st.markdown('<div class="qa-title-center">Análise Qualitativa AI</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Configurações")
    mode = st.radio("Modo", ["Fenomenológico", "Mapeamento", "Todos"])
    p_q = st.text_area("Pergunta Fenomenológica") if "Fenomenológico" in mode or "Todos" in mode else ""
    s_q = st.text_area("Perguntas Mapeamento") if "Mapeamento" in mode or "Todos" in mode else ""
    
    u_files = st.file_uploader("Upload PDFs", type="pdf", accept_multiple_files=True)
    run = st.button("🚀 Iniciar Análise", type="primary")

if run and u_files:
    st.session_state.analysis_done = False
    timer = st.empty()
    stop_timer, start_time = False, time.time()
    def update_t():
        while not stop_timer:
            elapsed = int(time.time() - start_time)
            timer.markdown(f'<div style="text-align:center; padding:10px; background:#fff; border:2px solid #17C3B2; border-radius:15px;">🧠 Analisando com Gemini 2.5... {elapsed}s</div>', unsafe_allow_html=True)
            time.sleep(1)
    t = threading.Thread(target=update_t); add_script_run_ctx(t); t.start()

    try:
        parts = [types.Part.from_bytes(data=f.getvalue(), mime_type="application/pdf") for f in u_files]
        prompt = f"Realize a análise.\nFENOMENOLOGIA: {p_q}. Extraia US com página no campo citacao_literal: \"Texto...\" (p. X).\nMAPEAMENTO: {s_q}."
        
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=parts + [prompt],
            config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=AnalysisResult, temperature=0.1)
        )
        st.session_state.result_data = json.loads(response.text)
        st.session_state.analysis_done = True
    except Exception as e: st.error(f"Erro: {e}")
    finally: stop_timer = True; t.join(); timer.empty()

# ============================================================
# RESULTADOS E DOWNLOADS
# ============================================================
if st.session_state.analysis_done and st.session_state.result_data:
    res = st.session_state.result_data
    tabs = st.tabs(["☰ Unidades", "📄 Significados", "🏷️ Categorias", "🧭 Mapeamento"])
    
    if res.get("fenomenologico"):
        with tabs[0]:
            for u in res["fenomenologico"].get("unidades_sentido", []):
                st.markdown(f'<div class="qa-shell" style="border-left:6px solid var(--blue-dark);"><span class="chip">{u.get("id_unidade")}</span> <span class="chip" style="background:#4A7A8C;">{u.get("documento")}</span><div class="quote" style="margin-top:10px;">{u.get("citacao_literal")}</div></div>', unsafe_allow_html=True)
        
        with tabs[1]:
            for s in res["fenomenologico"].get("unidades_significado", []):
                st.markdown(f'<div class="qa-shell"><span class="chip">{s.get("id_unidade")}</span><div style="display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-top:10px;"><div><small>TRECHO</small><div class="quote">{s.get("trecho_original")}</div></div><div><small>SÍNTESE</small><div style="padding:15px; background:#e8f4f8; border-radius:10px; font-weight:700;">{s.get("sintese")}</div></div></div></div>', unsafe_allow_html=True)

        with tabs[2]:
            cats = res["fenomenologico"].get("categorias", [])
            cols = st.columns(len(cats) if cats else 1)
            for i, c in enumerate(cats):
                with cols[i % len(cols)]:
                    st.markdown(f'<div class="qa-shell" style="height:100%; border-top:6px solid purple;"><h4 style="color:purple; text-align:center;">{c.get("nome")}</h4><p style="font-size:14px; text-align:justify;">{c.get("descricao")}</p><hr><small>US:</small><br>{" ".join([f"<span class=\'chip\' style=\'background:purple; font-size:10px;\'>{us}</span>" for us in c.get("unidades_relacionadas", [])])}</div>', unsafe_allow_html=True)

    if res.get("sistematico"):
        with tabs[3]:
            rows = []
            for doc in res["sistematico"].get("documentos", []):
                d = {"Documento": doc.get("documento")}
                for a in doc.get("respostas", []): d[a.get("pergunta")] = f"{a.get('evidencia_textual')} (p. {a.get('pagina')})"
                rows.append(d)
            if rows:
                df_map = pd.DataFrame(rows)
                col_t, col_c, col_d = st.columns([0.8, 0.05, 0.05])
                with col_t: st.subheader("Quadro de Mapeamento")
                with col_c: copy_button(df_map.to_csv(sep='\t', index=False), "copy_map")
                with col_d: st.download_button("⬇️", df_to_csv(df_map), "mapeamento.csv", "text/csv")
                render_quadro_html(df_map)
