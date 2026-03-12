@echo off
cd /d "%~dp0"
echo Enviando alteracoes para o GitHub...
git add .
git status
git commit -m "Atualiza app e arquivos alterados"
git push origin main
echo.
echo Pronto. O Streamlit Cloud vai atualizar o app em 1-2 minutos.
pause
