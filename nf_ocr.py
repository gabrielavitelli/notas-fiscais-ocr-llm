"""
Notas Fiscais BR: OCR (DocTR) -> LLM -> planilha (CSV ou Google Sheets).

Sem Google Cloud? Use --csv saida.csv (grava em CSV local; abra no Excel ou importe no Sheets).
Ler arquivos do Drive? Use Google Drive para Desktop e aponte a pasta sincronizada.

  set GROQ_API_KEY=...       # https://console.groq.com/keys
  python nf_ocr.py "pasta_ou_arquivo.pdf" --csv nf_extraidas.csv
"""
import os
import re
import json
import csv
import argparse
import unicodedata
from pathlib import Path

# Colunas da NF (planilha e CSV)
NF_COLUNAS = [
    "numero_nf", "data_emissao", "nome_comprador",
    "cnpj_emitente", "razao_social_emitente",
    "valor_total", "moeda", "rubrica",
    "discriminacao", "link_drive", "score_revisao", "itens",
]

# Linha de legenda na planilha: critério do score_revisao (campos principais = data, nome_comprador, valor, moeda)
LEGENDA_SCORE_REVISAO = "score_revisao: ok=completo (data, nome, valor, moeda); revisar=falta algum; verificar=dúvida"

# Rubricas para classificação (prestação de contas)
RUBRICAS = {
    "viagem": "Hotel, hospedagem, diária, Uber, táxi, ônibus, passagem aérea",
    "participacao_congresso": "Inscrição em congresso (nacional ou internacional)",
    "material_consumo": "Material de consumo",
    "material_permanente": "Material permanente (ex.: furadeira, equipamentos)",
    "servico_terceiros": "Serviço de terceiros (serviço feito fora, ex.: clip gage)",
}

# --- 1) DocTR: texto com espaços e quebras por LINHA ---
def _doctr_text_from_doc(result):
    """Extrai texto preservando linhas (espaço entre palavras, \\n entre linhas).
    Evita 'texto td junto': junta palavras por linha, linhas separadas por \\n."""
    lines = []
    for page in result.pages:
        for block in page.blocks:
            for line in block.lines:
                line_text = " ".join(w.value for w in line.words).strip()
                if line_text:
                    lines.append(line_text)
    return "\n".join(lines)


def ocr_file(path, model):
    """OCR de um PDF ou imagem; retorna texto formatado por linhas."""
    from doctr.io import DocumentFile
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        doc = DocumentFile.from_pdf(str(path))
    else:
        doc = DocumentFile.from_images([str(path)])
    result = model(doc)
    return _doctr_text_from_doc(result)


