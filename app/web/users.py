# app/web/users.py
"""
Benutzerverwaltung
"""

from flask import Blueprint, render_template_string, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import secrets
import string
from app import db
from app.models import User, LoginLog, AuditLog, AuditAction
from app.web.navigation import render_with_base_new as render_with_base
from functools import wraps

users_bp = Blueprint('users', __name__, url_prefix='/users')


def admin_required(f):
    """Decorator für Admin-only Funktionen"""

    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('Keine Berechtigung für diese Aktion!', 'danger')
            return redirect(url_for('web.dashboard'))
        return f(*args, **kwargs)

    return decorated_function


def log_audit(action_type, details, entity_type='User', entity_id=None):
    """Audit-Log für alle Aktionen mit korrekten Enum-Werten"""
    try:
        # Map action strings to correct AuditAction enum
        if 'CREATE' in action_type or 'CREATED' in action_type:
            audit_action = AuditAction.CREATE
        elif 'DELETE' in action_type:
            audit_action = AuditAction.DELETE
        elif 'LOGIN' in action_type:
            audit_action = AuditAction.LOGIN
        elif 'LOGOUT' in action_type:
            audit_action = AuditAction.LOGOUT
        elif 'EXPORT' in action_type:
            audit_action = AuditAction.EXPORT
        elif 'IMPORT' in action_type:
            audit_action = AuditAction.IMPORT
        else:
            # Alles andere ist UPDATE (inkl. USER_UPDATED, PASSWORD_RESET, etc.)
            audit_action = AuditAction.UPDATE

        audit = AuditLog(
            user_id=current_user.id,
            action=audit_action,
            entity_type=entity_type,
            entity_id=entity_id,
            details={'message': details, 'original_action': action_type},  # Store details as JSON
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string[:200] if request.user_agent else None
        )
        db.session.add(audit)
        db.session.commit()
    except Exception as e:
        print(f"Error logging audit: {e}")
        # Don't fail the main operation if audit logging fails
        db.session.rollback()
        pass


