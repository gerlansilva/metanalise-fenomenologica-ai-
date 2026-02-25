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
st.set_page_config(page_title="Metanálise Fenomenológica AI", page_icon="📖", layout="wide")

# ============================================================
# SESSION STATE (evitar reprocessar ao baixar CSV / reruns)
# ============================================================
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False
if "result_data" not in st.session_state:
    st.session_state.result_data = None
if "df_sys_long" not in st.session_state:
    st.session_state.df_sys_long = None
if "last_mode" not in st.session_state:
    st.session_state.last_mode = None
if "cross_synthesis" not in st.session_state:
    st.session_state.cross_synthesis = {}  # pergunta -> texto
if "cross_synthesis_mode_tag" not in st.session_state:
    st.session_state.cross_synthesis_mode_tag = None  # para invalidar sínteses quando muda análise

# ============================================================
# CSS / TEMA CLARO + CARDS
# ============================================================
st.markdown(
    """
    <style>
      .stApp { background: #ffffff !important; color: #111827 !important; }
      h1, h2, h3, h4, h5, h6 { color: #111827 !important; }

      textarea, input, .stTextInput > div > div > input {
        background-color: #ffffff !important;
        color: #111827 !important;
      }

      label, .stMarkdown, .stMarkdown p, .stCaption {
        color: #111827 !important;
      }

      [data-testid="stDataFrame"] { background: #ffffff !important; }
      .stDataFrame { background: #ffffff !important; }
      div[data-testid="stSidebar"], header, footer { background: #ffffff !important; }

      .stButton>button { border-radius: 10px; }

      /* ===== Cards ===== */
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
        line-height: 1.25;
        word-break: break-word;
      }

      .card {
        background-color: #f3f4f6;
        padding: 14px;
        border-radius: 12px;
        margin-bottom: 8px;
        color: #111827;
        line-height: 1.4;
        white-space: pre-wrap;
      }

      .evidence {
        border-left: 4px solid #d1d5db;
        padding-left: 10px;
        margin-top: 6px;
        color: #374151;
        font-style: italic;
        white-space: pre-wrap;
      }

      .page {
        margin-top: 6px;
        font-size: 12px;
        color: #6b7280;
        font-style: normal;
      }

      .row-divider {
        border-top: 1px solid #e5e7eb;
        margin-top: 16px;
        margin-bottom: 16px;
      }

      .muted {
        color: #9ca3af;
        font-size: 13px;
      }
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# GEMINI CLIENT
# ============================================================
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ Variável de ambiente GEMINI_API_KEY não encontrada. Configure-a para continuar.")
    st.stop()

client = genai.Client(api_key=api_key)

# ============================================================
# MODELOS PYDANTIC (STRUCTURED OUTPUT)
# ============================================================
class UnidadeSentido(BaseModel):
    id_unidade: str = Field(description="ID único automático, ex: DOC01_P087_US03")
    documento: str = Field(description="Nome do arquivo PDF")
    pagina: int | None = Field(description="Número da página, null se não identificado")
    citacao_literal: str = Field(description="Trecho literal exato")
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


# ============================================================
# FUNÇÃO: SÍNTESE TRANSVERSAL POR PERGUNTA (sem reprocessar PDFs)
# ============================================================
def gerar_sintese_transversal(pergunta: str, df_sub: pd.DataFrame) -> str:
    """
    Usa somente as respostas já extraídas (df_sub) para gerar síntese transversal.
    Não reprocessa PDFs.
    """
    linhas = []
    for _, r in df_sub.iterrows():
        doc = str(r.get("Documento", "")).strip()
        resp = str(r.get("Resposta", "")).strip()
        evid = str(r.get("Evidência", "")).strip()
        pag = r.get("Página", None)
        pag_str = f"{pag}" if (pag is not None and str(pag).strip() != "") else "null"

        linhas.append(
            f"- DOCUMENTO: {doc}\n"
            f"  RESPOSTA: {resp}\n"
            f"  EVIDÊNCIA: \"{evid}\"\n"
            f"  PÁGINA: {pag_str}\n"
        )

    corpus = "\n".join(linhas)

    prompt = f"""
Você está comparando resultados entre documentos para a MESMA pergunta, com base apenas nas respostas e evidências abaixo.

PERGUNTA:
{pergunta}

RESPOSTAS POR DOCUMENTO:
{corpus}

TAREFAS (nesta ordem):
1) CONVERGÊNCIAS (bullets)
2) DIVERGÊNCIAS (bullets)
3) DISTRIBUIÇÃO/CONTAGEM (Item — Nº de documentos). Use "não informado" quando apropriado.
4) SÍNTESE INTERPRETATIVA (6–10 linhas), em português acadêmico claro.

