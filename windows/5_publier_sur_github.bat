@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."
where git >nul 2>nul
if errorlevel 1 (
  echo Git est introuvable. Installez Git for Windows depuis git-scm.com puis relancez ce script.
  pause
  exit /b 1
)
echo Avant de continuer : creez sur github.com un depot VIDE nomme goutte-deau-mvp
echo (bouton New repository, Public, sans README ni .gitignore ni licence).
echo.
set /p URL=Collez l'adresse du depot (ex. https://github.com/moncompte/goutte-deau-mvp.git) : 
if "%URL%"=="" (echo Adresse vide, abandon. & pause & exit /b 1)
git remote remove origin >nul 2>nul
git remote add origin %URL%
git branch -M main
echo Envoi du code ; une fenetre de connexion GitHub peut s'ouvrir dans le navigateur.
git push -u origin main
if errorlevel 1 (echo L'envoi a echoue : verifiez l'adresse et la connexion GitHub. & pause & exit /b 1)
echo.
echo Depot en ligne : %URL:.git=%
pause
