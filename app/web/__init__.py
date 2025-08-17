# app/web/__init__.py
"""
Web Routes für Automaten Manager - Mit zentraler Navigation
"""

from flask import Blueprint, render_template, render_template_string, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, date, timedelta
from decimal import Decimal
from app import db
from app.models import User, Device, Entry, Expense, DeviceType, DeviceStatus, ExpenseCategory
from app.web.navigation import render_with_base_new as render_with_base

# Blueprint erstellen
main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__)

# ============================================================================
# AUTH ROUTES
# ============================================================================

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login Seite - MIT 2FA UNTERSTÜTZUNG"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard_modern.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        totp_code = request.form.get('totp_code')  # 2FA Code

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if user.is_locked():
                flash('Account ist gesperrt!', 'danger')
            else:
                # 2FA Check wenn aktiviert
                if user.two_factor_enabled:
                    if not totp_code:
                        # Zeige 2FA Eingabefeld
                        return render_template_string(get_2fa_template(), 
                                               username=username, 
                                               password=password,
                                               title='2FA Verifizierung')
                    
                    # Verifiziere 2FA Code
                    if not user.verify_2fa_token(totp_code):
                        flash('Ungültiger 2FA Code!', 'danger')
                        return render_template_string(get_2fa_template(), 
                                                     username=username, 
                                                     password=password,
                                                     title='2FA Verifizierung')
                
                # Login erfolgreich
                login_user(user, remember=True)
                user.record_login()
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard_modern.dashboard'))
        else:
            flash('Ungültige Anmeldedaten!', 'danger')
            if user:
                user.record_failed_login()

    # Standard Login Template
    return render_template_string(get_login_template(), title='Login - Automaten Manager')


