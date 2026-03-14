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
# IDENTIDADE VISUAL
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
  margin-bottom: 30px;
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
.qa-shell:hover { transform: translateY(-2px); }

.quote{
  font-family: "Asap Condensed", sans-serif;
  font-style: italic;
  font-size: 16px;
  line-height: 1.6;
  border-left: 5px solid var(--yellow);
  padding: 10px 15px;
  background: rgba(255, 203, 119, 0.1);
  border-radius: 0 12px 12px 0;
}

.chip{
  border-radius: 12px;
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 700;
  color: #FFF;
  background-color: var(--mint);
  margin-right: 5px;
}

.stButton > button {
  background-color: var(--coral) !important;
  color: #fff !important;
  border-radius: 24px !important;
  font-weight: 700 !important;
}
</style>
""", unsafe_allow_html=True)

# ============================================================
# MODELOS PYDANTIC ATUALIZADOS
# ============================================================
class UnidadeSentido(BaseModel):
    id_unidade: str = Field(description="Ex: US1, US2")
    documento: str
    pagina: int | None
    citacao_literal: str
    citacao_com_pagina: str = Field(description="Citação literal seguida da página, ex: 'Trecho...' (p. 10)")

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

# (Outros modelos permanecem iguais...)
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
# GEMINI CLIENT E LÓGICA DE ANÁLISE
# ============================================================
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

if "analysis_done" not in st.session_state: st.session_state.analysis_done = False
if "result_data" not in st.session_state: st.session_state.result_data = None
if "ris_pdfs" not in st.session_state: st.session_state.ris_pdfs = []
if "ris_texts" not in st.session_state: st.session_state.ris_texts = []

# (Interface e funções auxiliares de mapeamento permanecem as mesmas do seu código anterior...)
# Pulei para a parte do Prompt para focar na sua alteração:

def run_analysis(mode, phenom_q, thematic_q, sys_q, uploaded_files):
    gemini_files = [types.Part.from_bytes(data=f.getvalue(), mime_type="application/pdf") for f in (uploaded_files or [])]
    
    prompt_text = "Analise o corpus documental fornecido.\n\n"
    
    if "Fenomenológico" in mode or "Todos" in mode:
        prompt_text += (
            "=== MODO FENOMENOLÓGICO ===\n"
            f"INTERROGAÇÃO: {phenom_q}\n"
            "1. Extraia Unidades de Sentido (US).\n"
            "2. Para cada US, identifique OBRIGATORIAMENTE a página.\n"
            "3. No campo 'citacao_com_pagina', formate exatamente assim: \"Trecho literal...\" (p. XX).\n"
            "4. Transforme em Unidades de Significado e agrupe em Categorias.\n\n"
        )
    
    # ... (Restante do prompt para outros modos)

    response = client.models.generate_content(
        model="gemini-2.0-flash", # Ou o modelo que você estiver usando
        contents=gemini_files + [prompt_text],
        config=types.GenerateContentConfig(
            system_instruction="Você é um expert em análise qualitativa fenomenológica. Use JSON.",
            response_mime_type="application/json",
            response_schema=AnalysisResult,
            temperature=0.1,
        ),
    )
    return json.loads(response.text)

# ============================================================
# RENDERIZAÇÃO DOS RESULTADOS (A PARTE QUE VOCÊ PRECISAVA)
# ============================================================
st.markdown('<div class="qa-title-center">Análise Qualitativa AI</div>', unsafe_allow_html=True)

# ... (Sidebar e Lógica de Processamento)

if st.session_state.analysis_done:
    res = st.session_state.result_data
    
    # Abas dinâmicas baseadas no modo
    tabs = st.tabs(["☰ Unidades de Sentido", "📄 Unidades de Significado", "🏷️ Categorias"])
    
    # ABA 1: UNIDADES DE SENTIDO COM PÁGINA
    with tabs[0]:
        unidades = res.get("fenomenologico", {}).get("unidades_sentido", [])
        if unidades:
            for u in unidades:
                st.markdown(f"""
                <div class="qa-shell" style="border-left: 6px solid var(--blue-dark);">
                    <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
                        <div>
                            <span class="chip" style="background:var(--blue-dark);">{u.get('id_unidade')}</span>
                            <span class="chip" style="background:var(--muted); opacity:0.8;">{u.get('documento')}</span>
                        </div>
                        <span style="font-weight:bold; color:var(--coral);">Pág. {u.get('pagina')}</span>
                    </div>
                    <div class="quote">
                        {u.get('citacao_com_pagina')}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # ABA 2: UNIDADES DE SIGNIFICADO (SÍNTESE)
    with tabs[1]:
        significados = res.get("fenomenologico", {}).get("unidades_significado", [])
        for s in significados:
            st.markdown(f"""
            <div class="qa-shell">
                <span class="chip">{s.get('id_unidade')}</span>
                <div style="display:grid; grid-template-columns: 1fr 1fr; gap:20px; margin-top:15px;">
                    <div><small>TRECHO ORIGINAL</small><div class="quote" style="font-size:13px;">{s.get('trecho_original')}</div></div>
                    <div><small>SÍNTESE (SIGNIFICADO)</small><div style="padding:10px; background:#e8f4f8; border-radius:10px; font-weight:600;">{s.get('sintese')}</div></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ABA 3: CATEGORIAS (IGUAL À SUA IMAGEM)
    with tabs[2]:
        categorias = res.get("fenomenologico", {}).get("categorias", [])
        cols = st.columns(len(categorias) if categorias else 1)
        for i, cat in enumerate(categorias):
            with cols[i]:
                st.markdown(f"""
                <div class="qa-shell" style="height:100%; border-top: 5px solid purple;">
                    <h4 style="color:purple; text-align:center;">{cat.get('nome')}</h4>
                    <p style="font-size:14px; text-align:justify;">{cat.get('descricao')}</p>
                    <hr>
                    <small>UNIDADES RELACIONADAS:</small><br>
                    {' '.join([f'<span class="chip" style="background:purple; font-size:10px;">{us}</span>' for us in cat.get('unidades_relacionadas', [])])}
                </div>
                """, unsafe_allow_html=True)

# ... (Restante do seu código Streamlit original)
