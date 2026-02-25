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
# SESSION STATE
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
    st.session_state.cross_synthesis = {}
if "cross_synthesis_mode_tag" not in st.session_state:
    st.session_state.cross_synthesis_mode_tag = None

# ============================================================
# CSS / TEMA CLARO + LAYOUT FENOMENOLÓGICO (estilo screenshot)
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

      /* ====== Top bar export ====== */
      .topbar {
        display:flex;
        align-items:center;
        justify-content:space-between;
        gap:16px;
        margin-bottom:10px;
      }

      /* ====== Table-like layout ====== */
      .grid-header {
        display:grid;
        grid-template-columns: 220px 1.2fr 1.1fr;
        gap: 18px;
        padding: 14px 0 10px 0;
        border-bottom: 1px solid #e5e7eb;
      }
      .grid-header .h {
        font-weight: 800;
        font-size: 12px;
        letter-spacing: .08em;
        color: #6b7280;
        text-transform: uppercase;
      }

      .grid-row {
        display:grid;
        grid-template-columns: 220px 1.2fr 1.1fr;
        gap: 18px;
        padding: 18px 0;
        border-bottom: 1px solid #eef2f7;
      }

      .idblock {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-weight: 700;
        color: #111827;
        margin-bottom: 6px;
        word-break: break-word;
      }
      .docblock {
        color:#111827;
        font-weight:600;
        margin-bottom: 6px;
        word-break: break-word;
      }
      .pagblock {
        color:#6b7280;
        font-size: 12px;
      }

      .quote {
        font-style: italic;
        color:#111827;
        line-height:1.55;
        white-space: pre-wrap;
        border-left: 4px solid #d1d5db;
        padding-left: 12px;
      }

      .cj-title {
        font-weight: 800;
        font-size: 12px;
        letter-spacing: .06em;
        color:#6b7280;
        text-transform: uppercase;
        margin-top: 4px;
        margin-bottom: 6px;
      }
      .cj-text {
        color:#111827;
        line-height:1.55;
        white-space: pre-wrap;
      }

      /* ====== Significado layout ====== */
      .grid-header-sig {
        display:grid;
        grid-template-columns: 220px 1.2fr 1.1fr;
        gap: 18px;
        padding: 14px 0 10px 0;
        border-bottom: 1px solid #e5e7eb;
      }
      .grid-row-sig {
        display:grid;
        grid-template-columns: 220px 1.2fr 1.1fr;
        gap: 18px;
        padding: 18px 0;
        border-bottom: 1px solid #eef2f7;
      }

      .synth-card {
        background:#f3f4f6;
        padding: 16px;
        border-radius: 14px;
        font-weight: 700;
        color:#111827;
        line-height:1.5;
        white-space: pre-wrap;
      }

      /* ====== Categorias cards grid ====== */
      .cat-grid {
        display:grid;
        grid-template-columns: 1fr 1fr;
        gap: 18px;
      }
      .cat-card {
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        padding: 18px;
        background: #ffffff;
        box-shadow: 0 1px 0 rgba(17,24,39,0.04);
      }
      .cat-title {
        font-family: ui-serif, Georgia, Cambria, "Times New Roman", Times, serif;
        font-weight: 800;
        font-size: 26px;
        line-height: 1.2;
        margin-bottom: 10px;
        color:#111827;
      }
      .cat-desc {
        color:#111827;
        line-height:1.6;
        margin-bottom: 14px;
        white-space: pre-wrap;
      }
      .cat-sub {
        font-weight: 800;
        font-size: 12px;
        letter-spacing: .08em;
        color: #6b7280;
        text-transform: uppercase;
        margin-bottom: 10px;
      }
      .chips {
        display:flex;
        flex-wrap: wrap;
        gap: 10px;
      }
      .chip {
        border: 1px solid #e5e7eb;
        border-radius: 10px;
        padding: 6px 10px;
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size: 13px;
        color:#111827;
        background:#ffffff;
      }

      /* Responsivo */
      @media (max-width: 1100px) {
        .grid-header, .grid-row, .grid-header-sig, .grid-row-sig {
          grid-template-columns: 1fr;
        }
        .cat-grid { grid-template-columns: 1fr; }
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
)

phenom_q = ""
sys_q = ""

if mode in ["Fenomenológico", "Ambos"]:
    phenom_q = st.text_area(
        "Interrogação Fenomenológica",
        placeholder="Ex: Como o fenômeno X se constitui nos textos analisados?",
        height=110,
    )

if mode in ["Mapeamento Sistemático", "Ambos"]:
    sys_q = st.text_area(
        "Perguntas para Mapeamento Sistemático (1 por linha)",
        placeholder="1. Qual é o objetivo do estudo?\n2. Qual metodologia é utilizada?\n3. Quais softwares foram utilizados?",
        height=150,
    )

