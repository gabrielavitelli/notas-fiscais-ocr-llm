# Como deixar o app funcionando 24/7

Duas situações:

- **Quer que funcione mesmo com o PC desligado?** → Use a **nuvem**: guia **[DEPLOY_NUVEM.md](DEPLOY_NUVEM.md)** (Streamlit Community Cloud, grátis).
- **PC fica ligado** e quer rodar aí? → Use o **script no PC** abaixo.

---

## 1. No seu PC (Windows) — PC ligado

Se o computador ficar ligado 24/7, o app pode rodar nele e ser acessado pela rede local (ou por túnel, se quiser acessar de fora).

### 1.1 Rodar e reiniciar se cair

Use o script **`iniciar_app_24-7.bat`** (na pasta do projeto):

- Dá duplo clique ou execute no terminal.
- Mantém o Streamlit rodando; se fechar por erro, **reabre sozinho** após 5 segundos.
- Para parar: feche a janela do terminal ou use Ctrl+C.

**Se você usa conda:** abra o `.bat` no Bloco de notas e, logo após a linha `cd /d "%~dp0"`, adicione (trocando `SummerSchool` pelo nome do seu ambiente):

```bat
call conda activate SummerSchool
```

### 1.2 Abrir ao iniciar o Windows

Para o app subir assim que o Windows ligar:

1. Pressione **Win + R**, digite `shell:startup` e Enter.
2. Na pasta que abrir, crie um **atalho** para o arquivo `iniciar_app_24-7.bat` (botão direito no .bat → Enviar para → Área de trabalho (criar atalho), depois copie o atalho para a pasta do Startup).
3. Ou: **Agendador de Tarefas** (taskschd.msc) → Criar Tarefa Básica → Disparo: “Quando o computador iniciar” → Ação: Iniciar programa → Programa: caminho do `iniciar_app_24-7.bat`.

Assim o app fica rodando 24/7 enquanto o PC estiver ligado.

### 1.3 Acessar de outro dispositivo na mesma rede

No PC onde o app está rodando, o terminal mostra algo como:

```text
Local URL: http://localhost:8501
Network URL: http://192.168.x.x:8501
```

No celular ou em outro PC na **mesma rede Wi‑Fi**, abra no navegador o **Network URL** (ex.: `http://192.168.1.10:8501`).

---

## 2. Na nuvem — PC desligado (grátis)

Para o app funcionar **mesmo com o seu PC desligado**, coloque-o na **Streamlit Community Cloud**. Você acessa por um link na internet (celular, qualquer PC).

**Guia completo:** **[DEPLOY_NUVEM.md](DEPLOY_NUVEM.md)**

Resumo: subir o código no **GitHub**, conectar em [share.streamlit.io](https://share.streamlit.io), configurar as chaves em **Secrets** e fazer o deploy. O app fica com uma URL pública (ex.: `https://seu-app.streamlit.app`). Em Configurações, deixe o caminho da planilha em branco; use **Exportar CSV** para baixar os dados.

---

## 3. VPS ou servidor (Linux)

Se tiver um servidor ou VPS (Oracle Cloud Free Tier, DigitalOcean, etc.):

1. Instalar Python e as dependências no servidor.
2. Copiar o projeto e o `.env` (ou variáveis de ambiente) para o servidor.
3. Rodar com **systemd** ou **screen/tmux** para manter 24/7 e reiniciar se cair.

Exemplo de serviço **systemd** (`/etc/systemd/system/notas-fiscais.service`):

```ini
[Unit]
Description=Notas Fiscais Streamlit
After=network.target

[Service]
User=seu_usuario
WorkingDirectory=/caminho/para/notas_fiscais
ExecStart=/usr/bin/python3 -m streamlit run app.py --server.port 8501 --server.address 0.0.0.0
Restart=always
RestartSec=5
Environment=PATH=/usr/bin

[Install]
WantedBy=multi-user.target
```

Depois:

```bash
sudo systemctl daemon-reload
sudo systemctl enable notas-fiscais
sudo systemctl start notas-fiscais
```

Assim o app fica funcionando 24/7 no servidor.

---

## Resumo

| Onde rodar      | 24/7? | Melhor para                          |
|-----------------|-------|--------------------------------------|
| **Seu PC**      | Sim*  | Planilha no Drive, uso interno       |
| **Streamlit Cloud** | Sim  | Acesso pela internet, sem Drive local |
| **VPS/servidor**| Sim   | Uso profissional, mais controle      |

\* Enquanto o PC estiver ligado e o script (ou tarefa agendada) estiver ativo.

Para o seu caso (planilha no Drive e app no PC), use o **script `iniciar_app_24-7.bat`** e, se quiser, **abrir ao iniciar o Windows** (item 1.2).
