@echo off
chcp 65001 >nul
cd /d "%~dp0.."
if not exist .venv (echo Lancez d'abord 1_installer_et_tester.bat & pause & exit /b 1)
call .venv\Scripts\activate.bat
set PYTHONPATH=src
set PYTHONIOENCODING=utf-8
start "goutte-api" /min cmd /c "uvicorn api.main:app --port 8000"
timeout /t 12 /nobreak >nul
echo Interface sur http://localhost:8501  (fermer cette fenetre pour l'arreter)
start "" http://localhost:8501
streamlit run app\streamlit_app.py --server.port 8501 --server.headless true
taskkill /fi "WINDOWTITLE eq goutte-api*" /t /f >nul 2>nul
