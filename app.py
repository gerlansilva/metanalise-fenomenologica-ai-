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
# IDENTIDADE VISUAL (CSS CUSTOMIZADO)
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
  --text-dark: #113F50; 
  --muted: #4A7A8C;
  --shadow: 0 8px 24px rgba(34, 124, 157, 0.1);
  --radius: 20px;
}

html, body { background: var(--bg) !important; }
.stApp { background: var(--bg) !important; color: var(--text-dark) !important; }
* { font-family: "Asap", sans-serif; }

.qa-title-center{
  font-family: "Amiko", sans-serif;
  font-weight: 700;
  font-size: 52px;
  text-align: center;
  color: var(--blue-dark);
  margin-bottom: 5px;
}

.qa-subtitle-center {
  font-family: "Annie Use Your Telescope", cursive;
  text-align: center;
  color: var(--coral);
  font-size: 26px;
  margin-bottom: 35px;
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
  font-size: 15px;
  line-height: 1.6;
  border-left: 5px solid var(--yellow);
  padding: 10px 15px;
  background: rgba(255, 203, 119, 0.1);
  border-radius: 0 12px 12px 0;
}

.chip{
  border-radius: 12px;
  padding: 4px 12px;
  font-size: 11px;
  font-weight: 700;
  color: #FFF;
  background-color: var(--mint);
  margin-right: 5px;
}

/* Botão Principal */
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
# MODELOS DE DADOS (PYDANTIC)
# ============================================================
class UnidadeSentido(BaseModel):
    id_unidade: str
    documento: str
    pagina: int | None
    citacao_formatada: str = Field(description="Citação literal e página: 'Texto...' (p. X)")

class UnidadeSignificado(BaseModel):
    id_unidade: str
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
# FUNÇÕES DE APOIO
# ============================================================
def df_to_tsv(df):
    output = io.StringIO()
    df.to_csv(output, sep='\t', index=False)
    return output.getvalue()

def render_quadro_html(df):
    html = f"""
    <div style="overflow-x:auto; border-radius:15px; border:1px solid #17C3B2;">
        <table style="width:100%; border-collapse: collapse; font-family:Asap; font-size:13px;">
            <thead>
                <tr style="background:#227C9D; color:white;">
                    {''.join([f'<th style="padding:12px; border:1px solid #ddd;">{c}</th>' for c in df.columns])}
                </tr>
            </thead>
            <tbody>
                {''.join([f'<tr>{" ".join([f"<td style=\'padding:10px; border:1px solid #eee; text-align:justify;\'>{v}</td>" for v in row])}</tr>' for row in df.values])}
            </tbody>
        </table>
    </div>
    """
    components.html(html, height=500, scrolling=True)

# ============================================================
# LOGICA DE SESSÃO E API
# ============================================================
if "analysis_done" not in st.session_state: st.session_state.analysis_done = False
if "result_data" not in st.session_state: st.session_state.result_data = None

api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# ============================================================
# INTERFACE - SIDEBAR
# ============================================================
with st.sidebar:
    st.header("⚙️ Configurações")
    mode = st.selectbox("Modo de Análise", ["Todos (3 modos)", "Fenomenológico", "Temático", "Mapeamento"])
    
    phenom_q = st.text_area("Interrogação Fenomenológica", "Como o fenômeno se manifesta?")
    thematic_q = st.text_area("Questão Temática", "Quais padrões emergem dos dados?")
    sys_q = st.text_area("Perguntas Mapeamento (1 por linha)", "Objetivo?\nMetodologia?")
    
    uploaded_files = st.file_uploader("Upload PDFs", type="pdf", accept_multiple_files=True)
    run = st.button("🚀 Iniciar Análise", type="primary")

