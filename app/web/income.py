# app/web/income.py
"""
Einnahmen-Modul für Automaten Manager
Komplett modernisiert mit allen Funktionen
"""

from flask import Blueprint, render_template_string, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import func, extract
from app import db
from app.models import Device, Entry, DeviceStatus, User
import json

income_bp = Blueprint('income', __name__, url_prefix='/income')


@income_bp.route('/')
@login_required
def index():
    """Einnahmen Dashboard"""
    # Zeiträume berechnen
    today = date.today()
    month_start = date(today.year, today.month, 1)
    week_start = today - timedelta(days=today.weekday())
    
    # Statistiken berechnen
    stats = {
        'today': db.session.query(func.sum(Entry.amount)).join(Device).filter(
            Device.owner_id == current_user.id,
            Entry.date == today
        ).scalar() or 0,
        
        'week': db.session.query(func.sum(Entry.amount)).join(Device).filter(
            Device.owner_id == current_user.id,
            Entry.date >= week_start
        ).scalar() or 0,
        
        'month': db.session.query(func.sum(Entry.amount)).join(Device).filter(
            Device.owner_id == current_user.id,
            Entry.date >= month_start
        ).scalar() or 0
    }
    
    # Letzte Einnahmen
    recent_entries = Entry.query.join(Device).filter(
        Device.owner_id == current_user.id
    ).order_by(Entry.date.desc(), Entry.created_at.desc()).limit(10).all()
    
    # Top Geräte diesen Monat
    top_devices = db.session.query(
        Device.name,
        func.sum(Entry.amount).label('total')
    ).join(Entry).filter(
        Device.owner_id == current_user.id,
        Entry.date >= month_start
    ).group_by(Device.id, Device.name).order_by(func.sum(Entry.amount).desc()).limit(5).all()
    
    content = f"""
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="text-white">
            <i class="bi bi-cash-coin"></i> Einnahmen
        </h2>
        <div>
            <a href="{url_for('entries.index')}" class="btn btn-outline-light me-2">
                <i class="bi bi-calendar-week"></i> Wochenansicht
            </a>
            <button class="btn btn-light" data-bs-toggle="modal" data-bs-target="#addIncomeModal">
                <i class="bi bi-plus-circle"></i> Neue Einnahme
            </button>
        </div>
    </div>

    <!-- Statistik-Karten -->
    <div class="row mb-4">
        <div class="col-md-4">
            <div class="card">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="text-muted mb-2">Heute</h6>
                            <h3 class="text-success">{stats['today']:.2f} €</h3>
                        </div>
                        <div class="text-success">
                            <i class="bi bi-calendar-day display-4"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="col-md-4">
            <div class="card">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="text-muted mb-2">Diese Woche</h6>
                            <h3 class="text-info">{stats['week']:.2f} €</h3>
                        </div>
                        <div class="text-info">
                            <i class="bi bi-calendar-week display-4"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="col-md-4">
            <div class="card">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h6 class="text-muted mb-2">Dieser Monat</h6>
                            <h3 class="text-primary">{stats['month']:.2f} €</h3>
                        </div>
                        <div class="text-primary">
                            <i class="bi bi-calendar-month display-4"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="row">
        <!-- Letzte Einnahmen -->
        <div class="col-md-8">
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">
                        <i class="bi bi-clock-history"></i> Letzte Einnahmen
                    </h5>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-hover">
                            <thead>
                                <tr>
                                    <th>Datum</th>
                                    <th>Gerät</th>
                                    <th>Betrag</th>
                                    <th>Beschreibung</th>
                                    <th>Aktionen</th>
                                </tr>
                            </thead>
                            <tbody>
    """
    
    if recent_entries:
        for entry in recent_entries:
            content += f"""
                                <tr>
                                    <td>{entry.date.strftime('%d.%m.%Y')}</td>
                                    <td>
                                        <span class="badge bg-secondary">{entry.device.name if entry.device else 'Allgemein'}</span>
                                    </td>
                                    <td class="text-success fw-bold">+{entry.amount:.2f} €</td>
                                    <td>{entry.description or '-'}</td>
                                    <td>
                                        <button class="btn btn-sm btn-outline-primary" onclick="editEntry({entry.id})">
                                            <i class="bi bi-pencil"></i>
                                        </button>
                                        <button class="btn btn-sm btn-outline-danger" onclick="deleteEntry({entry.id})">
                                            <i class="bi bi-trash"></i>
                                        </button>
                                    </td>
                                </tr>
            """
    else:
        content += """
                                <tr>
                                    <td colspan="5" class="text-center text-muted">Noch keine Einnahmen erfasst</td>
                                </tr>
        """
    
    content += """
                            </tbody>
                        </table>
                    </div>
                    <div class="text-center mt-3">
                        <a href="/income/all" class="btn btn-sm btn-outline-primary">
                            Alle Einnahmen anzeigen <i class="bi bi-arrow-right"></i>
                        </a>
                    </div>
                </div>
            </div>
        </div>

        <!-- Top Geräte -->
        <div class="col-md-4">
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">
                        <i class="bi bi-trophy"></i> Top Geräte (Monat)
                    </h5>
                </div>
                <div class="card-body">
    """
    
    if top_devices:
        for i, device in enumerate(top_devices, 1):
            icon = '🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else f'{i}.'
            percentage = float((device.total / stats['month']) * 100) if stats['month'] > 0 else 0
            content += f"""
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <div>
                            <span class="me-2">{icon}</span>
                            <strong>{device.name}</strong>
                        </div>
                        <div class="text-end">
                            <strong class="text-success">{device.total:.2f} €</strong><br>
                            <small class="text-muted">{percentage:.1f}%</small>
                        </div>
                    </div>
                    <div class="progress mb-3" style="height: 5px;">
                        <div class="progress-bar bg-success" style="width: {percentage}%"></div>
                    </div>
            """
    else:
        content += '<p class="text-muted text-center">Keine Daten vorhanden</p>'
    
    content += """
                </div>
            </div>

            <!-- Quick Stats -->
            <div class="card mt-3">
                <div class="card-header">
                    <h5 class="mb-0">
                        <i class="bi bi-graph-up"></i> Schnellstatistik
                    </h5>
                </div>
                <div class="card-body">
                    <div class="mb-3">
                        <small class="text-muted">Durchschnitt/Tag (30 Tage)</small>
                        <h4 class="text-info">
    """
    
    # Durchschnitt berechnen
    thirty_days_ago = today - timedelta(days=30)
    avg_daily = db.session.query(func.avg(Entry.amount)).join(Device).filter(
        Device.owner_id == current_user.id,
        Entry.date >= thirty_days_ago
    ).scalar() or 0
    
    content += f"""{avg_daily:.2f} €</h4>
                    </div>
                    <div class="mb-3">
                        <small class="text-muted">Aktive Geräte</small>
                        <h4 class="text-primary">
    """
    
    active_devices = Device.query.filter_by(
        owner_id=current_user.id,
        status=DeviceStatus.ACTIVE
    ).count()
    
    content += f"""{active_devices}</h4>
                    </div>
                    <div>
                        <small class="text-muted">Beste Tageseinnahme (30 Tage)</small>
                        <h4 class="text-success">
    """
    
    best_day = db.session.query(
        Entry.date,
        func.sum(Entry.amount).label('total')
    ).join(Device).filter(
        Device.owner_id == current_user.id,
        Entry.date >= thirty_days_ago
    ).group_by(Entry.date).order_by(func.sum(Entry.amount).desc()).first()
    
    if best_day:
        content += f"""{best_day.total:.2f} €</h4>
                        <small class="text-muted">{best_day.date.strftime('%d.%m.%Y')}</small>
        """
    else:
        content += "0.00 €</h4>"
    
    content += """
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Modal für neue Einnahme -->
    <div class="modal fade" id="addIncomeModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Neue Einnahme erfassen</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <form method="POST" action="/income/add">
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label">Gerät *</label>
                            <select name="device_id" class="form-select" required>
                                <option value="">-- Wählen --</option>
    """
    
    # Geräte für Dropdown
    devices = Device.query.filter_by(owner_id=current_user.id).order_by(Device.name).all()
    for device in devices:
        status_icon = '🟢' if device.status == DeviceStatus.ACTIVE else '🟡' if device.status == DeviceStatus.MAINTENANCE else '🔴'
        content += f'<option value="{device.id}">{status_icon} {device.name} - {device.location or "Kein Standort"}</option>'
    
    content += f"""
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Betrag (€) *</label>
                            <input type="number" name="amount" class="form-control" step="0.01" required placeholder="0.00">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Datum *</label>
                            <input type="date" name="date" class="form-control" value="{today}" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Beschreibung</label>
                            <textarea name="description" class="form-control" rows="2" placeholder="Optional"></textarea>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Abbrechen</button>
                        <button type="submit" class="btn btn-success">
                            <i class="bi bi-save"></i> Speichern
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
    """
    
    extra_scripts = """
    <script>
    function editEntry(id) {
        // TODO: Implementiere Bearbeiten-Funktion
        alert('Bearbeiten-Funktion kommt bald!');
    }
    
    function deleteEntry(id) {
        if (confirm('Einnahme wirklich löschen?')) {
            fetch(`/income/delete/${id}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                if (response.ok) {
                    location.reload();
                } else {
                    alert('Fehler beim Löschen!');
                }
            });
        }
    }
    </script>
    """
    
    extra_css = """
    <style>
        .card {
            transition: transform 0.2s;
        }
        .card:hover {
            transform: translateY(-2px);
        }
        .progress {
            background-color: #e9ecef;
        }
        .table-hover tbody tr:hover {
            background-color: rgba(0, 123, 255, 0.05);
        }
    </style>
    """
    
    from app.web.dashboard_modern import render_modern_template
    
    # Kombiniere Content, Scripts und CSS
    full_content = content
    if extra_css:
        full_content = f'<style>{extra_css}</style>' + full_content
    if extra_scripts:
        full_content = full_content + f'<script>{extra_scripts}</script>'
    
    return render_modern_template(
        content=full_content,
        title='Einnahmen',
        active_module='income',
        active_submodule='overview',
        breadcrumb=[
            {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
            {'text': 'Einnahmen'}
        ]
    )


@income_bp.route('/add', methods=['POST'])
@login_required
def add_income():
    """Neue Einnahme hinzufügen"""
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
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler: {str(e)}', 'danger')
    
    return redirect(url_for('income.index'))


@income_bp.route('/delete/<int:entry_id>', methods=['POST'])
@login_required
def delete_income(entry_id):
    """Einnahme löschen"""
    try:
        entry = Entry.query.join(Device).filter(
            Entry.id == entry_id,
            Device.owner_id == current_user.id
        ).first_or_404()
        
        db.session.delete(entry)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@income_bp.route('/all')
@login_required
def all_income():
    """Alle Einnahmen anzeigen"""
    # Filter-Parameter
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    # Alle Einnahmen mit Pagination
    entries = Entry.query.join(Device).filter(
        Device.owner_id == current_user.id
    ).order_by(Entry.date.desc(), Entry.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    content = f"""
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="text-white">
            <i class="bi bi-list-ul"></i> Alle Einnahmen
        </h2>
        <a href="{url_for('income.index')}" class="btn btn-light">
            <i class="bi bi-arrow-left"></i> Zurück zur Übersicht
        </a>
    </div>

    <div class="card">
        <div class="card-body">
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>Datum</th>
                            <th>Gerät</th>
                            <th>Betrag</th>
                            <th>Beschreibung</th>
                            <th>Aktionen</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    for entry in entries.items:
        content += f"""
                        <tr>
                            <td>{entry.date.strftime('%d.%m.%Y')}</td>
                            <td>{entry.device.name if entry.device else 'Allgemein'}</td>
                            <td class="text-success fw-bold">+{entry.amount:.2f} €</td>
                            <td>{entry.description or '-'}</td>
                            <td>
                                <button class="btn btn-sm btn-outline-danger" onclick="deleteEntry({entry.id})">
                                    <i class="bi bi-trash"></i>
                                </button>
                            </td>
                        </tr>
        """
    
    content += """
                    </tbody>
                </table>
            </div>
    """
    
    # Pagination
    if entries.pages > 1:
        content += '<nav><ul class="pagination justify-content-center">'
        for num in entries.iter_pages(left_edge=1, right_edge=1, left_current=1, right_current=2):
            if num:
                if num != entries.page:
                    content += f'<li class="page-item"><a class="page-link" href="?page={num}">{num}</a></li>'
                else:
                    content += f'<li class="page-item active"><span class="page-link">{num}</span></li>'
            else:
                content += '<li class="page-item disabled"><span class="page-link">...</span></li>'
        content += '</ul></nav>'
    
    content += """
        </div>
    </div>
    """
    
    extra_scripts = """
    <script>
    function deleteEntry(id) {
        if (confirm('Einnahme wirklich löschen?')) {
            fetch(`/income/delete/${id}`, {
                method: 'POST'
            }).then(() => location.reload());
        }
    }
    </script>
    """
    
    from app.web.dashboard_modern import render_modern_template
    
    # Kombiniere Content und Scripts
    full_content = content
    if extra_scripts:
        full_content = full_content + f'<script>{extra_scripts}</script>'
    
    return render_modern_template(
        content=full_content,
        title='Alle Einnahmen',
        active_module='income',
        active_submodule='all',
        breadcrumb=[
            {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
            {'text': 'Einnahmen', 'url': url_for('income.index')},
            {'text': 'Alle Einnahmen'}
        ]
    )
