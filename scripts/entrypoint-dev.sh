#!/bin/bash
# entrypoint-dev.sh - Development startup script

set -e

echo "🚀 Starting Automaten Manager (Development Mode)..."

# Wait for PostgreSQL
echo "⏳ Waiting for PostgreSQL..."
while ! nc -z postgres 5432; do
    sleep 0.1
done
echo "✅ PostgreSQL is ready!"

# Wait for Redis
echo "⏳ Waiting for Redis..."
while ! nc -z redis 6379; do
    sleep 0.1
done
echo "✅ Redis is ready!"

# Initialize database if needed
echo "🔧 Initializing database..."
python -c "
from app import create_app, db
app = create_app('development')
with app.app_context():
    db.create_all()
    print('✅ Database tables created!')
"

# Create admin user if not exists
echo "👤 Checking for admin user..."
python -c "
from app import create_app, db
from app.models import User
app = create_app('development')
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
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print('✅ Admin user created (admin/admin123)')
    else:
        print('✅ Admin user already exists')
"

echo "🎉 Development server starting..."
echo "📍 Access the application at: http://localhost:5000"
echo "📧 MailHog (Email testing): http://localhost:8025"
echo "🗄️ Adminer (Database): http://localhost:8080"
echo "🔴 Redis Commander: http://localhost:8081"
echo ""
echo "👤 Login credentials: admin / admin123"
echo ""

# Start the application
exec "$@"