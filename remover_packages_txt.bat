@echo off
cd /d "%~dp0"
echo Remove packages.txt do repositorio para o build na nuvem passar...
git pull origin main --rebase 2>nul
git rm packages.txt 2>nul
if errorlevel 1 git rm --cached packages.txt 2>nul
git status
git add -A
git commit -m "Remove packages.txt para build na nuvem (libgl1-mesa-glx nao existe no Debian novo)" 2>nul
if errorlevel 1 echo Nada para commitar ou erro. Confira git status.
git push origin main
echo.
echo Pronto. Aguarde o rebuild no Streamlit Cloud (1-2 min).
pause
