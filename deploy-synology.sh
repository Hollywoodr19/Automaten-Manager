#!/bin/bash
# Deployment Script für Synology NAS

echo "🚀 Automaten Manager - Synology Deployment"
echo "==========================================="

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Funktion für farbige Ausgabe
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# 1. Prüfe Docker
echo "Checking Docker installation..."
if command -v docker &> /dev/null; then
    print_status "Docker is installed"
    docker --version
else
    print_error "Docker is not installed!"
    exit 1
fi

if command -v docker-compose &> /dev/null; then
    print_status "Docker Compose is installed"
    docker-compose --version
else
    print_error "Docker Compose is not installed!"
    exit 1
fi

# 2. Erstelle Backup-Verzeichnisse
echo ""
echo "Creating backup directories..."
mkdir -p backups/postgres
mkdir -p backups/app
print_status "Backup directories created"

# 3. Generiere Secret Key wenn nicht vorhanden
if [ ! -f .env.production ]; then
    echo ""
    echo "Generating production environment file..."
    SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))' 2>/dev/null || echo "please-change-this-secret-key-$(date +%s)")
    DB_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_urlsafe(16))' 2>/dev/null || echo "ChangeMe$(date +%s)")
    
    cat > .env.production <<EOF
# Auto-generated production environment
DB_PASSWORD=${DB_PASSWORD}
SECRET_KEY=${SECRET_KEY}
FLASK_ENV=production
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_EMAIL=admin@localhost
EOF
    print_status "Environment file created (PLEASE CHANGE DEFAULT PASSWORDS!)"
    print_warning "Default admin credentials: admin/admin123"
else
    print_status "Using existing .env.production file"
fi

# 4. Build Docker Images
echo ""
echo "Building Docker images..."
docker-compose -f docker-compose.production.yml build
if [ $? -eq 0 ]; then
    print_status "Docker images built successfully"
else
    print_error "Failed to build Docker images"
    exit 1
fi

# 5. Start Services
echo ""
echo "Starting services..."
docker-compose -f docker-compose.production.yml up -d
if [ $? -eq 0 ]; then
    print_status "Services started successfully"
else
    print_error "Failed to start services"
    exit 1
fi

# 6. Warte auf Datenbank
echo ""
echo "Waiting for database to be ready..."
sleep 10

# 7. Zeige Status
echo ""
echo "Checking service status..."
docker-compose -f docker-compose.production.yml ps

# 8. Zeige Zugriffs-URLs
echo ""
echo "==========================================="
print_status "Deployment completed successfully!"
echo ""
echo "Access URLs:"
echo "  Web Interface: http://YOUR-NAS-IP:5000"
echo "  With Nginx:    http://YOUR-NAS-IP"
echo ""
echo "Default Credentials:"
echo "  Username: admin"
echo "  Password: admin123"
echo ""
print_warning "IMPORTANT: Change default passwords immediately!"
echo ""
echo "Useful commands:"
echo "  View logs:    docker-compose -f docker-compose.production.yml logs -f"
echo "  Stop:         docker-compose -f docker-compose.production.yml down"
echo "  Restart:      docker-compose -f docker-compose.production.yml restart"
echo "  Backup DB:    docker exec automaten_postgres pg_dump -U postgres automaten > backup.sql"
echo "==========================================="
