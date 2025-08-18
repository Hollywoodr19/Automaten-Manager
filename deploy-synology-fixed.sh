#!/bin/bash
# Deployment Script für Synology NAS - Mit sudo Support

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

# Prüfe ob sudo benötigt wird
DOCKER_CMD="docker"
DOCKER_COMPOSE_CMD="docker-compose"

# Test Docker-Zugriff
if ! docker ps >/dev/null 2>&1; then
    if sudo docker ps >/dev/null 2>&1; then
        print_warning "Docker benötigt sudo Rechte"
        DOCKER_CMD="sudo docker"
        DOCKER_COMPOSE_CMD="sudo docker-compose"
    else
        print_error "Docker ist nicht erreichbar. Bitte prüfen Sie die Installation."
        echo ""
        echo "Mögliche Lösungen:"
        echo "1. Fügen Sie Ihren Benutzer zur docker Gruppe hinzu:"
        echo "   sudo synogroup --add docker $USER"
        echo ""
        echo "2. Oder nutzen Sie das Script mit sudo:"
        echo "   sudo ./deploy-synology.sh"
        echo ""
        exit 1
    fi
fi

# 1. Prüfe Docker
echo "Checking Docker installation..."
if command -v docker &> /dev/null; then
    print_status "Docker is installed"
    $DOCKER_CMD --version
else
    print_error "Docker is not installed!"
    exit 1
fi

if command -v docker-compose &> /dev/null; then
    print_status "Docker Compose is installed"
    $DOCKER_COMPOSE_CMD --version
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

# 3. Prüfe .env.production
if [ ! -f .env.production ]; then
    if [ -f .env.production.secure ]; then
        echo ""
        echo "Using .env.production.secure as template..."
        cp .env.production.secure .env.production
        print_status "Environment file created from secure template"
        print_warning "Please verify passwords in .env.production"
    else
        echo ""
        echo "Creating default production environment file..."
        cat > .env.production <<EOF
# Auto-generated production environment
DB_PASSWORD=ChangeMe$(date +%s)
SECRET_KEY=please-change-this-secret-key-$(date +%s)
FLASK_ENV=production
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_EMAIL=admin@localhost
EOF
        print_status "Environment file created"
        print_warning "WICHTIG: Bitte ändern Sie die Standard-Passwörter in .env.production!"
    fi
else
    print_status "Using existing .env.production file"
fi

# 4. Prüfe Dockerfile
if [ ! -f Dockerfile ]; then
    print_error "Dockerfile not found!"
    echo "Creating basic Dockerfile..."
    cat > Dockerfile <<'EOF'
FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application files
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

CMD ["python", "run.py"]
EOF
    print_status "Dockerfile created"
fi

# 5. Build Docker Images
echo ""
echo "Building Docker images..."
$DOCKER_COMPOSE_CMD -f docker-compose.production.yml build
if [ $? -eq 0 ]; then
    print_status "Docker images built successfully"
else
    print_error "Failed to build Docker images"
    echo ""
    echo "Trying with sudo..."
    sudo docker-compose -f docker-compose.production.yml build
    if [ $? -eq 0 ]; then
        print_status "Docker images built with sudo"
        DOCKER_COMPOSE_CMD="sudo docker-compose"
    else
        print_error "Build failed even with sudo"
        exit 1
    fi
fi

# 6. Start Services
echo ""
echo "Starting services..."
$DOCKER_COMPOSE_CMD -f docker-compose.production.yml up -d
if [ $? -eq 0 ]; then
    print_status "Services started successfully"
else
    print_error "Failed to start services"
    exit 1
fi

# 7. Warte auf Datenbank
echo ""
echo "Waiting for database to be ready..."
sleep 10

# Prüfe ob PostgreSQL bereit ist
for i in {1..30}; do
    if $DOCKER_CMD exec automaten_postgres pg_isready -U postgres >/dev/null 2>&1; then
        print_status "Database is ready"
        break
    fi
    echo -n "."
    sleep 1
done

# 8. Zeige Status
echo ""
echo "Checking service status..."
$DOCKER_COMPOSE_CMD -f docker-compose.production.yml ps

# 9. Hole IP-Adresse
NAS_IP=$(ip route get 1 | awk '{print $NF;exit}' 2>/dev/null || hostname -I | cut -d' ' -f1)

# 10. Zeige Zugriffs-URLs
echo ""
echo "==========================================="
print_status "Deployment completed successfully!"
echo ""
echo "Access URLs:"
echo "  Web Interface: http://${NAS_IP}:5000"
echo "  Local Access:  http://localhost:5000"
echo ""
echo "Default Credentials:"
echo "  Username: admin"
echo "  Password: Check your .env.production file"
echo ""
print_warning "IMPORTANT: Change default passwords immediately!"
echo ""
echo "Useful commands:"
echo "  View logs:    $DOCKER_COMPOSE_CMD -f docker-compose.production.yml logs -f"
echo "  Stop:         $DOCKER_COMPOSE_CMD -f docker-compose.production.yml down"
echo "  Restart:      $DOCKER_COMPOSE_CMD -f docker-compose.production.yml restart"
echo "  Backup DB:    $DOCKER_CMD exec automaten_postgres pg_dump -U postgres automaten > backup.sql"
echo ""
echo "Container Health Check:"
$DOCKER_CMD ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo "==========================================="