@users_bp.route('/')
@login_required
def index():
    """Benutzerliste anzeigen"""
    # Nur Admins sehen alle User, normale User werden zu ihrem Profil weitergeleitet
    if not current_user.is_admin:
        return redirect(url_for('users.profile'))

    users = User.query.order_by(User.created_at.desc()).all()

    # Statistiken berechnen
    total_users = len(users)
    active_users = len([u for u in users if u.is_active])
    admin_users = len([u for u in users if u.is_admin])
    verified_users = len([u for u in users if u.is_verified])

    content = f'''
    <div class="container-fluid">
        <!-- Header mit Statistiken -->
        <div class="row mb-4">
            <div class="col-12">
                <div class="d-flex justify-content-between align-items-center mb-4">
                    <h2><i class="bi bi-people-fill"></i> Benutzerverwaltung</h2>
                    <button class="btn btn-primary" onclick="showAddUserModal()">
                        <i class="bi bi-person-plus-fill"></i> Benutzer hinzufügen
                    </button>
                </div>

                <!-- Statistik-Karten -->
                <div class="row g-3 mb-4">
                    <div class="col-md-3">
                        <div class="card border-0 shadow-sm">
                            <div class="card-body text-center">
                                <h3 class="text-primary mb-0">{total_users}</h3>
                                <small class="text-muted">Benutzer gesamt</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card border-0 shadow-sm">
                            <div class="card-body text-center">
                                <h3 class="text-success mb-0">{active_users}</h3>
                                <small class="text-muted">Aktiv</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card border-0 shadow-sm">
                            <div class="card-body text-center">
                                <h3 class="text-warning mb-0">{admin_users}</h3>
                                <small class="text-muted">Administratoren</small>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="card border-0 shadow-sm">
                            <div class="card-body text-center">
                                <h3 class="text-info mb-0">{verified_users}</h3>
                                <small class="text-muted">Verifiziert</small>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Benutzer-Karten -->
                <div class="row g-3">
    '''

    for user in users:
        # Avatar mit Initialen
        initials = user.full_name[:2].upper() if user.full_name else user.username[:2].upper()

        # Letzte Aktivität
        last_login = LoginLog.query.filter_by(user_id=user.id, success=True).order_by(LoginLog.timestamp.desc()).first()
        if last_login:
            # Zeit-Differenz berechnen
            time_diff = datetime.utcnow() - last_login.timestamp
            if time_diff.days == 0:
                if time_diff.seconds < 3600:
                    last_activity = f"Vor {time_diff.seconds // 60} Minuten"
                else:
                    last_activity = f"Vor {time_diff.seconds // 3600} Stunden"
            elif time_diff.days == 1:
                last_activity = "Gestern"
            else:
                last_activity = f"Vor {time_diff.days} Tagen"
        else:
            last_activity = "Noch nie eingeloggt"

        # Login-Anzahl
        login_count = LoginLog.query.filter_by(user_id=user.id, success=True).count()

        # Status-Badges
        badges = []
        if user.is_admin:
            badges.append('<span class="badge bg-warning">Admin</span>')
        if user.is_verified:
            badges.append('<span class="badge bg-success">Verifiziert</span>')
        if user.is_active:
            badges.append('<span class="badge bg-info">Aktiv</span>')
        else:
            badges.append('<span class="badge bg-danger">Gesperrt</span>')
        if user.two_factor_enabled:
            badges.append('<span class="badge bg-purple">2FA</span>')

        # Actions dropdown
        actions = f'''
            <div class="dropdown">
            <button class="btn btn-sm btn-outline-secondary dropdown-toggle" type="button" data-bs-toggle="dropdown">
                <i class="bi bi-three-dots-vertical"></i>
            </button>
            <ul class="dropdown-menu dropdown-menu-end">  <!-- NEU: dropdown-menu-end hinzugefügt -->
                <li><a class="dropdown-item" href="#" onclick="editUser({user.id})">
                    <i class="bi bi-pencil"></i> Bearbeiten</a></li>
                <li><a class="dropdown-item" href="#" onclick="resetPassword({user.id})">
                    <i class="bi bi-key"></i> Passwort zurücksetzen</a></li>
                <li><a class="dropdown-item" href="/users/activity/{user.id}">
                    <i class="bi bi-clock-history"></i> Aktivitäten</a></li>
                <li><hr class="dropdown-divider"></li>
        '''

        if user.is_active:
            actions += f'''
                    <li><a class="dropdown-item text-warning" href="#" onclick="toggleUserStatus({user.id}, false)">
                        <i class="bi bi-lock"></i> Sperren</a></li>
            '''
        else:
            actions += f'''
                    <li><a class="dropdown-item text-success" href="#" onclick="toggleUserStatus({user.id}, true)">
                        <i class="bi bi-unlock"></i> Entsperren</a></li>
            '''

        if user.id != current_user.id:  # Kann sich nicht selbst löschen
            actions += f'''
                    <li><a class="dropdown-item text-danger" href="#" onclick="deleteUser({user.id})">
                        <i class="bi bi-trash"></i> Löschen</a></li>
            '''

        actions += '''
                </ul>
            </div>
        '''

        content += f'''
            <div class="col-md-6 col-lg-4">
                <div class="card shadow-sm h-100">
                    <div class="card-body">
                        <div class="d-flex align-items-start">
                            <div class="avatar-circle me-3" style="background: {"#6f42c1" if user.is_admin else "#0d6efd"};">
                                {initials}
                            </div>
                            <div class="flex-grow-1">
                                <div class="d-flex justify-content-between align-items-start">
                                    <div>
                                        <h5 class="mb-1">{user.username}</h5>
                                        <p class="text-muted small mb-2">{user.email}</p>
                                        <div class="mb-2">
                                            {' '.join(badges)}
                                        </div>
                                    </div>
                                    {actions}
                                </div>
                                <hr class="my-2">
                                <div class="small text-muted">
                                    <i class="bi bi-clock"></i> {last_activity}<br>
                                    <i class="bi bi-box-arrow-in-right"></i> Logins: {login_count}<br>
                                    {f'<i class="bi bi-person"></i> {user.full_name}' if user.full_name else ''}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        '''

    content += '''
                </div>
            </div>
        </div>
    </div>

    <!-- Modals -->
    <!-- Add User Modal -->
    <div class="modal fade" id="addUserModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Neuen Benutzer anlegen</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <form id="addUserForm">
                        <div class="mb-3">
                            <label class="form-label">Benutzername*</label>
                            <input type="text" class="form-control" name="username" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">E-Mail*</label>
                            <input type="email" class="form-control" name="email" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Vorname</label>
                            <input type="text" class="form-control" name="first_name">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Nachname</label>
                            <input type="text" class="form-control" name="last_name">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Passwort</label>
                            <div class="input-group">
                                <input type="text" class="form-control" name="password" id="newPassword" readonly>
                                <button class="btn btn-outline-secondary" type="button" onclick="generatePassword()">
                                    <i class="bi bi-arrow-clockwise"></i> Generieren
                                </button>
                            </div>
                            <small class="text-muted">Wird automatisch generiert wenn leer</small>
                        </div>
                        <div class="form-check mb-3">
                            <input class="form-check-input" type="checkbox" name="is_admin" id="isAdmin">
                            <label class="form-check-label" for="isAdmin">
                                Administrator-Rechte
                            </label>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Abbrechen</button>
                    <button type="button" class="btn btn-primary" onclick="submitAddUser()">
                        <i class="bi bi-check-lg"></i> Benutzer anlegen
                    </button>
                </div>
            </div>
        </div>
    </div>

    <!-- Edit User Modal -->
    <div class="modal fade" id="editUserModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Benutzer bearbeiten</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <form id="editUserForm">
                        <input type="hidden" name="user_id" id="editUserId">
                        <div class="mb-3">
                            <label class="form-label">Benutzername*</label>
                            <input type="text" class="form-control" name="username" id="editUsername" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">E-Mail*</label>
                            <input type="email" class="form-control" name="email" id="editEmail" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Vorname</label>
                            <input type="text" class="form-control" name="first_name" id="editFirstName">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Nachname</label>
                            <input type="text" class="form-control" name="last_name" id="editLastName">
                        </div>
                        <div class="form-check mb-3">
                            <input class="form-check-input" type="checkbox" name="is_admin" id="editIsAdmin">
                            <label class="form-check-label" for="editIsAdmin">
                                Administrator-Rechte
                            </label>
                        </div>
                        <div class="form-check mb-3">
                            <input class="form-check-input" type="checkbox" name="is_active" id="editIsActive">
                            <label class="form-check-label" for="editIsActive">
                                Account aktiv
                            </label>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Abbrechen</button>
                    <button type="button" class="btn btn-primary" onclick="submitEditUser()">
                        <i class="bi bi-check-lg"></i> Speichern
                    </button>
                </div>
            </div>
        </div>
    </div>

    <style>
        .avatar-circle {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 1.2rem;
        }
        .bg-purple {
            background-color: #6f42c1;
        }
        .card {
            transition: transform 0.2s;
        }
        .card:hover {
            transform: translateY(-2px);
        }
    </style>
    '''

    extra_scripts = '''
    <script>
        function showAddUserModal() {
            generatePassword();
            new bootstrap.Modal(document.getElementById('addUserModal')).show();
        }

        function generatePassword() {
            const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789!@#$%';
            let password = '';
            for (let i = 0; i < 12; i++) {
                password += chars.charAt(Math.floor(Math.random() * chars.length));
            }
            document.getElementById('newPassword').value = password;
        }

        function submitAddUser() {
            const form = document.getElementById('addUserForm');
            const formData = new FormData(form);

            // Wenn kein Passwort, generiere eins
            if (!formData.get('password')) {
                generatePassword();
                formData.set('password', document.getElementById('newPassword').value);
            }

            fetch('/users/add', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert('Fehler: ' + data.message);
                }
            });
        }

        function editUser(userId) {
            fetch(`/users/get/${userId}`)
                .then(response => response.json())
                .then(data => {
                    document.getElementById('editUserId').value = data.id;
                    document.getElementById('editUsername').value = data.username;
                    document.getElementById('editEmail').value = data.email;
                    document.getElementById('editFirstName').value = data.first_name || '';
                    document.getElementById('editLastName').value = data.last_name || '';
                    document.getElementById('editIsAdmin').checked = data.is_admin;
                    document.getElementById('editIsActive').checked = data.is_active;

                    new bootstrap.Modal(document.getElementById('editUserModal')).show();
                });
        }

        function submitEditUser() {
            const form = document.getElementById('editUserForm');
            const formData = new FormData(form);

            fetch('/users/edit', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    alert('Fehler: ' + data.message);
                }
            });
        }

        function resetPassword(userId) {
            if (confirm('Wirklich ein neues Passwort generieren?')) {
                fetch(`/users/reset-password/${userId}`, {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert('Neues Passwort: ' + data.password + '\\n\\nBitte notieren!');
                    } else {
                        alert('Fehler: ' + data.message);
                    }
                });
            }
        }

        function toggleUserStatus(userId, activate) {
            const action = activate ? 'entsperren' : 'sperren';
            if (confirm(`Benutzer wirklich ${action}?`)) {
                fetch(`/users/toggle-status/${userId}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({active: activate})
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        location.reload();
                    } else {
                        alert('Fehler: ' + data.message);
                    }
                });
            }
        }

        function deleteUser(userId) {
            if (confirm('Benutzer wirklich LÖSCHEN? Diese Aktion kann nicht rückgängig gemacht werden!')) {
                fetch(`/users/delete/${userId}`, {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        location.reload();
                    } else {
                        alert('Fehler: ' + data.message);
                    }
                });
            }
        }
    </script>
    '''

    return render_template_string(
        render_with_base(content, title='Benutzerverwaltung', active_page='users', extra_scripts=extra_scripts)
    )


