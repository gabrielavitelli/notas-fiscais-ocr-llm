$ErrorActionPreference = "Stop"

$repoPath = "C:\Users\Operador\Documents\Gabriela\SummerSchool\notas_fiscais"
Set-Location $repoPath

Write-Host "== Auto deploy iniciado em $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') =="

# Garante branch atualizada antes de commitar.
git pull --rebase

# Adiciona tudo (ajuste se quiser limitar arquivos).
git add -A

# Se nao houver mudanca, sai sem erro.
$hasChanges = git diff --cached --name-only
if (-not $hasChanges) {
    Write-Host "Sem mudancas para commit."
    exit 0
}

$msg = "chore: auto update $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
git commit -m $msg
git push origin HEAD

Write-Host "Deploy concluido com sucesso."