uploaded_files = st.file_uploader("Corpus Documental (PDFs)", type="pdf", accept_multiple_files=True)

# ============================================================
# EXECUTAR ANÁLISE
# ============================================================
run = st.button("Iniciar Análise do Corpus", type="primary", disabled=not uploaded_files)

if run:
    st.session_state.analysis_done = False
    st.session_state.result_data = None
    st.session_state.df_sys_long = None
    st.session_state.last_mode = mode

    # invalidar sínteses anteriores
    st.session_state.cross_synthesis = {}
    st.session_state.cross_synthesis_mode_tag = None

    if mode in ["Fenomenológico", "Ambos"] and not phenom_q.strip():
        st.warning("Por favor, preencha a Interrogação Fenomenológica.")
        st.stop()

    if mode in ["Mapeamento Sistemático", "Ambos"] and not sys_q.strip():
        st.warning("Por favor, preencha as Perguntas para Mapeamento Sistemático.")
        st.stop()

    total_size = sum([f.size for f in uploaded_files])
    if total_size > 15 * 1024 * 1024:
        st.error(f"O tamanho total ({total_size / 1024 / 1024:.2f} MB) excede 15 MB. Reduza a quantidade de PDFs.")
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
                    temperature=0.2,
                ),
            )

            st.session_state.result_data = json.loads(response.text)
            st.session_state.analysis_done = True

            st.session_state.cross_synthesis_mode_tag = f"{mode}|{len(uploaded_files)}|{total_size}"

            st.success("Análise concluída com sucesso!")

        except Exception as e:
            if "exceeds the maximum number of tokens allowed" in str(e):
                st.error("O corpus excede o limite de tokens. Reduza a quantidade de PDFs.")
            else:
                st.error(f"Erro durante a análise: {e}")

