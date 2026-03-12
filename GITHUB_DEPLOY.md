# Configurar GitHub e fazer deploy no Streamlit Cloud

Siga na ordem. No final você terá um link do tipo `https://seu-app.streamlit.app`.

---

## Parte 1: Criar o repositório no GitHub

1. **Entrar no GitHub**  
   Acesse [github.com](https://github.com) e faça login (ou crie uma conta grátis).

2. **Novo repositório**  
   - Clique no **+** no canto superior direito → **New repository**.  
   - **Repository name:** por exemplo `notas-fiscais-app`.  
   - **Visibility:** Public.  
   - **Não** marque “Add a README file” (o projeto já tem arquivos).  
   - Clique em **Create repository**.

3. **Copiar a URL do repositório**  
   Na página que abrir, copie a URL. Ela será uma destas:
   - `https://github.com/SEU_USUARIO/notas-fiscais-app.git`
   - `git@github.com:SEU_USUARIO/notas-fiscais-app.git`  
   Guarde essa URL para o passo 6.

**Não precisa de Deploy Key.** O Streamlit Cloud acessa seu repositório pela sua conta do GitHub (quando você faz login em share.streamlit.io). O próximo passo é **enviar o código do seu PC para o GitHub** (Parte 2) e depois **conectar o repositório no Streamlit** (Parte 3).

---

## Parte 2: Subir o código do seu PC para o GitHub

4. **Abrir o terminal na pasta do app**  
   - No Windows: abra o **PowerShell** ou **Prompt de Comando**.  
   - Vá até a pasta onde estão `app.py` e `nf_ocr.py`:
     ```powershell
     cd "C:\Users\Operador\Documents\Gabriela\SummerSchool\notas_fiscais"
     ```
     (Ajuste o caminho se a pasta estiver em outro lugar.)

5. **Verificar se o Git está instalado**  
   Digite:
   ```powershell
   git --version
   ```
   Se aparecer “não reconhecido”, instale: [git-scm.com/download/win](https://git-scm.com/download/win).

6. **Rodar os comandos (troque a URL pela sua)**  
   Execute um por um, **substituindo** `https://github.com/SEU_USUARIO/notas-fiscais-app.git` pela URL que você copiou no passo 3:

   ```powershell
   git init
   git add app.py nf_ocr.py requirements.txt .gitignore README.md DEPLOY_NUVEM.md RODAR_24-7.md .env.example
   git add iniciar_app_24-7.bat GITHUB_DEPLOY.md
   git status
   ```
   O `git status` deve listar os arquivos que serão enviados. **Não** deve aparecer `.env` (ele fica só no seu PC).

   Depois:

   ```powershell
   git commit -m "App Notas Fiscais - deploy Streamlit Cloud"
   git branch -M main
   git remote add origin https://github.com/SEU_USUARIO/notas-fiscais-app.git
   git push -u origin main
   ```

   Se o GitHub pedir **usuário e senha**: use seu usuário do GitHub e, em vez da senha, um **Personal Access Token**. Para criar o token: GitHub → Settings → Developer settings → Personal access tokens → Generate new token (marque pelo menos `repo`).

   Se der erro de “remote origin already exists”:
   ```powershell
   git remote remove origin
   git remote add origin https://github.com/SEU_USUARIO/notas-fiscais-app.git
   git push -u origin main
   ```

7. **Conferir no GitHub**  
   Atualize a página do repositório no navegador. Devem aparecer: `app.py`, `nf_ocr.py`, `requirements.txt`, `README.md`, etc.

---

## Parte 3: Conectar no Streamlit Community Cloud e fazer o deploy

8. **Acessar o Streamlit Cloud**  
   Vá em [share.streamlit.io](https://share.streamlit.io) e faça login com **GitHub** (autorize se pedir).

9. **Criar um novo app**  
   - Clique em **New app**.  
   - **Repository:** `SEU_USUARIO/notas-fiscais-app` (ou o nome que você deu).  
   - **Branch:** `main`.  
   - **Main file path:** `app.py`.  
   - Clique em **Deploy!**.

10. **Configurar as chaves (Secrets)**  
    - Quando o deploy abrir (pode levar 1–2 minutos), clique na **engrenagem** (Settings) → **Secrets**.  
    - No quadro de texto, cole (com sua chave Groq de verdade):

    ```toml
    GROQ_API_KEY = "gsk_sua_chave_aqui"
    ```

    - Clique em **Save**. O app será reimplantado sozinho.

11. **Abrir o app**  
    No topo da página aparece o link, por exemplo:  
    `https://notas-fiscais-app-xxxxx.streamlit.app`  
    Abra esse link: o app deve carregar. Em **Configurações**, deixe o caminho da planilha em branco; use **Exportar CSV** para baixar os dados.

---

## Resumo rápido

| Passo | O que fazer |
|-------|-------------|
| 1–3   | GitHub: criar repositório e copiar URL |
| 4–6   | No PC: `cd` na pasta do app, `git init`, `git add`, `git commit`, `git remote add origin URL`, `git push -u origin main` |
| 7     | Conferir arquivos no GitHub |
| 8–9   | share.streamlit.io → New app → escolher repo e `app.py` → Deploy |
| 10–11 | Settings → Secrets → colocar `GROQ_API_KEY` → abrir o link do app |

**Deploy Key?** Não é necessário. O Streamlit Cloud usa o acesso que você dá ao fazer login com GitHub; ele só lê o repositório.

Se em algum passo aparecer uma mensagem de erro, copie a mensagem e o comando que você usou para poder corrigir.
