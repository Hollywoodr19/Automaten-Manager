# 🚀 Automaten Manager - Synology DS916+ Deployment Guide

## Voraussetzungen

- Synology DS916+ mit DSM 6.0 oder höher
- Docker Package installiert (über Package Center)
- SSH-Zugang zum NAS aktiviert

## Installation Schritt für Schritt

### 1. Projekt auf NAS übertragen

#### Option A: Über File Station (Einfach)
1. Öffnen Sie File Station auf Ihrem NAS
2. Erstellen Sie einen neuen Ordner: `/docker/automaten-manager`
3. Laden Sie alle Projektdateien in diesen Ordner hoch

#### Option B: Über Git (Empfohlen)
```bash
# SSH Verbindung zum NAS
ssh admin@YOUR-NAS-IP

# Zum Docker Verzeichnis wechseln
cd /volume1/docker

# Projekt klonen (falls Git installiert)
git clone https://github.com/yourusername/automaten-manager.git

# Oder: Dateien manuell kopieren
```

### 2. Container Station / Docker verwenden

#### Über Container Station GUI:
1. Öffnen Sie **Container Station** auf Ihrem NAS
2. Gehen Sie zu **Anwendungen** → **Erstellen**
3. Wählen Sie **Docker Compose Anwendung erstellen**
4. Name: `automaten-manager`
5. Pfad: Navigieren Sie zu `/docker/automaten-manager/docker-compose.production.yml`
6. Klicken Sie auf **Erstellen**

#### Über SSH/Terminal:
```bash
# SSH zum NAS
ssh admin@YOUR-NAS-IP

# Zum Projektverzeichnis
cd /volume1/docker/automaten-manager

# Environment-Datei anpassen
cp .env.production.example .env.production
nano .env.production  # Passwörter ändern!

# Container starten
docker-compose -f docker-compose.production.yml up -d

# Logs prüfen
docker-compose -f docker-compose.production.yml logs -f
```

### 3. Wichtige Konfigurationen

#### Passwörter ändern (.env.production):
```env
# WICHTIG: Diese Werte ändern!
DB_PASSWORD=IhrSicheresPasswort123!
SECRET_KEY=generieren-mit-python-secrets-modul
ADMIN_PASSWORD=NeuesAdminPasswort123!
```

#### Ports anpassen (falls nötig):
- Standard Web-Port: **5000**
- PostgreSQL: **5432** (nur intern)
- Redis: **6379** (nur intern)
- Nginx: **80/443** (optional)

### 4. Firewall & Port-Weiterleitung

#### Synology Firewall:
1. Öffnen Sie **Systemsteuerung** → **Sicherheit** → **Firewall**
2. Erstellen Sie neue Regel:
   - Port: 5000 (oder 80 wenn Nginx)
   - Protokoll: TCP
   - Aktion: Zulassen

#### Router Port-Weiterleitung (für externen Zugriff):
- Externes Port: 5000 → Internes Port: 5000
- NAS IP: 192.168.1.XXX (Ihre NAS IP)

### 5. Reverse Proxy Setup (Empfohlen)

#### Synology Reverse Proxy:
1. **Systemsteuerung** → **Anwendungsportal** → **Reverse Proxy**
2. **Erstellen**:
   - Beschreibung: Automaten Manager
   - Quelle:
     - Protokoll: HTTPS
     - Hostname: automaten.ihre-domain.de
     - Port: 443
   - Ziel:
     - Protokoll: HTTP
     - Hostname: localhost
     - Port: 5000

### 6. SSL/HTTPS aktivieren

#### Let's Encrypt auf Synology:
1. **Systemsteuerung** → **Sicherheit** → **Zertifikat**
2. **Hinzufügen** → **Let's Encrypt Zertifikat**
3. Domain eingeben
4. Zertifikat für Reverse Proxy verwenden

### 7. Backup einrichten

#### Automatisches Backup:
Erstellen Sie eine geplante Aufgabe:

```bash
#!/bin/bash
# backup-automaten.sh

BACKUP_DIR="/volume1/backups/automaten-manager"
DATE=$(date +%Y%m%d_%H%M%S)

# Datenbank Backup
docker exec automaten_postgres pg_dump -U postgres automaten > \
    ${BACKUP_DIR}/db_backup_${DATE}.sql

# App-Daten Backup
docker run --rm -v automaten-manager_app_uploads:/data -v ${BACKUP_DIR}:/backup \
    alpine tar czf /backup/uploads_${DATE}.tar.gz -C /data .

# Alte Backups löschen (älter als 30 Tage)
find ${BACKUP_DIR} -name "*.sql" -mtime +30 -delete
find ${BACKUP_DIR} -name "*.tar.gz" -mtime +30 -delete
```