# --- 2) LLM: texto → JSON estruturado (NF BR) ---
PROMPT_NF = """Extraia os dados desta nota fiscal (texto do OCR) e classifique na rubrica correta.

Retorne APENAS um JSON válido, sem markdown, com as chaves:
- numero_nf (string)
- data_emissao (YYYY-MM-DD)
- nome_comprador (string: APENAS o nome da pessoa ou razão social de quem comprou/contratou; NÃO inclua CPF, CNPJ nem números no início — só o nome)
- cnpj_emitente (string: APENAS os 14 dígitos do CNPJ de quem EMITIU a nota, o fornecedor; procure no documento e preencha quando aparecer)
- razao_social_emitente (string)
- valor_total (número, só o valor)
- moeda (string: sigla da moeda, ex. BRL, USD, EUR, ou null se não aparecer)
- rubrica (string: exatamente UMA das opções abaixo, conforme o tipo de despesa)
- score_revisao (string: "ok" | "revisar" | "verificar". OBRIGATÓRIO basear nos 4 campos principais: data_emissao, nome_comprador, valor_total, moeda. Use "ok" somente quando os quatro estiverem preenchidos e coerentes; "revisar" quando faltar algum deles ou houver incoerência; "verificar" quando houver dúvida.)
- itens (lista de strings, descrição dos itens/serviços)

RUBRICAS (escolha UMA que melhor se encaixe):
- viagem: hotel, hospedagem, Uber, táxi, ônibus, passagem aérea, transporte
- participacao_congresso: inscrição em congresso (nacional ou internacional)
- material_consumo: compra de PRODUTOS/MATERIAIS (kit, ferro de solda, sensor, papel, consumíveis, componentes, etc.) — use para itens físicos consumíveis ou pequenos equipamentos de consumo
- material_permanente: material permanente, equipamentos (furadeira, máquinas, bens duráveis)
- servico_terceiros: SERVIÇO prestado por terceiro (mão de obra, execução de serviço, manutenção contratada, clip gage feito fora) — NÃO use para compra de produtos/materiais; só quando a despesa é pelo serviço em si

REGRA DE PRIORIDADE MUITO IMPORTANTE:
- Se houver indícios de hospedagem (ex.: HOTEL, HOSPEDAGEM, DIARIA/DIÁRIA, CHECK-IN, CHECK-OUT, APTO, HÓSPEDE, TOTAL DIARIA), classifique como **viagem**.
- Nesses casos de hotel/hospedagem, NÃO usar servico_terceiros.

Se um campo não for encontrado, use null. valor_total: só o número. moeda: BRL se for real brasileiro quando não estiver explícito. score_revisao: o mais importante é data + nome_comprador + valor + moeda; ok só se os quatro estiverem presentes e coerentes.
{nomes_pesquisadores}

Texto do documento:
---
{texto}
---
JSON:"""


def _normalize_llm_json(out):
    out = (out or "").strip()
    if out.startswith("```"):
        out = re.sub(r"^```\w*\n?", "", out)
        out = re.sub(r"\n?```\s*$", "", out)
    return json.loads(out)


# --- Groq (grátis, rápido): https://console.groq.com/keys ---
# Listar modelos: python list_groq_models.py
# Ex.: llama-3.1-8b-instant, llama-3.3-70b-versatile, openai/gpt-oss-20b, groq/compound-mini
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

def _build_prompt(texto, nomes_pesquisadores=None):
    """Monta o prompt com texto e, se houver, lista de nomes de pesquisadores para a IA preferir em nome_comprador."""
    nomes_hint = ""
    if nomes_pesquisadores:
        nomes_list = ", ".join(str(n).strip() for n in nomes_pesquisadores if n and str(n).strip())
        if nomes_list:
            nomes_hint = "Nomes conhecidos de pesquisadores (use exatamente um destes em nome_comprador quando o documento se referir ao comprador/destinatário): " + nomes_list + "\n"
    return PROMPT_NF.format(texto=texto, nomes_pesquisadores=nomes_hint)


def _llm_groq(prompt, api_key):
    from openai import OpenAI
    client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=api_key)
    r = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=1024,
    )
    raw = (r.choices[0].message.content or "").strip()
    return _normalize_llm_json(raw)


# --- Hugging Face (Inference Providers): https://huggingface.co/settings/tokens --- nova API "Inference Providers" (router.huggingface.co) — a antiga api-inference retorna 410 Gone.
# Modelos que funcionam na nova API: https://huggingface.co/models?inference=warm&pipeline_tag=conversational
_HF_MODELS = [
    "google/gemma-2-2b-it",                    # pequeno, rápido, bom para instruções
    "Qwen/Qwen2.5-7B-Instruct-1M",             # conversacional, contexto longo
    "mistralai/Mistral-7B-Instruct-v0.2",      # bom para JSON
]

