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
# IDENTIDADE VISUAL (CSS ORIGINAL PRESERVADO)
# ============================================================
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Amiko:wght@400;600;700&family=Annie+Use+Your+Telescope&family=Asap+Condensed:wght@400;600;700&family=Asap:wght@400;600;700&display=swap" rel="stylesheet">

<style>
:root{
  --blue-dark: #227C9D;
  --mint: #17C3B2;
  --yellow: #FFCB77;
  --cream: #FEF9EF;
  --coral: #FE6D73;
  --bg: var(--cream); 
  --panel: #FFFFFF;
  --panel2: #FFF5E1; 
  --text-dark: #113F50; 
  --muted: #4A7A8C;
  --shadow: 0 8px 24px rgba(34, 124, 157, 0.1);
  --shadow2: 0 4px 12px rgba(23, 195, 178, 0.15);
  --radius: 20px;
}

html, body { background: var(--bg) !important; }
.stApp { background: var(--bg) !important; color: var(--text-dark) !important; }
* { font-family: "Asap", system-ui, -apple-system, sans-serif; }

.block-container { max-width: 1320px; padding-top: 28px; padding-bottom: 32px; }

.qa-title-center{
  font-family: "Amiko", sans-serif;
  font-weight: 700;
  font-size: 52px;
  text-align: center;
  color: var(--blue-dark);
}

.qa-shell{
  background: var(--panel);
  border: 1px solid rgba(23, 195, 178, 0.2);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 24px;
  margin-bottom: 20px;
  transition: transform 0.2s ease;
}

.quote{
  font-family: "Asap Condensed", sans-serif;
  font-style: italic;
  font-size: 16px;
  line-height: 1.6;
  border-left: 5px solid var(--yellow);
  padding: 8px 15px;
  background: rgba(255, 203, 119, 0.1);
  border-radius: 0 12px 12px 0;
}

.chip{
  border-radius: 12px;
  padding: 6px 14px;
  font-size: 13px;
  font-weight: 700;
  color: #FFF;
  background-color: var(--mint);
}

