# app/__init__.py
"""
Automaten Manager v2.0 - Hauptanwendung
Vollständige Version mit allen Features
"""

from flask import Flask, render_template_string, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Extensions HIER initialisieren (werden von models importiert)
db = SQLAlchemy()
login_manager = LoginManager()


def create_app(config='development'):
    """Application Factory"""
    import os

    # Template-Ordner richtig setzen
    template_dir = os.path.abspath(os.path.dirname(__file__) + '/../templates')
    static_dir = os.path.abspath(os.path.dirname(__file__) + '/../static')

    app = Flask(__name__,
                template_folder=template_dir,
                static_folder=static_dir)

    # Konfiguration
    app.config['SECRET_KEY'] = 'dev-secret-key-change-in-production'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:password@postgres:5432/automaten'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Extensions mit App verbinden
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Bitte melden Sie sich an, um fortzufahren.'
    login_manager.login_message_category = 'info'

    # Web Blueprints registrieren - AUSSERHALB des app_context!
    from app.web import main_bp, auth_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    print("✅ Main and Auth Blueprints registered successfully!")

    # Entries Blueprint registrieren
    try:
        from app.web.entries import entries_bp
        app.register_blueprint(entries_bp)
        print("✅ Entries Blueprint registered successfully!")
    except ImportError as e:
        print(f"⚠️ Entries Blueprint not found: {e}")

    # Expenses Blueprint registrieren
    try:
        from app.web.expenses import expenses_bp
        app.register_blueprint(expenses_bp)
        print("✅ Expenses Blueprint registered successfully!")
    except ImportError as e:
        print(f"⚠️ Expenses Blueprint not found: {e}")

    # Refills Blueprint registrieren
    try:
        from app.web.refills import refills_bp
        app.register_blueprint(refills_bp)
        print("✅ Refills Blueprint registered successfully!")
    except ImportError as e:
        print(f"⚠️ Refills Blueprint not found: {e}")

    # Products Blueprint registrieren
    try:
        from app.web.products import products_bp
        app.register_blueprint(products_bp)
        print("✅ Products Blueprint registered successfully!")
    except ImportError as e:
        print(f"⚠️ Products Blueprint not found: {e}")

    # Supplier Blueprint registrieren
    try:
        from app.web.suppliers import suppliers_bp
        app.register_blueprint(suppliers_bp)
        print("✅ Supplier Blueprint registered successfully!")
    except ImportError as e:
        print(f"⚠️ Supplier Blueprint not found: {e}")

    # Device Blueprint registrieren
    try:
        from app.web.devices import devices_bp
        app.register_blueprint(devices_bp)
        print("✅ Devices Blueprint registered successfully!")
    except ImportError as e:
        print(f"⚠️ Devices Blueprint not found: {e}")

        # Users Blueprint registrieren
    try:
        from app.web.users import users_bp
        app.register_blueprint(users_bp)
        print("✅ Users Blueprint registered successfully!")
    except ImportError as e:
        print(f"⚠️ Users Blueprint not found: {e}")

    # Models und Datenbank-Setup - NACH Blueprint-Registrierung
    with app.app_context():
        # Models werden HIER importiert (nicht oben!)
        from app import models  # Importiert das ganze models Modul

        # Tabellen erstellen
        db.create_all()

        # Admin-User erstellen
        create_admin_user()

    # Standard Routes (für Tests)
    register_default_routes(app)

    return app


def create_admin_user():
    """Admin User erstellen falls nicht vorhanden"""
    from app.models import User  # Import HIER, nicht oben

    admin = User.query.filter_by(username='admin').first()
    if not admin:
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
        print("✅ Admin user created (admin/admin123)")


def register_default_routes(app):
    """Standard Test-Routes registrieren"""

    @app.route('/test')
    def test():
        """Test-Route für Basis-Funktionalität"""
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Automaten Manager - Test</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body { 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    min-height: 100vh;
                }
                .main-card { 
                    background: white; 
                    border-radius: 20px; 
                    padding: 40px; 
                    margin-top: 50px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="main-card">
                    <h1 class="text-center mb-4">🎉 Automaten Manager v2.0</h1>
                    <div class="alert alert-success text-center">
                        <h4>✅ System läuft mit Web-Interface!</h4>
                    </div>

                    <div class="text-center mt-4">
                        <a href="/" class="btn btn-primary btn-lg">
                            <i class="bi bi-house"></i> Zur Hauptseite
                        </a>
                        <a href="/dashboard" class="btn btn-success btn-lg">
                            <i class="bi bi-speedometer2"></i> Dashboard
                        </a>
                        <a href="/devices" class="btn btn-warning btn-lg">
                            <i class="bi bi-pc-display"></i> Geräte
                        </a>
                        <a href="/api/stats" class="btn btn-info btn-lg">
                            <i class="bi bi-graph-up"></i> API Stats
                        </a>
                    </div>

                    <div class="mt-4">
                        <h5>Registrierte Routes:</h5>
                        <ul>
                            <li>/login - Anmeldung</li>
                            <li>/dashboard - Dashboard</li>
                            <li>/devices - Geräte-Verwaltung</li>
                            <li>/entries - Einnahmen</li>
                            <li>/expenses - Ausgaben</li>
                            <li>/refills - Warenwirtschaft</li>
                        </ul>
                    </div>
                </div>
            </div>
        </body>
        </html>
        ''')

    @app.route('/api/stats')
    def api_stats():
        """Statistiken aus der Datenbank"""
        from app.models import User, Device, Entry, Expense

        return jsonify({
            'status': 'success',
            'data': {
                'users': User.query.count(),
                'devices': Device.query.count(),
                'entries': Entry.query.count(),
                'expenses': Expense.query.count()
            }
        })

    @app.route('/api/test')
    def api_test():
        """Test der Models"""
        from app.models import User, Device

        try:
            # Test Query
            admin = User.query.filter_by(username='admin').first()
            devices = Device.query.all()

            return jsonify({
                'status': 'success',
                'admin_exists': admin is not None,
                'admin_email': admin.email if admin else None,
                'device_count': len(devices)
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500

    @app.route('/api/routes')
    def list_routes():
        """Debug: Zeigt alle registrierten Routes"""
        import urllib
        output = []
        for rule in app.url_map.iter_rules():
            options = {}
            for arg in rule.arguments:
                options[arg] = "[{0}]".format(arg)

            methods = ','.join(rule.methods)
            url = urllib.parse.unquote("{:50s} {:20s} {}".format(
                rule.endpoint, methods, rule.rule
            ))
            output.append(url)

        return jsonify({
            'status': 'success',
            'routes': sorted(output)
        })


# User loader für Flask-Login
@login_manager.user_loader
def load_user(user_id):
    # Import hier um Circular Import zu vermeiden
    from app.models import User
    return User.query.get(int(user_id))