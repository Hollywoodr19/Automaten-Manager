# Automaten Manager - Projektstruktur und Status
**Letzte Aktualisierung:** 2025-01-17
**Claude Session:** Dashboard Modernisierung

## 🎯 Projekt-Übersicht
- **Zweck:** Verwaltungssystem für Automaten (Snacks, Getränke, etc.)
- **Tech-Stack:** Python Flask, SQLAlchemy, Docker, PostgreSQL
- **Status:** Dashboard-Modernisierung im Gange

## 📁 Hauptstruktur
```
H:\Projekt\Automaten\
├── app/                    # Hauptanwendung
│   ├── __init__.py        # Flask App Initialisierung
│   ├── models.py          # Datenbank-Modelle
│   ├── web/               # Web-Module
│   │   ├── __init__.py
│   │   ├── dashboard.py   # Altes Dashboard
│   │   ├── dashboard_modern.py  # NEUES modernes Dashboard
│   │   ├── auth.py        # Authentifizierung
│   │   ├── devices.py     # Geräte-Verwaltung
│   │   ├── entries.py     # Einnahmen/Ausgaben
│   │   ├── income.py      # Einnahmen-Modul
│   │   ├── expenses.py    # Ausgaben-Modul
│   │   ├── refills.py     # Nachfüllungen
│   │   ├── products.py    # Produkt-Verwaltung
│   │   ├── suppliers.py   # Lieferanten
│   │   ├── users.py       # Benutzer-Verwaltung
│   │   └── reports.py     # Berichte
│   └── templates/         # HTML Templates
│       ├── dashboard_old.html
│       └── [andere templates]
├── docker-compose.yml     # Docker Konfiguration
├── Dockerfile
└── requirements.txt

## 🔧 Aktuelle Arbeiten (Session vom 2025-01-17)

### ✅ Was wurde erfolgreich gemacht:
1. **Modernes Dashboard komplett implementiert** (`dashboard_modern.py`)
   - Glassmorphism Design mit Gradient-Background
   - Kontextbasierte Sidebar-Navigation
   - Hover-Effekte und moderne UI
   - Alle Module-Routen funktionieren

2. **Navigation-System fertiggestellt:**
   - Im Dashboard: Sidebar zeigt ALLE Module
   - In Modulen: Sidebar zeigt nur Dashboard-Link + modul-spezifische Unterpunkte
   - Breadcrumb-Navigation überall implementiert

3. **Module an modernes Design angepasst:**
   - ✅ Dashboard-Module (devices, inventory, income, expenses, reports, settings)
   - ✅ Devices-Modul
   - ✅ Users-Modul  
   - ✅ Entries-Modul
   - ✅ Expenses-Modul
   - ✅ Refills-Modul
   - ✅ Products-Modul
   - ✅ Suppliers-Modul

4. **Routen-System:**
   - `/` und `/dashboard` → führen zum modernen Dashboard
   - Altes Dashboard unter `/dashboard_old` verfügbar
   - Alle Sub-Module haben funktionierende Routen

### 🔄 In Bearbeitung:
1. **Weitere Module-Anpassungen:**
   - Reports-Modul Details
   - Income-Modul Details
   - Weitere Sub-Module

## 🗄️ Datenbank-Modelle (models.py)

### Wichtige Models:
- **User**: Benutzer-Verwaltung
- **Device**: Automaten (mit DeviceStatus Enum)
- **Entry**: Einnahmen/Ausgaben (type='income'/'expense')
- **Product**: Produkte (möglicherweise ohne current_stock, min_stock)
- **Refill**: Nachfüllungen
- **Supplier**: Lieferanten

### DeviceStatus Enum:
```python
class DeviceStatus(Enum):
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    INACTIVE = "inactive"
```

## 🎨 Design-System (Modernes Dashboard)

### Farben:
- Background: Linear Gradient (Purple-Blue)
- Cards: Weiß mit Schatten
- Erfolg/Einnahmen: Grün (#10b981)
- Fehler/Ausgaben: Rot (#ef4444)
- Sidebar: Glassmorphism-Effekt

### Komponenten:
- Stat-Cards mit Icons
- Hover-Sidebar (250px → 280px on hover)
- Moderne Tabellen mit Badges
- Quick Action Buttons

## 📝 Nächste Schritte:
1. Model-Referenzen korrigieren
2. Fehlende Templates erstellen
3. Sub-Module implementieren
4. Tests durchführen

## 🔗 Wichtige URLs:
- Hauptzugriff: http://127.0.0.1:5000/
- Modernes Dashboard: http://127.0.0.1:5000/modern/dashboard
- Altes Dashboard: http://127.0.0.1:5000/dashboard_old

## 🐛 Debug-Commands:
```bash
# Docker neu starten
docker-compose restart automaten_app

# Logs anzeigen
docker-compose logs -f automaten_app

# In Container einloggen
docker exec -it automaten_app bash
```

## 📌 Notizen für nächste Session:
- Dashboard funktioniert grundlegend
- Navigation-Konzept implementiert
- Model-Kompatibilität muss noch überprüft werden
- Sub-Module müssen noch ausgebaut werden