def _llm_hf(prompt, token):
    from openai import OpenAI
    client = OpenAI(base_url="https://router.huggingface.co/v1", api_key=token)
    last_err = None
    for model_id in _HF_MODELS:
        try:
            r = client.chat.completions.create(
                model=model_id,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=1024,
            )
            raw = (r.choices[0].message.content or "").strip()
            if not raw:
                continue
            return _normalize_llm_json(raw)
        except Exception as e:
            last_err = e
            err = str(e).lower()
            if "410" in err or "gone" in err or "not found" in err or "rate" in err or "model_not_supported" in err or "not supported by any provider" in err:
                continue
            raise
    raise RuntimeError(
        f"Hugging Face falhou em todos os modelos. Verifique: 1) Token com permissão 'Inference Providers' em "
        "https://huggingface.co/settings/tokens 2) Modelos em https://huggingface.co/playground. Último erro: %s"
        % last_err
    ) from last_err


# --- Transformers local (sem API key): pip install transformers torch ---
def _llm_transformers(prompt):
    from transformers import pipeline
    # distilgpt2 tem contexto curto; truncar prompt se necessário
    prompt = prompt[:1800] + "\nJSON:" if len(prompt) > 1800 else prompt + "\nJSON:"
    pipe = pipeline(
        "text-generation",
        model="distilgpt2",
        device=-1,
    )
    out = pipe(prompt, max_new_tokens=350, do_sample=False, pad_token_id=pipe.model.config.eos_token_id)[0]["generated_text"]
    if not out or prompt not in out:
        out = out or ""
    else:
        out = out.split("JSON:")[-1].strip()
    start = out.find("{")
    if start >= 0:
        depth, end = 0, start
        for i, c in enumerate(out[start:], start):
            if c == "{": depth += 1
            elif c == "}": depth -= 1
            if depth == 0: end = i; break
        out = out[start:end + 1]
    return _normalize_llm_json(out)


def llm_extrair(texto, api_key=None, nomes_pesquisadores=None):
    """Ordem: Groq (grátis) -> Hugging Face -> Transformers (local, sem chave).
    nomes_pesquisadores: lista de nomes para a IA preferir em nome_comprador quando o documento se referir ao comprador."""
    texto = texto[:8000]
    prompt = _build_prompt(texto, nomes_pesquisadores)
    groq_key = os.environ.get("GROQ_API_KEY") or api_key
    hf_token = os.environ.get("HF_TOKEN")
    provider = os.environ.get("LLM_PROVIDER", "").lower()

    tentativas = []
    if provider == "groq" or (not provider and groq_key):
        tentativas.append(("Groq", lambda: _llm_groq(prompt, groq_key)))
    if provider == "hf" or (not provider and hf_token):
        tentativas.append(("HF", lambda: _llm_hf(prompt, hf_token)))
    if provider == "transformers" or (not provider and not groq_key and not hf_token):
        tentativas.append(("Transformers", lambda: _llm_transformers(prompt)))

    last_err = None
    for nome, fn in tentativas:
        try:
            return fn()
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM não retornou JSON válido: {e}") from e
        except Exception as e:
            last_err = e
            if provider:
                raise
    raise RuntimeError(
        "Nenhuma LLM disponível. Defina uma chave (uma vez só): "
        "No PC: crie/edite o arquivo .env na pasta do projeto com GROQ_API_KEY=... (copie de .env.example). "
        "Na nuvem: share.streamlit.io → seu app → Settings → Secrets → adicione GROQ_API_KEY ou HF_TOKEN. "
        "O .env não é enviado ao GitHub. Último erro: " + str(last_err)
    ) from last_err


def _enforce_rubrica_rules(dados, texto_ocr):
    """Corrige rubrica em casos bem evidentes para reduzir erro da LLM."""
    if not isinstance(dados, dict):
        return dados
    text = (texto_ocr or "").lower()
    itens = dados.get("itens")
    if isinstance(itens, list):
        text += " " + " ".join(str(x).lower() for x in itens)
    elif isinstance(itens, str):
        text += " " + itens.lower()
    # Também considera descrição curta da nota.
    text += " " + str(dados.get("discriminacao") or "").lower()

    # Normaliza acentos para melhorar match (diária/diaria, hóspede/hospede).
    text_norm = "".join(
        ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn"
    )
    rub = str(dados.get("rubrica") or "").strip().lower().replace(" ", "_")

    hospedagem_signals = [
        "hospedagem", "hotel", "diaria", "diária", "check-in", "check-out",
        "hospede", "hóspede", "total diaria", "total diária", "apto",
    ]
    if any(s in text_norm for s in hospedagem_signals):
        dados["rubrica"] = "viagem"
        return dados

    return dados


