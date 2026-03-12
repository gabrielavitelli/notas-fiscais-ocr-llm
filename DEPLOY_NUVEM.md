# App na nuvem — funciona com o PC desligado

Para o **Notas Fiscais** ficar acessível 24/7 pela internet, mesmo com o seu computador desligado, use o **Streamlit Community Cloud** (grátis).

---

## O que muda na nuvem

| No seu PC | Na nuvem |
|-----------|----------|
| Planilha em pasta do Drive (ex.: `G:\Meu Drive\...`) | Não existe esse disco; **deixe o campo em branco** em Configurações |
| Chaves no arquivo `.env` | Chaves em **Secrets** no painel do Streamlit |
| Dados e estado no seu disco | Estado e CSV só na sessão; **exporte o CSV** quando precisar guardar |

Na nuvem você continua: enviando arquivos, processando e **exportando CSV** pelo botão. Quem precisar da planilha no Drive pode baixar o CSV no app e depois importar no Drive/Sheets.

---

## Passo a passo (Streamlit Community Cloud)

### 1. Conta no GitHub

- Se ainda não tiver: crie em [github.com](https://github.com/join).
- Crie um **repositório** (pode ser privado). Ex.: `meu-notas-fiscais`.

### 2. Subir o projeto no GitHub

**Guia detalhado com comandos:** [GITHUB_DEPLOY.md](GITHUB_DEPLOY.md)

Na pasta do projeto (onde estão `app.py`, `nf_ocr.py`, etc.):

**Opção A — Pasta já é um repositório Git:**

```bash
cd caminho/para/notas_fiscais
git add app.py nf_ocr.py requirements.txt pipeline_fluxograma.png
git add DEPLOY_NUVEM.md RODAR_24-7.md
git commit -m "Deploy na nuvem"
git remote add origin https://github.com/SEU_USUARIO/meu-notas-fiscais.git
git push -u origin main
```

**Opção B — Ainda não é um repositório:**

```bash
cd caminho/para/notas_fiscais
git init
git add app.py nf_ocr.py requirements.txt pipeline_fluxograma.png
git add DEPLOY_NUVEM.md RODAR_24-7.md
git commit -m "Deploy na nuvem"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/meu-notas-fiscais.git
git push -u origin main
```

**Importante:** não faça `git add .env` — o `.env` não deve ir para o GitHub (contém chaves). O arquivo `.gitignore` já deve conter `.env`.

### 3. Conta no Streamlit Community Cloud

- Acesse [share.streamlit.io](https://share.streamlit.io).
- Faça login com a **conta do GitHub**.

### 4. Novo app

- Clique em **“New app”**.
- **Repository:** escolha `SEU_USUARIO/meu-notas-fiscais`.
- **Branch:** `main`.
- **Main file path:** `app.py` (ou o caminho relativo ao repositório, ex.: `notas_fiscais/app.py` se o app estiver numa subpasta).
- Clique em **“Deploy!”**.

### 5. Configurar Secrets (chaves de API)

- No painel do app no Streamlit Cloud, abra **“Settings”** (engrenagem) → **“Secrets”**.
- Cole no editor (substitua pela sua chave real):

```toml
GROQ_API_KEY = "gsk_sua_chave_aqui"
```

Se usar Hugging Face:

```toml
GROQ_API_KEY = "gsk_sua_chave_aqui"
HF_TOKEN = "hf_seu_token_aqui"
```

- Salve. O app será reimplantado e passará a usar essas chaves; **não** use `.env` na nuvem.

### 6. Usar o app

- A URL será algo como: `https://seu-app.streamlit.app`.
- Abra no celular ou em qualquer PC; funciona com o **seu PC desligado**.
- Em **Configurações**, deixe o **“Caminho do arquivo CSV”** em branco (planilha no Drive não existe na nuvem).
- Use **Exportar CSV** para baixar os dados quando precisar.

---

## Requisitos no repositório

O Streamlit Cloud precisa encontrar:

- `app.py` (ou o caminho que você escolheu como “Main file path”).
- `requirements.txt` na **raiz do repositório** (ou na mesma pasta do `app.py`).

Se o projeto no GitHub estiver assim:

```text
meu-notas-fiscais/
  app.py
  nf_ocr.py
  requirements.txt
  pipeline_fluxograma.png
```

em “Main file path” use: **`app.py`**.

Se estiver em subpasta:

```text
SummerSchool/
  notas_fiscais/
    app.py
    nf_ocr.py
    requirements.txt
```

em “Main file path” use: **`notas_fiscais/app.py`** e coloque o `requirements.txt` em `notas_fiscais/` ou na raiz (o Cloud procura na raiz e na pasta do app).

---

## Resumo

1. Subir código no **GitHub** (sem `.env`).
2. Conectar o repositório no **Streamlit Community Cloud** e fazer deploy de `app.py`.
3. Configurar **Secrets** com `GROQ_API_KEY` (e `HF_TOKEN` se usar).
4. Usar o link do app (ex.: `https://seu-app.streamlit.app`) em qualquer lugar — **funciona com o PC desligado**. Para ter “planilha” na nuvem, use só o app e **exporte CSV** quando precisar guardar.
