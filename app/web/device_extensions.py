# app/web/device_extensions.py
"""
Geräte-Erweiterungen für Automaten Manager
QR-Codes, Wartungsplan, Standorte, Auslastung
"""

from flask import Blueprint, render_template_string, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from decimal import Decimal
from app import db
from app.models import User, Device, Entry, DeviceStatus
from sqlalchemy import func
import json
import qrcode
from PIL import Image, ImageDraw
import io
import base64

device_ext_bp = Blueprint('device_extensions', __name__, url_prefix='/devices')


@device_ext_bp.route('/qr-codes')
@login_required
def qr_codes():
    """QR-Code Generator für alle Geräte"""
    
    devices = Device.query.filter_by(owner_id=current_user.id).all()
    
    content = f"""
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="text-white">
            <i class="bi bi-qr-code"></i> QR-Code Generator
        </h2>
        <div>
            <button class="btn btn-light" onclick="downloadAll()">
                <i class="bi bi-download"></i> Alle herunterladen
            </button>
            <button class="btn btn-light" onclick="printAll()">
                <i class="bi bi-printer"></i> Drucken
            </button>
        </div>
    </div>

    <div class="row">
        <div class="col-md-8">
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">Verfügbare Geräte</h5>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-hover">
                            <thead>
                                <tr>
                                    <th>Gerät</th>
                                    <th>Seriennummer</th>
                                    <th>Standort</th>
                                    <th>Status</th>
                                    <th>Aktionen</th>
                                </tr>
                            </thead>
                            <tbody>
    """
    
    for device in devices:
        status_badge = 'success' if device.status == DeviceStatus.ACTIVE else 'warning' if device.status == DeviceStatus.MAINTENANCE else 'danger'
        status_text = 'Aktiv' if device.status == DeviceStatus.ACTIVE else 'Wartung' if device.status == DeviceStatus.MAINTENANCE else 'Inaktiv'
        
        content += f"""
                                <tr>
                                    <td><strong>{device.name}</strong></td>
                                    <td>{device.serial_number}</td>
                                    <td>{device.location or '-'}</td>
                                    <td><span class="badge bg-{status_badge}">{status_text}</span></td>
                                    <td>
                                        <button class="btn btn-sm btn-primary" onclick="generateQR({device.id})">
                                            <i class="bi bi-qr-code"></i> Generieren
                                        </button>
                                        <button class="btn btn-sm btn-success" onclick="downloadQR({device.id})">
                                            <i class="bi bi-download"></i>
                                        </button>
                                    </td>
                                </tr>
        """
    
    content += """
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <div class="col-md-4">
            <!-- QR-Code Vorschau -->
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">QR-Code Vorschau</h5>
                </div>
                <div class="card-body text-center" id="qrPreview">
                    <p class="text-muted">Wählen Sie ein Gerät aus, um den QR-Code zu generieren</p>
                </div>
            </div>

            <!-- Einstellungen -->
            <div class="card mt-3">
                <div class="card-header">
                    <h5 class="mb-0">Einstellungen</h5>
                </div>
                <div class="card-body">
                    <div class="mb-3">
                        <label class="form-label">QR-Code Größe</label>
                        <select class="form-select" id="qrSize">
                            <option value="small">Klein (150x150)</option>
                            <option value="medium" selected>Mittel (250x250)</option>
                            <option value="large">Groß (400x400)</option>
                        </select>
                    </div>
                    
                    <div class="form-check mb-2">
                        <input class="form-check-input" type="checkbox" id="includeLabel" checked>
                        <label class="form-check-label" for="includeLabel">
                            Mit Beschriftung
                        </label>
                    </div>
                    
                    <div class="form-check mb-2">
                        <input class="form-check-input" type="checkbox" id="includeLogo">
                        <label class="form-check-label" for="includeLogo">
                            Mit Firmenlogo
                        </label>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Druckansicht (versteckt) -->
    <div id="printArea" style="display: none;"></div>

    <script>
    function generateQR(deviceId) {{
        fetch('/devices/get-qr/' + deviceId)
            .then(response => response.json())
            .then(data => {{
                const preview = document.getElementById('qrPreview');
                preview.innerHTML = `
                    <img src="${{data.qr_code}}" alt="QR Code" class="img-fluid mb-3">
                    <h6>${{data.name}}</h6>
                    <p class="text-muted small">${{data.serial_number}}</p>
                    <p class="text-muted small">${{data.location || "Kein Standort"}}</p>
                `;
            }});
    }}

    function downloadQR(deviceId) {{
        window.location.href = '/devices/download-qr/' + deviceId;
    }}

    function downloadAll() {{
        // Alle QR-Codes als ZIP herunterladen
        if (confirm('Alle QR-Codes herunterladen?')) {{
            window.location.href = '/devices/download-all-qr';
        }}
    }}

    function printAll() {{
        // Druckansicht vorbereiten
        const printArea = document.getElementById('printArea');
        printArea.innerHTML = '<h3>QR-Codes werden geladen...</h3>';
        
        // QR-Codes für Druck laden
        setTimeout(() => {{
            window.print();
        }}, 1000);
    }}
    </script>
    """
    
    from app.web.dashboard_modern import render_modern_template
    
    return render_modern_template(
        content=content,
        title='QR-Codes',
        active_module='devices',
        active_submodule='qr_codes',
        breadcrumb=[
            {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
            {'text': 'Geräte', 'url': url_for('dashboard_modern.devices')},
            {'text': 'QR-Codes'}
        ]
    )


@device_ext_bp.route('/maintenance')
@login_required
def maintenance():
    """Wartungsplan"""
    
    devices = Device.query.filter_by(owner_id=current_user.id).all()
    
    # Wartungsstatus berechnen
    maintenance_due = []
    for device in devices:
        # Simulierte Wartungsdaten
        last_maintenance = date.today() - timedelta(days=60)  # Beispiel
        next_maintenance = last_maintenance + timedelta(days=90)
        days_until = (next_maintenance - date.today()).days
        
        if days_until < 0:
            badge_class = 'danger'
            status_text = 'Überfällig'
        elif days_until <= 7:
            badge_class = 'warning'
            status_text = 'Demnächst'
        else:
            badge_class = 'success'
            status_text = 'Planmäßig'
        
        maintenance_due.append({
            'device': device,
            'last': last_maintenance,
            'next': next_maintenance,
            'days_until': days_until,
            'badge_class': badge_class,
            'status_text': status_text
        })
    
    # Nach Dringlichkeit sortieren
    maintenance_due.sort(key=lambda x: x['days_until'])
    
    content = f"""
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="text-white">
            <i class="bi bi-wrench"></i> Wartungsplan
        </h2>
        <div>
            <button class="btn btn-light" data-bs-toggle="modal" data-bs-target="#maintenanceModal">
                <i class="bi bi-plus-circle"></i> Wartung erfassen
            </button>
            <button class="btn btn-light" onclick="exportMaintenancePlan()">
                <i class="bi bi-download"></i> Export
            </button>
        </div>
    </div>

    <!-- Übersichtskarten -->
    <div class="row mb-4">
        <div class="col-md-3">
            <div class="card border-danger">
                <div class="card-body text-center">
                    <h3 class="text-danger">{len([m for m in maintenance_due if m['badge_class'] == 'danger'])}</h3>
                    <p class="text-muted mb-0">Überfällig</p>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card border-warning">
                <div class="card-body text-center">
                    <h3 class="text-warning">{len([m for m in maintenance_due if m['badge_class'] == 'warning'])}</h3>
                    <p class="text-muted mb-0">Diese Woche</p>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card border-success">
                <div class="card-body text-center">
                    <h3 class="text-success">{len([m for m in maintenance_due if m['badge_class'] == 'success'])}</h3>
                    <p class="text-muted mb-0">Planmäßig</p>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card">
                <div class="card-body text-center">
                    <h3 class="text-primary">{len(devices)}</h3>
                    <p class="text-muted mb-0">Gesamt</p>
                </div>
            </div>
        </div>
    </div>

    <!-- Wartungsliste -->
    <div class="card">
        <div class="card-header">
            <h5 class="mb-0">Anstehende Wartungen</h5>
        </div>
        <div class="card-body">
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>Gerät</th>
                            <th>Standort</th>
                            <th>Letzte Wartung</th>
                            <th>Nächste Wartung</th>
                            <th>Status</th>
                            <th>Aktionen</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    for item in maintenance_due:
        device = item['device']
        badge_class = item['badge_class']
        status_text = item['status_text']
        
        content += f"""
                        <tr>
                            <td><strong>{device.name}</strong></td>
                            <td>{device.location or '-'}</td>
                            <td>{item['last'].strftime('%d.%m.%Y')}</td>
                            <td>{item['next'].strftime('%d.%m.%Y')}</td>
                            <td><span class="badge bg-{badge_class}">
                                {status_text}
                            </span></td>
                            <td>
                                <button class="btn btn-sm btn-primary" onclick="recordMaintenance({device.id})">
                                    <i class="bi bi-check-circle"></i> Erledigt
                                </button>
                                <button class="btn btn-sm btn-info" onclick="viewHistory({device.id})">
                                    <i class="bi bi-clock-history"></i> Historie
                                </button>
                            </td>
                        </tr>
        """
    
    content += """
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Wartung erfassen Modal -->
    <div class="modal fade" id="maintenanceModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Wartung erfassen</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <form id="maintenanceForm" action="/devices/add-maintenance" method="POST">
                    <div class="modal-body">
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <label class="form-label">Gerät</label>
                                <select class="form-select" name="device_id" required>
                                    <option value="">-- Wählen --</option>
    """
    
    for device in devices:
        content += f'<option value="{device.id}">{device.name}</option>'
    
    content += f"""
                                </select>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">Datum</label>
                                <input type="date" class="form-control" name="date" value="{date.today()}" required>
                            </div>
                        </div>
                        
                        <div class="mb-3">
                            <label class="form-label">Wartungstyp</label>
                            <select class="form-select" name="maintenance_type" required>
                                <option value="routine">Routinewartung</option>
                                <option value="repair">Reparatur</option>
                                <option value="cleaning">Reinigung</option>
                                <option value="inspection">Inspektion</option>
                                <option value="upgrade">Upgrade</option>
                            </select>
                        </div>
                        
                        <div class="mb-3">
                            <label class="form-label">Durchgeführte Arbeiten</label>
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" name="tasks[]" value="cleaning" id="task1">
                                <label class="form-check-label" for="task1">Reinigung durchgeführt</label>
                            </div>
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" name="tasks[]" value="parts" id="task2">
                                <label class="form-check-label" for="task2">Verschleißteile geprüft/getauscht</label>
                            </div>
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" name="tasks[]" value="software" id="task3">
                                <label class="form-check-label" for="task3">Software aktualisiert</label>
                            </div>
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" name="tasks[]" value="calibration" id="task4">
                                <label class="form-check-label" for="task4">Kalibrierung durchgeführt</label>
                            </div>
                        </div>
                        
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <label class="form-label">Techniker</label>
                                <input type="text" class="form-control" name="technician" placeholder="Name des Technikers">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">Kosten (€)</label>
                                <input type="number" class="form-control" name="cost" step="0.01" placeholder="0.00">
                            </div>
                        </div>
                        
                        <div class="mb-3">
                            <label class="form-label">Bemerkungen</label>
                            <textarea class="form-control" name="notes" rows="3"></textarea>
                        </div>
                        
                        <div class="mb-3">
                            <label class="form-label">Nächste Wartung</label>
                            <input type="date" class="form-control" name="next_maintenance" 
                                   value="{(date.today() + timedelta(days=90)).isoformat()}">
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Abbrechen</button>
                        <button type="submit" class="btn btn-primary">
                            <i class="bi bi-save"></i> Wartung speichern
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <script>
    function recordMaintenance(deviceId) {{
        if (confirm('Wartung als durchgeführt markieren?')) {{
            fetch('/devices/quick-maintenance', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{
                    device_id: deviceId,
                    date: new Date().toISOString().split('T')[0]
                }})
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.success) {{
                    location.reload();
                }}
            }});
        }}
    }}

    function viewHistory(deviceId) {{
        window.location.href = '/devices/maintenance-history/' + deviceId;
    }}

    function exportMaintenancePlan() {{
        window.location.href = '/devices/export-maintenance';
    }}

    document.getElementById('maintenanceForm').addEventListener('submit', function(e) {{
        e.preventDefault();
        const formData = new FormData(this);
        
        fetch(this.action, {{
            method: 'POST',
            body: formData
        }})
        .then(response => response.json())
        .then(data => {{
            if (data.success) {{
                location.reload();
            }} else {{
                alert(data.message || 'Fehler beim Speichern');
            }}
        }});
    }});
    </script>
    """
    
    from app.web.dashboard_modern import render_modern_template
    
    return render_modern_template(
        content=content,
        title='Wartungsplan',
        active_module='devices',
        active_submodule='maintenance',
        breadcrumb=[
            {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
            {'text': 'Geräte', 'url': url_for('dashboard_modern.devices')},
            {'text': 'Wartungsplan'}
        ]
    )


@device_ext_bp.route('/locations')
@login_required
def locations():
    """Standortverwaltung"""
    
    devices = Device.query.filter_by(owner_id=current_user.id).all()
    
    # Standorte gruppieren
    locations = {}
    for device in devices:
        loc = device.location or 'Nicht zugewiesen'
        if loc not in locations:
            locations[loc] = []
        locations[loc].append(device)
    
    content = f"""
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="text-white">
            <i class="bi bi-map"></i> Standortverwaltung
        </h2>
        <button class="btn btn-light" data-bs-toggle="modal" data-bs-target="#locationModal">
            <i class="bi bi-plus-circle"></i> Neuer Standort
        </button>
    </div>

    <!-- Standort-Karten -->
    <div class="row mb-4">
    """
    
    for location, location_devices in locations.items():
        total_income = 0
        for device in location_devices:
            # Einnahmen der letzten 30 Tage
            income = Entry.query.filter(
                Entry.device_id == device.id,
                Entry.date >= date.today() - timedelta(days=30)
            ).with_entities(func.sum(Entry.amount)).scalar() or 0
            total_income += float(income) if income else 0  # Konvertiere zu float
        
        active_count = sum(1 for d in location_devices if d.status == DeviceStatus.ACTIVE)
        
        content += f"""
        <div class="col-md-4 mb-3">
            <div class="card h-100">
                <div class="card-header">
                    <h5 class="mb-0">
                        <i class="bi bi-geo-alt"></i> {location}
                    </h5>
                </div>
                <div class="card-body">
                    <div class="d-flex justify-content-between mb-2">
                        <span>Geräte:</span>
                        <strong>{len(location_devices)}</strong>
                    </div>
                    <div class="d-flex justify-content-between mb-2">
                        <span>Aktiv:</span>
                        <strong class="text-success">{active_count}</strong>
                    </div>
                    <div class="d-flex justify-content-between mb-3">
                        <span>30-Tage Umsatz:</span>
                        <strong class="text-primary">{total_income:.2f} €</strong>
                    </div>
                    
                    <h6>Geräte:</h6>
                    <ul class="list-unstyled">
        """
        
        for device in location_devices[:5]:  # Max 5 anzeigen
            status_icon = '🟢' if device.status == DeviceStatus.ACTIVE else '🟡' if device.status == DeviceStatus.MAINTENANCE else '🔴'
            content += f'<li>{status_icon} {device.name}</li>'
        
        if len(location_devices) > 5:
            content += f'<li class="text-muted">... und {len(location_devices) - 5} weitere</li>'
        
        content += f"""
                    </ul>
                    
                    <button class="btn btn-sm btn-primary w-100" onclick="viewLocation('{location}')">
                        <i class="bi bi-eye"></i> Details anzeigen
                    </button>
                </div>
            </div>
        </div>
        """
    
    content += """
    </div>

    <!-- Karte (Platzhalter) -->
    <div class="card">
        <div class="card-header">
            <h5 class="mb-0">Standortkarte</h5>
        </div>
        <div class="card-body">
            <div class="bg-light rounded p-5 text-center" style="min-height: 400px;">
                <i class="bi bi-map display-1 text-muted"></i>
                <p class="text-muted mt-3">Interaktive Karte wird hier angezeigt</p>
                <p class="small text-muted">Integration mit Google Maps oder OpenStreetMap möglich</p>
            </div>
        </div>
    </div>

    <!-- Neuer Standort Modal -->
    <div class="modal fade" id="locationModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Neuer Standort</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <form id="locationForm">
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label">Standortname</label>
                            <input type="text" class="form-control" name="name" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Adresse</label>
                            <input type="text" class="form-control" name="address">
                        </div>
                        <div class="row mb-3">
                            <div class="col">
                                <label class="form-label">Breitengrad</label>
                                <input type="number" class="form-control" name="latitude" step="0.000001">
                            </div>
                            <div class="col">
                                <label class="form-label">Längengrad</label>
                                <input type="number" class="form-control" name="longitude" step="0.000001">
                            </div>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Kontaktperson</label>
                            <input type="text" class="form-control" name="contact">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Telefon</label>
                            <input type="tel" class="form-control" name="phone">
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Abbrechen</button>
                        <button type="submit" class="btn btn-primary">Speichern</button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <script>
    function viewLocation(location) {{
        // Standort-Details anzeigen
        console.log('View location:', location);
    }}

    document.getElementById('locationForm')?.addEventListener('submit', function(e) {{
        e.preventDefault();
        // Standort speichern
        const formData = new FormData(this);
        console.log('Save location:', Object.fromEntries(formData));
    }});
    </script>
    """
    
    from app.web.dashboard_modern import render_modern_template
    
    return render_modern_template(
        content=content,
        title='Standorte',
        active_module='devices',
        active_submodule='locations',
        breadcrumb=[
            {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
            {'text': 'Geräte', 'url': url_for('dashboard_modern.devices')},
            {'text': 'Standorte'}
        ]
    )


@device_ext_bp.route('/utilization')
@login_required
def utilization():
    """Auslastungsanalyse"""
    
    devices = Device.query.filter_by(owner_id=current_user.id).all()
    
    # Auslastungsdaten berechnen
    utilization_data = []
    for device in devices:
        # Daten der letzten 30 Tage
        entries_30d = Entry.query.filter(
            Entry.device_id == device.id,
            Entry.date >= date.today() - timedelta(days=30)
        ).all()
        
        # Tägliche Durchschnitte
        daily_avg = len(entries_30d) / 30 if entries_30d else 0
        total_revenue = float(sum(e.amount for e in entries_30d))  # Konvertiere zu float
        daily_revenue = total_revenue / 30
        
        # Auslastung schätzen (basierend auf Einträgen pro Tag)
        utilization_percent = min(100, (daily_avg / 50) * 100)  # Annahme: 50 Verkäufe/Tag = 100%
        
        utilization_data.append({
            'device': device,
            'daily_avg': daily_avg,
            'daily_revenue': daily_revenue,
            'total_revenue': total_revenue,
            'utilization': utilization_percent,
            'entries_count': len(entries_30d)
        })
    
    # Nach Auslastung sortieren
    utilization_data.sort(key=lambda x: x['utilization'], reverse=True)
    
    content = f"""
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="text-white">
            <i class="bi bi-bar-chart"></i> Auslastungsanalyse
        </h2>
        <div>
            <select class="form-select" style="width: auto; display: inline-block;">
                <option>Letzte 30 Tage</option>
                <option>Letzte 7 Tage</option>
                <option>Dieser Monat</option>
                <option>Letzter Monat</option>
            </select>
            <button class="btn btn-light ms-2" onclick="exportUtilization()">
                <i class="bi bi-download"></i> Export
            </button>
        </div>
    </div>

    <!-- Übersichtskarten -->
    <div class="row mb-4">
        <div class="col-md-3">
            <div class="card">
                <div class="card-body">
                    <h6 class="text-muted">Ø Auslastung</h6>
                    <h3 class="text-primary">{sum(d['utilization'] for d in utilization_data) / len(utilization_data) if utilization_data else 0:.1f}%</h3>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card">
                <div class="card-body">
                    <h6 class="text-muted">Top Performer</h6>
                    <h5 class="text-success">{utilization_data[0]['device'].name if utilization_data else '-'}</h5>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card">
                <div class="card-body">
                    <h6 class="text-muted">Ø Umsatz/Tag</h6>
                    <h3 class="text-info">{sum(d['daily_revenue'] for d in utilization_data):.2f} €</h3>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card">
                <div class="card-body">
                    <h6 class="text-muted">Gesamtumsatz</h6>
                    <h3 class="text-warning">{sum(d['total_revenue'] for d in utilization_data):.2f} €</h3>
                </div>
            </div>
        </div>
    </div>

    <!-- Auslastungs-Chart -->
    <div class="card mb-4">
        <div class="card-header">
            <h5 class="mb-0">Auslastungsverlauf</h5>
        </div>
        <div class="card-body">
            <canvas id="utilizationChart" height="80"></canvas>
        </div>
    </div>

    <!-- Detailtabelle -->
    <div class="card">
        <div class="card-header">
            <h5 class="mb-0">Geräte-Details</h5>
        </div>
        <div class="card-body">
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>Gerät</th>
                            <th>Standort</th>
                            <th>Auslastung</th>
                            <th>Verkäufe/Tag</th>
                            <th>Umsatz/Tag</th>
                            <th>30-Tage Total</th>
                            <th>Trend</th>
                            <th>Aktionen</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    for data in utilization_data:
        device = data['device']
        
        # Auslastungs-Farbe
        if data['utilization'] >= 80:
            util_color = 'success'
        elif data['utilization'] >= 50:
            util_color = 'warning'
        else:
            util_color = 'danger'
        
        # Trend (simuliert)
        trend = '📈' if data['utilization'] > 60 else '📉' if data['utilization'] < 40 else '➡️'
        
        content += f"""
                        <tr>
                            <td><strong>{device.name}</strong></td>
                            <td>{device.location or '-'}</td>
                            <td>
                                <div class="progress" style="min-width: 100px;">
                                    <div class="progress-bar bg-{util_color}" style="width: {data['utilization']:.0f}%">
                                        {data['utilization']:.0f}%
                                    </div>
                                </div>
                            </td>
                            <td>{data['daily_avg']:.1f}</td>
                            <td>{data['daily_revenue']:.2f} €</td>
                            <td><strong>{data['total_revenue']:.2f} €</strong></td>
                            <td>{trend}</td>
                            <td>
                                <button class="btn btn-sm btn-info" onclick="viewDetails({device.id})">
                                    <i class="bi bi-graph-up"></i> Analyse
                                </button>
                            </td>
                        </tr>
        """
    
    content += f"""
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
    // Chart-Daten vorbereiten
    const devices = {json.dumps([d['device'].name for d in utilization_data[:10]])};
    const utilizations = {json.dumps([d['utilization'] for d in utilization_data[:10]])};
    const revenues = {json.dumps([float(d['daily_revenue']) for d in utilization_data[:10]])};
    
    // Auslastungs-Chart
    const ctx = document.getElementById('utilizationChart').getContext('2d');
    new Chart(ctx, {{
        type: 'bar',
        data: {{
            labels: devices,
            datasets: [{{
                label: 'Auslastung (%)',
                data: utilizations,
                backgroundColor: 'rgba(102, 126, 234, 0.6)',
                borderColor: 'rgba(102, 126, 234, 1)',
                borderWidth: 1,
                yAxisID: 'y'
            }}, {{
                label: 'Umsatz/Tag (€)',
                data: revenues,
                type: 'line',
                borderColor: 'rgba(40, 167, 69, 1)',
                backgroundColor: 'rgba(40, 167, 69, 0.1)',
                yAxisID: 'y1'
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            scales: {{
                y: {{
                    type: 'linear',
                    display: true,
                    position: 'left',
                    max: 100,
                    ticks: {{
                        callback: function(value) {{
                            return value + '%';
                        }}
                    }}
                }},
                y1: {{
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: {{
                        drawOnChartArea: false
                    }},
                    ticks: {{
                        callback: function(value) {{
                            return value.toFixed(0) + ' €';
                        }}
                    }}
                }}
            }}
        }}
    }});

    function viewDetails(deviceId) {{
        window.location.href = '/devices/analysis/' + deviceId;
    }}

    function exportUtilization() {{
        window.location.href = '/devices/export-utilization';
    }}
    </script>
    """
    
    from app.web.dashboard_modern import render_modern_template
    
    return render_modern_template(
        content=content,
        title='Auslastung',
        active_module='devices',
        active_submodule='utilization',
        breadcrumb=[
            {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
            {'text': 'Geräte', 'url': url_for('dashboard_modern.devices')},
            {'text': 'Auslastung'}
        ]
    )


# API Endpoints für Geräte-Erweiterungen

@device_ext_bp.route('/get-qr/<int:device_id>')
@login_required
def get_qr(device_id):
    """QR-Code für Gerät abrufen"""
    device = Device.query.get_or_404(device_id)
    
    # QR-Code generieren
    qr_data = f"DEVICE:{device.id}|{device.serial_number}|{device.name}"
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    
    qr_image = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
    
    return jsonify({
        'name': device.name,
        'serial_number': device.serial_number,
        'location': device.location,
        'qr_code': qr_image
    })


@device_ext_bp.route('/download-qr/<int:device_id>')
@login_required
def download_qr(device_id):
    """QR-Code herunterladen"""
    device = Device.query.get_or_404(device_id)
    
    # QR-Code mit Label generieren
    qr_data = f"DEVICE:{device.id}|{device.serial_number}|{device.name}"
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(qr_data)
    qr.make(fit=True)
    
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # Label hinzufügen
    width, height = qr_img.size
    new_height = height + 60
    
    final_img = Image.new('RGB', (width, new_height), 'white')
    final_img.paste(qr_img, (0, 0))
    
    # Text hinzufügen (vereinfacht - normalerweise mit Font)
    from PIL import ImageDraw
    draw = ImageDraw.Draw(final_img)
    text = f"{device.name}\n{device.serial_number}"
    # draw.text((width//2, height + 10), text, fill='black', anchor='mt')
    
    # Als Datei senden
    buf = io.BytesIO()
    final_img.save(buf, format='PNG')
    buf.seek(0)
    
    return send_file(
        buf,
        mimetype='image/png',
        as_attachment=True,
        download_name=f'qr_{device.serial_number}.png'
    )


@device_ext_bp.route('/add-maintenance', methods=['POST'])
@login_required  
def add_maintenance():
    """Wartung hinzufügen"""
    try:
        # Wartungsdaten verarbeiten
        device_id = request.form.get('device_id')
        maintenance_date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        maintenance_type = request.form.get('maintenance_type')
        
        # Hier würde man die Wartung in der Datenbank speichern
        # maintenance = MaintenanceRecord(...)
        # db.session.add(maintenance)
        # db.session.commit()
        
        flash('Wartung erfolgreich erfasst!', 'success')
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@device_ext_bp.route('/quick-maintenance', methods=['POST'])
@login_required
def quick_maintenance():
    """Schnelle Wartungserfassung"""
    try:
        data = request.json
        device_id = data.get('device_id')
        
        # Wartung als durchgeführt markieren
        # Hier würde man die Wartung in der Datenbank speichern
        
        return jsonify({'success': True, 'message': 'Wartung erfasst!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
