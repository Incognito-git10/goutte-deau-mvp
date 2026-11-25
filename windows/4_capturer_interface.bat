@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
if not exist .venv (echo Lancez d'abord 1_installer_et_tester.bat & pause & exit /b 1)
call .venv\Scripts\activate.bat
set PYTHONPATH=src
set PYTHONIOENCODING=utf-8
echo Demarrage de l'API et de l'interface en arriere-plan ...
start "goutte-api" /min cmd /c "uvicorn api.main:app --port 8000"
start "goutte-ui" /min cmd /c "streamlit run app\streamlit_app.py --server.port 8501 --server.headless true"
timeout /t 15 /nobreak >nul
set EDGE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe
if not exist "%EDGE%" set EDGE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe
echo Capture de la page (Microsoft Edge sans fenetre) ...
"%EDGE%" --headless=new --disable-gpu --hide-scrollbars --window-size=1280,1650 --virtual-time-budget=20000 --screenshot="%CD%\reports\capture_streamlit.png" "http://localhost:8501/?embed=true"
taskkill /fi "WINDOWTITLE eq goutte-api*" /t /f >nul 2>nul
taskkill /fi "WINDOWTITLE eq goutte-ui*" /t /f >nul 2>nul
if exist reports\capture_streamlit.png (
  echo Capture enregistree : reports\capture_streamlit.png
  start "" reports\capture_streamlit.png
) else (
  echo La capture automatique a echoue. Lancez 3_lancer_interface.bat puis Windows+Maj+S.
)
pause
