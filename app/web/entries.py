# app/web/entries.py
"""
Erweiterte Einnahmen-Erfassung mit Wochenansicht
Mit zentraler Navigation
"""

from flask import Blueprint, render_template_string, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from decimal import Decimal
from app import db
from app.models import Device, Entry, DeviceStatus
import json

# NEU: Import der zentralen Navigation
from app.web.navigation import render_with_base_new as render_with_base

entries_bp = Blueprint('entries', __name__, url_prefix='/entries')


def get_week_dates(week_offset=0):
    """Gibt Start- und Enddatum der Woche zurück"""
    today = date.today()
    week_start = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


@entries_bp.route('/')
@login_required
def index():
    """Wochenansicht der Einnahmen"""
    # Aktuelle Woche
    week_offset = int(request.args.get('week', 0))
    week_start, week_end = get_week_dates(week_offset)

    # Geräte des Users
    devices = Device.query.filter_by(
        owner_id=current_user.id,
        status=DeviceStatus.ACTIVE
    ).order_by(Device.name).all()

    # Einnahmen der Woche laden
    entries = Entry.query.join(Device).filter(
        Device.owner_id == current_user.id,
        Entry.date >= week_start,
        Entry.date <= week_end
    ).all()

    # Einnahmen in Dictionary organisieren {device_id: {date: amount}}
    entries_dict = {}
    for entry in entries:
        if entry.device_id not in entries_dict:
            entries_dict[entry.device_id] = {}
        entries_dict[entry.device_id][entry.date.isoformat()] = float(entry.amount)

    # Wochentage generieren
    weekdays = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        weekdays.append({
            'date': day,
            'name': ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'][i],
            'is_today': day == date.today(),
            'is_weekend': i >= 5
        })

    # Zusätzliche CSS für Wochenansicht
    extra_css = """
    <style>
        /* Wochenansicht Styles */
        .week-view-table {
            background: white;
            border-radius: 15px;
            overflow: hidden;
        }
        .week-view-table th {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            font-weight: 600;
            text-align: center;
            padding: 12px;
        }
        .week-view-table td {
            padding: 8px;
            vertical-align: middle;
        }
        .revenue-input {
            width: 100px;
            text-align: right;
            border: 1px solid #dee2e6;
            border-radius: 8px;
            padding: 6px 10px;
            transition: all 0.3s;
        }
        .revenue-input:focus {
            border-color: #667eea;
            box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
            transform: scale(1.05);
        }
        .revenue-input.has-value {
            background-color: #e8f5e9;
            border-color: #4caf50;
            font-weight: 600;
        }
        .day-header {
            font-size: 0.875rem;
            color: #6c757d;
        }
        .today-column {
            background-color: #f0f4ff;
        }
        .weekend-column {
            background-color: #fff3e0;
        }
        .device-row:hover {
            background-color: #f8f9fa;
        }
        .total-row {
            background: linear-gradient(90deg, #f8f9fa, #e9ecef);
            font-weight: bold;
        }
        .total-cell {
            font-size: 1.1rem;
            color: #28a745;
        }
        .quick-actions {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 1000;
        }
        .device-status {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 5px;
        }
        .status-active { background-color: #28a745; }
        .status-maintenance { background-color: #ffc107; }
        .status-inactive { background-color: #6c757d; }

        /* Animation */
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        .btn-save {
            animation: pulse 2s infinite;
        }

        /* Summary Cards */
        .summary-card {
            transition: transform 0.3s;
        }
        .summary-card:hover {
            transform: translateY(-5px);
        }
    </style>
    """

    # JavaScript für Interaktivität
    extra_scripts = f"""
    <script>
    // Einnahmen-Daten
    let entriesData = {json.dumps(entries_dict)};
    let hasChanges = false;
    let deviceNames = {{}};

    // Gerätenamen speichern
    {' '.join([f"deviceNames[{device.id}] = '{device.name}';" for device in devices])}

    // Input Change Handler
    function updateEntry(deviceId, date, input) {{
        const value = parseFloat(input.value) || 0;

        // Update data
        if (!entriesData[deviceId]) entriesData[deviceId] = {{}};
        entriesData[deviceId][date] = value;

        // Visual feedback
        if (value > 0) {{
            input.classList.add('has-value');
        }} else {{
            input.classList.remove('has-value');
        }}

        // Update totals
        updateTotals();
        hasChanges = true;

        // Enable save button
        document.getElementById('saveButton').disabled = false;
        document.getElementById('saveButton').classList.add('btn-save');
    }}

    // Berechne Summen
    function updateTotals() {{
        // Tages-Summen
        {' '.join([f'''
        let day{i}Total = 0;
        document.querySelectorAll('.day-{i}').forEach(input => {{
            day{i}Total += parseFloat(input.value) || 0;
        }});
        document.getElementById('day-{i}-total').textContent = day{i}Total.toFixed(2) + ' €';
        ''' for i in range(7)])}

        // Geräte-Summen und bestes Gerät ermitteln
        let bestDevice = '';
        let bestAmount = 0;

        document.querySelectorAll('[data-device-id]').forEach(row => {{
            const deviceId = row.dataset.deviceId;
            let deviceTotal = 0;
            row.querySelectorAll('input').forEach(input => {{
                deviceTotal += parseFloat(input.value) || 0;
            }});
            document.getElementById('device-' + deviceId + '-total').textContent = deviceTotal.toFixed(2) + ' €';

            // Bestes Gerät ermitteln
            if (deviceTotal > bestAmount) {{
                bestAmount = deviceTotal;
                bestDevice = deviceNames[deviceId] || 'Gerät ' + deviceId;
            }}
        }});

        // Gesamt-Summe
        let grandTotal = 0;
        document.querySelectorAll('.revenue-input').forEach(input => {{
            grandTotal += parseFloat(input.value) || 0;
        }});
        document.getElementById('grand-total').textContent = grandTotal.toFixed(2) + ' €';
        document.getElementById('grand-total-2').textContent = grandTotal.toFixed(2) + ' €';

        // Durchschnitt berechnen
        let dailyAvg = grandTotal / 7;
        document.getElementById('daily-avg').textContent = dailyAvg.toFixed(2) + ' €';

        // Bestes Gerät anzeigen
        document.getElementById('best-device').textContent = bestDevice || '-';
    }}

    // Enter-Taste Navigation
    document.addEventListener('keydown', function(e) {{
        if (e.key === 'Enter' && e.target.classList.contains('revenue-input')) {{
            e.preventDefault();
            const inputs = Array.from(document.querySelectorAll('.revenue-input'));
            const currentIndex = inputs.indexOf(e.target);
            if (currentIndex < inputs.length - 1) {{
                inputs[currentIndex + 1].focus();
                inputs[currentIndex + 1].select();
            }}
        }}
    }});

    // Speichern
    async function saveEntries() {{
        document.getElementById('saveButton').disabled = true;
        document.getElementById('saveButton').innerHTML = '<span class="spinner-border spinner-border-sm"></span> Speichert...';

        try {{
            const response = await fetch('/entries/save-week', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{
                    week_start: '{week_start.isoformat()}',
                    entries: entriesData
                }})
            }});

            const result = await response.json();
            if (result.success) {{
                // Success message
                showAlert('success', 'Einnahmen wurden gespeichert!');
                hasChanges = false;
                document.getElementById('saveButton').classList.remove('btn-save');
                document.getElementById('saveButton').innerHTML = '<i class="bi bi-check-circle"></i> Gespeichert';

                // Reload after 1 second
                setTimeout(() => location.reload(), 1000);
            }} else {{
                showAlert('danger', 'Fehler beim Speichern: ' + result.message);
                document.getElementById('saveButton').disabled = false;
                document.getElementById('saveButton').innerHTML = '<i class="bi bi-save"></i> Speichern';
            }}
        }} catch (error) {{
            showAlert('danger', 'Netzwerkfehler: ' + error);
            document.getElementById('saveButton').disabled = false;
            document.getElementById('saveButton').innerHTML = '<i class="bi bi-save"></i> Speichern';
        }}
    }}

    // Letzte Woche kopieren
    async function copyLastWeek() {{
        if (!confirm('Möchten Sie die Werte der letzten Woche übernehmen?')) return;

        try {{
            const response = await fetch('/entries/copy-last-week?week_offset={week_offset}');
            const data = await response.json();

            // Fill inputs with last week's data
            Object.keys(data).forEach(deviceId => {{
                Object.keys(data[deviceId]).forEach(dayOffset => {{
                    const input = document.querySelector(`input[data-device-id="${{deviceId}}"][data-day="${{dayOffset}}"]`);
                    if (input) {{
                        input.value = data[deviceId][dayOffset];
                        input.classList.add('has-value');
                    }}
                }});
            }});

            updateTotals();
            hasChanges = true;
            document.getElementById('saveButton').disabled = false;
            showAlert('info', 'Werte der letzten Woche wurden übernommen');
        }} catch (error) {{
            showAlert('danger', 'Fehler beim Laden der letzten Woche');
        }}
    }}

    // Alert anzeigen
    function showAlert(type, message) {{
        const alertHtml = `
            <div class="alert alert-${{type}} alert-dismissible fade show" role="alert">
                ${{message}}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        document.getElementById('alerts').innerHTML = alertHtml;
    }}

    // Tab Navigation
    function switchTab(tab) {{
        // Update buttons
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        event.target.classList.add('active');

        // Show/hide content
        document.querySelectorAll('.tab-content').forEach(content => content.style.display = 'none');
        document.getElementById(tab).style.display = 'block';
    }}

    // Beim Verlassen warnen
    window.addEventListener('beforeunload', function (e) {{
        if (hasChanges) {{
            e.preventDefault();
            e.returnValue = '';
        }}
    }});

    // Initial totals
    document.addEventListener('DOMContentLoaded', updateTotals);
    </script>
    """

    # HTML Content
    content = f"""
    <div id="alerts"></div>

    <!-- Header -->
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="text-white">
            <i class="bi bi-calendar-week"></i> Wochenerfassung
        </h2>
        <div class="btn-group">
            <a href="?week={week_offset - 1}" class="btn btn-light">
                <i class="bi bi-chevron-left"></i> Vorherige
            </a>
            <button class="btn btn-light" disabled>
                KW {week_start.isocalendar()[1]} 
                ({week_start.strftime('%d.%m.')} - {week_end.strftime('%d.%m.%Y')})
            </button>
            <a href="?week={week_offset + 1}" class="btn btn-light">
                Nächste <i class="bi bi-chevron-right"></i>
            </a>
        </div>
    </div>

    <!-- Summary Cards -->
    <div class="row mb-4">
        <div class="col-md-3">
            <div class="card summary-card">
                <div class="card-body text-center">
                    <h6 class="text-muted">Wochensumme</h6>
                    <h3 id="grand-total-2" class="text-success">0.00 €</h3>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card summary-card">
                <div class="card-body text-center">
                    <h6 class="text-muted">Durchschnitt/Tag</h6>
                    <h3 id="daily-avg" class="text-info">0.00 €</h3>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card summary-card">
                <div class="card-body text-center">
                    <h6 class="text-muted">Bestes Gerät</h6>
                    <h3 id="best-device" class="text-primary" style="font-size: 1.2rem;">-</h3>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card summary-card">
                <div class="card-body text-center">
                    <h6 class="text-muted">Aktive Geräte</h6>
                    <h3 class="text-secondary">{len(devices)}</h3>
                </div>
            </div>
        </div>
    </div>

    <!-- Tabs -->
    <div class="card mb-4">
        <div class="card-header">
            <div class="btn-group" role="group">
                <button class="btn btn-outline-primary tab-btn active" onclick="switchTab('week-view')">
                    <i class="bi bi-table"></i> Wochenansicht
                </button>
                <button class="btn btn-outline-primary tab-btn" onclick="switchTab('quick-entry')">
                    <i class="bi bi-lightning"></i> Schnelleingabe
                </button>
            </div>
        </div>
        <div class="card-body p-0">
            <!-- Wochenansicht Tab -->
            <div id="week-view" class="tab-content">
                <div class="table-responsive">
                    <table class="table table-hover week-view-table mb-0">
                        <thead>
                            <tr>
                                <th style="width: 200px;">Gerät</th>
    """

    # Spalten-Header für jeden Tag
    for i, day in enumerate(weekdays):
        classes = 'today-column' if day['is_today'] else 'weekend-column' if day['is_weekend'] else ''
        content += f"""
                                <th class="{classes}">
                                    {day['name']}<br>
                                    <span class="day-header">{day['date'].strftime('%d.%m.')}</span>
                                </th>
        """

    content += """
                                <th style="width: 120px;">Summe</th>
                            </tr>
                        </thead>
                        <tbody>
    """

    # Zeile für jedes Gerät
    for device in devices:
        content += f"""
                            <tr class="device-row" data-device-id="{device.id}">
                                <td>
                                    <span class="device-status status-{device.status.value}"></span>
                                    <strong>{device.name}</strong>
                                    <br>
                                    <small class="text-muted">{device.location or 'Kein Standort'}</small>
                                </td>
        """

        # Input für jeden Tag
        for i, day in enumerate(weekdays):
            value = entries_dict.get(device.id, {}).get(day['date'].isoformat(), '')
            has_value_class = 'has-value' if value else ''
            classes = 'today-column' if day['is_today'] else 'weekend-column' if day['is_weekend'] else ''

            content += f"""
                                <td class="{classes}">
                                    <input type="number" 
                                           class="form-control revenue-input day-{i} {has_value_class}"
                                           data-device-id="{device.id}"
                                           data-day="{i}"
                                           value="{value}"
                                           step="0.01"
                                           placeholder="0.00"
                                           onchange="updateEntry({device.id}, '{day['date'].isoformat()}', this)">
                                </td>
            """

        content += f"""
                                <td class="text-end">
                                    <strong id="device-{device.id}-total">0.00 €</strong>
                                </td>
                            </tr>
        """

    # Summen-Zeile
    content += """
                            <tr class="total-row">
                                <td><strong>GESAMT</strong></td>
    """

    for i in range(7):
        content += f'<td class="text-center total-cell" id="day-{i}-total">0.00 €</td>'

    content += """
                                <td class="text-end total-cell" id="grand-total">0.00 €</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Schnelleingabe Tab -->
            <div id="quick-entry" class="tab-content" style="display: none;">
                <div class="p-4">
                    <h5>Schnelleingabe für heute</h5>
                    <p class="text-muted">Geben Sie die heutigen Einnahmen schnell ein:</p>
                    <div class="row">
    """

    # Schnelleingabe für heute
    for device in devices:
        content += f"""
                        <div class="col-md-6 mb-3">
                            <div class="input-group">
                                <span class="input-group-text">{device.name}</span>
                                <input type="number" class="form-control" step="0.01" placeholder="0.00">
                                <span class="input-group-text">€</span>
                            </div>
                        </div>
        """

    content += """
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Action Buttons -->
    <div class="d-flex justify-content-between mb-4">
        <div>
            <button class="btn btn-secondary" onclick="copyLastWeek()">
                <i class="bi bi-clipboard"></i> Letzte Woche kopieren
            </button>
            <button class="btn btn-warning" onclick="if(confirm('Alle Eingaben löschen?')) location.reload()">
                <i class="bi bi-arrow-clockwise"></i> Neu laden
            </button>
        </div>
        <button id="saveButton" class="btn btn-success btn-lg" onclick="saveEntries()" disabled>
            <i class="bi bi-save"></i> Speichern
        </button>
    </div>

    <!-- Quick Actions (Floating) -->
    <div class="quick-actions">
        <a href="/entries/add" class="btn btn-primary btn-lg rounded-circle" title="Einzelne Einnahme">
            <i class="bi bi-plus"></i>
        </a>
    </div>
    """

    # VERWENDE DIE ZENTRALE NAVIGATION!
    return render_template_string(
        render_with_base(
            content,
            active_page='entries',  # Markiert "Einnahmen" als aktiv
            title='Einnahmen - Automaten Manager',
            extra_css=extra_css,
            extra_scripts=extra_scripts
        )
    )


