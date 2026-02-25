import streamlit as st
import pandas as pd
import json
import os
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# Configuração da página
st.set_page_config(page_title="Metanálise Fenomenológica AI", page_icon="📖", layout="wide")

# Inicializa o cliente Gemini
# Certifique-se de configurar a variável de ambiente GEMINI_API_KEY
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.warning("⚠️ Variável de ambiente GEMINI_API_KEY não encontrada. Por favor, configure-a para continuar.")
    st.stop()

client = genai.Client(api_key=api_key)

# --- Modelos Pydantic para Saída Estruturada (Structured Output) ---

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

# --- Interface do Usuário (UI) ---

st.title("📖 Metanálise Fenomenológica AI")
st.markdown("""
Faça o upload de múltiplos artigos em PDF e escolha o modo de análise. 
O sistema analisará os textos como um corpus único, extraindo unidades fenomenológicas 
ou realizando um mapeamento sistemático.
""")

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

if st.button("Iniciar Análise do Corpus", type="primary", disabled=not uploaded_files):
    if mode in ["Fenomenológico", "Ambos"] and not phenom_q.strip():
        st.warning("Por favor, preencha a Interrogação Fenomenológica.")
        st.stop()
    if mode in ["Mapeamento Sistemático", "Ambos"] and not sys_q.strip():
        st.warning("Por favor, preencha as Perguntas para Mapeamento Sistemático.")
        st.stop()
        
    # Validação de tamanho (limite de ~15MB para não estourar 1M tokens)
    total_size = sum([f.size for f in uploaded_files])
    if total_size > 15 * 1024 * 1024:
        st.error(f"O tamanho total dos arquivos ({total_size / 1024 / 1024:.2f} MB) excede o limite seguro de 15 MB. Por favor, reduza o número de PDFs.")
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
                prompt_text += "Regras: Forneça respostas objetivas, cite a evidência textual exata e a página onde foi encontrada.\n\n"

            contents = gemini_files + [prompt_text]

            # Selecionar o Schema correto baseado no modo
            schema = AnalysisResult
            if mode == "Fenomenológico":
                schema = PhenomenologicalResult
            elif mode == "Mapeamento Sistemático":
                schema = SystematicResult

            # Chamada à API
            response = client.models.generate_content(
                model='gemini-2.5-pro', # Usando o modelo Pro mais recente
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
            
            if mode in ["Fenomenológico", "Ambos"] and phenom_data:
                # Aba 1: Unidades de Sentido
                with st_tabs[tab_idx]:
                    df_sentido = pd.DataFrame(phenom_data["unidades_sentido"])
                    st.dataframe(df_sentido, use_container_width=True)
                    csv = df_sentido.to_csv(index=False).encode('utf-8')
                    st.download_button("Baixar CSV (Unidades de Sentido)", csv, "unidades_sentido.csv", "text/csv")
                tab_idx += 1
                
                # Aba 2: Unidades de Significado
                with st_tabs[tab_idx]:
                    df_sig = pd.DataFrame(phenom_data["unidades_significado"])
                    st.dataframe(df_sig, use_container_width=True)
                tab_idx += 1
                
                # Aba 3: Categorias
                with st_tabs[tab_idx]:
                    for cat in phenom_data["categorias"]:
                        with st.expander(f"📁 {cat['nome']}"):
                            st.write(cat['descricao'])
                            st.write("**Unidades Relacionadas:**", ", ".join(cat['unidades_relacionadas']))
                tab_idx += 1
                
            if mode in ["Mapeamento Sistemático", "Ambos"] and sys_data:
                # Aba 4: Mapeamento Sistemático (Formato Amplo / Wide Format)
                with st_tabs[tab_idx]:
                    docs = sys_data["documentos"]
                    
                    # Extrair perguntas únicas para virarem colunas
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
                                pag_str = f" (Pág. {ans_obj['pagina']})" if ans_obj.get('pagina') else ""
                                cell_val = f"Resposta: {ans_obj['resposta']}\n\nEvidência: \"{ans_obj['evidencia_textual']}\"{pag_str}"
                                row[q] = cell_val
                            else:
                                row[q] = "-"
                        rows.append(row)
                        
                    df_sys = pd.DataFrame(rows)
                    st.dataframe(df_sys, use_container_width=True)
                    
                    csv = df_sys.to_csv(index=False).encode('utf-8')
                    st.download_button("Baixar CSV (Mapeamento Sistemático)", csv, "mapeamento_sistematico.csv", "text/csv")

        except Exception as e:
            if "exceeds the maximum number of tokens allowed" in str(e):
                st.error("O corpus documental é muito grande (excede o limite de tokens). Por favor, reduza a quantidade de PDFs.")
            else:
                st.error(f"Erro durante a análise: {e}")
