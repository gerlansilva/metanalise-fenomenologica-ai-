import streamlit as st
import pandas as pd
import json
import os
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# =========================
# Configuração da página
# =========================
st.set_page_config(page_title="Metanálise Fenomenológica AI", page_icon="📖", layout="wide")

# =========================
# Forçar tema claro (fundo branco) + melhorar legibilidade
# =========================
st.markdown(
    """
    <style>
      .stApp { background: #ffffff !important; color: #111827 !important; }
      h1, h2, h3, h4, h5, h6 { color: #111827 !important; }

      /* Inputs e textareas */
      textarea, input, .stTextInput > div > div > input {
        background-color: #ffffff !important;
        color: #111827 !important;
      }

      /* Labels e textos */
      label, .stMarkdown, .stMarkdown p, .stCaption, .stText, div, span {
        color: #111827 !important;
      }

      /* Dataframes */
      [data-testid="stDataFrame"] { background: #ffffff !important; }
      .stDataFrame { background: #ffffff !important; }

      /* Sidebar/header/footer (evitar fundo escuro) */
      div[data-testid="stSidebar"], header, footer { background: #ffffff !important; }

      /* Botões */
      .stButton>button { border-radius: 10px; }

      /* Melhorar padding em expanders */
      details { background: #ffffff !important; border-radius: 12px; }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# Inicializa o cliente Gemini
# =========================
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.warning("⚠️ Variável de ambiente GEMINI_API_KEY não encontrada. Por favor, configure-a para continuar.")
    st.stop()

client = genai.Client(api_key=api_key)

# =========================
# Modelos Pydantic para Saída Estruturada
# =========================
class UnidadeSentido(BaseModel):
    id_unidade: str = Field(description="ID único automático, ex: DOC01_P087_US03")
    documento: str = Field(description="Nome do arquivo PDF")
    pagina: int | None = Field(description="Número da página onde o trecho aparece, null se não encontrado")
    citacao_literal: str = Field(description="Trecho exato do texto, sem alterações")
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
    sistematico: SystematicResult | None = None

# =========================
# UI
# =========================
st.title("📖 Metanálise Fenomenológica AI")
st.markdown(
    """
Faça o upload de múltiplos artigos em PDF e escolha o modo de análise.  
O sistema analisará os textos como um corpus único, extraindo unidades fenomenológicas  
ou realizando um mapeamento sistemático.
"""
)

mode = st.radio(
    "Modo de Análise",
    ["Fenomenológico", "Mapeamento Sistemático", "Ambos"],
    horizontal=True,
    help="Fenomenológico: Unidades de sentido, significado e categorias. Sistemático: Respostas objetivas a perguntas diretas."
)

phenom_q = ""
sys_q = ""

if mode in ["Fenomenológico", "Ambos"]:
    phenom_q = st.text_area(
        "Interrogação Fenomenológica",
        placeholder="Ex: Como o campo da Educação Estatística se constitui nos textos analisados?",
        height=100
    )

if mode in ["Mapeamento Sistemático", "Ambos"]:
    sys_q = st.text_area(
        "Perguntas para Mapeamento Sistemático",
        placeholder="1. Qual é o objetivo do estudo?\n2. Qual metodologia é utilizada?\n3. Qual referencial teórico?",
        height=150,
        help="Insira uma pergunta por linha."
    )

uploaded_files = st.file_uploader("Corpus Documental (PDFs)", type="pdf", accept_multiple_files=True)

# =========================
# Botão de execução
# =========================
if st.button("Iniciar Análise do Corpus", type="primary", disabled=not uploaded_files):
    if mode in ["Fenomenológico", "Ambos"] and not phenom_q.strip():
        st.warning("Por favor, preencha a Interrogação Fenomenológica.")
        st.stop()
    if mode in ["Mapeamento Sistemático", "Ambos"] and not sys_q.strip():
        st.warning("Por favor, preencha as Perguntas para Mapeamento Sistemático.")
        st.stop()

    # Validação de tamanho (limite de ~15MB para não estourar tokens)
    total_size = sum([f.size for f in uploaded_files])
    if total_size > 15 * 1024 * 1024:
        st.error(
            f"O tamanho total dos arquivos ({total_size / 1024 / 1024:.2f} MB) excede o limite seguro de 15 MB. "
            f"Por favor, reduza o número de PDFs."
        )
        st.stop()

    with st.spinner("Analisando o corpus documental... Isso pode levar alguns minutos."):
        try:
            # Preparar arquivos para a API do Gemini
            gemini_files = []
            for file in uploaded_files:
                gemini_files.append(
                    types.Part.from_bytes(
                        data=file.getvalue(),
                        mime_type="application/pdf"
                    )
                )

            prompt_text = "Leia todos os PDFs anexados como um corpus único.\n\n"

            if mode in ["Fenomenológico", "Ambos"]:
                prompt_text += "=== MODO FENOMENOLÓGICO ===\n"
                prompt_text += f"INTERROGAÇÃO FENOMENOLÓGICA:\n\"{phenom_q}\"\n\n"
                prompt_text += "Execute:\n"
                prompt_text += "ETAPA 1: Extraia unidades de sentido. Para cada unidade indique documento, página, citação literal exata, breve contexto e justificativa.\n"
                prompt_text += "Regras: NÃO parafrasear a citação, NÃO inventar páginas, NÃO omitir documento, cada unidade deve ser rastreável.\n"
                prompt_text += "ETAPA 2: Transforme cada unidade em unidade de significado.\n"
                prompt_text += "ETAPA 3: Agrupe convergências entre documentos.\n"
                prompt_text += "ETAPA 4: Sugira categorias fenomenológicas.\n\n"

            if mode in ["Mapeamento Sistemático", "Ambos"]:
                prompt_text += "=== MODO MAPEAMENTO SISTEMÁTICO ===\n"
                prompt_text += "Responda às seguintes perguntas para CADA documento anexado:\n"
                prompt_text += f"{sys_q}\n\n"
                prompt_text += "Regras: Forneça respostas objetivas, cite a evidência textual exata e a página onde foi encontrada.\n"
                prompt_text += "Se a página não puder ser identificada com certeza, retorne null.\n\n"

            contents = gemini_files + [prompt_text]

            # Selecionar o Schema correto baseado no modo
            schema = AnalysisResult
            if mode == "Fenomenológico":
                schema = PhenomenologicalResult
            elif mode == "Mapeamento Sistemático":
                schema = SystematicResult

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction="""Você é um assistente de análise qualitativa de corpus documental.
Você analisará múltiplos artigos científicos como um corpus único.
Siga estritamente as instruções do prompt e preencha o JSON de saída corretamente.
Nunca invente conteúdo. Sempre preserve a rastreabilidade.
Se o número da página não puder ser identificado com certeza, retorne null para a página.""",
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0.2
                ),
            )

            st.success("Análise concluída com sucesso!")

            # Parse da resposta JSON
            result_data = json.loads(response.text)

            st.header("Resultados da Análise")

            tabs = []
            if mode in ["Fenomenológico", "Ambos"]:
                tabs.extend(["Unidades de Sentido", "Unidades de Significado", "Categorias"])
            if mode in ["Mapeamento Sistemático", "Ambos"]:
                tabs.append("Mapeamento Sistemático")

            st_tabs = st.tabs(tabs)

            phenom_data = result_data if mode == "Fenomenológico" else result_data.get("fenomenologico")
            sys_data = result_data if mode == "Mapeamento Sistemático" else result_data.get("sistematico")

            tab_idx = 0

            # =========================
            # FENOMENOLÓGICO
            # =========================
            if mode in ["Fenomenológico", "Ambos"] and phenom_data:
                # Aba 1: Unidades de Sentido
                with st_tabs[tab_idx]:
                    df_sentido = pd.DataFrame(phenom_data["unidades_sentido"])

                    st.dataframe(
                        df_sentido,
                        use_container_width=True,
                        height=520,
                        column_config={
                            "id_unidade": st.column_config.TextColumn("ID", width="small"),
                            "documento": st.column_config.TextColumn("Documento", width="medium"),
                            "pagina": st.column_config.NumberColumn("Página", width="small"),
                            "citacao_literal": st.column_config.TextColumn("Citação literal", width="large"),
                            "contexto_resumido": st.column_config.TextColumn("Contexto", width="medium"),
                            "justificativa_fenomenologica": st.column_config.TextColumn("Justificativa", width="medium"),
                        },
                    )

                    csv = df_sentido.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "Baixar CSV (Unidades de Sentido)",
                        csv,
                        "unidades_sentido.csv",
                        "text/csv"
                    )

                    st.subheader("Detalhes (leitura confortável)")
                    for _, r in df_sentido.iterrows():
                        titulo = f"{r.get('id_unidade','(sem id)')} — {r.get('documento','(sem doc)')} (p. {r.get('pagina')})"
                        with st.expander(titulo):
                            st.markdown("**Citação literal**")
                            st.write(r.get("citacao_literal", ""))
                            if pd.notna(r.get("contexto_resumido")) and r.get("contexto_resumido"):
                                st.markdown("**Contexto resumido**")
                                st.write(r.get("contexto_resumido"))
                            if pd.notna(r.get("justificativa_fenomenologica")) and r.get("justificativa_fenomenologica"):
                                st.markdown("**Justificativa fenomenológica**")
                                st.write(r.get("justificativa_fenomenologica"))

                tab_idx += 1

                # Aba 2: Unidades de Significado
                with st_tabs[tab_idx]:
                    df_sig = pd.DataFrame(phenom_data["unidades_significado"])

                    st.dataframe(
                        df_sig,
                        use_container_width=True,
                        height=520,
                        column_config={
                            "id_unidade": st.column_config.TextColumn("ID", width="small"),
                            "documento": st.column_config.TextColumn("Documento", width="medium"),
                            "trecho_original": st.column_config.TextColumn("Trecho original", width="large"),
                            "sintese": st.column_config.TextColumn("Síntese", width="large"),
                        },
                    )

                    csv2 = df_sig.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "Baixar CSV (Unidades de Significado)",
                        csv2,
                        "unidades_significado.csv",
                        "text/csv"
                    )

                    st.subheader("Detalhes")
                    for _, r in df_sig.iterrows():
                        titulo = f"{r.get('id_unidade','(sem id)')} — {r.get('documento','(sem doc)')}"
                        with st.expander(titulo):
                            st.markdown("**Trecho original**")
                            st.write(r.get("trecho_original", ""))
                            st.markdown("**Síntese**")
                            st.write(r.get("sintese", ""))

                tab_idx += 1

                # Aba 3: Categorias
                with st_tabs[tab_idx]:
                    for cat in phenom_data["categorias"]:
                        with st.expander(f"📁 {cat['nome']}"):
                            st.write(cat["descricao"])
                            st.write("**Unidades Relacionadas:**", ", ".join(cat["unidades_relacionadas"]))

                tab_idx += 1

            # =========================
            # SISTEMÁTICO
            # =========================
            if mode in ["Mapeamento Sistemático", "Ambos"] and sys_data:
                with st_tabs[tab_idx]:
                    docs = sys_data["documentos"]

                    view = st.radio(
                        "Visualização",
                        ["Tabela (Longa / legível)", "Tabela (Wide / colunas)"],
                        horizontal=True
                    )

                    if view == "Tabela (Longa / legível)":
                        rows_long = []
                        for doc in docs:
                            for ans in doc["respostas"]:
                                rows_long.append({
                                    "Documento": doc["documento"],
                                    "Pergunta": ans["pergunta"],
                                    "Resposta": ans["resposta"],
                                    "Evidência": ans["evidencia_textual"],
                                    "Página": ans.get("pagina")
                                })

                        df_long = pd.DataFrame(rows_long)

                        st.dataframe(
                            df_long,
                            use_container_width=True,
                            height=600,
                            column_config={
                                "Documento": st.column_config.TextColumn("Documento", width="medium"),
                                "Pergunta": st.column_config.TextColumn("Pergunta", width="medium"),
                                "Resposta": st.column_config.TextColumn("Resposta", width="large"),
                                "Evidência": st.column_config.TextColumn("Evidência", width="large"),
                                "Página": st.column_config.NumberColumn("Página", width="small"),
                            },
                        )

                        st.subheader("Detalhes por item")
                        for _, r in df_long.iterrows():
                            with st.expander(f"{r['Documento']} — {r['Pergunta']} (p. {r.get('Página')})"):
                                st.markdown("**Resposta**")
                                st.write(r["Resposta"])
                                st.markdown("**Evidência**")
                                st.write(r["Evidência"])

                        csv_long = df_long.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            "Baixar CSV (Mapeamento - Long)",
                            csv_long,
                            "mapeamento_sistematico_long.csv",
                            "text/csv"
                        )

                    else:
                        unique_qs = []
                        for doc in docs:
                            for ans in doc["respostas"]:
                                if ans["pergunta"] not in unique_qs:
                                    unique_qs.append(ans["pergunta"])

                        rows = []
                        for doc in docs:
                            row = {"Documento": doc["documento"]}
                            for q in unique_qs:
                                ans_obj = next((a for a in doc["respostas"] if a["pergunta"] == q), None)
                                if ans_obj:
                                    pag_str = f" (Pág. {ans_obj['pagina']})" if ans_obj.get("pagina") else ""
                                    row[q] = f"Resposta: {ans_obj['resposta']}\n\nEvidência: \"{ans_obj['evidencia_textual']}\"{pag_str}"
                                else:
                                    row[q] = "-"
                            rows.append(row)

                        df_wide = pd.DataFrame(rows)
                        st.dataframe(df_wide, use_container_width=True, height=600)

                        csv_wide = df_wide.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            "Baixar CSV (Mapeamento - Wide)",
                            csv_wide,
                            "mapeamento_sistematico_wide.csv",
                            "text/csv"
                        )

        except Exception as e:
            if "exceeds the maximum number of tokens allowed" in str(e):
                st.error("O corpus documental é muito grande (excede o limite de tokens). Por favor, reduza a quantidade de PDFs.")
            else:
                st.error(f"Erro durante a análise: {e}")