def reclassificar_rubrica_processada(dados, texto_ocr=""):
    """API pública para reclassificar rubrica em registros já processados."""
    if not isinstance(dados, dict):
        return dados
    clone = dict(dados)
    return _enforce_rubrica_rules(clone, texto_ocr)


# --- 3) Google Sheets: append linha ---
def _limpar_nome_comprador(s):
    """Remove só CPF/CNPJ do início (padrão 11 ou 14 dígitos). Não corta nome; se não achar doc no início, devolve o texto original."""
    if not s or not isinstance(s, str):
        return s or ""
    s = s.strip()
    # Só remove no início um CNPJ (14 dígitos) ou CPF (11 dígitos) com formatação opcional
    cnpj = re.match(r"^\s*\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s-]?\d{4}[-\s]?\d{2}\s*", s)
    cpf = re.match(r"^\s*\d{3}[.\s]?\d{3}[.\s]?\d{3}[-\s]?\d{2}\s*", s)
    if cnpj:
        return s[cnpj.end() :].strip() or s
    if cpf:
        return s[cpf.end() :].strip() or s
    # Se houver só dígitos/separadores no início e depois letras (nome), usa a parte após os números
    m = re.match(r"^[\d\s.\/\-]+(\s+\S.+)", s)
    if m:
        rest = m.group(1).strip()
        if len(rest) >= 2 and rest[0].isalpha():
            return rest
    return s


def _resolver_nome_mascarado(nome, lista_pesquisadores):
    """Se o nome vier com asteriscos (ex: Bern***) ou for um prefixo curto, tenta
    identificar com um pesquisador cadastrado (ex: Bernardo). Retorna o nome completo
    quando houver uma única correspondência; caso contrário devolve o nome original."""
    if not nome or not isinstance(nome, str):
        return nome or ""
    nome = nome.strip()
    if not lista_pesquisadores:
        return nome
    # Extrai o prefixo antes de asteriscos (ex: "Bern***" -> "Bern")
    prefix = re.sub(r"\*.*", "", nome).strip() or nome
    prefix = prefix.strip()
    if len(prefix) < 2:
        return nome
    lista = [str(p).strip() for p in lista_pesquisadores if p and str(p).strip()]
    matches = [p for p in lista if p.lower().startswith(prefix.lower())]
    if len(matches) == 1:
        return matches[0]
    return nome


def _dados_para_linha(dados):
    """Uma linha (lista) com as colunas da NF."""
    itens = dados.get("itens") or []
    valor = dados.get("valor_total")
    raw_moeda = (dados.get("moeda") or "BRL").strip().upper()
    if not raw_moeda or raw_moeda in ("R$", "REAL", "REAIS"):
        moeda = "BRL"
    elif raw_moeda in ("$", "US$", "DOLAR", "DÓLAR"):
        moeda = "USD"
    elif raw_moeda in ("€", "EURO", "EUR"):
        moeda = "EUR"
    else:
        moeda = raw_moeda if len(raw_moeda) <= 4 else "BRL"
    rubrica = (dados.get("rubrica") or "").strip().lower().replace(" ", "_")
    if rubrica and rubrica not in RUBRICAS:
        rubrica = rubrica
    score = (dados.get("score_revisao") or "").strip().lower()
    if score not in ("ok", "revisar", "verificar"):
        score = score or "verificar"
    nome_comprador = _limpar_nome_comprador(dados.get("nome_comprador") or "")
    cnpj_emitente = (dados.get("cnpj_emitente") or "")
    if isinstance(cnpj_emitente, (int, float)):
        cnpj_emitente = str(int(cnpj_emitente))
    cnpj_emitente = re.sub(r"\D", "", str(cnpj_emitente))  # só dígitos
    return [
        dados.get("numero_nf"),
        dados.get("data_emissao"),
        nome_comprador,
        cnpj_emitente,
        dados.get("razao_social_emitente"),
        valor,
        moeda,
        rubrica,
        dados.get("discriminacao", ""),
        dados.get("link_drive", ""),
        score,
        json.dumps(itens, ensure_ascii=False) if isinstance(itens, list) else str(itens),
    ]


