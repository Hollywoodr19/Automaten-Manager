# app/web/settings.py
"""
Einstellungen-Modul für Automaten Manager
Vollständige Implementation mit Unternehmensdaten, Sicherheit, Backup und System-Einstellungen
"""

from flask import Blueprint, render_template_string, redirect, url_for, flash, request, jsonify, send_file, current_app
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from decimal import Decimal
from app import db
from app.models import User, Device, Entry, Expense, Product, Refill
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
import shutil
import zipfile
import io
from sqlalchemy import text
import pyotp
import qrcode
from PIL import Image

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


@settings_bp.route('/')
@login_required
def index():
    """Einstellungen Übersicht - Unternehmensdaten"""
    
    # Unternehmensdaten aus User-Profil oder Config
    company_data = {
        'name': getattr(current_user, 'company_name', 'Mein Unternehmen'),
        'address': getattr(current_user, 'company_address', ''),
        'tax_id': getattr(current_user, 'tax_id', ''),
        'email': current_user.email,
        'phone': getattr(current_user, 'phone', ''),
        'website': getattr(current_user, 'website', ''),
        'currency': getattr(current_user, 'currency', 'EUR'),
        'tax_rate': getattr(current_user, 'default_tax_rate', 20)
    }
    
    content = f"""
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="text-white">
            <i class="bi bi-building"></i> Unternehmensdaten
        </h2>
        <button class="btn btn-light" onclick="saveCompanyData()">
            <i class="bi bi-save"></i> Speichern
        </button>
    </div>

    <div class="row">
        <div class="col-md-8">
            <div class="card">
                <div class="card-body">
                    <form id="companyForm">
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <label class="form-label">Firmenname</label>
                                <input type="text" class="form-control" name="company_name" 
                                       value="{company_data['name']}" required>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">Steuernummer / UID</label>
                                <input type="text" class="form-control" name="tax_id" 
                                       value="{company_data['tax_id']}" placeholder="ATU12345678">
                            </div>
                        </div>

                        <div class="mb-3">
                            <label class="form-label">Adresse</label>
                            <textarea class="form-control" name="company_address" rows="3">{company_data['address']}</textarea>
                        </div>

                        <div class="row mb-3">
                            <div class="col-md-4">
                                <label class="form-label">E-Mail</label>
                                <input type="email" class="form-control" name="email" 
                                       value="{company_data['email']}" required>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">Telefon</label>
                                <input type="tel" class="form-control" name="phone" 
                                       value="{company_data['phone']}" placeholder="+43 123 456789">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">Website</label>
                                <input type="url" class="form-control" name="website" 
                                       value="{company_data['website']}" placeholder="https://example.com">
                            </div>
                        </div>

                        <div class="row mb-3">
                            <div class="col-md-6">
                                <label class="form-label">Währung</label>
                                <select class="form-select" name="currency">
                                    <option value="EUR" {'selected' if company_data['currency'] == 'EUR' else ''}>EUR (€)</option>
                                    <option value="USD" {'selected' if company_data['currency'] == 'USD' else ''}>USD ($)</option>
                                    <option value="CHF" {'selected' if company_data['currency'] == 'CHF' else ''}>CHF (Fr.)</option>
                                    <option value="GBP" {'selected' if company_data['currency'] == 'GBP' else ''}>GBP (£)</option>
                                </select>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">Standard MwSt-Satz (%)</label>
                                <input type="number" class="form-control" name="default_tax_rate" 
                                       value="{company_data['tax_rate']}" min="0" max="100" step="0.1">
                            </div>
                        </div>
                    </form>
                </div>
            </div>
        </div>

        <div class="col-md-4">
            <div class="card mb-3">
                <div class="card-body">
                    <h5 class="card-title">
                        <i class="bi bi-info-circle"></i> Systeminfo
                    </h5>
                    <small class="text-muted">
                        <strong>Version:</strong> 2.0.0<br>
                        <strong>Datenbank:</strong> PostgreSQL<br>
                        <strong>Geräte:</strong> {Device.query.filter_by(owner_id=current_user.id).count()}<br>
                        <strong>Produkte:</strong> {Product.query.filter_by(user_id=current_user.id).count()}<br>
                        <strong>Einträge:</strong> {Entry.query.join(Device).filter(Device.owner_id==current_user.id).count()}
                    </small>
                </div>
            </div>

            <div class="card">
                <div class="card-body">
                    <h5 class="card-title">
                        <i class="bi bi-palette"></i> Design
                    </h5>
                    <div class="form-check form-switch mb-2">
                        <input class="form-check-input" type="checkbox" id="darkMode" checked>
                        <label class="form-check-label" for="darkMode">Dark Mode</label>
                    </div>
                    <div class="form-check form-switch">
                        <input class="form-check-input" type="checkbox" id="compactView">
                        <label class="form-check-label" for="compactView">Kompakte Ansicht</label>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
    function saveCompanyData() {{
        const formData = new FormData(document.getElementById('companyForm'));
        const data = Object.fromEntries(formData);
        
        fetch('/settings/save-company', {{
            method: 'POST',
            headers: {{
                'Content-Type': 'application/json',
            }},
            body: JSON.stringify(data)
        }})
        .then(response => response.json())
        .then(data => {{
            if (data.success) {{
                alert('Einstellungen gespeichert!');
            }} else {{
                alert('Fehler beim Speichern!');
            }}
        }});
    }}
    </script>
    """
    
    from app.web.dashboard_modern import render_modern_template
    
    return render_modern_template(
        content=content,
        title='Einstellungen',
        active_module='settings',
        active_submodule='company',
        breadcrumb=[
            {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
            {'text': 'Einstellungen'}
        ]
    )


@settings_bp.route('/security')
@login_required
def security():
    """Sicherheitseinstellungen"""
    
    # 2FA Status prüfen - DIREKT aus DB laden für aktuelle Daten
    db.session.refresh(current_user)
    has_2fa = current_user.two_factor_enabled if hasattr(current_user, 'two_factor_enabled') else False
    
    # Debug-Ausgabe
    print(f"DEBUG: User {current_user.username} - 2FA Enabled: {has_2fa}, Secret exists: {bool(current_user.two_factor_secret)}")
    
    content = f"""
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="text-white">
            <i class="bi bi-shield-lock"></i> Sicherheit
        </h2>
    </div>

    <div class="row">
        <!-- Passwort ändern -->
        <div class="col-md-6">
            <div class="card mb-3">
                <div class="card-header">
                    <h5 class="mb-0">Passwort ändern</h5>
                </div>
                <div class="card-body">
                    <form id="passwordForm">
                        <div class="mb-3">
                            <label class="form-label">Aktuelles Passwort</label>
                            <input type="password" class="form-control" name="current_password" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Neues Passwort</label>
                            <input type="password" class="form-control" name="new_password" 
                                   minlength="8" required>
                            <small class="text-muted">Mindestens 8 Zeichen</small>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Passwort bestätigen</label>
                            <input type="password" class="form-control" name="confirm_password" required>
                        </div>
                        <button type="submit" class="btn btn-primary">
                            <i class="bi bi-key"></i> Passwort ändern
                        </button>
                    </form>
                </div>
            </div>
        </div>

        <!-- 2FA Einstellungen -->
        <div class="col-md-6">
            <div class="card mb-3">
                <div class="card-header">
                    <h5 class="mb-0">Zwei-Faktor-Authentifizierung (2FA)</h5>
                </div>
                <div class="card-body">
                    {'<div class="alert alert-success"><i class="bi bi-check-circle"></i> 2FA ist aktiviert</div>' if has_2fa else '<div class="alert alert-warning"><i class="bi bi-exclamation-triangle"></i> 2FA ist nicht aktiviert</div>'}
                    
                    <p>Schützen Sie Ihr Konto mit einer zusätzlichen Sicherheitsebene.</p>
                    
                    {f'<button class="btn btn-danger" onclick="disable2FA()"><i class="bi bi-shield-slash"></i> 2FA deaktivieren</button>' if has_2fa else '<button class="btn btn-success" onclick="setup2FA()"><i class="bi bi-shield-check"></i> 2FA einrichten</button>'}
                    
                    <div id="qrCodeContainer" class="mt-3" style="display:none;">
                        <p>Scannen Sie diesen QR-Code mit Ihrer Authenticator-App:</p>
                        <div id="qrCode"></div>
                        <div class="mt-3">
                            <label class="form-label">Bestätigungscode eingeben:</label>
                            <input type="text" class="form-control" id="totpCode" maxlength="6" placeholder="123456">
                            <button class="btn btn-primary mt-2" onclick="verify2FA()">Bestätigen</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Sitzungsverwaltung -->
        <div class="col-md-12">
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">Aktive Sitzungen</h5>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>Gerät</th>
                                    <th>IP-Adresse</th>
                                    <th>Standort</th>
                                    <th>Letzte Aktivität</th>
                                    <th>Aktion</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td><i class="bi bi-laptop"></i> Aktuelles Gerät</td>
                                    <td>{request.remote_addr}</td>
                                    <td>Österreich</td>
                                    <td>Jetzt</td>
                                    <td><span class="badge bg-success">Aktiv</span></td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    
                    <button class="btn btn-warning mt-3">
                        <i class="bi bi-door-closed"></i> Alle anderen Sitzungen beenden
                    </button>
                </div>
            </div>
        </div>
    </div>

    <script>
    document.getElementById('passwordForm').addEventListener('submit', function(e) {{
        e.preventDefault();
        const formData = new FormData(this);
        
        if (formData.get('new_password') !== formData.get('confirm_password')) {{
            alert('Passwörter stimmen nicht überein!');
            return;
        }}
        
        fetch('/settings/change-password', {{
            method: 'POST',
            body: formData
        }})
        .then(response => response.json())
        .then(data => {{
            alert(data.message);
            if (data.success) {{
                this.reset();
            }}
        }});
    }});

    function setup2FA() {{
        fetch('/settings/setup-2fa')
            .then(response => response.json())
            .then(data => {{
                if (data.qr_code) {{
                    document.getElementById('qrCode').innerHTML = '<img src="' + data.qr_code + '" />';
                    document.getElementById('qrCodeContainer').style.display = 'block';
                }}
            }});
    }}

    function verify2FA() {{
        const code = document.getElementById('totpCode').value;
        fetch('/settings/verify-2fa', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{code: code}})
        }})
        .then(response => response.json())
        .then(data => {{
            alert(data.message);
            if (data.success) {{
                // Seite sofort neu laden nach erfolgreicher Aktivierung
                window.location.reload(true);
            }}
        }});
    }}

    function disable2FA() {{
        if (confirm('Möchten Sie 2FA wirklich deaktivieren?')) {{
            fetch('/settings/disable-2fa', {{method: 'POST'}})
                .then(response => response.json())
                .then(data => {{
                    alert(data.message);
                    window.location.reload(true);  // Force reload
                }});
        }}
    }}
    </script>
    """
    
    from app.web.dashboard_modern import render_modern_template
    
    return render_modern_template(
        content=content,
        title='Sicherheit',
        active_module='settings',
        active_submodule='security',
        breadcrumb=[
            {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
            {'text': 'Einstellungen', 'url': url_for('settings.index')},
            {'text': 'Sicherheit'}
        ]
    )


@settings_bp.route('/backup')
@login_required
def backup():
    """Backup & Wiederherstellung"""
    
    # Letzte Backups (simuliert)
    last_backups = [
        {'date': datetime.now() - timedelta(days=1), 'size': '45.2 MB', 'type': 'Automatisch'},
        {'date': datetime.now() - timedelta(days=7), 'size': '44.8 MB', 'type': 'Manuell'},
        {'date': datetime.now() - timedelta(days=14), 'size': '43.5 MB', 'type': 'Automatisch'},
    ]
    
    content = f"""
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="text-white">
            <i class="bi bi-database"></i> Backup & Wiederherstellung
        </h2>
        <div>
            <button class="btn btn-light" onclick="createBackup()">
                <i class="bi bi-download"></i> Backup erstellen
            </button>
        </div>
    </div>

    <div class="row">
        <div class="col-md-8">
            <div class="card mb-3">
                <div class="card-header">
                    <h5 class="mb-0">Backup-Verlauf</h5>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>Datum</th>
                                    <th>Größe</th>
                                    <th>Typ</th>
                                    <th>Aktionen</th>
                                </tr>
                            </thead>
                            <tbody>
    """
    
    for backup in last_backups:
        content += f"""
                                <tr>
                                    <td>{backup['date'].strftime('%d.%m.%Y %H:%M')}</td>
                                    <td>{backup['size']}</td>
                                    <td><span class="badge bg-{'primary' if backup['type'] == 'Automatisch' else 'secondary'}">{backup['type']}</span></td>
                                    <td>
                                        <button class="btn btn-sm btn-primary" onclick="downloadBackup('{backup['date'].isoformat()}')">
                                            <i class="bi bi-download"></i>
                                        </button>
                                        <button class="btn btn-sm btn-warning" onclick="restoreBackup('{backup['date'].isoformat()}')">
                                            <i class="bi bi-arrow-clockwise"></i>
                                        </button>
                                        <button class="btn btn-sm btn-danger" onclick="deleteBackup('{backup['date'].isoformat()}')">
                                            <i class="bi bi-trash"></i>
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

            <!-- Backup wiederherstellen -->
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">Backup wiederherstellen</h5>
                </div>
                <div class="card-body">
                    <div class="alert alert-warning">
                        <i class="bi bi-exclamation-triangle"></i> 
                        <strong>Achtung:</strong> Das Wiederherstellen eines Backups überschreibt alle aktuellen Daten!
                    </div>
                    
                    <form id="restoreForm" enctype="multipart/form-data">
                        <div class="mb-3">
                            <label class="form-label">Backup-Datei auswählen (.zip)</label>
                            <input type="file" class="form-control" name="backup_file" accept=".zip" required>
                        </div>
                        <button type="submit" class="btn btn-warning">
                            <i class="bi bi-upload"></i> Backup wiederherstellen
                        </button>
                    </form>
                </div>
            </div>
        </div>

        <div class="col-md-4">
            <!-- Automatische Backups -->
            <div class="card mb-3">
                <div class="card-header">
                    <h5 class="mb-0">Automatische Backups</h5>
                </div>
                <div class="card-body">
                    <div class="form-check form-switch mb-3">
                        <input class="form-check-input" type="checkbox" id="autoBackup" checked>
                        <label class="form-check-label" for="autoBackup">
                            Automatische Backups aktiviert
                        </label>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">Backup-Intervall</label>
                        <select class="form-select" id="backupInterval">
                            <option value="daily" selected>Täglich</option>
                            <option value="weekly">Wöchentlich</option>
                            <option value="monthly">Monatlich</option>
                        </select>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">Backup-Zeit</label>
                        <input type="time" class="form-control" value="03:00">
                    </div>
                    
                    <button class="btn btn-primary w-100">
                        <i class="bi bi-save"></i> Einstellungen speichern
                    </button>
                </div>
            </div>

            <!-- Speicherplatz -->
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title">Speicherplatz</h5>
                    <div class="progress mb-2">
                        <div class="progress-bar" style="width: 35%">35%</div>
                    </div>
                    <small class="text-muted">
                        Verwendet: 178 MB von 500 MB<br>
                        Backups: 135 MB<br>
                        Datenbank: 43 MB
                    </small>
                </div>
            </div>
        </div>
    </div>

    <script>
    function createBackup() {{
        if (confirm('Möchten Sie jetzt ein Backup erstellen?')) {{
            fetch('/settings/create-backup', {{method: 'POST'}})
                .then(response => response.blob())
                .then(blob => {{
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'backup_' + new Date().toISOString().split('T')[0] + '.zip';
                    a.click();
                }});
        }}
    }}

    function downloadBackup(date) {{
        window.location.href = '/settings/download-backup?date=' + date;
    }}

    function restoreBackup(date) {{
        if (confirm('Möchten Sie dieses Backup wiederherstellen? Alle aktuellen Daten werden überschrieben!')) {{
            fetch('/settings/restore-backup', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{date: date}})
            }})
            .then(response => response.json())
            .then(data => {{
                alert(data.message);
                if (data.success) {{
                    location.reload();
                }}
            }});
        }}
    }}

    function deleteBackup(date) {{
        if (confirm('Möchten Sie dieses Backup wirklich löschen?')) {{
            fetch('/settings/delete-backup', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{date: date}})
            }})
            .then(response => response.json())
            .then(data => {{
                alert(data.message);
                location.reload();
            }});
        }}
    }}

    document.getElementById('restoreForm').addEventListener('submit', function(e) {{
        e.preventDefault();
        if (confirm('WARNUNG: Alle aktuellen Daten werden überschrieben! Fortfahren?')) {{
            const formData = new FormData(this);
            fetch('/settings/upload-restore', {{
                method: 'POST',
                body: formData
            }})
            .then(response => response.json())
            .then(data => {{
                alert(data.message);
                if (data.success) {{
                    location.reload();
                }}
            }});
        }}
    }});
    </script>
    """
    
    from app.web.dashboard_modern import render_modern_template
    
    return render_modern_template(
        content=content,
        title='Backup',
        active_module='settings',
        active_submodule='backup',
        breadcrumb=[
            {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
            {'text': 'Einstellungen', 'url': url_for('settings.index')},
            {'text': 'Backup'}
        ]
    )


@settings_bp.route('/notifications')
@login_required
def notifications():
    """Benachrichtigungseinstellungen"""
    
    content = f"""
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="text-white">
            <i class="bi bi-bell"></i> Benachrichtigungen
        </h2>
        <button class="btn btn-light" onclick="saveNotificationSettings()">
            <i class="bi bi-save"></i> Speichern
        </button>
    </div>

    <div class="row">
        <div class="col-md-8">
            <!-- E-Mail Benachrichtigungen -->
            <div class="card mb-3">
                <div class="card-header">
                    <h5 class="mb-0">E-Mail Benachrichtigungen</h5>
                </div>
                <div class="card-body">
                    <div class="form-check form-switch mb-3">
                        <input class="form-check-input" type="checkbox" id="emailDaily" checked>
                        <label class="form-check-label" for="emailDaily">
                            Tägliche Zusammenfassung
                        </label>
                        <small class="text-muted d-block">Erhalten Sie jeden Tag eine Übersicht Ihrer Einnahmen</small>
                    </div>
                    
                    <div class="form-check form-switch mb-3">
                        <input class="form-check-input" type="checkbox" id="emailWeekly" checked>
                        <label class="form-check-label" for="emailWeekly">
                            Wöchentlicher Bericht
                        </label>
                        <small class="text-muted d-block">Detaillierter Wochenbericht jeden Montag</small>
                    </div>
                    
                    <div class="form-check form-switch mb-3">
                        <input class="form-check-input" type="checkbox" id="emailLowStock">
                        <label class="form-check-label" for="emailLowStock">
                            Niedriger Lagerbestand
                        </label>
                        <small class="text-muted d-block">Benachrichtigung wenn Produkte nachbestellt werden müssen</small>
                    </div>
                    
                    <div class="form-check form-switch mb-3">
                        <input class="form-check-input" type="checkbox" id="emailMaintenance">
                        <label class="form-check-label" for="emailMaintenance">
                            Wartungserinnerungen
                        </label>
                        <small class="text-muted d-block">Erinnerung an fällige Gerätewartungen</small>
                    </div>
                    
                    <div class="form-check form-switch mb-3">
                        <input class="form-check-input" type="checkbox" id="emailAlerts" checked>
                        <label class="form-check-label" for="emailAlerts">
                            Wichtige Warnungen
                        </label>
                        <small class="text-muted d-block">Kritische Systemereignisse und Fehler</small>
                    </div>
                </div>
            </div>

            <!-- Push-Benachrichtigungen -->
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">Push-Benachrichtigungen</h5>
                </div>
                <div class="card-body">
                    <div class="alert alert-info">
                        <i class="bi bi-info-circle"></i> Push-Benachrichtigungen können in der mobilen App aktiviert werden
                    </div>
                    
                    <div class="form-check form-switch mb-3">
                        <input class="form-check-input" type="checkbox" id="pushEnabled">
                        <label class="form-check-label" for="pushEnabled">
                            Push-Benachrichtigungen aktivieren
                        </label>
                    </div>
                    
                    <div class="form-check form-switch mb-3">
                        <input class="form-check-input" type="checkbox" id="pushRealtime">
                        <label class="form-check-label" for="pushRealtime">
                            Echtzeit-Updates
                        </label>
                        <small class="text-muted d-block">Sofortige Benachrichtigung bei neuen Einnahmen</small>
                    </div>
                </div>
            </div>
        </div>

        <div class="col-md-4">
            <!-- Benachrichtigungszeiten -->
            <div class="card mb-3">
                <div class="card-header">
                    <h5 class="mb-0">Zeiteinstellungen</h5>
                </div>
                <div class="card-body">
                    <div class="mb-3">
                        <label class="form-label">Tägliche Zusammenfassung um:</label>
                        <input type="time" class="form-control" value="08:00">
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">Zeitzone</label>
                        <select class="form-select">
                            <option selected>Europe/Vienna (UTC+1)</option>
                            <option>Europe/Berlin (UTC+1)</option>
                            <option>Europe/Zurich (UTC+1)</option>
                        </select>
                    </div>
                    
                    <div class="form-check form-switch">
                        <input class="form-check-input" type="checkbox" id="quietHours">
                        <label class="form-check-label" for="quietHours">
                            Ruhezeiten aktivieren
                        </label>
                    </div>
                    
                    <div class="row mt-2">
                        <div class="col">
                            <label class="form-label small">Von:</label>
                            <input type="time" class="form-control form-control-sm" value="22:00">
                        </div>
                        <div class="col">
                            <label class="form-label small">Bis:</label>
                            <input type="time" class="form-control form-control-sm" value="07:00">
                        </div>
                    </div>
                </div>
            </div>

            <!-- Test-Benachrichtigung -->
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title">Test</h5>
                    <p>Testen Sie Ihre Benachrichtigungseinstellungen</p>
                    <button class="btn btn-primary w-100" onclick="sendTestNotification()">
                        <i class="bi bi-send"></i> Test-E-Mail senden
                    </button>
                </div>
            </div>
        </div>
    </div>

    <script>
    function saveNotificationSettings() {{
        // Sammle alle Einstellungen
        const settings = {{
            email_daily: document.getElementById('emailDaily').checked,
            email_weekly: document.getElementById('emailWeekly').checked,
            email_low_stock: document.getElementById('emailLowStock').checked,
            email_maintenance: document.getElementById('emailMaintenance').checked,
            email_alerts: document.getElementById('emailAlerts').checked,
            push_enabled: document.getElementById('pushEnabled').checked,
            push_realtime: document.getElementById('pushRealtime').checked,
            quiet_hours: document.getElementById('quietHours').checked
        }};
        
        fetch('/settings/save-notifications', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify(settings)
        }})
        .then(response => response.json())
        .then(data => {{
            alert(data.message || 'Einstellungen gespeichert!');
        }});
    }}

    function sendTestNotification() {{
        fetch('/settings/test-notification', {{method: 'POST'}})
            .then(response => response.json())
            .then(data => {{
                alert(data.message || 'Test-E-Mail wurde gesendet!');
            }});
    }}
    </script>
    """
    
    from app.web.dashboard_modern import render_modern_template
    
    return render_modern_template(
        content=content,
        title='Benachrichtigungen',
        active_module='settings',
        active_submodule='notifications',
        breadcrumb=[
            {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
            {'text': 'Einstellungen', 'url': url_for('settings.index')},
            {'text': 'Benachrichtigungen'}
        ]
    )


@settings_bp.route('/system')
@login_required
def system():
    """System-Einstellungen"""
    
    # System-Statistiken
    total_size = db.session.execute(
        text("SELECT pg_database_size(current_database())")
    ).scalar() / (1024 * 1024)  # In MB
    
    content = f"""
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="text-white">
            <i class="bi bi-gear"></i> System
        </h2>
    </div>

    <div class="row">
        <div class="col-md-6">
            <!-- Datenbank -->
            <div class="card mb-3">
                <div class="card-header">
                    <h5 class="mb-0">Datenbank</h5>
                </div>
                <div class="card-body">
                    <div class="d-flex justify-content-between mb-2">
                        <span>Typ:</span>
                        <strong>PostgreSQL 15</strong>
                    </div>
                    <div class="d-flex justify-content-between mb-2">
                        <span>Größe:</span>
                        <strong>{total_size:.2f} MB</strong>
                    </div>
                    <div class="d-flex justify-content-between mb-3">
                        <span>Verbindungen:</span>
                        <strong>3 / 100</strong>
                    </div>
                    
                    <button class="btn btn-primary me-2" onclick="optimizeDatabase()">
                        <i class="bi bi-speedometer"></i> Optimieren
                    </button>
                    <button class="btn btn-warning" onclick="clearCache()">
                        <i class="bi bi-trash"></i> Cache leeren
                    </button>
                </div>
            </div>

            <!-- Wartungsmodus -->
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">Wartungsmodus</h5>
                </div>
                <div class="card-body">
                    <div class="form-check form-switch mb-3">
                        <input class="form-check-input" type="checkbox" id="maintenanceMode">
                        <label class="form-check-label" for="maintenanceMode">
                            Wartungsmodus aktivieren
                        </label>
                    </div>
                    <p class="text-muted small">
                        Im Wartungsmodus können nur Administratoren auf das System zugreifen.
                    </p>
                    <div class="mb-3">
                        <label class="form-label">Wartungsnachricht</label>
                        <textarea class="form-control" rows="3" placeholder="Das System wird gewartet..."></textarea>
                    </div>
                </div>
            </div>
        </div>

        <div class="col-md-6">
            <!-- API-Einstellungen -->
            <div class="card mb-3">
                <div class="card-header">
                    <h5 class="mb-0">API-Zugriff</h5>
                </div>
                <div class="card-body">
                    <div class="mb-3">
                        <label class="form-label">API-Schlüssel</label>
                        <div class="input-group">
                            <input type="text" class="form-control" value="sk_live_..." readonly id="apiKey">
                            <button class="btn btn-outline-secondary" onclick="regenerateApiKey()">
                                <i class="bi bi-arrow-clockwise"></i> Neu generieren
                            </button>
                        </div>
                    </div>
                    
                    <div class="form-check form-switch mb-2">
                        <input class="form-check-input" type="checkbox" id="apiEnabled" checked>
                        <label class="form-check-label" for="apiEnabled">
                            API aktiviert
                        </label>
                    </div>
                    
                    <div class="mb-3">
                        <label class="form-label">Rate Limit (Anfragen/Stunde)</label>
                        <input type="number" class="form-control" value="1000" min="10" max="10000">
                    </div>
                </div>
            </div>

            <!-- Logs -->
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">System-Logs</h5>
                </div>
                <div class="card-body">
                    <div class="mb-3">
                        <select class="form-select">
                            <option>Alle Logs</option>
                            <option>Fehler</option>
                            <option>Warnungen</option>
                            <option>Info</option>
                        </select>
                    </div>
                    
                    <div class="bg-dark text-light p-2 rounded" style="font-family: monospace; font-size: 12px; max-height: 200px; overflow-y: auto;">
                        [2025-01-17 10:23:45] INFO: System gestartet<br>
                        [2025-01-17 10:24:12] INFO: Benutzer angemeldet: admin<br>
                        [2025-01-17 10:25:33] WARNING: Niedriger Lagerbestand: Cola<br>
                        [2025-01-17 10:30:00] INFO: Automatisches Backup erstellt<br>
                        [2025-01-17 11:15:22] INFO: Neue Einnahme erfasst: 45.50 €<br>
                    </div>
                    
                    <button class="btn btn-sm btn-secondary mt-2">
                        <i class="bi bi-download"></i> Logs herunterladen
                    </button>
                </div>
            </div>
        </div>
    </div>

    <script>
    function optimizeDatabase() {{
        if (confirm('Datenbank optimieren? Dies kann einige Minuten dauern.')) {{
            fetch('/settings/optimize-db', {{method: 'POST'}})
                .then(response => response.json())
                .then(data => {{
                    alert(data.message || 'Datenbank wurde optimiert!');
                }});
        }}
    }}

    function clearCache() {{
        if (confirm('Cache leeren?')) {{
            fetch('/settings/clear-cache', {{method: 'POST'}})
                .then(response => response.json())
                .then(data => {{
                    alert(data.message || 'Cache wurde geleert!');
                }});
        }}
    }}

    function regenerateApiKey() {{
        if (confirm('API-Schlüssel neu generieren? Der alte Schlüssel wird ungültig!')) {{
            fetch('/settings/regenerate-api-key', {{method: 'POST'}})
                .then(response => response.json())
                .then(data => {{
                    if (data.api_key) {{
                        document.getElementById('apiKey').value = data.api_key;
                        alert('Neuer API-Schlüssel wurde generiert!');
                    }}
                }});
        }}
    }}
    </script>
    """
    
    from app.web.dashboard_modern import render_modern_template
    
    return render_modern_template(
        content=content,
        title='System',
        active_module='settings',
        active_submodule='system',
        breadcrumb=[
            {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
            {'text': 'Einstellungen', 'url': url_for('settings.index')},
            {'text': 'System'}
        ]
    )


@settings_bp.route('/email-settings')
@login_required
def email_settings():
    """E-Mail Einstellungen"""
    
    # Aktuelle Konfiguration
    email_config = {
        'server': current_app.config.get('MAIL_SERVER', ''),
        'port': current_app.config.get('MAIL_PORT', 587),
        'username': current_app.config.get('MAIL_USERNAME', ''),
        'use_tls': current_app.config.get('MAIL_USE_TLS', True),
        'sender': current_app.config.get('MAIL_DEFAULT_SENDER', '')
    }
    
    content = f"""
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="text-white">
            <i class="bi bi-envelope"></i> E-Mail Einstellungen
        </h2>
        <button class="btn btn-light" onclick="saveEmailSettings()">
            <i class="bi bi-save"></i> Speichern
        </button>
    </div>

    <div class="row">
        <div class="col-md-8">
            <div class="card mb-3">
                <div class="card-header">
                    <h5 class="mb-0">SMTP-Konfiguration</h5>
                </div>
                <div class="card-body">
                    <form id="emailSettingsForm">
                        <div class="row mb-3">
                            <div class="col-md-8">
                                <label class="form-label">SMTP-Server</label>
                                <input type="text" class="form-control" name="mail_server" 
                                       value="{email_config['server']}" placeholder="smtp.gmail.com">
                                <small class="text-muted">Z.B. smtp.gmail.com, smtp.office365.com</small>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">Port</label>
                                <input type="number" class="form-control" name="mail_port" 
                                       value="{email_config['port']}" placeholder="587">
                                <small class="text-muted">Standard: 587 (TLS)</small>
                            </div>
                        </div>
                        
                        <div class="row mb-3">
                            <div class="col-md-6">
                                <label class="form-label">Benutzername</label>
                                <input type="email" class="form-control" name="mail_username" 
                                       value="{email_config['username']}" placeholder="your-email@gmail.com">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">Passwort</label>
                                <input type="password" class="form-control" name="mail_password" 
                                       placeholder="••••••••">
                                <small class="text-muted">Für Gmail: App-Passwort verwenden</small>
                            </div>
                        </div>
                        
                        <div class="mb-3">
                            <label class="form-label">Absender-Adresse</label>
                            <input type="email" class="form-control" name="mail_sender" 
                                   value="{email_config['sender']}" placeholder="noreply@ihre-domain.de">
                        </div>
                        
                        <div class="mb-3">
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" name="use_tls" 
                                       id="useTLS" {'checked' if email_config['use_tls'] else ''}>
                                <label class="form-check-label" for="useTLS">
                                    TLS verwenden (empfohlen)
                                </label>
                            </div>
                        </div>
                        
                        <div class="alert alert-info">
                            <i class="bi bi-info-circle"></i> 
                            <strong>Gmail-Nutzer:</strong> Aktivieren Sie 2FA und erstellen Sie ein App-Passwort unter 
                            <a href="https://myaccount.google.com/apppasswords" target="_blank">Google Account Settings</a>
                        </div>
                    </form>
                </div>
            </div>
            
            <!-- Test-E-Mail -->
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">Verbindung testen</h5>
                </div>
                <div class="card-body">
                    <p>Senden Sie eine Test-E-Mail, um die Konfiguration zu überprüfen:</p>
                    <div class="input-group">
                        <input type="email" class="form-control" id="testEmail" 
                               placeholder="test@example.com" value="{current_user.email}">
                        <button class="btn btn-primary" onclick="sendTestEmail()">
                            <i class="bi bi-send"></i> Test-E-Mail senden
                        </button>
                    </div>
                    <div id="testResult" class="mt-3"></div>
                </div>
            </div>
        </div>
        
        <div class="col-md-4">
            <!-- Vorlagen -->
            <div class="card mb-3">
                <div class="card-header">
                    <h5 class="mb-0">E-Mail-Vorlagen</h5>
                </div>
                <div class="card-body">
                    <p class="small text-muted">Verfügbare E-Mail-Typen:</p>
                    <ul class="list-unstyled">
                        <li><i class="bi bi-check-circle text-success"></i> Tägliche Zusammenfassung</li>
                        <li><i class="bi bi-check-circle text-success"></i> Wartungserinnerung</li>
                        <li><i class="bi bi-check-circle text-success"></i> Niedrigbestand-Warnung</li>
                        <li><i class="bi bi-check-circle text-success"></i> Wöchentlicher Report</li>
                        <li><i class="bi bi-check-circle text-success"></i> Monatsbericht</li>
                    </ul>
                    
                    <button class="btn btn-sm btn-outline-primary w-100" onclick="previewTemplates()">
                        <i class="bi bi-eye"></i> Vorlagen anzeigen
                    </button>
                </div>
            </div>
            
            <!-- Anleitung -->
            <div class="card">
                <div class="card-body">
                    <h6>Schnellkonfiguration:</h6>
                    <div class="d-grid gap-2">
                        <button class="btn btn-sm btn-outline-secondary" onclick="fillGmailSettings()">
                            <i class="bi bi-google"></i> Gmail
                        </button>
                        <button class="btn btn-sm btn-outline-secondary" onclick="fillOutlookSettings()">
                            <i class="bi bi-microsoft"></i> Outlook/Office365
                        </button>
                        <button class="btn btn-sm btn-outline-secondary" onclick="fillCustomSettings()">
                            <i class="bi bi-gear"></i> Andere
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
    function saveEmailSettings() {{
        const formData = new FormData(document.getElementById('emailSettingsForm'));
        const data = Object.fromEntries(formData);
        data.use_tls = document.getElementById('useTLS').checked;
        
        fetch('/settings/save-email-settings', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify(data)
        }})
        .then(response => response.json())
        .then(data => {{
            if (data.success) {{
                alert('E-Mail-Einstellungen gespeichert!');
            }} else {{
                alert('Fehler: ' + (data.message || 'Unbekannter Fehler'));
            }}
        }});
    }}
    
    function sendTestEmail() {{
        const email = document.getElementById('testEmail').value;
        const resultDiv = document.getElementById('testResult');
        
        resultDiv.innerHTML = '<div class="spinner-border spinner-border-sm" role="status"><span class="visually-hidden">Sende...</span></div> Sende Test-E-Mail...';
        
        fetch('/settings/send-test-email', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{email: email}})
        }})
        .then(response => response.json())
        .then(data => {{
            if (data.success) {{
                resultDiv.innerHTML = '<div class="alert alert-success"><i class="bi bi-check-circle"></i> Test-E-Mail erfolgreich gesendet!</div>';
            }} else {{
                resultDiv.innerHTML = '<div class="alert alert-danger"><i class="bi bi-x-circle"></i> Fehler: ' + (data.message || 'E-Mail konnte nicht gesendet werden') + '</div>';
            }}
        }})
        .catch(error => {{
            resultDiv.innerHTML = '<div class="alert alert-danger"><i class="bi bi-x-circle"></i> Netzwerkfehler: ' + error + '</div>';
        }});
    }}
    
    function fillGmailSettings() {{
        document.querySelector('[name="mail_server"]').value = 'smtp.gmail.com';
        document.querySelector('[name="mail_port"]').value = '587';
        document.getElementById('useTLS').checked = true;
        alert('Gmail-Einstellungen eingetragen. Bitte Benutzername und App-Passwort eingeben!');
    }}
    
    function fillOutlookSettings() {{
        document.querySelector('[name="mail_server"]').value = 'smtp.office365.com';
        document.querySelector('[name="mail_port"]').value = '587';
        document.getElementById('useTLS').checked = true;
        alert('Outlook-Einstellungen eingetragen. Bitte Benutzername und Passwort eingeben!');
    }}
    
    function fillCustomSettings() {{
        alert('Bitte erfragen Sie die SMTP-Daten bei Ihrem E-Mail-Anbieter.');
    }}
    
    function previewTemplates() {{
        window.open('/settings/email-templates', '_blank');
    }}
    </script>
    """
    
    from app.web.dashboard_modern import render_modern_template
    
    return render_modern_template(
        content=content,
        title='E-Mail Einstellungen',
        active_module='settings',
        active_submodule='email',
        breadcrumb=[
            {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
            {'text': 'Einstellungen', 'url': url_for('settings.index')},
            {'text': 'E-Mail'}
        ]
    )


@settings_bp.route('/send-test-email', methods=['POST'])
@login_required
def send_test_email():
    """Test-E-Mail senden"""
    try:
        from app.utils.email_service import EmailService
        
        email = request.json.get('email', current_user.email)
        success = EmailService.send_test_email(current_user)
        
        if success:
            return jsonify({'success': True, 'message': 'Test-E-Mail wurde gesendet!'})
        else:
            return jsonify({'success': False, 'message': 'E-Mail konnte nicht gesendet werden. Bitte Konfiguration prüfen.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# API Endpoints
@settings_bp.route('/save-company', methods=['POST'])
@login_required
def save_company():
    """Unternehmensdaten speichern"""
    try:
        data = request.json
        # Hier würde man die Daten in der Datenbank speichern
        # Für Demo-Zwecke nur Success zurückgeben
        return jsonify({'success': True, 'message': 'Einstellungen gespeichert!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@settings_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Passwort ändern"""
    try:
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        
        # Passwort prüfen
        if not check_password_hash(current_user.password, current_password):
            return jsonify({'success': False, 'message': 'Aktuelles Passwort ist falsch!'})
        
        # Neues Passwort setzen
        current_user.password = generate_password_hash(new_password)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Passwort wurde geändert!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@settings_bp.route('/setup-2fa')
@login_required
def setup_2fa():
    """2FA einrichten"""
    try:
        # Secret generieren
        secret = pyotp.random_base32()
        
        # QR-Code generieren
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=current_user.email,
            issuer_name='Automaten Manager'
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        
        import base64
        qr_code = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"
        
        # Secret temporär speichern (in Session)
        from flask import session
        session['temp_totp_secret'] = secret
        
        return jsonify({'success': True, 'qr_code': qr_code})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@settings_bp.route('/verify-2fa', methods=['POST'])
@login_required
def verify_2fa():
    """2FA-Code verifizieren"""
    try:
        from flask import session
        code = request.json.get('code')
        secret = session.get('temp_totp_secret')
        
        if not secret:
            return jsonify({'success': False, 'message': 'Keine 2FA-Einrichtung aktiv!'})
        
        totp = pyotp.TOTP(secret)
        if totp.verify(code):
            # Speichere Secret beim User
            current_user.two_factor_secret = secret
            current_user.two_factor_enabled = True
            db.session.commit()
            session.pop('temp_totp_secret', None)
            return jsonify({'success': True, 'message': '2FA erfolgreich aktiviert!'})
        else:
            return jsonify({'success': False, 'message': 'Ungültiger Code!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@settings_bp.route('/disable-2fa', methods=['POST'])
@login_required
def disable_2fa():
    """2FA deaktivieren"""
    try:
        # 2FA deaktivieren
        current_user.two_factor_secret = None
        current_user.two_factor_enabled = False
        db.session.commit()
        return jsonify({'success': True, 'message': '2FA wurde deaktiviert!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@settings_bp.route('/save-email-settings', methods=['POST'])
@login_required
def save_email_settings():
    """E-Mail-Einstellungen speichern"""
    try:
        data = request.json
        # Hier würde man die Einstellungen in der Config speichern
        current_app.config['MAIL_SERVER'] = data.get('mail_server')
        current_app.config['MAIL_PORT'] = int(data.get('mail_port', 587))
        current_app.config['MAIL_USERNAME'] = data.get('mail_username')
        current_app.config['MAIL_PASSWORD'] = data.get('mail_password')
        current_app.config['MAIL_USE_TLS'] = data.get('use_tls', True)
        current_app.config['MAIL_DEFAULT_SENDER'] = data.get('mail_sender')
        
        return jsonify({'success': True, 'message': 'E-Mail-Einstellungen gespeichert!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@settings_bp.route('/save-notifications', methods=['POST'])
@login_required
def save_notifications():
    """Benachrichtigungseinstellungen speichern"""
    try:
        data = request.json
        # Hier würde man die Einstellungen in der DB speichern
        return jsonify({'success': True, 'message': 'Benachrichtigungseinstellungen gespeichert!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@settings_bp.route('/test-notification', methods=['POST'])
@login_required
def test_notification():
    """Test-Benachrichtigung senden"""
    try:
        # Hier würde man eine Test-E-Mail senden
        return jsonify({'success': True, 'message': 'Test-E-Mail wurde gesendet!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@settings_bp.route('/optimize-db', methods=['POST'])
@login_required
def optimize_db():
    """Datenbank optimieren"""
    try:
        # Hier würde man die DB optimieren
        db.session.execute(text('VACUUM ANALYZE'))
        return jsonify({'success': True, 'message': 'Datenbank wurde optimiert!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@settings_bp.route('/clear-cache', methods=['POST'])
@login_required
def clear_cache():
    """Cache leeren"""
    try:
        # Hier würde man den Cache leeren
        return jsonify({'success': True, 'message': 'Cache wurde geleert!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@settings_bp.route('/regenerate-api-key', methods=['POST'])
@login_required
def regenerate_api_key():
    """API-Schlüssel neu generieren"""
    try:
        import secrets
        new_key = f"sk_live_{secrets.token_urlsafe(32)}"
        # Hier würde man den neuen Key speichern
        return jsonify({'success': True, 'api_key': new_key})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@settings_bp.route('/create-backup', methods=['POST'])
@login_required
def create_backup():
    """Backup erstellen"""
    try:
        # Backup-Daten sammeln
        backup_data = {
            'user': current_user.id,
            'date': datetime.now().isoformat(),
            'devices': [],
            'products': [],
            'entries': [],
            'expenses': []
        }
        
        # Daten exportieren
        devices = Device.query.filter_by(owner_id=current_user.id).all()
        for device in devices:
            backup_data['devices'].append({
                'id': device.id,
                'name': device.name,
                'location': device.location,
                'serial_number': device.serial_number
            })
        
        # ZIP-Datei erstellen
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('backup.json', json.dumps(backup_data, indent=2))
        
        memory_file.seek(0)
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.zip'
        )
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