@users_bp.route('/profile')
@login_required
def profile():
    """Eigenes Profil anzeigen und bearbeiten"""

    # Login-Historie
    recent_logins = LoginLog.query.filter_by(
        user_id=current_user.id,
        success=True
    ).order_by(LoginLog.timestamp.desc()).limit(10).all()

    content = f'''
    <div class="container">
        <div class="row">
            <div class="col-lg-4">
                <!-- Profil-Karte -->
                <div class="card shadow-sm mb-4">
                    <div class="card-body text-center">
                        <div class="avatar-circle mx-auto mb-3" style="width: 100px; height: 100px; font-size: 2.5rem; background: {"#6f42c1" if current_user.is_admin else "#0d6efd"};">
                            {current_user.full_name[:2].upper() if current_user.full_name else current_user.username[:2].upper()}
                        </div>
                        <h4>{current_user.username}</h4>
                        <p class="text-muted">{current_user.email}</p>
                        <div class="mb-3">
                            {'<span class="badge bg-warning">Administrator</span>' if current_user.is_admin else ''}
                            {'<span class="badge bg-success">Verifiziert</span>' if current_user.is_verified else ''}
                            {'<span class="badge bg-purple">2FA aktiviert</span>' if current_user.two_factor_enabled else ''}
                        </div>
                        <hr>
                        <div class="text-start small">
                            <p><strong>Mitglied seit:</strong><br>{current_user.created_at.strftime("%d.%m.%Y")}</p>
                            <p><strong>Letzter Login:</strong><br>{recent_logins[0].timestamp.strftime("%d.%m.%Y %H:%M") if recent_logins else "Nie"}</p>
                        </div>
                    </div>
                </div>

                <!-- Sicherheit -->
                <div class="card shadow-sm">
                    <div class="card-body">
                        <h5 class="card-title mb-3">
                            <i class="bi bi-shield-check"></i> Sicherheit
                        </h5>
                        <div class="d-grid gap-2">
                            <button class="btn btn-outline-primary" onclick="showChangePasswordModal()">
                                <i class="bi bi-key"></i> Passwort ändern
                            </button>
                            <button class="btn btn-outline-primary" onclick="toggle2FA()">
                                <i class="bi bi-phone"></i> 
                                {'2FA deaktivieren' if current_user.two_factor_enabled else '2FA aktivieren'}
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-lg-8">
                <!-- Profil bearbeiten -->
                <div class="card shadow-sm mb-4">
                    <div class="card-body">
                        <h5 class="card-title mb-4">
                            <i class="bi bi-person-lines-fill"></i> Profil bearbeiten
                        </h5>
                        <form id="profileForm">
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label class="form-label">Benutzername</label>
                                    <input type="text" class="form-control" name="username" value="{current_user.username}" required>
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label class="form-label">E-Mail</label>
                                    <input type="email" class="form-control" name="email" value="{current_user.email}" required>
                                </div>
                            </div>
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label class="form-label">Vorname</label>
                                    <input type="text" class="form-control" name="first_name" value="{current_user.first_name or ''}">
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label class="form-label">Nachname</label>
                                    <input type="text" class="form-control" name="last_name" value="{current_user.last_name or ''}">
                                </div>
                            </div>
                            <button type="submit" class="btn btn-primary">
                                <i class="bi bi-check-lg"></i> Änderungen speichern
                            </button>
                        </form>
                    </div>
                </div>

                <!-- Login-Historie -->
                <div class="card shadow-sm">
                    <div class="card-body">
                        <h5 class="card-title mb-3">
                            <i class="bi bi-clock-history"></i> Letzte Anmeldungen
                        </h5>
                        <div class="table-responsive">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>Zeitpunkt</th>
                                        <th>IP-Adresse</th>
                                        <th>Browser</th>
                                    </tr>
                                </thead>
                                <tbody>
    '''

    for login in recent_logins:
        browser = "Unbekannt"
        if login.user_agent:
            if "Chrome" in login.user_agent:
                browser = "Chrome"
            elif "Firefox" in login.user_agent:
                browser = "Firefox"
            elif "Safari" in login.user_agent:
                browser = "Safari"
            elif "Edge" in login.user_agent:
                browser = "Edge"

        content += f'''
                                    <tr>
                                        <td>{login.timestamp.strftime("%d.%m.%Y %H:%M")}</td>
                                        <td>{login.ip_address or "Unbekannt"}</td>
                                        <td>{browser}</td>
                                    </tr>
        '''

    content += '''
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Passwort ändern Modal -->
    <div class="modal fade" id="changePasswordModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Passwort ändern</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <form id="changePasswordForm">
                        <div class="mb-3">
                            <label class="form-label">Aktuelles Passwort</label>
                            <input type="password" class="form-control" name="current_password" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Neues Passwort</label>
                            <input type="password" class="form-control" name="new_password" id="newPasswordChange" required>
                            <div class="form-text">Mindestens 8 Zeichen</div>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Neues Passwort bestätigen</label>
                            <input type="password" class="form-control" name="confirm_password" required>
                        </div>
                        <div class="mb-3">
                            <div class="progress" style="height: 5px;">
                                <div class="progress-bar" id="passwordStrength" role="progressbar"></div>
                            </div>
                            <small id="passwordStrengthText" class="text-muted">Passwortstärke</small>
                        </div>
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Abbrechen</button>
                    <button type="button" class="btn btn-primary" onclick="submitChangePassword()">
                        <i class="bi bi-check-lg"></i> Passwort ändern
                    </button>
                </div>
            </div>
        </div>
    </div>

    <style>
        .avatar-circle {
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }
        .bg-purple {
            background-color: #6f42c1;
        }
    </style>
    '''

    extra_scripts = '''
    <script>
        // Profil-Formular
        document.getElementById('profileForm').addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);

            fetch('/users/update-profile', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showAlert('Profil erfolgreich aktualisiert!', 'success');
                    setTimeout(() => location.reload(), 1500);
                } else {
                    showAlert('Fehler: ' + data.message, 'danger');
                }
            });
        });

        // Passwort-Stärke prüfen
        document.getElementById('newPasswordChange')?.addEventListener('input', function() {
            const password = this.value;
            let strength = 0;

            if (password.length >= 8) strength += 25;
            if (password.length >= 12) strength += 25;
            if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength += 25;
            if (/[0-9]/.test(password)) strength += 12.5;
            if (/[^A-Za-z0-9]/.test(password)) strength += 12.5;

            const bar = document.getElementById('passwordStrength');
            const text = document.getElementById('passwordStrengthText');

            bar.style.width = strength + '%';

            if (strength < 50) {
                bar.className = 'progress-bar bg-danger';
                text.textContent = 'Schwaches Passwort';
            } else if (strength < 75) {
                bar.className = 'progress-bar bg-warning';
                text.textContent = 'Mittleres Passwort';
            } else {
                bar.className = 'progress-bar bg-success';
                text.textContent = 'Starkes Passwort';
            }
        });

        function showChangePasswordModal() {
            new bootstrap.Modal(document.getElementById('changePasswordModal')).show();
        }

        function submitChangePassword() {
            const form = document.getElementById('changePasswordForm');
            const formData = new FormData(form);

            if (formData.get('new_password') !== formData.get('confirm_password')) {
                alert('Die Passwörter stimmen nicht überein!');
                return;
            }

            fetch('/users/change-password', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Passwort erfolgreich geändert!');
                    location.reload();
                } else {
                    alert('Fehler: ' + data.message);
                }
            });
        }

        function toggle2FA() {
            if (confirm('2-Faktor-Authentifizierung ' + 
                       ('{current_user.two_factor_enabled}' === 'True' ? 'deaktivieren' : 'aktivieren') + '?')) {
                fetch('/users/toggle-2fa', {
                    method: 'POST'
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        if (data.qr_code) {
                            // Zeige QR-Code für 2FA Setup
                            alert('Scannen Sie den QR-Code mit Ihrer Authenticator-App');
                        }
                        location.reload();
                    } else {
                        alert('Fehler: ' + data.message);
                    }
                });
            }
        }

        function showAlert(message, type) {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3`;
            alertDiv.style.zIndex = '9999';
            alertDiv.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            document.body.appendChild(alertDiv);

            setTimeout(() => {
                alertDiv.remove();
            }, 5000);
        }
    </script>
    '''

    return render_template_string(
        render_with_base(content, title='Mein Profil', active_page='profile', extra_scripts=extra_scripts)
    )


