@echo off
REM Git Setup und Push Script für Automaten Manager (Windows)

echo ========================================
echo   Automaten Manager - Git Setup
echo ========================================
echo.

REM Überprüfe ob git installiert ist
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Git ist nicht installiert!
    echo Bitte installieren Sie Git von: https://git-scm.com/download/win
    pause
    exit /b 1
)

REM Git Status anzeigen
echo Aktueller Git Status:
echo ----------------------
git status --short
echo.

REM Alle Dateien zum Staging hinzufügen
echo Fuege alle Dateien hinzu...
git add -A
echo.

REM Commit erstellen
echo Erstelle Commit...
git commit -m "🚀 Automaten Manager v2.0 - Production Ready" -m "Features:" -m "- Vollständige Geräteverwaltung mit Auto-Generierung" -m "- Warenwirtschaft mit Nachfüllungen" -m "- Finanzmanagement (Einnahmen/Ausgaben)" -m "- Modernes Dashboard mit Sidebar" -m "- Benutzerverwaltung" -m "- Docker Deployment Ready"
echo.

REM Remote hinzufügen
echo ========================================
echo   GitHub Remote Setup
echo ========================================
echo.
echo Moechten Sie zu GitHub pushen? (j/n)
set /p push_github=

if /i "%push_github%"=="j" (
    echo.
    echo Bitte geben Sie Ihre GitHub Repository URL ein:
    echo Format: https://github.com/USERNAME/REPOSITORY.git
    set /p repo_url=Repository URL: 
    
    if not "%repo_url%"=="" (
        REM Prüfe ob origin bereits existiert
        git remote get-url origin >nul 2>&1
        if %errorlevel% equ 0 (
            echo Remote 'origin' existiert bereits. Aktualisiere...
            git remote set-url origin %repo_url%
        ) else (
            echo Fuege Remote 'origin' hinzu...
            git remote add origin %repo_url%
        )
        
        REM Branch zu main umbenennen
        for /f "tokens=*" %%i in ('git rev-parse --abbrev-ref HEAD') do set current_branch=%%i
        if "%current_branch%"=="master" (
            echo Benenne Branch zu 'main' um...
            git branch -M main
        )
        
        REM Push zum Remote Repository
        echo.
        echo Pushe zum Repository...
        git push -u origin main
        
        echo.
        echo ========================================
        echo   ERFOLGREICH zu GitHub gepusht!
        echo   Repository: %repo_url%
        echo ========================================
    )
) else (
    echo.
    echo Lokaler Commit wurde erstellt.
    echo Sie koennen spaeter mit 'git push' zu GitHub pushen.
)

echo.
echo ========================================
echo   Fertig!
echo ========================================
echo.
echo Naechste Schritte:
echo 1. Oeffnen Sie Ihr GitHub Repository
echo 2. Fuegen Sie eine LICENSE Datei hinzu
echo 3. Aktivieren Sie GitHub Actions fuer CI/CD
echo 4. Konfigurieren Sie Secrets fuer Deployment
echo.
pause
