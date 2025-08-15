# app/web/__init__.py
"""
Web Routes für Automaten Manager - Mit zentraler Navigation
"""

from flask import Blueprint, render_template, render_template_string, redirect, url_for, flash, request, jsonify, get_flashed_messages
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime, date, timedelta
from decimal import Decimal
from app import db
from app.models import User, Device, Entry, Expense, DeviceType, DeviceStatus, ExpenseCategory
from app.web.navigation import render_with_base_new as render_with_base  # NEU: Zentrale Navigation!
from app.web.devices import devices_bp
import secrets
import string

# Blueprint erstellen
main_bp = Blueprint('main', __name__)
auth_bp = Blueprint('auth', __name__)

# KEINE lokale render_with_base mehr - wir nutzen die zentrale!

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def generate_serial_number(device_type, manufacturer=None, model=None):
    """
    Generiert intelligente Seriennummer
    Format: TYP-HER-MOD-JAHR-CODE
    """
    type_prefixes = {
        'kaffee': 'KAF',
        'getraenke': 'GET',
        'snacks': 'SNK',
        'kombi': 'KMB'
    }
    prefix = type_prefixes.get(device_type, 'DEV')

    # Hersteller-Code (erste 3 Buchstaben)
    mfg_code = 'XXX'
    if manufacturer:
        mfg_code = ''.join(c for c in manufacturer.upper()[:3] if c.isalpha())
        mfg_code = mfg_code.ljust(3, 'X')

    # Modell-Code (erste 2 Zeichen)
    model_code = 'XX'
    if model:
        model_code = ''.join(c for c in model.upper()[:2] if c.isalnum())
        model_code = model_code.ljust(2, '0')

    # Jahr
    year = datetime.now().year

    # Zufälliger Code
    random_code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))

    return f"{prefix}-{mfg_code}-{model_code}-{year}-{random_code}"