# Backend-Routes für User-Management
@users_bp.route('/add', methods=['POST'])
@admin_required
def add_user():
    """Neuen Benutzer anlegen"""
    try:
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        is_admin = request.form.get('is_admin') == 'on'

        # Prüfe ob User schon existiert
        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'message': 'Benutzername bereits vergeben'})

        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'message': 'E-Mail bereits registriert'})

        # Generiere Passwort wenn keins angegeben
        if not password:
            password = ''.join(secrets.choice(string.ascii_letters + string.digits + '!@#$%') for _ in range(12))

        # User erstellen
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_admin=is_admin,
            is_active=True,
            is_verified=False
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        log_audit('USER_CREATED', f'User {username} created by {current_user.username}')

        flash(f'Benutzer "{username}" wurde erstellt. Passwort: {password}', 'success')
        return jsonify({'success': True, 'password': password})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@users_bp.route('/get/<int:user_id>')
@admin_required
def get_user(user_id):
    """Benutzer-Daten für Bearbeitung abrufen"""
    user = User.query.get_or_404(user_id)
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_admin': user.is_admin,
        'is_active': user.is_active
    })


@users_bp.route('/edit', methods=['POST'])
@admin_required
def edit_user():
    """Benutzer bearbeiten"""
    try:
        user_id = request.form.get('user_id')
        user = User.query.get_or_404(user_id)

        # Verhindere dass der letzte Admin seine Admin-Rechte verliert
        if user.is_admin and request.form.get('is_admin') != 'on':
            admin_count = User.query.filter_by(is_admin=True).count()
            if admin_count == 1:
                return jsonify({'success': False, 'message': 'Der letzte Administrator kann nicht herabgestuft werden'})

        user.username = request.form.get('username')
        user.email = request.form.get('email')
        user.first_name = request.form.get('first_name')
        user.last_name = request.form.get('last_name')
        user.is_admin = request.form.get('is_admin') == 'on'
        user.is_active = request.form.get('is_active') == 'on'

        db.session.commit()

        log_audit('USER_UPDATED', f'User {user.username} updated by {current_user.username}')

        flash(f'Benutzer "{user.username}" wurde aktualisiert', 'success')
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@users_bp.route('/reset-password/<int:user_id>', methods=['POST'])
@admin_required
def reset_password(user_id):
    """Passwort zurücksetzen"""
    try:
        user = User.query.get_or_404(user_id)

        # Generiere neues Passwort
        new_password = ''.join(secrets.choice(string.ascii_letters + string.digits + '!@#$%') for _ in range(12))
        user.set_password(new_password)

        db.session.commit()

        log_audit('PASSWORD_RESET', f'Password reset for user {user.username} by {current_user.username}')

        return jsonify({'success': True, 'password': new_password})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@users_bp.route('/toggle-status/<int:user_id>', methods=['POST'])