def get_login_template():
    """Login Template HTML"""
    return '''
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-card {
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 400px;
            width: 100%;
        }
        .login-header {
            text-align: center;
            margin-bottom: 30px;
        }
        .login-header i {
            font-size: 48px;
            color: #667eea;
            margin-bottom: 10px;
        }
        .btn-login {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            color: white;
            padding: 12px;
            border-radius: 10px;
            width: 100%;
            font-weight: 600;
        }
        .btn-login:hover {
            background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
            color: white;
        }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="login-header">
            <i class="bi bi-cpu-fill"></i>
            <h3>Automaten Manager</h3>
            <p class="text-muted">Bitte anmelden</p>
        </div>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <form method="POST">
            <div class="mb-3">
                <label class="form-label">Benutzername</label>
                <input type="text" name="username" class="form-control" required autofocus>
            </div>
            <div class="mb-3">
                <label class="form-label">Passwort</label>
                <input type="password" name="password" class="form-control" required>
            </div>
            <div class="mb-3 form-check">
                <input type="checkbox" class="form-check-input" id="remember" name="remember">
                <label class="form-check-label" for="remember">Angemeldet bleiben</label>
            </div>
            <button type="submit" class="btn btn-login">
                <i class="bi bi-box-arrow-in-right"></i> Anmelden
            </button>
        </form>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''


def get_2fa_template():
    """2FA Verification Template"""
    return '''
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.8.1/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .login-card {
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 400px;
            width: 100%;
        }
        .login-header {
            text-align: center;
            margin-bottom: 30px;
        }
        .login-header i {
            font-size: 48px;
            color: #667eea;
            margin-bottom: 10px;
        }
        .btn-verify {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            color: white;
            padding: 12px;
            border-radius: 10px;
            width: 100%;
            font-weight: 600;
        }
        .code-input {
            font-size: 24px;
            text-align: center;
            letter-spacing: 10px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="login-header">
            <i class="bi bi-shield-lock-fill"></i>
            <h3>2FA Verifizierung</h3>
            <p class="text-muted">Geben Sie Ihren 6-stelligen Code ein</p>
        </div>
        
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        
        <form method="POST">
            <input type="hidden" name="username" value="{{ username }}">
            <input type="hidden" name="password" value="{{ password }}">
            
            <div class="mb-4">
                <label class="form-label">Authenticator Code</label>
                <input type="text" 
                       name="totp_code" 
                       class="form-control code-input" 
                       maxlength="6" 
                       pattern="[0-9]{6}" 
                       placeholder="000000"
                       required 
                       autofocus>
                <small class="text-muted">Öffnen Sie Ihre Authenticator-App</small>
            </div>
            
            <button type="submit" class="btn btn-verify">
                <i class="bi bi-check-circle"></i> Verifizieren
            </button>
            
            <div class="text-center mt-3">
                <a href="{{ url_for('auth.login') }}" class="text-muted">
                    <i class="bi bi-arrow-left"></i> Zurück zum Login
                </a>
            </div>
        </form>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Auto-focus and formatting
        document.querySelector('.code-input').addEventListener('input', function(e) {
            this.value = this.value.replace(/[^0-9]/g, '');
            if (this.value.length === 6) {
                // Auto-submit when 6 digits entered
                // this.form.submit();
            }
        });
    </script>
</body>
</html>
'''


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout"""
    logout_user()
    flash('Erfolgreich abgemeldet!', 'success')
    return redirect(url_for('auth.login'))


# ============================================================================
# MAIN ROUTES - REDIRECT TO MODERN DASHBOARD
# ============================================================================

@main_bp.route('/')
def index():
    """Startseite"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard_modern.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard - Redirect to modern version"""
    return redirect(url_for('dashboard_modern.dashboard'))


@main_bp.route('/dashboard_old')
@login_required
def dashboard_old():
    """Old Dashboard - Kept for reference"""
    # Statistiken
    devices = Device.query.filter_by(owner_id=current_user.id).all()
    total_devices = len(devices)
    active_devices = len([d for d in devices if d.status == DeviceStatus.ACTIVE])

    # Einnahmen heute
    today_entries = Entry.query.join(Device).filter(
        Device.owner_id == current_user.id,
        Entry.date == date.today()
    ).all()
    today_revenue = sum(e.amount for e in today_entries)

    # Einnahmen diese Woche
    week_start = date.today() - timedelta(days=date.today().weekday())
    week_entries = Entry.query.join(Device).filter(
        Device.owner_id == current_user.id,
        Entry.date >= week_start
    ).all()
    week_revenue = sum(e.amount for e in week_entries)

    # Einnahmen diesen Monat
    month_start = date.today().replace(day=1)
    month_entries = Entry.query.join(Device).filter(
        Device.owner_id == current_user.id,
        Entry.date >= month_start
    ).all()
    month_revenue = sum(e.amount for e in month_entries)

    # Letzte Einträge
    recent_entries = Entry.query.join(Device).filter(
        Device.owner_id == current_user.id
    ).order_by(Entry.created_at.desc()).limit(5).all()

    content = f"""
    <h2 class="text-white mb-4">Dashboard</h2>

    <div class="row mb-4">
        <div class="col-md-3">
            <div class="card stat-card">
                <div class="card-body">
                    <h6 class="text-muted">Heute</h6>
                    <h3>{today_revenue:.2f} €</h3>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stat-card">
                <div class="card-body">
                    <h6 class="text-muted">Diese Woche</h6>
                    <h3>{week_revenue:.2f} €</h3>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stat-card">
                <div class="card-body">
                    <h6 class="text-muted">Dieser Monat</h6>
                    <h3>{month_revenue:.2f} €</h3>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stat-card">
                <div class="card-body">
                    <h6 class="text-muted">Aktive Geräte</h6>
                    <h3>{active_devices} / {total_devices}</h3>
                </div>
            </div>
        </div>
    </div>

    <div class="row">
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <h5>📊 Letzte Einträge</h5>
                </div>
                <div class="card-body">
    """

    if recent_entries:
        content += """
        <table class="table">
            <thead>
                <tr>
                    <th>Datum</th>
                    <th>Gerät</th>
                    <th>Betrag</th>
                </tr>
            </thead>
            <tbody>
        """
        for entry in recent_entries:
            content += f"""
            <tr>
                <td>{entry.date}</td>
                <td>{entry.device.name}</td>
                <td>{entry.amount:.2f} €</td>
            </tr>
            """
        content += "</tbody></table>"
    else:
        content += '<p class="text-muted">Noch keine Einträge vorhanden</p>'

    content += """
                </div>
            </div>
        </div>

        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <h5>🎰 Meine Geräte</h5>
                </div>
                <div class="card-body">
    """

    if devices:
        content += '<ul class="list-group">'
        for device in devices:
            status_color = 'success' if device.status.value == 'active' else 'warning'
            content += f"""
            <li class="list-group-item d-flex justify-content-between">
                <span>{device.name}</span>
                <span class="badge bg-{status_color}">{device.status.value}</span>
            </li>
            """
        content += '</ul>'
    else:
        content += """
        <p class="text-muted">Noch keine Geräte hinzugefügt</p>
        <a href="/devices" class="btn btn-primary">
            <i class="bi bi-plus"></i> Erstes Gerät hinzufügen
        </a>
        """

    content += """
                </div>
            </div>
        </div>
    </div>
    """

    # Zentrale Navigation mit active_page Parameter
    return render_template_string(
        render_with_base(
            content,
            active_page='dashboard',
            title='Dashboard - Automaten Manager'
        )
    )


@main_bp.route('/entries/add', methods=['GET', 'POST'])
@login_required
def add_entry():
    """Einnahme hinzufügen"""
    devices = Device.query.filter_by(owner_id=current_user.id).all()
    messages = []

    if request.method == 'POST':
        try:
            entry = Entry(
                device_id=request.form.get('device_id'),
                amount=Decimal(request.form.get('amount')),
                date=datetime.strptime(request.form.get('date'), '%Y-%m-%d').date(),
                description=request.form.get('description'),
                user_id=current_user.id
            )
            db.session.add(entry)
            db.session.commit()
            flash('Einnahme wurde erfasst!', 'success')
            return redirect(url_for('dashboard_modern.dashboard'))
        except Exception as e:
            messages.append(('danger', f'Fehler: {str(e)}'))
            db.session.rollback()

    content = """
    <div class="row justify-content-center">
        <div class="col-md-6">
            <div class="card">
                <div class="card-header">
                    <h4>💰 Einnahme erfassen</h4>
                </div>
                <div class="card-body">
    """

    if devices:
        content += f"""
        <form method="POST">
            <div class="mb-3">
                <label class="form-label">Gerät</label>
                <select name="device_id" class="form-select" required>
        """
        for device in devices:
            content += f'<option value="{device.id}">{device.name} - {device.location}</option>'

        content += f"""
                </select>
            </div>
            <div class="mb-3">
                <label class="form-label">Betrag (€)</label>
                <input type="number" name="amount" class="form-control" step="0.01" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Datum</label>
                <input type="date" name="date" class="form-control" value="{date.today()}" required>
            </div>
            <div class="mb-3">
                <label class="form-label">Beschreibung (optional)</label>
                <textarea name="description" class="form-control" rows="2"></textarea>
            </div>
            <button type="submit" class="btn btn-success">
                <i class="bi bi-check-circle"></i> Einnahme speichern
            </button>
            <a href="/dashboard" class="btn btn-secondary">
                Abbrechen
            </a>
        </form>
        """
    else:
        content += """
        <div class="alert alert-warning">
            <i class="bi bi-exclamation-triangle"></i> 
            Sie müssen zuerst ein Gerät hinzufügen!
        </div>
        <a href="/devices" class="btn btn-primary">
            <i class="bi bi-plus"></i> Gerät hinzufügen
        </a>
        """

    content += """
                </div>
            </div>
        </div>
    </div>
    """

    # Zentrale Navigation mit active_page Parameter
    return render_template_string(
        render_with_base(
            content,
            active_page='entries',
            title='Einnahme erfassen - Automaten Manager',
            messages=messages
        )
    )