.stButton > button {
  background-color: var(--coral) !important;
  color: #fff !important;
  border-radius: 24px !important;
  font-weight: 700 !important;
  width: 100%;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# SESSION STATE
# ============================================================
for key in ["analysis_done", "result_data", "last_mode", "ris_pdfs", "ris_texts"]:
    if key not in st.session_state: st.session_state[key] = None if key in ["result_data", "last_mode"] else ([] if "ris" in key else False)

# ============================================================
# GEMINI CLIENT
# ============================================================
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# ============================================================
# MODELOS PYDANTIC (UNIFICADOS E MELHORADOS)
# ============================================================
class UnidadeSentido(BaseModel):
    id_unidade: str
    documento: str
    pagina: int | None
    citacao_literal: str
    citacao_formatada: str = Field(description="Citação literal e página no formato: 'Texto...' (p. X).")

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

class ThematicTheme(BaseModel):
    nome: str
    descricao: str
    codigos_relacionados: list[str]

class ThematicResult(BaseModel):
    codigos: list[ThematicCode]
    temas: list[ThematicTheme]

class SystematicAnswer(BaseModel):
    pergunta: str
    resposta: str
    evidencia_textual: str
    pagina: int | None

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
# FUNÇÕES AUXILIARES (RIS, UNPAYWALL, TSV)
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
            pdf_url = res.json()['best_oa_location'].get('url_for_pdf')
            if pdf_url:
                pdf_res = requests.get(pdf_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
                if pdf_res.status_code == 200: return pdf_res.content
    except: pass
    return None

def df_to_tsv(df):
    output = io.StringIO()
    df.to_csv(output, sep='\t', index=False, quoting=csv.QUOTE_MINIMAL)
    return output.getvalue()

def render_quadro_html(df, max_height_px=650):
    def esc(x): return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    html = f"""<style>.qa-wrap{{overflow:auto; max-height:{max_height_px}px; border-radius:16px; border:1px solid #17C3B2; background:#FFF;}}
    table.qa-table{{border-collapse:collapse; width:100%; font-size:14px; color:#113F50;}}
    th{{position:sticky; top:0; background:#227C9D; color:#FEF9EF; padding:16px; font-weight:700; text-align:center; min-width:300px;}}
    td{{padding:16px; border-bottom:1px solid #eee; vertical-align:top; text-align:justify; white-space:pre-wrap;}}
    .doc-col{{position:sticky; left:0; background:#FFF; font-weight:700; color:#227C9D; border-right:1px solid #17C3B2; text-align:center; vertical-align:middle; width:200px;}}</style>
    <div class="qa-wrap"><table class="qa-table"><thead><tr>"""
    for i, col in enumerate(df.columns): html += f"<th>{esc(col)}</th>"
    html += "</tr></thead><tbody>"
    for _, row in df.iterrows():
        html += "<tr>"
        for i, col in enumerate(df.columns):
            cl = ' class="doc-col"' if i == 0 else ""
            html += f"<td{cl}>{esc(row[col])}</td>"
        html += "</tr>"
    html += "</tbody></table></div>"
    components.html(html, height=max_height_px + 30, scrolling=True)

# ============================================================
# INTERFACE E LÓGICA DE EXECUÇÃO
# ============================================================
st.markdown('<div class="qa-title-center">Análise Qualitativa AI</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Configurações")
    mode = st.radio("Modo", ["Fenomenológico", "Temático (Braun & Clarke)", "Mapeamento Sistemático", "Todos (3 modos)"])
    
    phenom_q = st.text_area("Interrogação Fenomenológica", height=100) if "Fenomenológico" in mode or "Todos" in mode else ""
    thematic_q = st.text_area("Questão Temática", height=100) if "Temático" in mode or "Todos" in mode else ""
    sys_q = st.text_area("Perguntas Mapeamento", height=100) if "Mapeamento" in mode or "Todos" in mode else ""
    
    st.subheader("📚 Corpus")
    with st.expander("📥 RIS / DOI"):
        ris_file = st.file_uploader("Arquivo .ris", type=["ris", "txt"])
        if ris_file and st.button("Processar RIS"):
            entries = parse_ris(ris_file.getvalue().decode("utf-8", errors="ignore"))
            for entry in entries:
                doi = entry.get('DO', '').replace('https://doi.org/', '').strip()
                pdf = fetch_oa_pdf(doi) if doi else None
                if pdf: st.session_state.ris_pdfs.append({"name": entry.get('TI', 'Doc')+'.pdf', "bytes": pdf})
                else: st.session_state.ris_texts.append({"name": entry.get('TI', 'Resumo'), "text": entry.get('AB', '')})
    
    uploaded_files = st.file_uploader("PDFs Manuais", type="pdf", accept_multiple_files=True)
    total_docs = len(uploaded_files or []) + len(st.session_state.ris_pdfs) + len(st.session_state.ris_texts)
    run = st.button("🚀 Iniciar Análise", type="primary", disabled=(total_docs == 0))

if run:
    st.session_state.analysis_done = False
    timer_placeholder = st.empty()
    stop_timer, start_time = False, time.time()

    def timer_loop():
        while not stop_timer:
            elapsed = int(time.time() - start_time)
            prog = min(99, int((elapsed / (total_docs * 10 + 5)) * 90))
            timer_placeholder.markdown(f'<div style="background:#FFF; padding:20px; border-radius:15px; border:2px solid #17C3B2; text-align:center;">🧠 Analisando... {prog}% | {elapsed}s</div>', unsafe_allow_html=True)
            time.sleep(1)

    t = threading.Thread(target=timer_loop); add_script_run_ctx(t); t.start()

    try:
        contents = [types.Part.from_bytes(data=f.getvalue(), mime_type="application/pdf") for f in (uploaded_files or [])]
        for p in st.session_state.ris_pdfs: contents.append(types.Part.from_bytes(data=p['bytes'], mime_type="application/pdf"))
        for t_doc in st.session_state.ris_texts: contents.append(types.Part.from_text(text=t_doc['text']))
        
        prompt = f"Analise o corpus.\n\n"
        if phenom_q: prompt += f"FENOMENOLOGIA: {phenom_q}. Extraia US com página. Formate 'citacao_formatada' como: 'Trecho...' (p. X).\n"
        if thematic_q: prompt += f"TEMÁTICA: {thematic_q}. Crie códigos e temas.\n"
        if sys_q: prompt += f"MAPEAMENTO: {sys_q}. Use citações literais.\n"

        response = client.models.generate_content(
            model="gemini-2.0-flash", contents=contents + [prompt],
            config=types.GenerateContentConfig(system_instruction="Use JSON.", response_mime_type="application/json", response_schema=AnalysisResult)
        )
        st.session_state.result_data = json.loads(response.text)
        st.session_state.analysis_done, st.session_state.last_mode = True, mode
    finally:
        stop_timer = True; t.join(); timer_placeholder.empty()

# ============================================================
# RENDERIZAÇÃO DOS RESULTADOS
# ============================================================
if st.session_state.analysis_done:
    res = st.session_state.result_data
    tabs = st.tabs(["☰ Unidades (US)", "📄 Significados", "🏷️ Categorias", "🧩 Temático", "🧭 Mapeamento"])
    
    with tabs[0]: # Unidades de Sentido
        if res.get("fenomenologico"):
            for u in res["fenomenologico"]["unidades_sentido"]:
                st.markdown(f'<div class="qa-shell" style="border-left:6px solid var(--blue-dark);"><span class="chip">{u["id_unidade"]}</span> <span class="chip" style="background:var(--muted);">{u["documento"]}</span><div class="quote" style="margin-top:10px;">{u["citacao_formatada"]}</div></div>', unsafe_allow_html=True)

    with tabs[1]: # Unidades de Significado
        if res.get("fenomenologico"):
            for s in res["fenomenologico"]["unidades_significado"]:
                st.markdown(f'<div class="qa-shell"><span class="chip">{s["id_unidade"]}</span><div style="display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-top:10px;"><div><small>ORIGINAL</small><div class="quote">{s["trecho_original"]}</div></div><div><small>SÍNTESE</small><div style="padding:15px; background:#e8f4f8; border-radius:10px;">{s["sintese"]}</div></div></div></div>', unsafe_allow_html=True)

    with tabs[2]: # Categorias (VISUAL DA IMAGEM)
        if res.get("fenomenologico"):
            cats = res["fenomenologico"]["categorias"]
            cols = st.columns(len(cats) if cats else 1)
            for i, c in enumerate(cats):
                with cols[i]:
                    st.markdown(f'<div class="qa-shell" style="height:100%; border-top:6px solid purple;"><h4 style="color:purple; text-align:center;">{c["nome"]}</h4><p style="font-size:14px; text-align:justify;">{c["descricao"]}</p><hr><small>RELACIONADAS:</small><br>{" ".join([f'<span class="chip" style="background:purple; font-size:10px;">{us}</span>' for us in c["unidades_relacionadas"]])}</div>', unsafe_allow_html=True)

    with tabs[3]: # Temático
        if res.get("tematico"):
            for t in res["tematico"]["temas"]:
                st.markdown(f'<div class="qa-shell"><h3>🧩 {t["nome"]}</h3><p>{t["descricao"]}</p></div>', unsafe_allow_html=True)

    with tabs[4]: # Mapeamento
        if res.get("sistematico"):
            rows = []
            for doc in res["sistematico"]["documentos"]:
                d = {"Documento": doc["documento"]}
                for a in doc["respostas"]: d[a["pergunta"]] = f"{a['evidencia_textual']} (p. {a['pagina']})"
                rows.append(d)
            df = pd.DataFrame(rows)
            render_quadro_html(df)
            st.download_button("Baixar Quadro", df_to_tsv(df), "mapeamento.tsv")