def _discriminacoes_no_csv(csv_path):
    """Retorna o conjunto de valores já presentes na coluna discriminacao do CSV (evita duplicata)."""
    path = Path(csv_path)
    if not path.exists():
        return set()
    try:
        with open(path, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=";")
            header = next(reader, None)
            if not header or "discriminacao" not in header:
                return set()
            idx = header.index("discriminacao")
            return {row[idx].strip() for row in reader if len(row) > idx and row[idx].strip()}
    except Exception:
        return set()


def _linha_legenda_score():
    """Uma linha com a legenda do score_revisao na coluna correta; demais células vazias."""
    row = [""] * len(NF_COLUNAS)
    idx = NF_COLUNAS.index("score_revisao")
    row[idx] = LEGENDA_SCORE_REVISAO
    return row


def registro_from_dados(dados):
    """Retorna um dict com as mesmas chaves que uma linha do CSV (para uso no app)."""
    return dict(zip(NF_COLUNAS, _dados_para_linha(dados)))


def csv_append(dados, csv_path):
    """Grava/append numa planilha CSV local. Não adiciona se já existir linha com o mesmo discriminacao (nome do arquivo)."""
    path = Path(csv_path)
    discriminacao = (dados.get("discriminacao") or "").strip()
    if discriminacao and discriminacao in _discriminacoes_no_csv(path):
        return False
    file_exists = path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        if not file_exists:
            w.writerow(NF_COLUNAS)
            w.writerow(_linha_legenda_score())
        w.writerow(_dados_para_linha(dados))
    return True


def sheet_append(dados, sheet_id=None, creds_path=None):
    """Adiciona uma linha no Google Sheets (requer conta Google Cloud ativa)."""
    sheet_id = sheet_id or os.environ.get("GOOGLE_SHEET_ID")
    creds_path = creds_path or os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if not sheet_id or not creds_path:
        raise ValueError("Defina GOOGLE_SHEET_ID e GOOGLE_CREDENTIALS_JSON (ou use --csv para planilha local).")
    import gspread
    from google.oauth2.service_account import Credentials
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file"]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    ws = sh.sheet1
    if not ws.acell("A1").value or ws.acell("A1").value != "numero_nf":
        ws.insert_row(NF_COLUNAS, 1)
        ws.insert_row(_linha_legenda_score(), 2)
    ws.append_row(_dados_para_linha(dados), value_input_option="USER_ENTERED")
    return True


