@echo off
title Notas Fiscais - Rodando 24/7
cd /d "%~dp0"

:loop
echo [%date% %time%] Iniciando o app...
python -m streamlit run app.py --server.port 8501
echo [%date% %time%] App encerrado. Reiniciando em 5 segundos...
timeout /t 5 /nobreak >nul
goto loop