@entries_bp.route('/save-week', methods=['POST'])
@login_required
def save_week():
    """Speichert alle Einnahmen einer Woche"""
    try:
        data = request.get_json()
        week_start = datetime.strptime(data['week_start'], '%Y-%m-%d').date()
        entries_data = data['entries']

        # Lösche existierende Einträge korrekt
        week_end = week_start + timedelta(days=6)

        # Erst die Einträge finden
        existing_entries = Entry.query.join(Device).filter(
            Device.owner_id == current_user.id,
            Entry.date >= week_start,
            Entry.date <= week_end
        ).all()

        # Dann einzeln löschen
        for entry in existing_entries:
            db.session.delete(entry)

        # Neue Einträge erstellen
        for device_id, dates in entries_data.items():
            # Prüfen ob das Gerät dem User gehört
            device = Device.query.filter_by(
                id=int(device_id),
                owner_id=current_user.id
            ).first()

            if device:  # Nur wenn Gerät existiert und dem User gehört
                for date_str, amount in dates.items():
                    if amount > 0:  # Nur speichern wenn Betrag > 0
                        entry = Entry(
                            device_id=int(device_id),
                            amount=Decimal(str(amount)),
                            date=datetime.strptime(date_str, '%Y-%m-%d').date(),
                            user_id=current_user.id,
                            description='Wochenerfassung'
                        )
                        db.session.add(entry)

        db.session.commit()
        return jsonify({'success': True, 'message': 'Einnahmen gespeichert'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@entries_bp.route('/copy-last-week')
@login_required
def copy_last_week():
    """Kopiert die Einnahmen der vorherigen Woche"""
    week_offset = int(request.args.get('week_offset', 0))

    # Letzte Woche berechnen
    last_week_start, last_week_end = get_week_dates(week_offset - 1)

    # Einnahmen der letzten Woche laden
    entries = Entry.query.join(Device).filter(
        Device.owner_id == current_user.id,
        Entry.date >= last_week_start,
        Entry.date <= last_week_end
    ).all()

    # In Format für Frontend konvertieren (device_id -> day_offset -> amount)
    result = {}
    for entry in entries:
        day_offset = (entry.date - last_week_start).days
        if entry.device_id not in result:
            result[entry.device_id] = {}
        result[entry.device_id][day_offset] = float(entry.amount)

    return jsonify(result)


@entries_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_single():
    """Einzelne Einnahme hinzufügen (Original-Route)"""
    from app.web import add_entry
    return add_entry()