# Script para subir o app Notas Fiscais para o GitHub (depois conectar no Streamlit Cloud)
# Uso: edite a linha $repoUrl abaixo com a URL do SEU repositório e execute no PowerShell:
#   cd "C:\Users\Operador\Documents\Gabriela\SummerSchool\notas_fiscais"
#   .\subir_github.ps1

$repoUrl = "https://github.com/gabrielavitelli/notas-fiscais-ocr-llm"   # <-- TROQUE pela URL do seu repo

Write-Host "=== Subindo projeto para o GitHub ===" -ForegroundColor Cyan
Write-Host ""

# Garantir que o Git esteja no PATH (no conda/SummerSchool o Git as vezes nao aparece)
$gitCmd = Get-Command git -ErrorAction SilentlyContinue
if (-not $gitCmd) {
    $gitPaths = @(
        "C:\Program Files\Git\bin",
        "C:\Program Files (x86)\Git\bin"
    )
    foreach ($p in $gitPaths) {
        if (Test-Path (Join-Path $p "git.exe")) {
            $env:Path = "$p;$env:Path"
            break
        }
    }
}
# Verificar de novo apos eventual ajuste do PATH
try {
    $null = & git --version 2>&1
} catch {
    Write-Host "O Git nao foi encontrado." -ForegroundColor Red
    Write-Host "Instale em: https://git-scm.com/download/win" -ForegroundColor Yellow
    exit 1
}

if (-not (Test-Path "app.py")) {
    Write-Host "ERRO: Execute este script DENTRO da pasta notas_fiscais (onde esta o app.py)" -ForegroundColor Red
    exit 1
}

if ($repoUrl -match "SEU_USUARIO") {
    Write-Host "AVISO: Edite o script e troque SEU_USUARIO/notas-fiscais-app pela URL do seu repositorio." -ForegroundColor Yellow
    Write-Host "Exemplo: https://github.com/gabriela/notas-fiscais-app.git" -ForegroundColor Yellow
    exit 1
}

git init 2>$null
git add app.py nf_ocr.py requirements.txt .gitignore README.md DEPLOY_NUVEM.md RODAR_24-7.md .env.example iniciar_app_24-7.bat GITHUB_DEPLOY.md 2>$null
if (Test-Path "pipeline_fluxograma.png") { git add pipeline_fluxograma.png }

Write-Host "Arquivos que serao enviados:" -ForegroundColor Green
git status --short
Write-Host ""

# Git precisa de nome e email para o commit
$gitEmail = git config --global user.email 2>$null
$gitName = git config --global user.name 2>$null
if (-not $gitEmail -or -not $gitName) {
    Write-Host "Configure seu nome e email do Git (uma vez so):" -ForegroundColor Yellow
    Write-Host '  git config --global user.email "gabrielavitelli@gmail.com"' -ForegroundColor White
    Write-Host '  git config --global user.name "gabrielavitelli"' -ForegroundColor White
    Write-Host ""
    if (-not $gitEmail) { git config --global user.email "gabrielavitelli@gmail.com" }
    if (-not $gitName)  { git config --global user.name "gabrielavitelli" }
    Write-Host "Nome e email configurados." -ForegroundColor Green
}

$confirma = Read-Host "Continuar e dar commit? (s/n)"
if ($confirma -ne "s" -and $confirma -ne "S") { exit 0 }

git commit -m "App Notas Fiscais - deploy Streamlit Cloud"
git branch -M main

$rem = git remote get-url origin 2>$null
if ($rem) {
    Write-Host "Remote origin ja existe: $rem" -ForegroundColor Yellow
    $trocar = Read-Host "Quer trocar para $repoUrl ? (s/n)"
    if ($trocar -eq "s" -or $trocar -eq "S") {
        git remote remove origin
        git remote add origin $repoUrl
    }
} else {
    git remote add origin $repoUrl
}

Write-Host ""
Write-Host "Enviando para o GitHub (pode pedir usuario/senha ou token)..." -ForegroundColor Cyan
git push -u origin main

Write-Host ""
Write-Host "Pronto. Agora va em https://share.streamlit.io e conecte este repositorio." -ForegroundColor Green
Write-Host "Main file path: app.py   |   Em Secrets coloque: GROQ_API_KEY = sua_chave" -ForegroundColor Green
