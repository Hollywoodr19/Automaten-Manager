# app/web/automations.py
"""
Automatisierungen für Automaten Manager
- Wiederkehrende Ausgaben
- Automatische Nachbestellungen
- Scheduled Tasks
"""

from flask import Blueprint, render_template_string, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from app import db
from app.models import Expense, ExpenseCategory, Device, Product
from sqlalchemy import and_, or_, func
import json

automations_bp = Blueprint('automations', __name__, url_prefix='/automations')

# Neue Model für wiederkehrende Ausgaben
class RecurringExpense(db.Model):
    """Wiederkehrende Ausgaben"""
    __tablename__ = 'recurring_expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    category = db.Column(db.Enum(ExpenseCategory), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=True)
    
    # Wiederholungs-Einstellungen
    frequency = db.Column(db.String(20), nullable=False)  # daily, weekly, monthly, yearly
    interval = db.Column(db.Integer, default=1)  # Alle X Tage/Wochen/Monate
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    
    # Wochentage für wöchentliche Wiederholung (JSON Array)
    weekdays = db.Column(db.Text, nullable=True)  # [1,3,5] für Mo, Mi, Fr
    
    # Tag des Monats für monatliche Wiederholung
    day_of_month = db.Column(db.Integer, nullable=True)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    last_created = db.Column(db.Date, nullable=True)
    next_due = db.Column(db.Date, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='recurring_expenses')
    device = db.relationship('Device', backref='recurring_expenses')
    
    def calculate_next_due(self):
        """Berechnet das nächste Fälligkeitsdatum"""
        if not self.is_active:
            return None
            
        base_date = self.last_created or self.start_date
        
        if self.frequency == 'daily':
            next_date = base_date + timedelta(days=self.interval)
        elif self.frequency == 'weekly':
            next_date = base_date + timedelta(weeks=self.interval)
        elif self.frequency == 'monthly':
            next_date = base_date + relativedelta(months=self.interval)
        elif self.frequency == 'yearly':
            next_date = base_date + relativedelta(years=self.interval)
        else:
            next_date = base_date + timedelta(days=1)
        
        # End date check
        if self.end_date and next_date > self.end_date:
            return None
            
        return next_date
    
    def create_expense(self):
        """Erstellt eine Ausgabe basierend auf dieser Vorlage"""
        expense = Expense(
            user_id=self.user_id,
            amount=self.amount,
            category=self.category,
            device_id=self.device_id,
            description=f"{self.name} (Automatisch erstellt)",
            date=date.today()
        )
        db.session.add(expense)
        
        # Update last_created und next_due
        self.last_created = date.today()
        self.next_due = self.calculate_next_due()
        
        db.session.commit()
        return expense


