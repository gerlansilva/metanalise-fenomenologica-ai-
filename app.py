# --- SUBSTITUA/APENAS ATUALIZE o bloco de CSS do QUADRO (cards) ---
# (você pode colar este CSS no seu st.markdown("<style>...</style>", unsafe_allow_html=True)

st.markdown("""
<style>
/* ==========================
   QUADRO (cards) com scroll
   ========================== */
.qa-table-wrap{
  background: rgba(241,233,216,0.55);
  border: 1px solid rgba(47,36,28,0.14);
  border-radius: calc(var(--radius) + 6px);
  box-shadow: var(--shadow2);
  overflow: auto;
  max-height: 72vh;
}

/* tabela */
.qa-table{
  border-collapse: separate;
  border-spacing: 0;
  width: max-content;
  min-width: 100%;
  table-layout: fixed;         /* <- essencial p/ largura padrão */
}

/* cabeçalho fixo */
.qa-table thead th{
  position: sticky;
  top: 0;
  z-index: 5;
  background: var(--panel);
  color: var(--text);
  text-align: left;
  font-family: "Work Sans", sans-serif;
  font-weight: 800;
  font-size: 14px;
  border-bottom: 1px solid rgba(47,36,28,0.16);
  padding: 14px 14px;
  white-space: normal;         /* permite quebrar no título */
  word-break: break-word;
  overflow-wrap: anywhere;
}

/* primeira coluna fixa */
.qa-table .sticky-col{
  position: sticky;
  left: 0;
  z-index: 6;
  background: var(--panel);
  border-right: 1px solid rgba(47,36,28,0.10);
}

/* TAMANHOS PADRÃO (ajuste aqui) */
:root{
  --doc-col: 280px;            /* largura padrão do Documento */
  --cell-col: 520px;           /* largura padrão das outras colunas */
}

/* cabeçalhos com largura padrão */
.qa-table thead th.sticky-col{ width: var(--doc-col) !important; min-width: var(--doc-col) !important; max-width: var(--doc-col) !important; }
.qa-table thead th:not(.sticky-col){ width: var(--cell-col) !important; min-width: var(--cell-col) !important; max-width: var(--cell-col) !important; }

/* células com largura padrão */
.qa-table td{
  vertical-align: top;
  padding: 14px 14px;
  border-bottom: 1px solid rgba(47,36,28,0.10);
}
.qa-table td.doccell{
  width: var(--doc-col) !important;
  min-width: var(--doc-col) !important;
  max-width: var(--doc-col) !important;
}
.qa-table td:not(.doccell){
  width: var(--cell-col) !important;
  min-width: var(--cell-col) !important;
  max-width: var(--cell-col) !important;
}

/* card dentro da célula */
.cell-card{
  background: rgba(255,255,255,0.45);
  border: 1px solid rgba(47,36,28,0.14);
  border-radius: 14px;
  box-shadow: var(--shadow2);
  padding: 12px 12px;
}

/* texto: sempre aparecer inteiro (sem cortar) */
.cell-text{
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
  line-height: 1.55;
  font-size: 13.5px;
  color: var(--text);
}

/* label pequeno */
.cell-label{
  font-size: 11px;
  font-weight: 800;
  color: var(--muted);
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
</style>
""", unsafe_allow_html=True)
