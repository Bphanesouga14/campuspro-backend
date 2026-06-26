@echo off
:: ============================================================
::  installer_windows.bat
::  Script d'installation pour Windows
::  Double-cliquer OU exécuter dans PowerShell/CMD
:: ============================================================

echo.
echo  LGS - Installation des dependances (Windows)
echo ================================================
echo.

:: Vérifier que Python est installé
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERREUR] Python n'est pas installe ou pas dans le PATH.
    echo Telechargez Python 3.11+ sur https://www.python.org/downloads/
    echo Cochez "Add Python to PATH" lors de l'installation.
    pause
    exit /b 1
)

echo [1/4] Mise a jour de pip...
python -m pip install --upgrade pip

echo.
echo [2/4] Installation des dependances...
:: --only-binary=:all: force l'utilisation de wheels pre-compilees
:: (evite de compiler du C, ce qui necessite Visual Studio)
pip install --only-binary=:all: -r requirements.txt

IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERREUR] L'installation a echoue.
    echo Essayez la commande manuelle dans ce dossier :
    echo   pip install --only-binary=:all: -r requirements.txt
    pause
    exit /b 1
)

echo.
echo [3/4] Verification de l'installation...
python -c "import fastapi, sqlalchemy, asyncpg, pydantic, bcrypt, jwt; print('OK')"

IF %ERRORLEVEL% NEQ 0 (
    echo [ERREUR] Certains modules ne s'importent pas correctement.
    pause
    exit /b 1
)

echo.
echo [4/4] Creation du fichier .env si absent...
IF NOT EXIST .env (
    copy .env.example .env
    echo Fichier .env cree depuis .env.example
    echo IMPORTANT : Editez .env et renseignez vos identifiants Supabase et JWT_SECRET_KEY
) ELSE (
    echo Fichier .env deja present, pas de modification.
)

echo.
echo ================================================
echo  Installation terminee avec succes !
echo ================================================
echo.
echo Etapes suivantes :
echo   1. Editez le fichier .env avec vos identifiants Supabase
echo   2. Creez le compte admin :   python creer_admin.py
echo   3. Demarrez le serveur  :   uvicorn main:app --reload
echo   4. Ouvrez                :   http://localhost:8000/docs
echo.
pause