@automations_bp.route('/')
@login_required
def index():
    """Automatisierungen Übersicht"""
    
    # Wiederkehrende Ausgaben
    recurring = RecurringExpense.query.filter_by(
        user_id=current_user.id
    ).order_by(RecurringExpense.next_due.asc()).all()
    
    # Statistiken
    active_automations = len([r for r in recurring if r.is_active])
    total_monthly = sum([r.amount for r in recurring if r.is_active and r.frequency == 'monthly'])
    next_due = min([r.next_due for r in recurring if r.next_due], default=None)
    
    content = f"""
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="text-white">
            <i class="bi bi-arrow-repeat"></i> Automatisierungen
        </h2>
        <button class="btn btn-light" onclick="showNewRecurringModal()">
            <i class="bi bi-plus-circle"></i> Neue Automatisierung
        </button>
    </div>

    <!-- Statistik Cards -->
    <div class="row mb-4">
        <div class="col-md-3">
            <div class="card">
                <div class="card-body">
                    <h6 class="text-muted mb-2">Aktive Automatisierungen</h6>
                    <h3 class="mb-0">{active_automations}</h3>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card">
                <div class="card-body">
                    <h6 class="text-muted mb-2">Monatliche Ausgaben</h6>
                    <h3 class="mb-0 text-danger">-{total_monthly:.2f} €</h3>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card">
                <div class="card-body">
                    <h6 class="text-muted mb-2">Nächste Fälligkeit</h6>
                    <h3 class="mb-0">{next_due.strftime('%d.%m.%Y') if next_due else '-'}</h3>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card">
                <div class="card-body">
                    <h6 class="text-muted mb-2">Heute fällig</h6>
                    <h3 class="mb-0">{len([r for r in recurring if r.next_due == date.today()])}</h3>
                </div>
            </div>
        </div>
    </div>

    <!-- Tabs -->
    <ul class="nav nav-tabs mb-4">
        <li class="nav-item">
            <a class="nav-link active" data-bs-toggle="tab" href="#recurring">
                <i class="bi bi-arrow-repeat"></i> Wiederkehrende Ausgaben
            </a>
        </li>
        <li class="nav-item">
            <a class="nav-link" data-bs-toggle="tab" href="#rules">
                <i class="bi bi-gear"></i> Regeln
            </a>
        </li>
        <li class="nav-item">
            <a class="nav-link" data-bs-toggle="tab" href="#history">
                <i class="bi bi-clock-history"></i> Verlauf
            </a>
        </li>
    </ul>

    <!-- Tab Content -->
    <div class="tab-content">
        <!-- Wiederkehrende Ausgaben -->
        <div class="tab-pane fade show active" id="recurring">
            <div class="card">
                <div class="card-body">
                    {render_recurring_expenses_table(recurring)}
                </div>
            </div>
        </div>
        
        <!-- Regeln -->
        <div class="tab-pane fade" id="rules">
            <div class="card">
                <div class="card-body">
                    <h5>Automatische Regeln</h5>
                    <div class="list-group">
                        <div class="list-group-item">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <h6 class="mb-1">Niedrigbestand-Benachrichtigung</h6>
                                    <small class="text-muted">E-Mail wenn Produkt unter Mindestbestand</small>
                                </div>
                                <div class="form-check form-switch">
                                    <input class="form-check-input" type="checkbox" checked>
                                </div>
                            </div>
                        </div>
                        <div class="list-group-item">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <h6 class="mb-1">Wartungserinnerung</h6>
                                    <small class="text-muted">5 Tage vor fälliger Wartung</small>
                                </div>
                                <div class="form-check form-switch">
                                    <input class="form-check-input" type="checkbox" checked>
                                </div>
                            </div>
                        </div>
                        <div class="list-group-item">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <h6 class="mb-1">Tägliche Zusammenfassung</h6>
                                    <small class="text-muted">Jeden Tag um 20:00 Uhr</small>
                                </div>
                                <div class="form-check form-switch">
                                    <input class="form-check-input" type="checkbox">
                                </div>
                            </div>
                        </div>
                        <div class="list-group-item">
                            <div class="d-flex justify-content-between align-items-center">
                                <div>
                                    <h6 class="mb-1">Auto-Backup</h6>
                                    <small class="text-muted">Wöchentlich sonntags</small>
                                </div>
                                <div class="form-check form-switch">
                                    <input class="form-check-input" type="checkbox" checked>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Verlauf -->
        <div class="tab-pane fade" id="history">
            <div class="card">
                <div class="card-body">
                    <h5>Automatisierungs-Verlauf</h5>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Datum</th>
                                <th>Typ</th>
                                <th>Aktion</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>{datetime.now().strftime('%d.%m.%Y %H:%M')}</td>
                                <td><span class="badge bg-primary">Ausgabe</span></td>
                                <td>Miete erstellt</td>
                                <td><span class="badge bg-success">Erfolgreich</span></td>
                            </tr>
                            <tr>
                                <td>{(datetime.now() - timedelta(days=1)).strftime('%d.%m.%Y %H:%M')}</td>
                                <td><span class="badge bg-info">E-Mail</span></td>
                                <td>Wartungserinnerung gesendet</td>
                                <td><span class="badge bg-success">Erfolgreich</span></td>
                            </tr>
                            <tr>
                                <td>{(datetime.now() - timedelta(days=2)).strftime('%d.%m.%Y %H:%M')}</td>
                                <td><span class="badge bg-warning">Backup</span></td>
                                <td>Automatisches Backup erstellt</td>
                                <td><span class="badge bg-success">Erfolgreich</span></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <!-- Modal für neue wiederkehrende Ausgabe -->
    <div class="modal fade" id="newRecurringModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Neue wiederkehrende Ausgabe</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <form id="recurringForm" onsubmit="saveRecurringExpense(event)">
                    <div class="modal-body">
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <label class="form-label">Name</label>
                                <input type="text" class="form-control" name="name" required
                                       placeholder="z.B. Miete, Strom, Internet">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">Betrag</label>
                                <div class="input-group">
                                    <input type="number" class="form-control" name="amount" 
                                           step="0.01" required>
                                    <span class="input-group-text">€</span>
                                </div>
                            </div>
                        </div>
                        
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <label class="form-label">Kategorie</label>
                                <select class="form-select" name="category" required>
                                    <option value="">Bitte wählen...</option>
                                    <option value="rent">Miete</option>
                                    <option value="utilities">Nebenkosten</option>
                                    <option value="insurance">Versicherung</option>
                                    <option value="maintenance">Wartung</option>
                                    <option value="other">Sonstiges</option>
                                </select>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">Gerät (optional)</label>
                                <select class="form-select" name="device_id">
                                    <option value="">Alle Geräte</option>
                                    <!-- Geräte werden dynamisch geladen -->
                                </select>
                            </div>
                        </div>
                        
                        <div class="row mb-3">
                            <div class="col-md-4">
                                <label class="form-label">Wiederholung</label>
                                <select class="form-select" name="frequency" onchange="updateFrequencyOptions(this)">
                                    <option value="monthly">Monatlich</option>
                                    <option value="weekly">Wöchentlich</option>
                                    <option value="daily">Täglich</option>
                                    <option value="yearly">Jährlich</option>
                                </select>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">Intervall</label>
                                <div class="input-group">
                                    <span class="input-group-text">Alle</span>
                                    <input type="number" class="form-control" name="interval" value="1" min="1">
                                    <span class="input-group-text" id="intervalUnit">Monate</span>
                                </div>
                            </div>
                            <div class="col-md-4" id="dayOfMonthGroup">
                                <label class="form-label">Tag des Monats</label>
                                <input type="number" class="form-control" name="day_of_month" 
                                       min="1" max="31" value="1">
                            </div>
                        </div>
                        
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <label class="form-label">Startdatum</label>
                                <input type="date" class="form-control" name="start_date" 
                                       value="{date.today().isoformat()}" required>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">Enddatum (optional)</label>
                                <input type="date" class="form-control" name="end_date">
                                <small class="text-muted">Leer lassen für unbegrenzt</small>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Abbrechen</button>
                        <button type="submit" class="btn btn-primary">
                            <i class="bi bi-save"></i> Speichern
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <script>
    function showNewRecurringModal() {{
        const modal = new bootstrap.Modal(document.getElementById('newRecurringModal'));
        modal.show();
    }}
    
    function updateFrequencyOptions(select) {{
        const frequency = select.value;
        const intervalUnit = document.getElementById('intervalUnit');
        const dayOfMonthGroup = document.getElementById('dayOfMonthGroup');
        
        switch(frequency) {{
            case 'daily':
                intervalUnit.textContent = 'Tage';
                dayOfMonthGroup.style.display = 'none';
                break;
            case 'weekly':
                intervalUnit.textContent = 'Wochen';
                dayOfMonthGroup.style.display = 'none';
                break;
            case 'monthly':
                intervalUnit.textContent = 'Monate';
                dayOfMonthGroup.style.display = 'block';
                break;
            case 'yearly':
                intervalUnit.textContent = 'Jahre';
                dayOfMonthGroup.style.display = 'none';
                break;
        }}
    }}
    
    function saveRecurringExpense(event) {{
        event.preventDefault();
        const formData = new FormData(event.target);
        const data = Object.fromEntries(formData);
        
        fetch('/automations/recurring/create', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify(data)
        }})
        .then(response => response.json())
        .then(data => {{
            if (data.success) {{
                location.reload();
            }} else {{
                alert('Fehler: ' + data.message);
            }}
        }});
    }}
    
    function toggleRecurring(id) {{
        fetch(`/automations/recurring/${{id}}/toggle`, {{
            method: 'POST'
        }})
        .then(response => response.json())
        .then(data => {{
            if (data.success) {{
                location.reload();
            }}
        }});
    }}
    
    function deleteRecurring(id) {{
        if (confirm('Wirklich löschen?')) {{
            fetch(`/automations/recurring/${{id}}/delete`, {{
                method: 'DELETE'
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    location.reload();
                }}
            }});
        }}
    }}
    
    function runNow(id) {{
        if (confirm('Ausgabe jetzt erstellen?')) {{
            fetch(`/automations/recurring/${{id}}/run`, {{
                method: 'POST'
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    alert('Ausgabe wurde erstellt!');
                    location.reload();
                }}
            }});
        }}
    }}
    </script>
    """
    
    from app.web.dashboard_modern import render_modern_template
    
    return render_modern_template(
        content=content,
        title='Automatisierungen',
        active_module='automations',
        breadcrumb=[
            {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
            {'text': 'Automatisierungen'}
        ]
    )


def render_recurring_expenses_table(recurring):
    """Rendert die Tabelle der wiederkehrenden Ausgaben"""
    if not recurring:
        return """
        <div class="text-center py-5">
            <i class="bi bi-arrow-repeat text-muted" style="font-size: 3rem;"></i>
            <p class="text-muted mt-3">Keine wiederkehrenden Ausgaben vorhanden</p>
        </div>
        """
    
    rows = ""
    for r in recurring:
        frequency_text = {
            'daily': 'Täglich',
            'weekly': 'Wöchentlich', 
            'monthly': 'Monatlich',
            'yearly': 'Jährlich'
        }.get(r.frequency, r.frequency)
        
        if r.interval > 1:
            frequency_text = f"Alle {r.interval} {frequency_text}"
        
        status_badge = 'success' if r.is_active else 'secondary'
        status_text = 'Aktiv' if r.is_active else 'Pausiert'
        
        rows += f"""
        <tr>
            <td>
                <div class="form-check form-switch">
                    <input class="form-check-input" type="checkbox" 
                           {'checked' if r.is_active else ''}
                           onchange="toggleRecurring({r.id})">
                </div>
            </td>
            <td>
                <strong>{r.name}</strong><br>
                <small class="text-muted">{r.category.value}</small>
            </td>
            <td class="text-danger">-{r.amount:.2f} €</td>
            <td>{frequency_text}</td>
            <td>{r.next_due.strftime('%d.%m.%Y') if r.next_due else '-'}</td>
            <td>
                <span class="badge bg-{status_badge}">{status_text}</span>
            </td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="runNow({r.id})"
                            title="Jetzt ausführen">
                        <i class="bi bi-play-fill"></i>
                    </button>
                    <button class="btn btn-outline-secondary" onclick="editRecurring({r.id})"
                            title="Bearbeiten">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-danger" onclick="deleteRecurring({r.id})"
                            title="Löschen">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
        """
    
    return f"""
    <table class="table table-hover">
        <thead>
            <tr>
                <th width="50">Aktiv</th>
                <th>Name</th>
                <th>Betrag</th>
                <th>Wiederholung</th>
                <th>Nächste Fälligkeit</th>
                <th>Status</th>
                <th width="120">Aktionen</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    """


# API Endpoints
@automations_bp.route('/recurring/create', methods=['POST'])
@login_required
def create_recurring():
    """Neue wiederkehrende Ausgabe erstellen"""
    try:
        data = request.json
        
        recurring = RecurringExpense(
            user_id=current_user.id,
            name=data['name'],
            amount=float(data['amount']),
            category=ExpenseCategory[data['category'].upper()],
            device_id=data.get('device_id') or None,
            frequency=data['frequency'],
            interval=int(data.get('interval', 1)),
            start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date(),
            end_date=datetime.strptime(data['end_date'], '%Y-%m-%d').date() if data.get('end_date') else None,
            day_of_month=int(data.get('day_of_month', 1)) if data['frequency'] == 'monthly' else None
        )
        
        recurring.next_due = recurring.calculate_next_due()
        
        db.session.add(recurring)
        db.session.commit()
        
        return jsonify({'success': True, 'id': recurring.id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@automations_bp.route('/recurring/<int:id>/toggle', methods=['POST'])
@login_required
def toggle_recurring(id):
    """Wiederkehrende Ausgabe aktivieren/deaktivieren"""
    recurring = RecurringExpense.query.get_or_404(id)
    
    if recurring.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Keine Berechtigung'})
    
    recurring.is_active = not recurring.is_active
    if recurring.is_active:
        recurring.next_due = recurring.calculate_next_due()
    else:
        recurring.next_due = None
    
    db.session.commit()
    
    return jsonify({'success': True, 'active': recurring.is_active})


@automations_bp.route('/recurring/<int:id>/delete', methods=['DELETE'])
@login_required
def delete_recurring(id):
    """Wiederkehrende Ausgabe löschen"""
    recurring = RecurringExpense.query.get_or_404(id)
    
    if recurring.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Keine Berechtigung'})
    
    db.session.delete(recurring)
    db.session.commit()
    
    return jsonify({'success': True})


@automations_bp.route('/recurring/<int:id>/run', methods=['POST'])
@login_required
def run_recurring(id):
    """Wiederkehrende Ausgabe manuell ausführen"""
    recurring = RecurringExpense.query.get_or_404(id)
    
    if recurring.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Keine Berechtigung'})
    
    expense = recurring.create_expense()
    
    return jsonify({'success': True, 'expense_id': expense.id})


# Scheduled Task (mit APScheduler oder Celery)
def process_recurring_expenses():
    """Prozessiert alle fälligen wiederkehrenden Ausgaben"""
    today = date.today()
    
    due_expenses = RecurringExpense.query.filter(
        RecurringExpense.is_active == True,
        RecurringExpense.next_due <= today
    ).all()
    
    for recurring in due_expenses:
        try:
            recurring.create_expense()
            print(f"Created expense for: {recurring.name}")
        except Exception as e:
            print(f"Error creating expense for {recurring.name}: {e}")
