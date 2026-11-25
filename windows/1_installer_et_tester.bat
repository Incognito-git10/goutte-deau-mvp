@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
echo === Goutte d'eau : installation, pipeline complet et tests ===
where python >nul 2>nul
if errorlevel 1 (
  echo Python est introuvable. Installez Python 3.11 ou plus depuis python.org en cochant "Add python.exe to PATH".
  pause
  exit /b 1
)
if not exist .venv (
  echo Creation de l'environnement virtuel .venv ...
  python -m venv .venv || goto :erreur
)
call .venv\Scripts\activate.bat
set PYTHONPATH=src
set PYTHONIOENCODING=utf-8
python -m pip install --upgrade pip >nul
echo Installation des dependances (quelques minutes la premiere fois) ...
pip install -r requirements.txt || goto :erreur
echo Collecte et base SQLite ...
python -m goutte.collecte --csv data\export_infoclimat.csv > reports\collecte.log 2>&1 || goto :erreur
echo Entrainement et evaluation ...
python -m goutte.entrainement > reports\entrainement.log 2>&1 || goto :erreur
python -m goutte.rapport || goto :erreur
echo Tests (unitaires + API) ...
python -m pytest -q > reports\resultats_tests.txt 2>&1
type reports\resultats_tests.txt
echo.
echo Resultats enregistres dans reports\resultats_tests.txt
pause
exit /b 0
:erreur
echo Une etape a echoue : voir les messages ci-dessus et les fichiers reports\*.log
pause
exit /b 1