def get_next_device_name(device_type):
    """Generiert automatisch einen Gerätenamen"""
    type_names = {
        'kaffee': 'Kaffeeautomat',
        'getraenke': 'Getränkeautomat',
        'snacks': 'Snackautomat',
        'kombi': 'Kombiautomat'
    }
    count = Device.query.filter_by(
        type=DeviceType(device_type),
        owner_id=current_user.id
    ).count() + 1
    return f"{type_names.get(device_type, 'Automat')} #{count}"

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
        <a href="/devices/add" class="btn btn-primary">
            <i class="bi bi-plus"></i> Erstes Gerät hinzufügen
        </a>
        """

    content += """
                </div>
            </div>
        </div>
    </div>
    """

    # NEU: Zentrale Navigation mit active_page Parameter!
    return render_template_string(
        render_with_base(
            content,
            active_page='dashboard',  # Markiert "Dashboard" als aktiv
            title='Dashboard - Automaten Manager'
        )
    )


# ============================================================================
# ERWEITERTE GERÄTE-VERWALTUNG MIT EDIT/DELETE
# ============================================================================

@main_bp.route('/devices_old')
@login_required
def devices():
    """Geräte-Liste mit Edit/Delete Buttons"""
    devices = Device.query.filter_by(owner_id=current_user.id).all()

    # JavaScript für Modal-Funktionen
    extra_scripts = """
    <script>
    function editDevice(deviceId) {
        fetch(`/devices/api/${deviceId}`)
            .then(response => response.json())
            .then(device => {
                document.getElementById('deviceModalTitle').textContent = 'Gerät bearbeiten';
                document.getElementById('deviceForm').action = `/devices/edit/${deviceId}`;
                document.getElementById('device_id').value = deviceId;

                // Felder füllen
                document.getElementById('name').value = device.name;
                document.getElementById('type').value = device.type;
                document.getElementById('manufacturer').value = device.manufacturer || '';
                document.getElementById('model').value = device.model || '';
                document.getElementById('serial_number').value = device.serial_number || '';
                document.getElementById('location').value = device.location || '';
                document.getElementById('purchase_price').value = device.purchase_price || '';

                // Modal öffnen
                new bootstrap.Modal(document.getElementById('deviceModal')).show();
            });
    }

    function deleteDevice(deviceId, deviceName) {
        if (confirm(`Möchten Sie das Gerät "${deviceName}" wirklich löschen?`)) {
            fetch(`/devices/delete/${deviceId}`, { method: 'POST' })
                .then(() => location.reload());
        }
    }

    // Auto-generate serial number preview
    document.addEventListener('DOMContentLoaded', function() {
        const serialInput = document.getElementById('serial_number');
        const typeSelect = document.getElementById('type');
        const manufacturerInput = document.getElementById('manufacturer');
        const modelInput = document.getElementById('model');

        function updateSerialPreview() {
            if (!serialInput.value) {
                const typeMap = {'kaffee': 'KAF', 'getraenke': 'GET', 'snacks': 'SNK', 'kombi': 'KMB'};
                const type = typeMap[typeSelect.value] || 'DEV';

                let mfg = 'XXX';
                if (manufacturerInput.value) {
                    mfg = manufacturerInput.value.toUpperCase().replace(/[^A-Z]/g, '').substr(0, 3).padEnd(3, 'X');
                }

                let model = 'XX';
                if (modelInput.value) {
                    model = modelInput.value.toUpperCase().replace(/[^A-Z0-9]/g, '').substr(0, 2).padEnd(2, '0');
                }

                const year = new Date().getFullYear();
                serialInput.placeholder = `${type}-${mfg}-${model}-${year}-XXXXXX (auto)`;
                serialInput.classList.add('auto-generated');
            }
        }

        if (typeSelect) typeSelect.addEventListener('change', updateSerialPreview);
        if (manufacturerInput) manufacturerInput.addEventListener('input', updateSerialPreview);
        if (modelInput) modelInput.addEventListener('input', updateSerialPreview);

        if (serialInput) {
            serialInput.addEventListener('input', function() {
                if (this.value) {
                    this.classList.remove('auto-generated');
                } else {
                    updateSerialPreview();
                }
            });
        }
    });

    // Reset form when modal closes
    document.addEventListener('DOMContentLoaded', function() {
        const modal = document.getElementById('deviceModal');
        if (modal) {
            modal.addEventListener('hidden.bs.modal', function () {
                document.getElementById('deviceModalTitle').textContent = 'Neues Gerät hinzufügen';
                document.getElementById('deviceForm').action = '/devices/add';
                document.getElementById('deviceForm').reset();
                document.getElementById('device_id').value = '';
            });
        }
    });
    </script>
    """

    # CSS für Geräte
    extra_css = """
    <style>
        .device-card { position: relative; transition: all 0.3s; }
        .device-card:hover { transform: translateY(-5px); box-shadow: 0 15px 40px rgba(0,0,0,0.15); }
        .device-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 5px;
            background: linear-gradient(90deg, #667eea, #764ba2);
        }
        .device-card.status-active::before { background: #28a745; }
        .device-card.status-maintenance::before { background: #ffc107; }
        .device-card.status-inactive::before { background: #6c757d; }

        .action-buttons {
            position: absolute;
            top: 1rem;
            right: 1rem;
            opacity: 0;
            transition: opacity 0.3s;
        }
        .device-card:hover .action-buttons { opacity: 1; }

        .auto-generated {
            background-color: #f0f8ff;
            border: 2px dashed #667eea;
        }
        .hint-text {
            color: #6c757d;
            font-size: 0.875rem;
            font-style: italic;
            margin-top: 0.25rem;
        }
    </style>
    """

    content = """
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="text-white">Meine Geräte</h2>
        <button class="btn btn-light" data-bs-toggle="modal" data-bs-target="#deviceModal">
            <i class="bi bi-plus-circle"></i> Gerät hinzufügen
        </button>
    </div>

    <div class="row">
    """

    if devices:
        for device in devices:
            status_color = 'success' if device.status.value == 'active' else 'warning' if device.status.value == 'maintenance' else 'secondary'
            content += f"""
            <div class="col-md-4 mb-3">
                <div class="card device-card status-{device.status.value}">
                    <div class="action-buttons">
                        <button class="btn btn-sm btn-warning" onclick="editDevice({device.id})" title="Bearbeiten">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="deleteDevice({device.id}, '{device.name}')" title="Löschen">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                    <div class="card-body">
                        <h5>{device.name}</h5>
                        <p class="text-muted">{device.type.value.title()}</p>
                        <p><i class="bi bi-geo-alt"></i> {device.location or 'Kein Standort'}</p>
                        <p><i class="bi bi-cash"></i> Einnahmen: {device.get_total_revenue():.2f} €</p>
                        <small class="text-muted">SN: {device.serial_number or 'Keine'}</small><br>
            """

            # Hersteller und Modell anzeigen falls vorhanden
            if hasattr(device, 'manufacturer') and device.manufacturer:
                content += f'<small class="text-muted">Hersteller: {device.manufacturer}</small><br>'
            if hasattr(device, 'model') and device.model:
                content += f'<small class="text-muted">Modell: {device.model}</small><br>'

            content += f"""
                        <span class="badge bg-{status_color} mt-2">{device.status.value}</span>
                    </div>
                </div>
            </div>
            """
    else:
        content += """
        <div class="col-12">
            <div class="card">
                <div class="card-body text-center py-5">
                    <i class="bi bi-inbox display-1 text-muted"></i>
                    <p class="mt-3">Noch keine Geräte vorhanden</p>
                    <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#deviceModal">
                        <i class="bi bi-plus"></i> Erstes Gerät hinzufügen
                    </button>
                </div>
            </div>
        </div>
        """

    content += """
    </div>

    <!-- Device Modal -->
    <div class="modal fade" id="deviceModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="deviceModalTitle">Neues Gerät hinzufügen</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <form id="deviceForm" method="POST" action="/devices/add">
                    <div class="modal-body">
                        <input type="hidden" id="device_id" name="device_id">

                        <div class="row">
                            <div class="col-md-6">
                                <div class="mb-3">
                                    <label class="form-label">Name</label>
                                    <input type="text" id="name" name="name" class="form-control" 
                                           placeholder="Wird automatisch generiert wenn leer">
                                    <div class="hint-text">z.B. Kaffeeautomat #1</div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="mb-3">
                                    <label class="form-label">Typ *</label>
                                    <select id="type" name="type" class="form-select" required>
                                        <option value="kaffee">☕ Kaffee</option>
                                        <option value="getraenke">🥤 Getränke</option>
                                        <option value="snacks">🍫 Snacks</option>
                                        <option value="kombi">📦 Kombi</option>
                                    </select>
                                </div>
                            </div>
                        </div>

                        <div class="row">
                            <div class="col-md-6">
                                <div class="mb-3">
                                    <label class="form-label">Hersteller</label>
                                    <input type="text" id="manufacturer" name="manufacturer" class="form-control" 
                                           placeholder="z.B. Nescafé, Coca-Cola">
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="mb-3">
                                    <label class="form-label">Modell</label>
                                    <input type="text" id="model" name="model" class="form-control" 
                                           placeholder="z.B. Alegria 8/30">
                                </div>
                            </div>
                        </div>

                        <div class="mb-3">
                            <label class="form-label">Seriennummer</label>
                            <input type="text" id="serial_number" name="serial_number" class="form-control" 
                                   placeholder="Wird automatisch generiert wenn leer">
                            <div class="hint-text">Format: TYP-HER-MOD-JAHR-CODE</div>
                        </div>

                        <div class="mb-3">
                            <label class="form-label">Standort</label>
                            <input type="text" id="location" name="location" class="form-control" 
                                   placeholder="z.B. Eingangsbereich">
                        </div>

                        <div class="mb-3">
                            <label class="form-label">Anschaffungspreis (€)</label>
                            <input type="number" id="purchase_price" name="purchase_price" class="form-control" 
                                   step="0.01" value="900.00">
                        </div>
                    </div>

                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Abbrechen</button>
                        <button type="submit" class="btn btn-primary">
                            <i class="bi bi-check-circle"></i> Speichern
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
    """

    # NEU: Zentrale Navigation mit active_page Parameter!
    return render_template_string(
        render_with_base(
            content,
            active_page='devices',  # Markiert "Geräte" als aktiv
            title='Geräte - Automaten Manager',
            extra_scripts=extra_scripts,
            extra_css=extra_css
        )
    )


@main_bp.route('/devices/api/<int:device_id>')
@login_required
def get_device_api(device_id):
    """API Endpoint für Device-Daten (für JavaScript)"""
    device = Device.query.filter_by(id=device_id, owner_id=current_user.id).first_or_404()
    return jsonify({
        'id': device.id,
        'name': device.name,
        'type': device.type.value,
        'manufacturer': getattr(device, 'manufacturer', ''),
        'model': getattr(device, 'model', ''),
        'serial_number': device.serial_number,
        'location': device.location,
        'purchase_price': float(device.purchase_price) if device.purchase_price else 0
    })


@main_bp.route('/devices/add', methods=['GET', 'POST'])
@login_required
def add_device():
    """Gerät hinzufügen - erweitert mit Auto-Features"""
    if request.method == 'POST':
        try:
            # Auto-generate name if empty
            name = request.form.get('name')
            if not name:
                name = get_next_device_name(request.form.get('type'))

            # Auto-generate serial number if empty
            serial_number = request.form.get('serial_number')
            if not serial_number:
                serial_number = generate_serial_number(
                    request.form.get('type'),
                    request.form.get('manufacturer'),
                    request.form.get('model')
                )

            device = Device(
                name=name,
                type=DeviceType(request.form.get('type')),
                status=DeviceStatus.ACTIVE,
                location=request.form.get('location'),
                serial_number=serial_number,
                purchase_price=Decimal(request.form.get('purchase_price', 0)),
                owner_id=current_user.id
            )

            # Setze Hersteller und Modell falls vorhanden
            if hasattr(Device, 'manufacturer'):
                device.manufacturer = request.form.get('manufacturer')
            if hasattr(Device, 'model'):
                device.model = request.form.get('model')

            db.session.add(device)
            db.session.commit()
            flash(f'Gerät "{device.name}" wurde hinzugefügt!', 'success')
            return redirect(url_for('main.devices'))
        except Exception as e:
            flash(f'Fehler: {str(e)}', 'danger')
            db.session.rollback()

    return redirect(url_for('main.devices'))


@main_bp.route('/devices/edit/<int:device_id>', methods=['POST'])
@login_required
def edit_device(device_id):
    """Gerät bearbeiten"""
    device = Device.query.filter_by(id=device_id, owner_id=current_user.id).first_or_404()

    try:
        device.name = request.form.get('name', device.name)
        device.type = DeviceType(request.form.get('type', device.type.value))
        device.location = request.form.get('location')
        device.serial_number = request.form.get('serial_number', device.serial_number)
        device.purchase_price = Decimal(request.form.get('purchase_price', device.purchase_price))

        # Update Hersteller und Modell falls vorhanden
        if hasattr(device, 'manufacturer'):
            device.manufacturer = request.form.get('manufacturer')
        if hasattr(device, 'model'):
            device.model = request.form.get('model')

        db.session.commit()
        flash(f'Gerät "{device.name}" wurde aktualisiert!', 'success')
    except Exception as e:
        flash(f'Fehler beim Aktualisieren: {str(e)}', 'danger')
        db.session.rollback()

    return redirect(url_for('main.devices'))


@main_bp.route('/devices/delete/<int:device_id>', methods=['POST'])
@login_required
def delete_device(device_id):
    """Gerät löschen"""
    device = Device.query.filter_by(id=device_id, owner_id=current_user.id).first_or_404()

    try:
        device_name = device.name
        db.session.delete(device)
        db.session.commit()
        flash(f'Gerät "{device_name}" wurde gelöscht!', 'warning')
    except Exception as e:
        flash(f'Fehler beim Löschen: {str(e)}', 'danger')
        db.session.rollback()

    return redirect(url_for('main.devices'))


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

    # NEU: Zentrale Navigation mit active_page Parameter!
    return render_template_string(
        render_with_base(
            content,
            active_page='entries',  # Markiert "Einnahmen" als aktiv
            title='Einnahme erfassen - Automaten Manager',
            messages=messages
        )
    )