# --- Pipeline e CLI ---
def processar_arquivo(path, model, api_key, sheet_id, creds_path, csv_path=None, dry_run=False, nomes_pesquisadores=None, return_text=False):
    """Retorna (ok, dados) por padrão.
    Se return_text=True, retorna (ok, dados, texto_ocr)."""
    path = Path(path)
    print(f"[OCR] {path.name}...")
    texto = ocr_file(path, model)
    if not texto.strip():
        print(f"  -> Sem texto extraído. Pulando.")
        return (False, None, texto) if return_text else (False, None)
    print(f"[LLM] Estruturando...")
    dados = llm_extrair(texto, api_key, nomes_pesquisadores=nomes_pesquisadores)
    dados = _enforce_rubrica_rules(dados, texto)
    dados["discriminacao"] = path.name
    dados["link_drive"] = dados.get("link_drive") or ""
    # Resolve nome com asteriscos (ex: Bern***) usando a lista de pesquisadores (ex: Bernardo)
    nome_limpo = _limpar_nome_comprador(dados.get("nome_comprador") or "")
    dados["nome_comprador"] = _resolver_nome_mascarado(nome_limpo, nomes_pesquisadores or [])
    if dry_run:
        print(json.dumps(dados, indent=2, ensure_ascii=False))
        return (True, dados, texto) if return_text else (True, dados)
    if csv_path:
        if csv_append(dados, csv_path):
            print(f"  -> CSV atualizado: {csv_path} (NF {dados.get('numero_nf')})")
            return (True, dados, texto) if return_text else (True, dados)
        print(f"  -> Já existe no CSV (discriminacao={path.name}). Pulando.")
        return (True, None, texto) if return_text else (True, None)
    if sheet_id and creds_path:
        try:
            sheet_append(dados, sheet_id, creds_path)
            print(f"  -> Google Sheets atualizado. NF {dados.get('numero_nf')}.")
            return (True, dados, texto) if return_text else (True, dados)
        except Exception as e:
            print(f"  -> Google Sheets falhou ({e}). Use --csv saida.csv para planilha local.")
            if csv_append(dados, "nf_extraidas.csv"):
                print(f"  -> Gravado em nf_extraidas.csv")
                return (True, dados, texto) if return_text else (True, dados)
            return (True, None, texto) if return_text else (True, None)
    if csv_append(dados, "nf_extraidas.csv"):
        print(f"  -> Gravado em nf_extraidas.csv (NF {dados.get('numero_nf')}).")
        return (True, dados, texto) if return_text else (True, dados)
    print(f"  -> Já existe no CSV (discriminacao={path.name}). Pulando.")
    return (True, None, texto) if return_text else (True, None)


def main():
    # Carrega .env da pasta do script (para não precisar definir variáveis no terminal)
    from pathlib import Path
    _env = Path(__file__).resolve().parent / ".env"
    if _env.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(_env)
        except ImportError:
            pass

    p = argparse.ArgumentParser(description="OCR de NFs (DocTR) + LLM -> planilha (CSV ou Google Sheets)")
    p.add_argument("entrada", nargs="?", default=".", help="Arquivo PDF/imagem ou pasta (pode ser pasta do Drive sincronizada)")
    p.add_argument("--dry-run", action="store_true", help="Só extrair e imprimir JSON")
    p.add_argument("--csv", metavar="ARQUIVO", help="Gravar na planilha CSV local (não usa Google). Ex.: --csv saida.csv")
    p.add_argument("--no-sheet", action="store_true", help="Não usar Google Sheets (grava em nf_extraidas.csv se não passar --csv)")
    args = p.parse_args()

    entrada = Path(args.entrada)
    if entrada.is_file():
        arquivos = [entrada]
    else:
        arquivos = list(entrada.glob("*.pdf")) + list(entrada.glob("*.png")) + list(entrada.glob("*.jpg"))
    if not arquivos:
        print("Nenhum PDF ou imagem encontrado.")
        return

    print("Carregando modelo DocTR...")
    from doctr.models import ocr_predictor
    model = ocr_predictor(pretrained=True)

    api_key = os.environ.get("GROQ_API_KEY")
    csv_path = args.csv
    if not csv_path and (args.no_sheet or not os.environ.get("GOOGLE_SHEET_ID") or not os.environ.get("GOOGLE_CREDENTIALS_JSON")):
        csv_path = "nf_extraidas.csv"
    sheet_id = None if (args.no_sheet or csv_path) else os.environ.get("GOOGLE_SHEET_ID")
    creds_path = os.environ.get("GOOGLE_CREDENTIALS_JSON")

    for f in arquivos:
        try:
            processar_arquivo(
                f, model, api_key,
                sheet_id=sheet_id,
                creds_path=creds_path,
                csv_path=csv_path,
                dry_run=args.dry_run,
            )
        except Exception as e:
            print(f"  Erro em {f.name}: {e}")


if __name__ == "__main__":
    main()
