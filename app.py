"""
Notas Fiscais — Dashboard para extração estruturada de notas fiscais (OCR + IA).
Uma única aba: upload → processamento → resultados (filtros e exportação CSV).
Chaves de API no arquivo .env.
"""
import os
from pathlib import Path

_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_path)
    except ImportError:
        pass

import json
import tempfile
import time
import csv as csv_module
from datetime import datetime

import pandas as pd
import streamlit as st

# Na nuvem (Streamlit Cloud): chaves vêm de Secrets; no PC: .env
try:
    for k, v in (getattr(st, "secrets", None) or {}).items():
        if isinstance(v, str) and str(k).isupper():
            os.environ.setdefault(str(k), v)
except Exception:
    pass

import nf_ocr

VERSION = "1.0.0"
LAST_UPDATE = "2025-03"

# Arquivo de estado persistente (memória entre sessões)
STATE_FILE = Path(__file__).resolve().parent / "notas_fiscais_state.json"
LOG_DUVIDAS_FILE = Path(__file__).resolve().parent / "notas_fiscais_duvidas_erros.json"

STYLE = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  html, body, [data-testid="stAppViewContainer"] { font-family: 'Inter', sans-serif; background: #F8FAFC; }
  /* Sidebar: fundo claro #F1F5F9 → texto bem escuro para contraste */
  section[data-testid="stSidebar"] { background: #F1F5F9 !important; }
  section[data-testid="stSidebar"] .stMarkdown,
  section[data-testid="stSidebar"] .stMarkdown p,
  section[data-testid="stSidebar"] .stMarkdown h1,
  section[data-testid="stSidebar"] .stMarkdown h2,
  section[data-testid="stSidebar"] .stMarkdown h3,
  section[data-testid="stSidebar"] .stMarkdown span,
  section[data-testid="stSidebar"] .stCaption,
  section[data-testid="stSidebar"] .stCaption span,
  section[data-testid="stSidebar"] label,
  section[data-testid="stSidebar"] span,
  section[data-testid="stSidebar"] p,
  section[data-testid="stSidebar"] div,
  section[data-testid="stSidebar"] [data-testid="stRadio"] label,
  section[data-testid="stSidebar"] [data-testid="stRadio"] span,
  section[data-testid="stSidebar"] [data-testid="stRadio"] p,
  section[data-testid="stSidebar"] [data-testid="stRadio"] div,
  section[data-testid="stSidebar"] * { color: #000000 !important; }
  section[data-testid="stSidebar"] a { color: #000000 !important; }
  /* Área principal (Início, Upload, Recente): texto preto em fundo claro */
  [data-testid="stAppViewContainer"] .stMarkdown,
  [data-testid="stAppViewContainer"] .stMarkdown p,
  [data-testid="stAppViewContainer"] .stMarkdown li,
  [data-testid="stAppViewContainer"] .stMarkdown h1,
  [data-testid="stAppViewContainer"] .stMarkdown h2,
  [data-testid="stAppViewContainer"] .stMarkdown h3,
  [data-testid="stAppViewContainer"] .stMarkdown h4,
  [data-testid="stAppViewContainer"] .stMarkdown h5,
  [data-testid="stAppViewContainer"] .stMarkdown h6,
  [data-testid="stAppViewContainer"] .stMarkdown span,
  [data-testid="stAppViewContainer"] .stCaption,
  [data-testid="stAppViewContainer"] .stCaption span,
  [data-testid="stAppViewContainer"] .stCaption div,
  [data-testid="stVerticalBlock"] .stMarkdown,
  [data-testid="stVerticalBlock"] .stMarkdown p,
  [data-testid="stVerticalBlock"] .stCaption,
  [data-testid="stVerticalBlock"] .stCaption span { color: #000000 !important; }
  section.main .stMarkdown, section.main .stMarkdown p, section.main .stMarkdown li, section.main .stMarkdown h1,
  section.main .stMarkdown h2, section.main .stMarkdown h3, section.main .stMarkdown h4,
  section.main .stMarkdown h5, section.main .stMarkdown h6,
  section.main .stCaption, section.main .stCaption span { color: #000000 !important; }
  .nf-card { background: #FFFFFF; border-radius: 16px; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.06); border: 1px solid #E2E8F0; margin-bottom: 1rem; color: #000000 !important; }
  .nf-card strong { color: #000000 !important; }
  .nf-dropzone { border: 2px dashed #E2E8F0; border-radius: 16px; padding: 2.5rem; text-align: center; background: #F8FAFC; color: #000000 !important; }
  .nf-badge { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; color: #000000 !important; }
  .nf-badge-finalizado { background: #D1FAE5; color: #065f46 !important; }
  .nf-badge-erro { background: #FEE2E2; color: #991b1b !important; }
  .nf-badge-enviado { background: #E2E8F0; color: #334155 !important; }
  .nf-badge-ja_incluido { background: #FEF3C7; color: #92400E !important; }
  .nf-metric { background: #FFFFFF; border-radius: 12px; padding: 1rem; border: 1px solid #E2E8F0; text-align: center; color: #000000 !important; }
  .nf-metric-value { font-size: 1.5rem; font-weight: 700; color: #2563EB !important; }
  .nf-metric-label { font-size: 0.75rem; color: #000000 !important; margin-top: 0.25rem; }
  .nf-app-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem; margin-bottom: 1rem; }
  .nf-app-title { font-size: 1.5rem; font-weight: 700; color: #000000 !important; margin: 0; }
  .nf-app-desc { font-size: 0.875rem; color: #000000 !important; margin: 0.25rem 0 0 0; }
  .nf-status { display: inline-flex; align-items: center; padding: 0.35rem 0.75rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 500; background: #D1FAE5; color: #059669 !important; }
  .nf-postit { background: #FEF3C7; border-radius: 10px; padding: 0.75rem 1rem; border-left: 4px solid #F59E0B; font-size: 0.875rem; margin-bottom: 0.5rem; color: #000000 !important; }
  .stButton > button[kind="primary"] { background: #2563EB !important; color: #FFFFFF !important; border: none !important; font-weight: 600 !important; border-radius: 10px !important; }
  /* Widgets na área principal: labels em preto */
  section.main [data-testid="stRadio"] label, section.main [data-testid="stRadio"] span,
  section.main [data-testid="stSelectbox"] label, section.main [data-testid="stSelectbox"] span,
  section.main .stCheckbox label, section.main .stDateInput label,
  [data-testid="stAppViewContainer"] [data-testid="stRadio"] label,
  [data-testid="stAppViewContainer"] [data-testid="stRadio"] span,
  [data-testid="stAppViewContainer"] [data-testid="stSelectbox"] label,
  [data-testid="stAppViewContainer"] [data-testid="stSelectbox"] span,
  [data-testid="stAppViewContainer"] .stCheckbox label,
  [data-testid="stAppViewContainer"] .stDateInput label { color: #000000 !important; }
  section.main [data-testid="stFileUploader"] label, section.main [data-testid="stFileUploader"] span { color: #000000 !important; }
  section.main [data-testid="stProgress"] span, section.main [data-testid="stProgress"] label { color: #000000 !important; }
  section.main [data-testid="stProgress"] * { color: #000000 !important; }
  [data-testid="stAppViewContainer"] [data-testid="stFileUploader"] label,
  [data-testid="stAppViewContainer"] [data-testid="stFileUploader"] span,
  [data-testid="stAppViewContainer"] [data-testid="stFileUploader"] div,
  [data-testid="stAppViewContainer"] [data-testid="stFileUploader"] p,
  [data-testid="stAppViewContainer"] [data-testid="stFileUploader"] * { color: #000000 !important; }
  [data-testid="stAppViewContainer"] [data-testid="stProgress"] span,
  [data-testid="stAppViewContainer"] [data-testid="stProgress"] label,
  [data-testid="stAppViewContainer"] [data-testid="stProgress"] * { color: #000000 !important; }
  /* Spinner e texto "Processando… aguarde." / "Iniciando…" em preto */
  [data-testid="stSpinner"] *,
  [data-testid="stSpinner"] { color: #000000 !important; }
  [data-testid="stAppViewContainer"] [data-testid="stSpinner"],
  [data-testid="stAppViewContainer"] [data-testid="stSpinner"] * { color: #000000 !important; }
</style>
"""


def inject_css():
    st.markdown(STYLE, unsafe_allow_html=True)


def _load_state():
    """Carrega estado persistido (lista_pesquisadores, metrics, results, csv_drive_path, dúvidas/erros)."""
    out = {
        "lista_pesquisadores": [],
        "metrics": {"files_total": 0, "avg_ocr_sec": 0, "success_rate": 100, "fields_detected": 12, "revisar": 0, "verificar": 0, "erros_total": 0},
        "results": [],
        "csv_drive_path": "",
        "log_duvidas_erros": [],
    }
    if not STATE_FILE.exists():
        return out
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        out["lista_pesquisadores"] = data.get("lista_pesquisadores", []) or []
        out["metrics"] = {**out["metrics"], **(data.get("metrics") or {})}
        out["results"] = data.get("results", []) or []
        out["csv_drive_path"] = (data.get("csv_drive_path") or "").strip()
    except Exception:
        pass
    if LOG_DUVIDAS_FILE.exists():
        try:
            with open(LOG_DUVIDAS_FILE, "r", encoding="utf-8") as f:
                out["log_duvidas_erros"] = json.load(f)
        except Exception:
            pass
    return out


def _save_state():
    """Persiste estado para não perder ao fechar o app."""
    try:
        data = {
            "lista_pesquisadores": st.session_state.get("lista_pesquisadores", []),
            "metrics": st.session_state.get("metrics", {}),
            "results": st.session_state.get("results", []),
            "csv_drive_path": (st.session_state.get("csv_drive_path") or "").strip(),
        }
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=0)
    except Exception:
        pass


def _append_log_duvida(tipo, arquivo, mensagem, detalhe=None):
    """Registra dúvida ou erro para análise em longo prazo."""
    try:
        log = []
        if LOG_DUVIDAS_FILE.exists():
            with open(LOG_DUVIDAS_FILE, "r", encoding="utf-8") as f:
                log = json.load(f)
        log.append({
            "data_hora": datetime.now().isoformat(),
            "tipo": tipo,
            "arquivo": arquivo,
            "mensagem": mensagem,
            "detalhe": detalhe,
        })
        with open(LOG_DUVIDAS_FILE, "w", encoding="utf-8") as f:
            json.dump(log[-500:], f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def init_session_state():
    if "results" not in st.session_state:
        loaded = _load_state()
        st.session_state.results = loaded["results"]
        st.session_state.metrics = loaded["metrics"]
        st.session_state.lista_pesquisadores = loaded["lista_pesquisadores"]
        st.session_state.csv_drive_path = loaded.get("csv_drive_path", "") or ""
        st.session_state.log_duvidas_erros = loaded.get("log_duvidas_erros", [])
    if "processing" not in st.session_state:
        st.session_state.processing = []
    if "metrics" not in st.session_state:
        st.session_state.metrics = {
            "files_total": 0,
            "avg_ocr_sec": 0,
            "success_rate": 100,
            "fields_detected": 12,
            "revisar": 0,
            "verificar": 0,
            "erros_total": 0,
        }
    if "lista_pesquisadores" not in st.session_state:
        st.session_state.lista_pesquisadores = []
    if "csv_drive_path" not in st.session_state:
        st.session_state.csv_drive_path = ""
    if "log_duvidas_erros" not in st.session_state:
        st.session_state.log_duvidas_erros = []


@st.cache_resource
def carregar_modelo_doctr():
    from doctr.models import ocr_predictor
    return ocr_predictor(pretrained=True)


def render_header():
    st.markdown(f"""
    <div class="nf-app-header">
      <div>
        <h1 class="nf-app-title">📄 Notas Fiscai</h1>
        <p class="nf-app-desc">OCR + IA → extração estruturada de notas fiscais (PDF e imagens)</p>
      </div>
      <span class="nf-status">● Online</span>
      <span style="font-size:0.75rem;color:#0F172A;">v{VERSION} · {LAST_UPDATE}</span>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        st.markdown("### 📄 Notas Fiscais")
        st.markdown("---")
        pages = ["Início", "Revisar", "Configurações", "Sobre"]
        page = st.radio("Navegação", options=pages, key="sidebar_nav", label_visibility="collapsed")
        st.session_state.page = page
        st.markdown("---")
        st.caption("🔧 DocTR + LLM")


def run_processing(progress_placeholder):
    processing = st.session_state.get("processing", [])
    to_run = [i for i, p in enumerate(processing) if p.get("bytes") and p.get("status") not in ("Finalizado", "Erro")]
    if not to_run:
        return
    try:
        model = carregar_modelo_doctr()
    except Exception as e:
        st.error(f"Erro ao carregar modelo DocTR: {e}. Instale: pip install python-doctr torch")
        return
    api_key = os.environ.get("GROQ_API_KEY")
    nomes_pesquisadores = list(st.session_state.get("lista_pesquisadores", []))
    results = list(st.session_state.get("results", []))
    metrics = st.session_state.get("metrics", {})
    csv_drive_path = (st.session_state.get("csv_drive_path") or "").strip()
    use_drive_csv = bool(csv_drive_path)
    ja_incluidos = []
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        if use_drive_csv:
            csv_path = Path(csv_drive_path)
            try:
                csv_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
        else:
            csv_path = tmpdir / "nf_extraidas.csv"
        n_total = len(to_run)
        for idx, i in enumerate(to_run):
            item = processing[i]
            name = item["name"]
            progress_placeholder.progress((idx + 0.15) / n_total, text=f"Arquivo {idx+1} de {n_total}")
            st.session_state.processing[i]["status"] = "Validando"
            path = tmpdir / (name or f"file_{i}")
            path.write_bytes(item["bytes"])
            progress_placeholder.progress((idx + 0.4) / n_total, text=f"OCR e extração… {idx+1}/{n_total}")
            st.session_state.processing[i]["status"] = "OCR"
            t0 = time.time()
            try:
                ok, dados = nf_ocr.processar_arquivo(
                    path, model, api_key, sheet_id=None, creds_path=None,
                    csv_path=str(csv_path), dry_run=False, nomes_pesquisadores=nomes_pesquisadores,
                )
                elapsed = time.time() - t0
                if ok and dados is not None:
                    st.session_state.processing[i]["status"] = "Finalizado"
                    rec = nf_ocr.registro_from_dados(dados)
                    rec["_elapsed_sec"] = round(elapsed, 1)
                    results.append(rec)
                    score = (rec.get("score_revisao") or "").strip().lower()
                    if score == "revisar":
                        metrics["revisar"] = metrics.get("revisar", 0) + 1
                        _append_log_duvida("revisar", name, "Nota marcada para revisar (falta dado ou incoerência)", rec.get("numero_nf"))
                    elif score == "verificar":
                        metrics["verificar"] = metrics.get("verificar", 0) + 1
                        _append_log_duvida("verificar", name, "Nota com dúvida (verificar)", rec.get("numero_nf"))
                elif ok and dados is None:
                    st.session_state.processing[i]["status"] = "Já incluído (não duplicado)"
                    ja_incluidos.append(name)
                else:
                    st.session_state.processing[i]["status"] = "Erro"
                    metrics["erros_total"] = metrics.get("erros_total", 0) + 1
                    _append_log_duvida("erro", name, "Processamento falhou", None)
            except Exception as e:
                err_msg = str(e)[:60]
                st.session_state.processing[i]["status"] = f"Erro: {err_msg}"
                metrics["erros_total"] = metrics.get("erros_total", 0) + 1
                _append_log_duvida("erro", name, err_msg, None)
            st.session_state.processing[i]["progress"] = (idx + 1) / n_total * 100
            progress_placeholder.progress((idx + 1) / n_total, text=f"Concluído {idx+1}/{n_total}")
    if ja_incluidos:
        st.session_state.ultimos_ja_incluidos = ja_incluidos
    for p in st.session_state.processing:
        p.pop("bytes", None)
    st.session_state.results = results
    finished = len([p for p in st.session_state.processing if p.get("status") == "Finalizado"])
    st.session_state.metrics["files_total"] = st.session_state.metrics.get("files_total", 0) + finished
    if results:
        times = [r.get("_elapsed_sec", 0) for r in results if "_elapsed_sec" in r]
        if times:
            st.session_state.metrics["avg_ocr_sec"] = round(sum(times) / len(times), 1)
    total = len(st.session_state.processing)
    ok_count = len([p for p in st.session_state.processing if p.get("status") == "Finalizado"])
    st.session_state.metrics["success_rate"] = round(100 * ok_count / total, 0) if total else 100
    _save_state()


def results_to_dataframe(results=None):
    if results is None:
        results = st.session_state.get("results", [])
    if not results:
        return pd.DataFrame()
    rows = []
    for r in results:
        rows.append({
            "Empresa": r.get("razao_social_emitente", ""),
            "CNPJ": r.get("cnpj_emitente", ""),
            "Data": r.get("data_emissao", ""),
            "Valor": f"{r.get('valor_total', '')} {r.get('moeda', 'BRL')}".strip(),
            "Rubrica": r.get("rubrica", ""),
            "Pesquisador": r.get("nome_comprador", ""),
            "Produto": (r.get("itens", "") or r.get("discriminacao", ""))[:120],
        })
    return pd.DataFrame(rows)


def _build_full_csv(results=None):
    results = results or st.session_state.get("results", [])
    if not results:
        return ""
    header = list(results[0].keys())
    out = [";".join(header)]
    for r in results:
        out.append(";".join(str(r.get(k, "")) for k in header))
    return "\n".join(out)


def page_inicio():
    metrics = st.session_state.get("metrics", {})
    st.markdown("#### 📊 Métricas")
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    with c1:
        st.markdown(f'<div class="nf-metric"><div class="nf-metric-value">{metrics.get("files_total", 0)}</div><div class="nf-metric-label">Arquivos processados</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="nf-metric"><div class="nf-metric-value">{metrics.get("avg_ocr_sec", 0)}s</div><div class="nf-metric-label">Tempo médio (OCR)</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="nf-metric"><div class="nf-metric-value">{metrics.get("success_rate", 100)}%</div><div class="nf-metric-label">Taxa de sucesso</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="nf-metric"><div class="nf-metric-value">{metrics.get("fields_detected", 12)}</div><div class="nf-metric-label">Campos detectados</div></div>', unsafe_allow_html=True)
    with c5:
        st.markdown(f'<div class="nf-metric"><div class="nf-metric-value">{metrics.get("revisar", 0)}</div><div class="nf-metric-label">Revisar</div></div>', unsafe_allow_html=True)
    with c6:
        st.markdown(f'<div class="nf-metric"><div class="nf-metric-value">{metrics.get("verificar", 0)}</div><div class="nf-metric-label">Verificar</div></div>', unsafe_allow_html=True)
    with c7:
        st.markdown(f'<div class="nf-metric"><div class="nf-metric-value">{metrics.get("erros_total", 0)}</div><div class="nf-metric-label">Erros</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 1️⃣ Upload")
    st.markdown("Envie **PDF** ou **imagens** (PNG, JPG) das notas fiscais. O sistema extrai os dados automaticamente.")
    st.markdown('<div class="nf-dropzone">', unsafe_allow_html=True)
    uploaded = st.file_uploader(
        "Selecionar arquivos",
        type=["pdf", "png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key="uploader_main",
        label_visibility="collapsed",
    )
    st.caption("Formatos aceitos: PDF, PNG, JPG · **Máximo 200 MB** por arquivo")
    st.markdown('</div>', unsafe_allow_html=True)

    if uploaded:
        max_mb = 200
        valid = [f for f in uploaded if f.size / (1024 * 1024) <= max_mb]
        for f in uploaded:
            if f.size / (1024 * 1024) > max_mb:
                st.warning(f"**{f.name}** excede {max_mb} MB e foi ignorado.")
        if valid:
            clicou = st.button("▶️ Iniciar processamento", type="primary", use_container_width=True)
            if clicou:
                groq = os.environ.get("GROQ_API_KEY", "")
                hf = os.environ.get("HF_TOKEN", "")
                if not groq and not hf:
                    st.error("⚠️ Configure o arquivo **.env** na pasta do projeto com **GROQ_API_KEY** ou **HF_TOKEN**.")
                    return
                if groq:
                    os.environ["GROQ_API_KEY"] = groq
                if hf:
                    os.environ["HF_TOKEN"] = hf
                with st.spinner("Enviando..."):
                    st.session_state.processing = [
                        {"name": f.name, "status": "Enviado", "progress": 0, "bytes": f.getvalue()}
                        for f in valid
                    ]
                st.rerun()

    processing = st.session_state.get("processing", [])
    if processing:
        st.markdown("---")
        st.markdown("#### 2️⃣ Processamento")
        has_pending = any(p.get("bytes") for p in processing)
        if has_pending:
            with st.spinner("⏳ Processando… aguarde."):
                progress_placeholder = st.empty()
                progress_placeholder.progress(0, text="Iniciando…")
                try:
                    run_processing(progress_placeholder)
                except Exception as e:
                    progress_placeholder.empty()
                    st.error(f"Erro: {e}")
            st.rerun()

        for item in processing:
            name = item.get("name", "?")
            status = item.get("status", "Enviado")
            sc = "finalizado" if status == "Finalizado" else "erro" if "Erro" in str(status) else "enviado" if status == "Enviado" else "ja_incluido" if "Já incluído" in str(status) else "enviado"
            st.markdown(
                f'<div class="nf-card"><span style="color:#0F172A;font-weight:600;">{name}</span> <span class="nf-badge nf-badge-{sc}">{status}</span></div>',
                unsafe_allow_html=True,
            )
        if st.session_state.get("ultimos_ja_incluidos"):
            ja_list = st.session_state.ultimos_ja_incluidos
            st.warning(f"**Aviso:** Os seguintes arquivos já constavam na planilha e **não foram duplicados**: {', '.join(ja_list)}.")
            st.session_state.ultimos_ja_incluidos = []

    results = st.session_state.get("results", [])
    if results:
        st.markdown("---")
        st.markdown("#### 3️⃣ Resultados")
        st.markdown("Use os **filtros** abaixo para refinar a tabela. Depois **exporte em CSV** se precisar.")
        df_full = results_to_dataframe(results)

        st.markdown("**🔍 Filtros**")
        rubricas = ["viagem", "participacao_congresso", "material_consumo", "material_permanente", "servico_terceiros"]
        labels = ["Viagem", "Participação em congresso", "Material de consumo", "Material permanente", "Serviço de terceiros"]
        filtro_rubrica = st.radio("Rubrica", options=["Todas"] + labels, key="filtro_rubrica", horizontal=True)
        col_d, col_p = st.columns(2)
        with col_d:
            datas = sorted(set(r.get("data_emissao", "") for r in results if r.get("data_emissao")))
            use_cal = st.checkbox("Usar calendário para data", key="use_cal_data")
            if use_cal:
                from datetime import date
                d = st.date_input("📅 Selecione a data", key="filtro_data_cal")
                filtro_data = d.strftime("%Y-%m-%d") if d else "Todas"
            else:
                filtro_data = st.selectbox("Data", options=["Todas"] + datas, key="filtro_data")
        with col_p:
            pesquisadores_resultados = set(r.get("nome_comprador", "") for r in results if r.get("nome_comprador"))
            pesquisadores_config = set(st.session_state.get("lista_pesquisadores", []))
            pesquisadores = sorted(pesquisadores_resultados | pesquisadores_config)
            filtro_pesq = st.selectbox("Pesquisador", options=["Todos"] + pesquisadores, key="filtro_pesq")

        filtered = list(results)
        if filtro_rubrica != "Todas":
            rubrica_val = rubricas[labels.index(filtro_rubrica)]
            filtered = [r for r in filtered if (r.get("rubrica") or "").strip() == rubrica_val]
        if filtro_data != "Todas":
            filtered = [r for r in filtered if r.get("data_emissao") == filtro_data]
        if filtro_pesq != "Todos":
            filtered = [r for r in filtered if (r.get("nome_comprador") or "").strip() == filtro_pesq]

        df = results_to_dataframe(filtered)
        st.data_editor(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Empresa": st.column_config.TextColumn("Empresa", width="medium"),
                "CNPJ": st.column_config.TextColumn("CNPJ", width="small"),
                "Data": st.column_config.TextColumn("Data", width="small"),
                "Valor": st.column_config.TextColumn("Valor", width="small"),
                "Rubrica": st.column_config.TextColumn("Rubrica", width="medium"),
                "Pesquisador": st.column_config.TextColumn("Pesquisador", width="medium"),
                "Produto": st.column_config.TextColumn("Produto", width="large"),
            },
            key="results_editor",
        )
        csv_content = _build_full_csv(results)
        st.download_button("📥 Exportar CSV", data=csv_content, file_name="notas_fiscais.csv", mime="text/csv", use_container_width=True)

    st.markdown("---")
    st.markdown("#### 📌 Recente · Informações")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Últimos processamentos**")
        if processing:
            for item in processing[-5:]:
                st.caption(f"• {item.get('name', '?')} — {item.get('status', '')}")
        else:
            st.caption("Nenhum arquivo processado nesta sessão.")
    with col_b:
        st.markdown("**Informações do sistema**")
        st.markdown(f'<div class="nf-postit">📁 Total processados: <strong>{metrics.get("files_total", 0)}</strong> · ✅ Sucesso: <strong>{metrics.get("success_rate", 100)}%</strong></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="nf-postit">⚠️ Revisar: <strong>{metrics.get("revisar", 0)}</strong> · ❓ Verificar: <strong>{metrics.get("verificar", 0)}</strong> · ❌ Erros: <strong>{metrics.get("erros_total", 0)}</strong></div>', unsafe_allow_html=True)


def page_revisar():
    st.subheader("⚠️ Área de revisão")
    results = st.session_state.get("results", [])
    revisar = [r for r in results if (r.get("score_revisao") or "").strip().lower() in ("revisar", "verificar")]
    st.markdown("Itens com score **revisar** ou **verificar** (falta dado, incoerência ou dúvida). Revise e corrija na planilha ou no exporto.")
    if not revisar:
        st.info("Nenhum item para revisar no momento. Os que precisarem aparecerão aqui após o processamento.")
        return
    st.markdown(f"**{len(revisar)}** itens para revisar.")
    df = results_to_dataframe(revisar)
    df["Score"] = [r.get("score_revisao", "") for r in revisar]
    df["Arquivo"] = [r.get("discriminacao", "") for r in revisar]
    st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Empresa": st.column_config.TextColumn("Empresa", width="medium"),
            "CNPJ": st.column_config.TextColumn("CNPJ", width="small"),
            "Data": st.column_config.TextColumn("Data", width="small"),
            "Valor": st.column_config.TextColumn("Valor", width="small"),
            "Rubrica": st.column_config.TextColumn("Rubrica", width="medium"),
            "Pesquisador": st.column_config.TextColumn("Pesquisador", width="medium"),
            "Produto": st.column_config.TextColumn("Produto", width="large"),
            "Score": st.column_config.TextColumn("Score", width="small"),
            "Arquivo": st.column_config.TextColumn("Arquivo", width="medium"),
        },
        key="revisar_editor",
    )
    csv_revisar = _build_full_csv(revisar)
    st.download_button("📥 Exportar lista para revisão (CSV)", data=csv_revisar, file_name="notas_para_revisar.csv", mime="text/csv", use_container_width=True, key="dl_revisar")


def page_configuracoes():
    st.subheader("⚙️ Configurações")
    st.markdown("**📁 Planilha no Drive (ou pasta local)**")
    st.caption("Se preenchido, os dados são gravados direto nesse arquivo CSV (ex.: pasta sincronizada com Google Drive). Documentos já presentes não são duplicados.")
    csv_path = st.text_input(
        "Caminho do arquivo CSV",
        value=st.session_state.get("csv_drive_path", "") or "",
        placeholder="Ex.: G:\\Meu Drive\\notas_fiscais_silvia\\notas.csv",
        key="input_csv_drive_path",
    )
    if csv_path != st.session_state.get("csv_drive_path", ""):
        st.session_state.csv_drive_path = (csv_path or "").strip()
        _save_state()
    st.markdown("---")
    st.markdown("**👤 Pesquisadores** — os nomes abaixo aparecem no filtro e são enviados para a **IA** reconhecer melhor o **nome do comprador** na extração.")
    lista = st.session_state.get("lista_pesquisadores", [])
    nome_novo = st.text_input("Nome do pesquisador", key="novo_pesquisador", placeholder="Digite o nome e clique em Adicionar")
    if st.button("➕ Adicionar pesquisador"):
        if nome_novo and nome_novo.strip():
            if nome_novo.strip() not in lista:
                lista.append(nome_novo.strip())
                st.session_state.lista_pesquisadores = lista
                _save_state()
                st.rerun()
        else:
            st.warning("Digite um nome.")
    if lista:
        st.markdown("**Lista atual:**")
        for i, nome in enumerate(lista):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.caption(f"• {nome}")
            with col2:
                if st.button("🗑️ Remover", key=f"remover_{i}"):
                    lista.pop(i)
                    st.session_state.lista_pesquisadores = lista
                    _save_state()
                    st.rerun()

    st.markdown("---")
    st.markdown("**📋 Registro de dúvidas e erros** (últimas entradas)")
    log = []
    if LOG_DUVIDAS_FILE.exists():
        try:
            with open(LOG_DUVIDAS_FILE, "r", encoding="utf-8") as f:
                log = json.load(f)
        except Exception:
            pass
    if log:
        for entry in reversed(log[-20:]):
            tipo = entry.get("tipo", "")
            emoji = "⚠️" if tipo == "revisar" else "❓" if tipo == "verificar" else "❌"
            st.caption(f"{emoji} [{entry.get('data_hora', '')[:16]}] **{entry.get('arquivo', '?')}** — {entry.get('mensagem', '')}")
    else:
        st.caption("Nenhum registro ainda. As notas com score *revisar* ou *verificar* e erros de processamento são registrados aqui ao longo do tempo.")


def page_sobre():
    st.subheader("ℹ️ Sobre o sistema")
    fluxo_path = Path(__file__).resolve().parent / "pipeline_fluxograma.png"
    if not fluxo_path.exists():
        fluxo_path = Path(__file__).resolve().parent.parent / "assets" / "notas_fiscais_pipeline_flowchart.png"
    col_tex, col_img = st.columns([1, 1])
    with col_tex:
        st.markdown(
            "**📄 Notas Fiscais** extrai dados estruturados de **notas fiscais** usando **OCR** e **modelos de linguagem (IA)**.\n\n"
            "### O que é OCR?\n"
            "**OCR** (*Reconhecimento Óptico de Caracteres*) é a tecnologia que **lê** texto em imagens e PDFs. "
            "Em vez de digitar manualmente, o sistema *enxerga* o documento e transforma o que está escrito em texto editável. "
            "Aqui usamos o **DocTR**, que preserva linhas e espaços para a IA interpretar melhor. "
            "O resultado é um texto <u>organizado</u> por linhas, ideal para a extração dos campos."
        , unsafe_allow_html=True)
    with col_img:
        if fluxo_path.exists():
            st.image(str(fluxo_path), use_container_width=True)
            st.caption("Fluxo do processamento")
    st.markdown("""
    ### 📋 Pipeline

    1. **Upload** — Envio do PDF ou imagem.
    2. **OCR (DocTR)** — Extração do texto com preservação de linhas e espaços.
    3. **Extração (LLM)** — Um modelo de linguagem identifica número da NF, data, empresa, CNPJ, valor, moeda, rubrica, etc.
    4. **Estruturação** — Dados organizados em tabela; filtros por rubrica, data e pesquisador; exportação em CSV.

    ### 🔧 Modelos utilizados

    - **DocTR** — OCR para PDF e imagens.
    - **LLM** — Groq (Llama) ou Hugging Face (Gemma, Qwen, Mistral), configurado no arquivo **.env**. A IA classifica em **rubricas** e preenche os campos.
    """)


def main():
    st.set_page_config(page_title="Registo Notas Fiscais", page_icon="📄", layout="wide", initial_sidebar_state="expanded")
    inject_css()
    init_session_state()
    render_sidebar()
    render_header()

    page = st.session_state.get("page", "Início")
    if page == "Início":
        page_inicio()
    elif page == "Revisar":
        page_revisar()
    elif page == "Configurações":
        page_configuracoes()
    else:
        page_sobre()


if __name__ == "__main__":
    main()