# ============================================================
# RENDER RESULTADOS
# ============================================================
if st.session_state.analysis_done and st.session_state.result_data:
    result_data = st.session_state.result_data
    render_mode = st.session_state.last_mode or mode

    phenom_data = result_data if render_mode == "Fenomenológico" else (result_data.get("fenomenologico") or {})
    sys_data = result_data if render_mode == "Mapeamento Sistemático" else (result_data.get("sistematico") or {})

    # Contagens para títulos das abas (como no screenshot)
    n_us = len((phenom_data or {}).get("unidades_sentido", [])) if render_mode in ["Fenomenológico", "Ambos"] else 0
    n_um = len((phenom_data or {}).get("unidades_significado", [])) if render_mode in ["Fenomenológico", "Ambos"] else 0
    n_cat = len((phenom_data or {}).get("categorias", [])) if render_mode in ["Fenomenológico", "Ambos"] else 0

    st.header("Resultados")

    tabs = []
    if render_mode in ["Fenomenológico", "Ambos"]:
        tabs.extend([f"Unidades de Sentido ({n_us})", f"Unidades de Significado ({n_um})", f"Categorias ({n_cat})"])
    if render_mode in ["Mapeamento Sistemático", "Ambos"]:
        tabs.append("Mapeamento Sistemático")

    st_tabs = st.tabs(tabs)
    tab_idx = 0

    # ============================================================
    # FENOMENOLÓGICO — ESTILO “QUADRO” DA IMAGEM
    # ============================================================
    if render_mode in ["Fenomenológico", "Ambos"]:
        # ---------- Aba: Unidades de Sentido ----------
        with st_tabs[tab_idx]:
            unidades_sentido = (phenom_data or {}).get("unidades_sentido", [])
            if not unidades_sentido:
                st.warning("Nenhuma unidade de sentido foi retornada.")
            else:
                df_us = pd.DataFrame(unidades_sentido)

                # Top bar com export
                c1, c2 = st.columns([6, 1.6])
                with c1:
                    st.caption("ID/DOC/PÁG • Citação literal • Contexto & Justificativa")
                with c2:
                    csv = df_us.to_csv(index=False).encode("utf-8")
                    st.download_button("⬇️ Exportar CSV", csv, "unidades_sentido.csv", "text/csv", use_container_width=True)

                # Cabeçalho
                st.markdown(
                    """
                    <div class="grid-header">
                      <div class="h">ID / DOC / PÁG</div>
                      <div class="h">CITAÇÃO LITERAL</div>
                      <div class="h">CONTEXTO &amp; JUSTIFICATIVA</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                # Linhas
                for _, r in df_us.iterrows():
                    uid = r.get("id_unidade", "")
                    doc = r.get("documento", "")
                    pag = r.get("pagina", None)
                    pag_txt = f"Pág. {pag}" if (pag is not None and str(pag).strip() != "") else "Pág. null"

                    cit = r.get("citacao_literal", "")
                    ctx = (r.get("contexto_resumido", "") or "").strip()
                    jus = (r.get("justificativa_fenomenologica", "") or "").strip()

                    cj_html = ""
                    if ctx:
                        cj_html += f'<div class="cj-title">CONTEXTO:</div><div class="cj-text">{ctx}</div><br/>'
                    if jus:
                        cj_html += f'<div class="cj-title">JUSTIFICATIVA:</div><div class="cj-text">{jus}</div>'
                    if not cj_html:
                        cj_html = '<div class="muted">-</div>'

                    st.markdown(
                        f"""
                        <div class="grid-row">
                          <div>
                            <div class="idblock">{uid}</div>
                            <div class="docblock">{doc}</div>
                            <div class="pagblock">{pag_txt}</div>
                          </div>
                          <div class="quote">"{cit}"</div>
                          <div>{cj_html}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

        tab_idx += 1

        # ---------- Aba: Unidades de Significado ----------
        with st_tabs[tab_idx]:
            unidades_sig = (phenom_data or {}).get("unidades_significado", [])
            if not unidades_sig:
                st.warning("Nenhuma unidade de significado foi retornada.")
            else:
                df_um = pd.DataFrame(unidades_sig)

                c1, c2 = st.columns([6, 1.6])
                with c1:
                    st.caption("ID/Documento • Trecho original • Síntese de significado")
                with c2:
                    csv2 = df_um.to_csv(index=False).encode("utf-8")
                    st.download_button("⬇️ Exportar CSV", csv2, "unidades_significado.csv", "text/csv", use_container_width=True)

                st.markdown(
                    """
                    <div class="grid-header-sig">
                      <div class="h">ID / DOCUMENTO</div>
                      <div class="h">TRECHO ORIGINAL</div>
                      <div class="h">SÍNTESE DE SIGNIFICADO</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                for _, r in df_um.iterrows():
                    uid = r.get("id_unidade", "")
                    doc = r.get("documento", "")
                    tre = r.get("trecho_original", "")
                    syn = r.get("sintese", "")

                    st.markdown(
                        f"""
                        <div class="grid-row-sig">
                          <div>
                            <div class="idblock">{uid}</div>
                            <div class="docblock">{doc}</div>
                          </div>
                          <div class="quote">"{tre}"</div>
                          <div class="synth-card">{syn}</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

        tab_idx += 1

        # ---------- Aba: Categorias ----------
        with st_tabs[tab_idx]:
            categorias = (phenom_data or {}).get("categorias", [])
            if not categorias:
                st.warning("Nenhuma categoria foi retornada.")
            else:
                df_cat = pd.DataFrame(
                    [{
                        "nome": c.get("nome"),
                        "descricao": c.get("descricao"),
                        "unidades_relacionadas": ", ".join(c.get("unidades_relacionadas", []))
                    } for c in categorias]
                )

                c1, c2 = st.columns([6, 1.6])
                with c1:
                    st.caption("Categorias fenomenológicas (cards)")
                with c2:
                    csv3 = df_cat.to_csv(index=False).encode("utf-8")
                    st.download_button("⬇️ Exportar CSV", csv3, "categorias.csv", "text/csv", use_container_width=True)

                st.markdown('<div class="cat-grid">', unsafe_allow_html=True)
                for c in categorias:
                    nome = c.get("nome", "(sem nome)")
                    desc = c.get("descricao", "")
                    rel = c.get("unidades_relacionadas", [])

                    chips_html = ""
                    if rel:
                        chips_html = '<div class="chips">' + "".join([f'<span class="chip">{u}</span>' for u in rel]) + '</div>'
                    else:
                        chips_html = '<div class="muted">-</div>'

                    st.markdown(
                        f"""
                        <div class="cat-card">
                          <div class="cat-title">{nome}</div>
                          <div class="cat-desc">{desc}</div>
                          <div class="cat-sub">UNIDADES RELACIONADAS</div>
                          {chips_html}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                st.markdown("</div>", unsafe_allow_html=True)

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

                csv_long = df_long.to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Baixar CSV (Mapeamento Sistemático)", csv_long, "mapeamento_sistematico.csv", "text/csv")

                st.caption("Comparação transversal por pergunta + síntese IA (usa apenas respostas extraídas).")

                perguntas = df_long["Pergunta"].dropna().unique().tolist()
                st.subheader("Comparação transversal (por pergunta)")

                for pergunta in perguntas:
                    sub = df_long[df_long["Pergunta"] == pergunta].copy()

                    with st.expander(f"🔎 {pergunta}", expanded=False):
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
                                <div class="grid-row" style="grid-template-columns: 220px 1.2fr 1.1fr;">
                                  <div>
                                    <div class="docblock">{doc}</div>
                                    <div class="pagblock">{pag_txt}</div>
                                  </div>
                                  <div class="synth-card">{resp}</div>
                                  <div class="quote">"{evid}"</div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
