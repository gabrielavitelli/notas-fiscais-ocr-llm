@echo off
cd /d "%~dp0"
echo ========================================
echo   Deploy - Notas Fiscais para GitHub
echo ========================================
echo.

:: Se tiver alteracoes nao commitadas, pull pode falhar
git status
echo.
set PULL_OK=0
git pull origin main --rebase 2>nul && set PULL_OK=1
if %PULL_OK%==0 (
    echo [AVISO] Pull falhou ou ha alteracoes nao commitadas.
    echo Se der "rejected" no push, rode antes: git stash
    echo depois: git pull origin main --rebase
    echo         git push origin main
    echo         git stash pop
    echo.
)

git add .
git status
git commit -m "Atualiza app e arquivos alterados" 2>nul || echo (Nada novo para commitar)
echo.

git push origin main
if errorlevel 1 (
    echo.
    echo *** PUSH FALHOU! O app NAO foi atualizado. ***
    echo.
    echo Confira a mensagem acima. Se pedir "fetch first":
    echo   git stash
    echo   git pull origin main --rebase
    echo   git push origin main
    echo   git stash pop
    echo.
    pause
    exit /b 1
)

echo.
echo Repositorio: 
git remote get-url origin 2>nul
echo.
echo [OK] Push concluido. O Streamlit Cloud deve reconstruir em 2-5 min.
echo      Abra: https://share.streamlit.io (seus apps) para ver o status.
echo.
pause
