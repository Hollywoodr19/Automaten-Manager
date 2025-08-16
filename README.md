# 🎰 Automaten Manager v2.0

Ein professionelles Verwaltungssystem für Verkaufsautomaten mit vollständiger Warenwirtschaft, Finanzverwaltung und modernem Dashboard.

## 🚀 Features

### Kernfunktionen
- **Geräteverwaltung**: Vollständige Verwaltung von Verkaufsautomaten
- **Finanzverwaltung**: Einnahmen und Ausgaben tracking
- **Warenwirtschaft**: Nachfüllungen, Inventar und Lagerbestände
- **Modernes Dashboard**: Übersichtliche Statistiken mit Sidebar-Navigation
- **Benutzerverwaltung**: Multi-User System mit Admin-Funktionen

### Technische Features
- Automatische Namens- und Seriennummer-Generierung
- Inventar- und Wechselgeld-Management pro Gerät
- Lieferanten-Verwaltung
- Produkt-Katalog mit Kategorien
- Rabatt-System für Nachfüllungen
- Kassenbon-Upload Funktion

## 🛠️ Tech Stack

- **Backend**: Python 3.11, Flask
- **Datenbank**: PostgreSQL
- **Frontend**: Bootstrap 5, jQuery
- **Container**: Docker & Docker Compose
- **Authentication**: Flask-Login

## 📦 Installation

### Voraussetzungen
- Docker und Docker Compose
- Git

### Setup

1. **Repository klonen**
```bash
git clone https://github.com/[username]/automaten-manager.git
cd automaten-manager
```

2. **Environment-Datei erstellen**
```bash
cp .env.example .env
# .env anpassen mit eigenen Werten
```

3. **Docker Container starten**
```bash
docker-compose up -d --build
```

4. **Datenbank initialisieren**
Die Datenbank wird automatisch beim ersten Start initialisiert.

### Standard-Login
- **Username**: admin
- **Password**: admin123

⚠️ **Wichtig**: Ändern Sie das Admin-Passwort nach dem ersten Login!

## 🏗️ Projektstruktur

```
automaten-manager/
├── app/
│   ├── __init__.py           # Flask App Factory
│   ├── models/
│   │   ├── __init__.py        # Hauptmodels
│   │   └── inventory.py       # Warenwirtschafts-Models
│   └── web/
│       ├── __init__.py        # Hauptroutes & Dashboard
│       ├── navigation.py      # Zentrale Navigation
│       ├── devices.py         # Geräteverwaltung
│       ├── entries.py         # Einnahmen
│       ├── expenses.py        # Ausgaben
│       ├── refills.py         # Nachfüllungen
│       ├── products.py        # Produkte
│       ├── suppliers.py       # Lieferanten
│       ├── users.py           # Benutzerverwaltung
│       └── dashboard_modern.py # Modernes Dashboard
├── templates/
│   └── auth/
│       └── login.html         # Login-Template
├── docker-compose.yml         # Docker Konfiguration
├── Dockerfile                 # Container Build
├── requirements.txt           # Python Dependencies
└── run.py                     # Startskript
```

## 🎯 Verwendung

### Dashboard
Nach dem Login landen Sie auf dem modernen Dashboard mit:
- Einnahmen/Ausgaben Übersicht
- Gewinn/Verlust Berechnung
- Aktive Geräte Status
- Letzte Transaktionen

### Geräteverwaltung
- Automatische Namens- und Seriennummer-Generierung
- Inventar pro Gerät verwalten
- Wechselgeld-Bestand pflegen
- Status-Tracking (Aktiv, Wartung, Inaktiv)

### Warenwirtschaft
- Nachfüllungen mit mehreren Produkten erfassen
- Automatische Lagerbestands-Aktualisierung
- Lieferanten-Verwaltung
- Rabatt-System mit Zeilen-Rabatten

### Finanzübersicht
- Einnahmen pro Gerät erfassen
- Ausgaben kategorisiert verwalten
- Automatische Gewinn/Verlust Berechnung
- Export-Funktionen (in Entwicklung)

## 🔧 Entwicklung

### Lokale Entwicklung
```bash
# Virtual Environment erstellen
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# oder
.venv\Scripts\activate  # Windows

# Dependencies installieren
pip install -r requirements.txt

# Flask App starten
python run.py
```

### Datenbank-Migrationen
```bash
# In den Container verbinden
docker exec -it automaten_app bash

# Python Shell öffnen
python

# Neue Spalten hinzufügen (Beispiel)
from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    with db.engine.begin() as conn:
        conn.execute(text('ALTER TABLE devices ADD COLUMN new_field VARCHAR(100)'))
```

## 📊 API Endpoints

- `/api/stats` - Statistiken abrufen
- `/api/test` - System-Status prüfen
- `/api/routes` - Alle verfügbaren Routes anzeigen
- `/devices/api/<id>` - Gerätedaten als JSON

## 🐛 Bekannte Probleme & Lösungen

### Problem: "connection_type is an invalid keyword argument"
**Lösung**: Felder zum Model hinzufügen oder Datenbank-Migration durchführen

### Problem: "duplicate key value violates unique constraint"
**Lösung**: Automatische Rechnungsnummer-Generierung ist aktiviert

## 🤝 Contributing

Contributions sind willkommen! Bitte erstellen Sie einen Pull Request mit einer klaren Beschreibung der Änderungen.

## 📄 Lizenz

[MIT License](LICENSE)

## 👥 Autor

Entwickelt mit ❤️ für die effiziente Verwaltung von Verkaufsautomaten.

## 🔮 Geplante Features

- [ ] Erweiterte Reporting-Funktionen
- [ ] Mobile App
- [ ] QR-Code Integration
- [ ] Telemetrie-Anbindung
- [ ] Multi-Mandanten-Fähigkeit
- [ ] Export zu Buchhaltungssystemen
- [ ] Predictive Maintenance
- [ ] Route-Optimierung für Nachfüllungen

---

**Version**: 2.0.0  
**Status**: Production Ready  
**Letztes Update**: August 2025
