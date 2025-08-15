#!/bin/bash
# entrypoint.sh - Startup script for Automaten Manager

set -e

echo "Starting Automaten Manager v2.0..."

# Wait for PostgreSQL
echo "Waiting for PostgreSQL..."
while ! nc -z postgres 5432; do
    sleep 0.1
done
echo "PostgreSQL is ready!"

# Wait for Redis
echo "Waiting for Redis..."
while ! nc -z redis 6379; do
    sleep 0.1
done
echo "Redis is ready!"

# Run database migrations
echo "Running database migrations..."
flask db upgrade

# Create default admin user if not exists
echo "Checking for admin user..."
python -c "
from app import create_app, db
from app.models import User
app = create_app()
with app.app_context():
    if not User.query.filter_by(username='admin').first():
        print('Creating default admin user...')
        admin = User(
            username='admin',
            email='admin@automaten-manager.com',
            is_admin=True,
            is_active=True,
            is_verified=True
        )
        admin.set_password('changeme123!')
        db.session.add(admin)
        db.session.commit()
        print('Admin user created!')
"

# Start the application
echo "Starting application..."
exec "$@"