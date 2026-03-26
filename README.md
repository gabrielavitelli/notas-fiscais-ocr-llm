# 📄 Notas Fiscais — OCR + IA

App para **extração estruturada** de dados de notas fiscais (PDF e imagens): OCR com **DocTR**, classificação com **LLM** (Groq ou Hugging Face) e interface **Streamlit**. Extrai número, data, empresa, CNPJ, valor, moeda, rubrica e pesquisador. Exporta CSV, evita duplicatas e inclui área de revisão para itens com score *revisar* ou *verificar*.

---

## 🚀 Como usar

### Na nuvem (PC desligado)

Deploy grátis no **Streamlit Community Cloud** → [DEPLOY_NUVEM.md](DEPLOY_NUVEM.md).  
Se o build falhar com `libgl1-mesa-glx`, remova o arquivo do repo: `git rm packages.txt` → commit → push.

### No seu PC (com DocTR — fluxo completo)

```bash
cd notas_fiscais
pip install -r requirements-local.txt
streamlit run app.py
```

Abra o link no terminal (ex.: `http://localhost:8501`). Configure as chaves no [.env](.env.example) (copie para `.env` e preencha `GROQ_API_KEY`).  
O **requirements-local.txt** inclui DocTR + OpenCV headless; a barra de progresso avança a cada arquivo processado.

---

## 📋 O que o app faz

- **Upload** de PDFs e imagens (PNG, JPG)
- **OCR** com DocTR (texto por linhas, com espaços)
- **Extração** com LLM: número da NF, data, empresa, CNPJ, valor, moeda, rubrica, nome do comprador
- **Classificação** em rubricas (viagem, congresso, material de consumo, material permanente, serviço de terceiros)
- **Score de revisão** (ok / revisar / verificar)
- **Exportar CSV** e, no PC, gravar direto numa planilha (ex.: pasta do Drive)
- **Evita duplicatas** pelo nome do arquivo
- **Área Revisar** para itens que precisam de checagem

---

## 📁 Documentação

| Arquivo | Conteúdo |
|--------|----------|
| [DEPLOY_NUVEM.md](DEPLOY_NUVEM.md) | Deploy na nuvem (Streamlit Cloud) — funciona com PC desligado |
| [GITHUB_DEPLOY.md](GITHUB_DEPLOY.md) | Passo a passo: GitHub + Streamlit Cloud |
| [RODAR_24-7.md](RODAR_24-7.md) | Rodar 24/7 no PC ou na nuvem |

---

## ⚙️ Configuração rápida

1. **Chave Groq (recomendado):** [console.groq.com/keys](https://console.groq.com/keys) → crie uma chave e coloque no `.env` como `GROQ_API_KEY=gsk_...`
2. **Opcional — Hugging Face:** [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) → token com permissão "Inference Providers" → no `.env`: `HF_TOKEN=hf_...`
3. **Planilha no Drive (só no PC):** em Configurações no app, informe o caminho do CSV (ex.: `G:\Meu Drive\pasta\notas.csv`). Na nuvem deixe em branco e use **Exportar CSV**.

---

## 🖥️ Linha de comando

```bash
# Processar um arquivo
python nf_ocr.py nota.pdf --csv saida.csv

# Processar uma pasta (PDFs e imagens)
python nf_ocr.py "C:\pasta\notas" --csv saida.csv

# Só ver o JSON, sem gravar
python nf_ocr.py nota.pdf --dry-run
```

---

## Colunas exportadas (CSV e XLSX)

### CSV principal (processamento/persistência)

Colunas:

`numero_nf`, `data_emissao`, `nome_comprador`, `cnpj_emitente`, `razao_social_emitente`, `valor_total`, `moeda`, `rubrica`, `discriminacao`, `link_drive`, `score_revisao`, `itens`.

Observação: no CSV persistido pelo `nf_ocr.py`, a segunda linha traz a legenda do `score_revisao`.

### CSV individual (download por arquivo no app)

Quando o parser estruturado da nota encontra itens/valores com qualidade, o CSV individual sai com:

`DATA`, `PRODUTO`, `VALOR`, `TOTAL`.

Se a estrutura detalhada nao for encontrada, o app usa fallback para o CSV resumido (chaves completas do registro).

### CSV da area Revisar

Colunas:

`Empresa`, `CNPJ`, `Data`, `Valor`, `Rubrica`, `Pesquisador`, `Produto`, `Score`, `Arquivo`.

### XLSX (aba `Prestacao_Contas`)

Formato padrao (lote ou fallback):

`Data`, `Pesquisador`, `Empresa`, `CNPJ`, `Descricao`, `Rubrica`, `Produto`, `Valor total`, `Moeda`.

Formato estruturado (normalmente quando ha 1 nota e OCR detalhado):

`DATA`, `PRODUTO`, `VALOR`, `TOTAL`.

---

## Automacao local (README + deploy GitHub)

Sim, da para automatizar localmente (estilo "cron" no Windows) usando PowerShell + Agendador de Tarefas.

1. Crie um script de auto deploy (exemplo em `scripts/auto_deploy.ps1`).
2. Agende no Windows para rodar periodicamente.
3. O script faz: `git pull --rebase` -> `git add -A` -> `git commit` (se houver mudancas) -> `git push`.

Exemplo de agendamento diario as 18h:

```powershell
schtasks /Create /SC DAILY /TN "NotasFiscais-AutoDeploy" /TR "powershell -ExecutionPolicy Bypass -File C:\Users\Operador\Documents\Gabriela\SummerSchool\notas_fiscais\scripts\auto_deploy.ps1" /ST 18:00
```

Para remover a tarefa:

```powershell
schtasks /Delete /TN "NotasFiscais-AutoDeploy" /F
```

---

## Licença

Uso interno / projeto. Ajuste conforme sua necessidade.