REGRAS:
- Não invente informação.
- Não cite nada que não esteja nas respostas/evidências.
- Se houver contradição, explicite como divergência.
"""

    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt],
        config=types.GenerateContentConfig(temperature=0.2),
    )
    return resp.text


# ============================================================
# UI
# ============================================================
st.title("📖 Metanálise Fenomenológica AI")
st.markdown(
    """
Faça upload de múltiplos PDFs e escolha o modo de análise.  
Resultados ficam salvos; baixar CSV não reprocessa o corpus.
"""
)

mode = st.radio(
    "Modo de Análise",
    ["Fenomenológico", "Mapeamento Sistemático", "Ambos"],
    horizontal=True,
    help="Fenomenológico: unidades e categorias. Mapeamento: respostas objetivas por pergunta."
)

phenom_q = ""
sys_q = ""

if mode in ["Fenomenológico", "Ambos"]:
    phenom_q = st.text_area(
        "Interrogação Fenomenológica",
        placeholder="Ex: Como o campo X se constitui nos textos analisados?",
        height=110
    )

if mode in ["Mapeamento Sistemático", "Ambos"]:
    sys_q = st.text_area(
        "Perguntas para Mapeamento Sistemático (1 por linha)",
        placeholder="1. Qual é o objetivo do estudo?\n2. Qual metodologia é utilizada?\n3. Quais softwares foram utilizados?",
        height=150
    )

uploaded_files = st.file_uploader("Corpus Documental (PDFs)", type="pdf", accept_multiple_files=True)

# ============================================================
# EXECUTAR ANÁLISE (salva resultado em session_state)
# ============================================================
run = st.button("Iniciar Análise do Corpus", type="primary", disabled=not uploaded_files)

if run:
    # reset (para rodar só quando clicar)
    st.session_state.analysis_done = False
    st.session_state.result_data = None
    st.session_state.df_sys_long = None
    st.session_state.last_mode = mode

    # invalidar sínteses anteriores (pois são de outra execução)
    st.session_state.cross_synthesis = {}
    st.session_state.cross_synthesis_mode_tag = None

    if mode in ["Fenomenológico", "Ambos"] and not phenom_q.strip():
        st.warning("Por favor, preencha a Interrogação Fenomenológica.")
        st.stop()

    if mode in ["Mapeamento Sistemático", "Ambos"] and not sys_q.strip():
        st.warning("Por favor, preencha as Perguntas para Mapeamento Sistemático.")
        st.stop()

    # Limite de tamanho (ajuste se quiser)
    total_size = sum([f.size for f in uploaded_files])
    if total_size > 15 * 1024 * 1024:
        st.error(
            f"O tamanho total ({total_size / 1024 / 1024:.2f} MB) excede 15 MB. "
            "Reduza a quantidade de PDFs."
        )
        st.stop()

    with st.spinner("Analisando o corpus documental..."):
        try:
            gemini_files = [
                types.Part.from_bytes(data=f.getvalue(), mime_type="application/pdf")
                for f in uploaded_files
            ]

            prompt_text = "Leia todos os PDFs anexados como um corpus único.\n\n"

            if mode in ["Fenomenológico", "Ambos"]:
                prompt_text += "=== MODO FENOMENOLÓGICO ===\n"
                prompt_text += f"INTERROGAÇÃO FENOMENOLÓGICA:\n\"{phenom_q}\"\n\n"
                prompt_text += (
                    "ETAPA 1: Extraia unidades de sentido (documento, página, citação literal exata, contexto e justificativa).\n"
                    "REGRAS: NÃO parafrasear a citação; NÃO inventar páginas; NÃO omitir documento; rastreabilidade obrigatória.\n"
                    "ETAPA 2: Transforme cada unidade em unidade de significado.\n"
                    "ETAPA 3: Agrupe convergências entre documentos.\n"
                    "ETAPA 4: Sugira categorias fenomenológicas.\n\n"
                )

            if mode in ["Mapeamento Sistemático", "Ambos"]:
                prompt_text += "=== MODO MAPEAMENTO SISTEMÁTICO ===\n"
                prompt_text += "Responda às perguntas abaixo para CADA documento:\n"
                prompt_text += f"{sys_q}\n\n"
                prompt_text += (
                    "REGRAS: Respostas objetivas (máx. 3 frases). "
                    "Cite evidência textual literal e página. "
                    "Se página não puder ser identificada com certeza, retorne null.\n\n"
                )

            contents = gemini_files + [prompt_text]

            schema = AnalysisResult
            if mode == "Fenomenológico":
                schema = PhenomenologicalResult
            elif mode == "Mapeamento Sistemático":
                schema = SystematicResult

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=(
                        "Você é um assistente de análise qualitativa de corpus documental.\n"
                        "Nunca invente conteúdo. Preserve rastreabilidade.\n"
                        "Se o número da página não puder ser identificado com certeza, use null."
                    ),
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0.2
                ),
            )

            result_data = json.loads(response.text)

            st.session_state.analysis_done = True
            st.session_state.result_data = result_data

            # Tag para invalidar sínteses se necessário
            st.session_state.cross_synthesis_mode_tag = f"{mode}|{len(uploaded_files)}|{total_size}"

            st.success("Análise concluída com sucesso!")

        except Exception as e:
            if "exceeds the maximum number of tokens allowed" in str(e):
                st.error("O corpus excede o limite de tokens. Reduza a quantidade de PDFs.")
            else:
                st.error(f"Erro durante a análise: {e}")

# ============================================================
# RENDER RESULTADOS (fora do botão)
# ============================================================
if st.session_state.analysis_done and st.session_state.result_data:
    result_data = st.session_state.result_data

    # Renderiza pelo modo da última análise para evitar KeyError em reruns
    render_mode = st.session_state.last_mode or mode

    st.header("Resultados da Análise")

    tabs = []
    if render_mode in ["Fenomenológico", "Ambos"]:
        tabs.extend(["Unidades de Sentido", "Unidades de Significado", "Categorias"])
    if render_mode in ["Mapeamento Sistemático", "Ambos"]:
        tabs.append("Mapeamento Sistemático")

    st_tabs = st.tabs(tabs)

    phenom_data = result_data if render_mode == "Fenomenológico" else (result_data.get("fenomenologico") or {})
    sys_data = result_data if render_mode == "Mapeamento Sistemático" else (result_data.get("sistematico") or {})

    tab_idx = 0

    # ============================================================
    # FENOMENOLÓGICO — CARDS
    # ============================================================
    if render_mode in ["Fenomenológico", "Ambos"]:
        # Aba 1: Unidades de sentido (cards)
        with st_tabs[tab_idx]:
            unidades_sentido = (phenom_data or {}).get("unidades_sentido", [])
            if not unidades_sentido:
                st.warning("Nenhuma unidade de sentido foi retornada.")
            else:
                df_sentido = pd.DataFrame(unidades_sentido)

                # CSV no topo
                csv = df_sentido.to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Baixar CSV (Unidades de Sentido)", csv, "unidades_sentido.csv", "text/csv")
                st.caption("Abaixo, as unidades de sentido em formato de cards.")

                for _, r in df_sentido.iterrows():
                    doc = r.get("documento", "(sem doc)")
                    uid = r.get("id_unidade", "(sem id)")
                    pag = r.get("pagina", None)
                    pag_txt = f"PÁG. {pag}" if (pag is not None and str(pag).strip() != "") else "PÁG. null"

                    cit = r.get("citacao_literal", "")
                    ctx = r.get("contexto_resumido", "")
                    jus = r.get("justificativa_fenomenologica", "")

                    st.markdown(
                        f"""
                        <div class="doc-title">{doc} — {uid}</div>
                        <div class="card">{cit}</div>
                        <div class="evidence">{ctx if ctx else ""}
                          <div class="page">{pag_txt}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    if jus:
                        with st.expander("Ver justificativa fenomenológica"):
                            st.write(jus)

                    st.markdown('<div class="row-divider"></div>', unsafe_allow_html=True)

        tab_idx += 1

        # Aba 2: Unidades de significado (cards)
        with st_tabs[tab_idx]:
            unidades_significado = (phenom_data or {}).get("unidades_significado", [])
            if not unidades_significado:
                st.warning("Nenhuma unidade de significado foi retornada.")
            else:
                df_sig = pd.DataFrame(unidades_significado)
                csv2 = df_sig.to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Baixar CSV (Unidades de Significado)", csv2, "unidades_significado.csv", "text/csv")
                st.caption("Abaixo, as unidades de significado em formato de cards.")

                for _, r in df_sig.iterrows():
                    doc = r.get("documento", "(sem doc)")
                    uid = r.get("id_unidade", "(sem id)")
                    sint = r.get("sintese", "")
                    tre = r.get("trecho_original", "")

                    st.markdown(
                        f"""
                        <div class="doc-title">{doc} — {uid}</div>
                        <div class="card">{sint}</div>
                        """,
                        unsafe_allow_html=True
                    )
                    if tre:
                        with st.expander("Ver trecho original"):
                            st.write(tre)

                    st.markdown('<div class="row-divider"></div>', unsafe_allow_html=True)

        tab_idx += 1

        # Aba 3: Categorias (cards)
        with st_tabs[tab_idx]:
            categorias = (phenom_data or {}).get("categorias", [])
            if not categorias:
                st.warning("Nenhuma categoria foi retornada.")
            else:
                # CSV das categorias (opcional)
                df_cat = pd.DataFrame(
                    [{
                        "nome": c.get("nome"),
                        "descricao": c.get("descricao"),
                        "unidades_relacionadas": ", ".join(c.get("unidades_relacionadas", []))
                    } for c in categorias]
                )
                csv3 = df_cat.to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Baixar CSV (Categorias)", csv3, "categorias.csv", "text/csv")
                st.caption("Abaixo, as categorias em formato de cards.")

                for c in categorias:
                    nome = c.get("nome", "(sem nome)")
                    desc = c.get("descricao", "")
                    rel = c.get("unidades_relacionadas", [])

                    st.markdown(
                        f"""
                        <div class="card">
                          <b>{nome}</b><br><br>
                          {desc}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    if rel:
                        st.write("**Unidades relacionadas:**", ", ".join(rel))
                    st.markdown('<div class="row-divider"></div>', unsafe_allow_html=True)

        tab_idx += 1

    # ============================================================
    # MAPEAMENTO SISTEMÁTICO — CARDS + COMPARAÇÃO + SÍNTESE IA
    # ============================================================
    if render_mode in ["Mapeamento Sistemático", "Ambos"]:
        with st_tabs[tab_idx]:
            docs = (sys_data or {}).get("documentos", [])
            if not docs:
                st.warning("O mapeamento sistemático não foi retornado.")
            else:
                # Montar df_long (para export, comparação e síntese)
                rows_long = []
                for doc in docs:
                    for ans in doc.get("respostas", []):
                        rows_long.append({
                            "Documento": doc.get("documento"),
                            "Pergunta": ans.get("pergunta"),
                            "Resposta": ans.get("resposta"),
                            "Evidência": ans.get("evidencia_textual"),
                            "Página": ans.get("pagina"),
                        })

                df_long = pd.DataFrame(rows_long)
                st.session_state.df_sys_long = df_long

                # CSV no topo
                csv_long = df_long.to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Baixar CSV (Mapeamento Sistemático)", csv_long, "mapeamento_sistematico.csv", "text/csv")
                st.caption("Abaixo: comparação transversal por pergunta + cards por documento.")

                # Lista de perguntas na ordem em que aparecem
                perguntas = df_long["Pergunta"].dropna().unique().tolist()

                st.subheader("Comparação transversal (por pergunta)")

                for pergunta in perguntas:
                    sub = df_long[df_long["Pergunta"] == pergunta].copy()

                    with st.expander(f"🔎 {pergunta}", expanded=False):
                        # Tabela comparativa compacta (apoio)
                        st.dataframe(
                            sub[["Documento", "Resposta", "Página", "Evidência"]],
                            use_container_width=True,
                            height=260,
                            column_config={
                                "Documento": st.column_config.TextColumn("Documento", width="medium"),
                                "Resposta": st.column_config.TextColumn("Resposta", width="large"),
                                "Página": st.column_config.TextColumn("Página", width="small"),
                                "Evidência": st.column_config.TextColumn("Evidência", width="large"),
                            },
                        )

                        colA, colB = st.columns([1.3, 3.7])

                        with colA:
                            if st.button("Gerar síntese transversal", key=f"sintese_{hash(pergunta)}"):
                                with st.spinner("Gerando síntese (sem reprocessar PDFs)..."):
                                    texto = gerar_sintese_transversal(pergunta, sub)
                                    st.session_state.cross_synthesis[pergunta] = texto

                        # Mostrar síntese se existir
                        if pergunta in st.session_state.cross_synthesis:
                            st.markdown("### Síntese transversal")
                            st.write(st.session_state.cross_synthesis[pergunta])

                        st.markdown("### Evidências por documento (cards)")
                        for _, r in sub.iterrows():
                            doc = str(r.get("Documento", "(sem doc)"))
                            resp = str(r.get("Resposta", "")).strip()
                            evid = str(r.get("Evidência", "")).strip()
                            pag = r.get("Página", None)
                            pag_txt = f"PÁG. {pag}" if (pag is not None and str(pag).strip() != "") else "PÁG. null"

                            st.markdown(
                                f"""
                                <div class="doc-title">{doc}</div>
                                <div class="card">{resp}</div>
                                <div class="evidence">"{evid}"
                                  <div class="page">{pag_txt}</div>
                                </div>
                                <div class="row-divider"></div>
                                """,
                                unsafe_allow_html=True
                            )
