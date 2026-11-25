@echo off
chcp 65001 >nul
cd /d "%~dp0.."
if not exist .venv (echo Lancez d'abord 1_installer_et_tester.bat & pause & exit /b 1)
call .venv\Scripts\activate.bat
set PYTHONPATH=src
set PYTHONIOENCODING=utf-8
start "" http://localhost:8000/docs
echo API sur http://localhost:8000  (fermer cette fenetre pour l'arreter)
uvicorn api.main:app --port 8000
pause
