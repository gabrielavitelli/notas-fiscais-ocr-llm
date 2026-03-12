# Configurar .env pelo terminal (GROQ_API_KEY ou HF_TOKEN)

Siga no **PowerShell** (ou Prompt de Comando), na pasta do projeto.

---

## 1. Entrar na pasta do projeto

```powershell
cd "C:\Users\Operador\Documents\Gabriela\SummerSchool\notas_fiscais"
```

(Ajuste o caminho se a pasta estiver em outro lugar.)

---

## 2. Criar o arquivo .env com a chave Groq

**Troque `gsk_sua_chave_aqui` pela sua chave real** (pegue em https://console.groq.com/keys).

**PowerShell:**

```powershell
echo GROQ_API_KEY=gsk_sua_chave_aqui > .env
```

Se sua chave tiver espaços ou caracteres especiais, use aspas:

```powershell
Set-Content -Path .env -Value "GROQ_API_KEY=gsk_sua_chave_aqui" -Encoding UTF8
```

**Exemplo com chave real (troque pela sua):**

```powershell
echo GROQ_API_KEY=gsk_abc123xyz456... > .env
```

---

## 3. Conferir se o .env foi criado

```powershell
Get-Content .env
```

Deve aparecer uma linha com `GROQ_API_KEY=gsk_...`.

---

## 4. (Opcional) Usar Hugging Face em vez do Groq

Se quiser usar o Hugging Face, adicione no mesmo arquivo:

```powershell
Add-Content -Path .env -Value "HF_TOKEN=hf_seu_token_aqui" -Encoding UTF8
```

(Pegue o token em https://huggingface.co/settings/tokens.)

---

## Resumo rápido (copiar e colar)

1. Abra o PowerShell.
2. Vá na pasta:
   ```powershell
   cd "C:\Users\Operador\Documents\Gabriela\SummerSchool\notas_fiscais"
   ```
3. Crie o .env (**troque pela sua chave Groq**):
   ```powershell
   echo GROQ_API_KEY=gsk_COLE_SUA_CHAVE_AQUI > .env
   ```
4. Rode o app:
   ```powershell
   streamlit run app.py
   ```

Pronto. O app vai ler a chave do `.env` e não vai mais pedir para configurar.
