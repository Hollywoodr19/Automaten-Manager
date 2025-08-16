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
    """Login Seite - MIT TEMPLATE"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            if user.is_locked():
                flash('Account ist gesperrt!', 'danger')
            else:
                login_user(user, remember=True)
                user.record_login()
                next_page = request.args.get('next')
                return redirect(next_page or url_for('main.dashboard'))
        else:
            flash('Ungültige Anmeldedaten!', 'danger')
            if user:
                user.record_failed_login()

    # TEMPLATE VERWENDEN
    return render_template('auth/login.html', title='Login - Automaten Manager')


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout"""
    logout_user()
    flash('Erfolgreich abgemeldet!', 'success')
    return redirect(url_for('auth.login'))


# ============================================================================
# MAIN ROUTES - MIT ZENTRALER NAVIGATION
# ============================================================================

@main_bp.route('/')
def index():
    """Startseite"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard"""
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
            return redirect(url_for('main.dashboard'))
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