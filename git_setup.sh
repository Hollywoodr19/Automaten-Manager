#!/bin/bash
# Git Setup und Push Script für Automaten Manager

echo "🚀 Automaten Manager - Git Setup"
echo "================================="

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Überprüfe ob git installiert ist
if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ Git ist nicht installiert!${NC}"
    exit 1
fi

# Git Status anzeigen
echo -e "\n${YELLOW}📊 Aktueller Git Status:${NC}"
git status --short

# Alle Dateien zum Staging hinzufügen
echo -e "\n${YELLOW}➕ Füge alle Dateien hinzu...${NC}"
git add -A

# Commit erstellen
echo -e "\n${YELLOW}📝 Erstelle Commit...${NC}"
git commit -m "🚀 Automaten Manager v2.0 - Production Ready

Features:
- Vollständige Geräteverwaltung mit Auto-Generierung
- Warenwirtschaft mit Nachfüllungen
- Finanzmanagement (Einnahmen/Ausgaben)
- Modernes Dashboard mit Sidebar
- Benutzerverwaltung
- Lieferanten & Produkt-Management
- Docker Deployment Ready"

# Remote hinzufügen (falls noch nicht vorhanden)
echo -e "\n${YELLOW}🔗 GitHub Remote Setup:${NC}"
echo "Bitte geben Sie Ihre GitHub Repository URL ein:"
echo "Format: https://github.com/USERNAME/REPOSITORY.git"
read -p "Repository URL: " REPO_URL

if [ ! -z "$REPO_URL" ]; then
    # Prüfe ob origin bereits existiert
    if git remote get-url origin &> /dev/null; then
        echo -e "${YELLOW}Remote 'origin' existiert bereits. Aktualisiere...${NC}"
        git remote set-url origin "$REPO_URL"
    else
        echo -e "${GREEN}Füge Remote 'origin' hinzu...${NC}"
        git remote add origin "$REPO_URL"
    fi
    
    # Branch umbenennen zu main (falls noch master)
    CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
    if [ "$CURRENT_BRANCH" = "master" ]; then
        echo -e "${YELLOW}Benenne Branch zu 'main' um...${NC}"
        git branch -M main
    fi
    
    # Push zum Remote Repository
    echo -e "\n${YELLOW}📤 Pushe zum Repository...${NC}"
    git push -u origin main
    
    echo -e "\n${GREEN}✅ Erfolgreich zu GitHub gepusht!${NC}"
    echo -e "${GREEN}Repository: $REPO_URL${NC}"
else
    echo -e "${YELLOW}⚠️  Kein Remote Repository angegeben. Lokaler Commit wurde erstellt.${NC}"
fi

echo -e "\n${GREEN}✨ Fertig!${NC}"
echo "Nächste Schritte:"
echo "1. Öffnen Sie Ihr GitHub Repository"
echo "2. Fügen Sie eine LICENSE Datei hinzu"
echo "3. Konfigurieren Sie GitHub Actions für CI/CD"
echo "4. Aktivieren Sie GitHub Pages für Dokumentation"