@admin_required
def toggle_status(user_id):
    """Benutzer sperren/entsperren"""
    try:
        user = User.query.get_or_404(user_id)

        # Verhindere dass sich Admin selbst sperrt
        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'Sie können sich nicht selbst sperren'})

        user.is_active = request.json.get('active', False)
        db.session.commit()

        action = 'activated' if user.is_active else 'deactivated'
        log_audit(f'USER_{action.upper()}', f'User {user.username} {action} by {current_user.username}')

        flash(f'Benutzer "{user.username}" wurde {"entsperrt" if user.is_active else "gesperrt"}', 'success')
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@users_bp.route('/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Benutzer löschen"""
    try:
        user = User.query.get_or_404(user_id)

        # Verhindere dass sich Admin selbst löscht
        if user.id == current_user.id:
            return jsonify({'success': False, 'message': 'Sie können sich nicht selbst löschen'})

        # Verhindere dass der letzte Admin gelöscht wird
        if user.is_admin:
            admin_count = User.query.filter_by(is_admin=True).count()
            if admin_count == 1:
                return jsonify({'success': False, 'message': 'Der letzte Administrator kann nicht gelöscht werden'})

        username = user.username
        db.session.delete(user)
        db.session.commit()

        log_audit('USER_DELETED', f'User {username} deleted by {current_user.username}')

        flash(f'Benutzer "{username}" wurde gelöscht', 'success')
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@users_bp.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    """Eigenes Profil aktualisieren"""
    try:
        current_user.username = request.form.get('username')
        current_user.email = request.form.get('email')
        current_user.first_name = request.form.get('first_name')
        current_user.last_name = request.form.get('last_name')

        db.session.commit()

        log_audit('PROFILE_UPDATED', f'User {current_user.username} updated their profile')

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


@users_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Eigenes Passwort ändern"""
    try:
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')

        # Prüfe aktuelles Passwort
        if not current_user.check_password(current_password):
            return jsonify({'success': False, 'message': 'Aktuelles Passwort ist falsch'})

        # Setze neues Passwort
        current_user.set_password(new_password)
        db.session.commit()

        log_audit('PASSWORD_CHANGED', f'User {current_user.username} changed their password')

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


# Ersetzen Sie in Ihrer users.py die user_activity Funktion mit dieser korrigierten Version:

@users_bp.route('/activity/<int:user_id>')
@admin_required
def user_activity(user_id):
    """Aktivitäten eines Benutzers anzeigen"""
    user = User.query.get_or_404(user_id)

    # Hole alle Aktivitäten
    logins = LoginLog.query.filter_by(user_id=user_id).order_by(LoginLog.timestamp.desc()).limit(50).all()
    # WICHTIG: AuditLog hat 'created_at' statt 'timestamp'!
    audits = AuditLog.query.filter_by(user_id=user_id).order_by(AuditLog.created_at.desc()).limit(50).all()

    content = f'''
    <div class="container">
        <h2 class="mb-4">
            <i class="bi bi-clock-history"></i> Aktivitäten von {user.username}
        </h2>

        <div class="row">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>Login-Historie</h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>Zeit</th>
                                        <th>Status</th>
                                        <th>IP</th>
                                    </tr>
                                </thead>
                                <tbody>
    '''

    for login in logins:
        status = '<span class="badge bg-success">Erfolg</span>' if login.success else '<span class="badge bg-danger">Fehlgeschlagen</span>'
        content += f'''
                                    <tr>
                                        <td>{login.timestamp.strftime("%d.%m.%Y %H:%M")}</td>
                                        <td>{status}</td>
                                        <td>{login.ip_address or "Unbekannt"}</td>
                                    </tr>
        '''

    content += '''
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>

            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>Aktionen</h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>Zeit</th>
                                        <th>Aktion</th>
                                        <th>Details</th>
                                    </tr>
                                </thead>
                                <tbody>
    '''

    for audit in audits:
        # Zeige die Aktion korrekt an
        action_display = audit.action.value if audit.action else 'Unbekannt'

        # Details aus JSON extrahieren falls vorhanden
        details_text = ''
        if audit.details:
            if isinstance(audit.details, dict):
                details_text = audit.details.get('message', '') or audit.details.get('original_action', '')
            else:
                details_text = str(audit.details)

        content += f'''
                                    <tr>
                                        <td>{audit.created_at.strftime("%d.%m.%Y %H:%M")}</td>
                                        <td><span class="badge bg-secondary">{action_display}</span></td>
                                        <td class="small">{details_text[:50]}...</td>
                                    </tr>
        '''

    content += '''
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="mt-4">
            <a href="/users" class="btn btn-secondary">
                <i class="bi bi-arrow-left"></i> Zurück zur Übersicht
            </a>
        </div>
    </div>
    '''

    return render_template_string(
        render_with_base(content, title=f'Aktivitäten - {user.username}', active_page='users')
    )


@users_bp.route('/toggle-2fa', methods=['POST'])
@login_required
def toggle_2fa():
    """2FA aktivieren/deaktivieren"""
    try:
        if current_user.two_factor_enabled:
            # Deaktiviere 2FA
            current_user.two_factor_enabled = False
            current_user.two_factor_secret = None
            db.session.commit()

            log_audit('2FA_DISABLED', f'User {current_user.username} disabled 2FA')
            return jsonify({'success': True})
        else:
            # Aktiviere 2FA
            secret = current_user.setup_2fa()
            current_user.two_factor_enabled = True
            db.session.commit()

            # QR-Code generieren
            qr_code = current_user.get_2fa_qr_code()

            log_audit('2FA_ENABLED', f'User {current_user.username} enabled 2FA')
            return jsonify({'success': True, 'qr_code': qr_code, 'secret': secret})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})