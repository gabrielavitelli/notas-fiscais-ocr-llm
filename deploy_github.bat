@echo off
cd /d "%~dp0"
echo Enviando alteracoes para o GitHub...
git pull origin main --rebase
git add .
git status
git commit -m "Atualiza app e arquivos alterados" 2>nul || echo Nada para commitar.
git push origin main
echo.
echo Pronto. O Streamlit Cloud vai atualizar o app em 1-2 minutos.
pause