**Aufgabenplaner:**
1. **Systemsteuerung** → **Aufgabenplaner**
2. **Erstellen** → **Geplante Aufgabe** → **Benutzerdefiniertes Skript**
3. Schedule: Täglich um 2:00 Uhr
4. Skript: Pfad zum Backup-Skript

### 8. Performance-Optimierung

#### Docker Ressourcen (Container Station):
- CPU-Limit: 2 Cores
- RAM-Limit: 2 GB
- Swap: 1 GB

#### PostgreSQL Tuning:
```sql
-- In docker-compose.production.yml unter postgres:
command: 
  - "postgres"
  - "-c"
  - "shared_buffers=256MB"
  - "-c"
  - "max_connections=100"
  - "-c"
  - "effective_cache_size=1GB"
```

### 9. Monitoring

#### Synology Resource Monitor:
- **Ressourcen-Monitor** → **Docker** Tab
- Überwachen Sie CPU, RAM und Netzwerk

#### Docker Stats:
```bash
docker stats --no-stream
```

#### Health Check:
```bash
curl http://localhost:5000/api/health
```

## 🔧 Troubleshooting

### Container startet nicht:
```bash
# Logs prüfen
docker logs automaten_app
docker logs automaten_postgres

# Container neu starten
docker-compose -f docker-compose.production.yml restart
```

### Datenbank-Verbindung fehlgeschlagen:
```bash
# Postgres Status prüfen
docker exec automaten_postgres pg_isready

# Datenbank manuell erstellen
docker exec -it automaten_postgres psql -U postgres
CREATE DATABASE automaten;
```

### Port bereits belegt:
```bash
# Prüfe welche Ports verwendet werden
sudo netstat -tlnp | grep :5000

# Ändere Port in docker-compose.production.yml
ports:
  - "5001:5000"  # Externer Port 5001
```

### Speicherplatz voll:
```bash
# Docker aufräumen
docker system prune -a
docker volume prune
```

## 📊 Empfohlene Systemanforderungen

### Minimum:
- 2 GB RAM für Docker
- 10 GB freier Speicherplatz
- DSM 6.2 oder höher

### Empfohlen:
- 4 GB RAM für Docker
- 20 GB freier Speicherplatz
- SSD Cache aktiviert
- DSM 7.0 oder höher

## 🔐 Sicherheits-Checkliste

- [ ] Alle Standard-Passwörter geändert
- [ ] Firewall-Regeln konfiguriert
- [ ] SSL/HTTPS aktiviert
- [ ] Regelmäßige Backups eingerichtet
- [ ] 2FA für Admin-Zugang aktiviert
- [ ] Fail2ban konfiguriert (optional)
- [ ] Docker-Updates automatisiert

## 📱 Zugriff

### Lokal:
```
http://192.168.1.XXX:5000
```

### Extern (mit DynDNS):
```
https://automaten.ihre-domain.de
```

### Mobile App:
PWA kann auf Smartphone installiert werden:
1. Öffnen Sie die URL im Browser
2. "Zum Startbildschirm hinzufügen"

## 🆘 Support

Bei Problemen:
1. Prüfen Sie die Logs: `docker-compose logs -f`
2. Konsultieren Sie die [Hauptdokumentation](README.md)
3. Erstellen Sie ein Issue auf GitHub

## 📝 Nützliche Befehle

```bash
# Status prüfen
docker-compose -f docker-compose.production.yml ps

# Logs anzeigen
docker-compose -f docker-compose.production.yml logs -f app

# Container neustarten
docker-compose -f docker-compose.production.yml restart

# Datenbank-Backup
docker exec automaten_postgres pg_dump -U postgres automaten > backup_$(date +%Y%m%d).sql

# Datenbank wiederherstellen
docker exec -i automaten_postgres psql -U postgres automaten < backup.sql

# In Container einloggen
docker exec -it automaten_app /bin/sh

# Update durchführen
git pull
docker-compose -f docker-compose.production.yml build
docker-compose -f docker-compose.production.yml up -d
```

---

**Viel Erfolg mit Ihrer Installation! 🎉**