# ============================================================
# EXECUÇÃO DA ANÁLISE
# ============================================================
if run and uploaded_files:
    with st.spinner("Analisando documentos..."):
        parts = [types.Part.from_bytes(data=f.getvalue(), mime_type="application/pdf") for f in uploaded_files]
        
        prompt = f"""
        Analise o corpus anexado seguindo estas diretrizes:
        
        1. FENOMENOLOGIA:
           - Pergunta: {phenom_q}
           - Extraia Unidades de Sentido (US) com página.
           - No campo 'citacao_formatada', use o formato: "Texto literal..." (p. X).
           
        2. TEMÁTICA:
           - Pergunta: {thematic_q}
           - Crie códigos e temas (Braun & Clarke).
           
        3. MAPEAMENTO:
           - Responda: {sys_q}
           - Use evidências literais.
        """
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=parts + [prompt],
            config=types.GenerateContentConfig(
                system_instruction="Assistente de Pesquisa Qualitativa. Responda estritamente em JSON.",
                response_mime_type="application/json",
                response_schema=AnalysisResult,
                temperature=0.2
            )
        )
        st.session_state.result_data = json.loads(response.text)
        st.session_state.analysis_done = True

# ============================================================
# EXIBIÇÃO DOS RESULTADOS
# ============================================================
if st.session_state.analysis_done:
    res = st.session_state.result_data
    st.markdown('<div class="qa-title-center">Análise Qualitativa AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="qa-subtitle-center">Resultados Processados com IA</div>', unsafe_allow_html=True)

    tab_list = []
    if res.get("fenomenologico"): tab_list.extend(["☰ Unidades", "🏷️ Categorias"])
    if res.get("tematico"): tab_list.append("🧩 Temas")
    if res.get("sistematico"): tab_list.append("🧭 Mapeamento")
    
    st_tabs = st.tabs(tab_list)
    curr = 0

    # --- ABA FENOMENOLOGIA (UNIDADES) ---
    if res.get("fenomenologico"):
        with st_tabs[curr]:
            for us in res["fenomenologico"]["unidades_sentido"]:
                st.markdown(f"""
                <div class="qa-shell" style="border-left: 5px solid var(--blue-dark);">
                    <span class="chip" style="background:var(--blue-dark);">{us['id_unidade']}</span>
                    <span class="chip" style="background:var(--muted);">{us['documento']}</span>
                    <div class="quote" style="margin-top:10px;">{us['citacao_formatada']}</div>
                </div>
                """, unsafe_allow_html=True)
        curr += 1
        
        with st_tabs[curr]:
            cats = res["fenomenologico"]["categorias"]
            cols = st.columns(len(cats))
            for i, c in enumerate(cats):
                with cols[i]:
                    st.markdown(f"""
                    <div class="qa-shell" style="border-top: 5px solid purple; height:100%;">
                        <h4 style="color:purple; text-align:center;">{c['nome']}</h4>
                        <p style="font-size:13px; text-align:justify;">{c['descricao']}</p>
                        <hr>
                        { ' '.join([f'<span class="chip" style="background:purple; font-size:9px;">{u}</span>' for u in c['unidades_relacionadas']]) }
                    </div>
                    """, unsafe_allow_html=True)
        curr += 1

    # --- ABA TEMÁTICA ---
    if res.get("tematico"):
        with st_tabs[curr]:
            for t in res["tematico"]["temas"]:
                st.markdown(f"### 🧩 Tema: {t['nome']}")
                st.info(t['descricao'])
                st.write(f"Códigos: {', '.join(t['codigos_relacionados'])}")
        curr += 1

    # --- ABA MAPEAMENTO ---
    if res.get("sistematico"):
        with st_tabs[curr]:
            data_map = []
            for doc in res["sistematico"]["documentos"]:
                row = {"Documento": doc["documento"]}
                for ans in doc["respostas"]:
                    row[ans["pergunta"]] = f"{ans['evidencia_textual']} (p. {ans['pagina']})"
                data_map.append(row)
            df_map = pd.DataFrame(data_map)
            render_quadro_html(df_map)
            st.download_button("Baixar TSV", df_to_tsv(df_map), "mapeamento.tsv")
