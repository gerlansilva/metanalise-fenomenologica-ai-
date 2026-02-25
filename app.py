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
    page_title="Revisão sistemática",
    page_icon="📖",
    layout="wide"
)

# ============================================================
# SESSION STATE (evitar reprocessamento)
# ============================================================
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False

if "result_data" not in st.session_state:
    st.session_state.result_data = None

if "df_sys_long" not in st.session_state:
    st.session_state.df_sys_long = None

if "last_mode" not in st.session_state:
    st.session_state.last_mode = None


# ============================================================
# CSS / TEMA CLARO + CARDS
# ============================================================
st.markdown("""
<style>

.stApp {
    background: #ffffff !important;
    color: #111827 !important;
}

.header {
    font-weight: 800;
    font-size: 12px;
    letter-spacing: .08em;
    color: #6b7280;
    margin-bottom: 8px;
    text-transform: uppercase;
}

.doc-title {
    font-weight: 700;
    font-size: 16px;
    color: #111827;
}

.card {
    background-color: #f3f4f6;
    padding: 14px;
    border-radius: 12px;
    margin-bottom: 8px;
}

.evidence {
    border-left: 4px solid #d1d5db;
    padding-left: 10px;
    margin-top: 6px;
    font-style: italic;
}

.page {
    font-size: 12px;
    color: #6b7280;
}

.row-divider {
    border-top: 1px solid #e5e7eb;
    margin-top: 16px;
    margin-bottom: 16px;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# GEMINI CLIENT
# ============================================================
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error("Configure GEMINI_API_KEY")
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
    contexto_resumido: str | None
    justificativa_fenomenologica: str | None


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
    sistematico: SystematicResult | None = None


# ============================================================
# UI
# ============================================================
st.title("📖 Metanálise Fenomenológica AI")

mode = st.radio(
    "Modo de análise",
    ["Fenomenológico", "Mapeamento Sistemático", "Ambos"],
    horizontal=True
)

phenom_q = ""
sys_q = ""

if mode in ["Fenomenológico", "Ambos"]:

    phenom_q = st.text_area(
        "Interrogação fenomenológica",
        height=120
    )

if mode in ["Mapeamento Sistemático", "Ambos"]:

    sys_q = st.text_area(
        "Perguntas (uma por linha)",
        height=150
    )

uploaded_files = st.file_uploader(
    "Upload PDFs",
    type="pdf",
    accept_multiple_files=True
)


# ============================================================
# BOTÃO EXECUTAR
# ============================================================
run = st.button("Iniciar análise", type="primary", disabled=not uploaded_files)

if run:

    st.session_state.analysis_done = False
    st.session_state.result_data = None
    st.session_state.last_mode = mode

    with st.spinner("Processando..."):

        gemini_files = [
            types.Part.from_bytes(
                data=f.getvalue(),
                mime_type="application/pdf"
            )
            for f in uploaded_files
        ]

        prompt = "Leia os PDFs como corpus.\n\n"

        if mode in ["Fenomenológico", "Ambos"]:

            prompt += f"""
INTERROGAÇÃO FENOMENOLÓGICA:
{phenom_q}
"""

        if mode in ["Mapeamento Sistemático", "Ambos"]:

            prompt += f"""
MAPEAMENTO SISTEMÁTICO:
{sys_q}
"""

        contents = gemini_files + [prompt]

        schema = AnalysisResult

        if mode == "Fenomenológico":
            schema = PhenomenologicalResult

        if mode == "Mapeamento Sistemático":
            schema = SystematicResult

        response = client.models.generate_content(

            model="gemini-2.5-flash",

            contents=contents,

            config=types.GenerateContentConfig(
                response_schema=schema,
                response_mime_type="application/json",
                temperature=0.2
            )
        )

        result_data = json.loads(response.text)

        st.session_state.result_data = result_data
        st.session_state.analysis_done = True

        st.success("Análise concluída.")


# ============================================================
# RENDER RESULTADOS
# ============================================================
if st.session_state.analysis_done and st.session_state.result_data:

    result_data = st.session_state.result_data
    render_mode = st.session_state.last_mode

    st.header("Resultados")

    tabs = []

    if render_mode in ["Fenomenológico", "Ambos"]:
        tabs += ["Unidades de Sentido", "Unidades de Significado", "Categorias"]

    if render_mode in ["Mapeamento Sistemático", "Ambos"]:
        tabs += ["Mapeamento Sistemático"]

    st_tabs = st.tabs(tabs)

    phenom_data = (
        result_data
        if render_mode == "Fenomenológico"
        else result_data.get("fenomenologico", {})
    )

    sys_data = (
        result_data
        if render_mode == "Mapeamento Sistemático"
        else result_data.get("sistematico", {})
    )

    tab = 0


    # ============================================================
    # FENOMENOLÓGICO
    # ============================================================
    if render_mode in ["Fenomenológico", "Ambos"]:

        unidades = phenom_data.get("unidades_sentido", [])

        with st_tabs[tab]:

            if unidades:

                df = pd.DataFrame(unidades)

                st.dataframe(df, use_container_width=True)

                csv = df.to_csv(index=False).encode()

                st.download_button(
                    "Baixar CSV",
                    csv,
                    "unidades_sentido.csv"
                )

        tab += 1


        significado = phenom_data.get("unidades_significado", [])

        with st_tabs[tab]:

            if significado:

                df = pd.DataFrame(significado)

                st.dataframe(df)

        tab += 1


        categorias = phenom_data.get("categorias", [])

        with st_tabs[tab]:

            for cat in categorias:

                with st.expander(cat.get("nome", "")):

                    st.write(cat.get("descricao", ""))

        tab += 1


    # ============================================================
    # SISTEMÁTICO
    # ============================================================
    if render_mode in ["Mapeamento Sistemático", "Ambos"]:

        with st_tabs[tab]:

            docs = sys_data.get("documentos", [])

            rows = []

            for doc in docs:

                for ans in doc.get("respostas", []):

                    rows.append({

                        "Documento": doc.get("documento"),

                        "Pergunta": ans.get("pergunta"),

                        "Resposta": ans.get("resposta"),

                        "Evidência": ans.get("evidencia_textual"),

                        "Página": ans.get("pagina")

                    })

            df_long = pd.DataFrame(rows)

            st.session_state.df_sys_long = df_long


            # CSV topo
            csv = df_long.to_csv(index=False).encode()

            st.download_button(
                "⬇️ Baixar CSV (Mapeamento)",
                csv,
                "mapeamento.csv"
            )


            st.subheader("Comparação transversal")


            perguntas = df_long["Pergunta"].unique()

            for pergunta in perguntas:

                sub = df_long[df_long["Pergunta"] == pergunta]

                with st.expander(pergunta):

                    st.dataframe(sub, use_container_width=True)

                    for _, r in sub.iterrows():

                        st.markdown(f"""
<div class="doc-title">{r["Documento"]}</div>

<div class="card">{r["Resposta"]}</div>

<div class="evidence">
"{r["Evidência"]}"
<div class="page">Pág. {r["Página"]}</div>
</div>

<div class="row-divider"></div>
""", unsafe_allow_html=True)
