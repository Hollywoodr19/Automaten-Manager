# app/web/devices.py
"""
Erweiterte Geräte-Verwaltung mit Inventar-Tracking und Wechselgeld-Management
"""

from flask import Blueprint, render_template_string, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from decimal import Decimal
from app import db
from app.models import Device, DeviceType, DeviceStatus, Product, Entry, Expense
from app.web.navigation import render_with_base_new as render_with_base
import json
import secrets
import string

devices_bp = Blueprint('devices', __name__, url_prefix='/devices')

# Wechselgeld-Definitionen (gleich wie bei Expenses)
COIN_DENOMINATIONS = {
    '2.00': {'name': '2 €', 'value': 2.00},
    '1.00': {'name': '1 €', 'value': 1.00},
    '0.50': {'name': '50 Cent', 'value': 0.50},
    '0.20': {'name': '20 Cent', 'value': 0.20},
    '0.10': {'name': '10 Cent', 'value': 0.10},
    '0.05': {'name': '5 Cent', 'value': 0.05}
}


def generate_serial_number(device_type, manufacturer=None):
    """Generiert intelligente Seriennummer"""
    type_prefixes = {
        'kaffee': 'KAF',
        'getraenke': 'GET',
        'snacks': 'SNK',
        'kombi': 'KMB'
    }
    prefix = type_prefixes.get(device_type, 'DEV')

    mfg_code = 'XXX'
    if manufacturer:
        mfg_code = ''.join(c for c in manufacturer.upper()[:3] if c.isalpha())
        mfg_code = mfg_code.ljust(3, 'X')

    year = datetime.now().year
    random_code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))

    return f"{prefix}-{mfg_code}-{year}-{random_code}"


def generate_device_name(device_type, location=None):
    """Generiert automatisch einen Gerätenamen basierend auf Typ"""
    type_names = {
        'kaffee': 'Kaffeeautomat',
        'getraenke': 'Getränkeautomat',
        'snacks': 'Snackautomat',
        'kombi': 'Kombiautomat'
    }

    base_name = type_names.get(device_type, 'Automat')

    # Zähle existierende Geräte vom gleichen Typ
    count = Device.query.filter_by(
        type=DeviceType(device_type),
        owner_id=current_user.id
    ).count() + 1

    return f"{base_name} #{count}"


@devices_bp.route('/')
@login_required
def index():
    """Geräte-Übersicht mit erweiterten Features"""
    devices = Device.query.filter_by(owner_id=current_user.id).all()

    # Statistiken für jedes Gerät berechnen
    device_stats = {}
    for device in devices:
        # Einnahmen letzte 30 Tage
        month_ago = date.today() - timedelta(days=30)
        entries = Entry.query.filter(
            Entry.device_id == device.id,
            Entry.date >= month_ago
        ).all()
        month_revenue = sum(e.amount for e in entries)

        # Inventar-Status
        inventory_data = {}
        if hasattr(device, 'inventory_data') and device.inventory_data:
            try:
                inventory_data = json.loads(device.inventory_data)
            except:
                pass

        # Wechselgeld-Status
        change_money = {}
        if hasattr(device, 'change_money') and device.change_money:
            try:
                change_money = json.loads(device.change_money)
            except:
                pass

        device_stats[device.id] = {
            'month_revenue': month_revenue,
            'inventory': inventory_data,
            'change_money': change_money,
            'total_revenue': device.get_total_revenue() if hasattr(device, 'get_total_revenue') else 0
        }

        # JavaScript für erweiterte Funktionen
        extra_scripts = """
        <script>
        function showDeviceDetails(deviceId) {
            fetch(`/devices/api/${deviceId}`)
                .then(response => response.json())
                .then(data => {
                    // Details Modal füllen
                    document.getElementById('detailDeviceName').textContent = data.name;
                    document.getElementById('detailDeviceType').textContent = data.type;
                    document.getElementById('detailDeviceStatus').textContent = data.status;
                    document.getElementById('detailDeviceLocation').textContent = data.location || 'Kein Standort';

                    // Inventar anzeigen
                    let inventoryHtml = '';
                    if (data.inventory && Object.keys(data.inventory).length > 0) {
                        for (const [productId, qty] of Object.entries(data.inventory)) {
                            inventoryHtml += `
                                <div class="inventory-item">
                                    <span>${data.product_names[productId] || 'Produkt ' + productId}</span>
                                    <span class="badge bg-primary">${qty} Stück</span>
                                </div>
                            `;
                        }
                    } else {
                        inventoryHtml = '<p class="text-muted">Kein Inventar erfasst</p>';
                    }
                    document.getElementById('inventoryList').innerHTML = inventoryHtml;

                    // Wechselgeld anzeigen
                    let changeHtml = '';
                    let totalChange = 0;
                    if (data.change_money && Object.keys(data.change_money).length > 0) {
                        for (const [coin, qty] of Object.entries(data.change_money)) {
                            const value = parseFloat(coin) * qty;
                            totalChange += value;
                            changeHtml += `
                                <div class="change-item">
                                    <span>${coin} €</span>
                                    <span class="badge bg-warning text-dark">${qty}x = ${value.toFixed(2)} €</span>
                                </div>
                            `;
                        }
                        changeHtml += `<div class="mt-2"><strong>Gesamt: ${totalChange.toFixed(2)} €</strong></div>`;
                    } else {
                        changeHtml = '<p class="text-muted">Kein Wechselgeld erfasst</p>';
                    }
                    document.getElementById('changeList').innerHTML = changeHtml;

                    // Modal öffnen
                    new bootstrap.Modal(document.getElementById('deviceDetailsModal')).show();
                });
        }

        function editDevice(deviceId) {
            fetch(`/devices/api/${deviceId}`)
                .then(response => response.json())
                .then(data => {
                    document.getElementById('device_id').value = deviceId;
                    document.getElementById('name').value = data.name;
                    document.getElementById('type').value = data.type;
                    document.getElementById('manufacturer').value = data.manufacturer || '';
                    document.getElementById('model').value = data.model || '';
                    document.getElementById('serial_number').value = data.serial_number || '';
                    document.getElementById('location').value = data.location || '';
                    document.getElementById('purchase_price').value = data.purchase_price || '';
                    document.getElementById('status').value = data.status;
                    document.getElementById('connection_type').value = data.connection_type || 'offline';

                    document.getElementById('deviceModalTitle').textContent = 'Gerät bearbeiten';
                    document.getElementById('deviceForm').action = `/devices/edit/${deviceId}`;

                    new bootstrap.Modal(document.getElementById('deviceModal')).show();
                });
        }

        function showInventoryModal(deviceId) {
            document.getElementById('inventory_device_id').value = deviceId;

            // Lade aktuelle Inventardaten
            fetch(`/devices/api/${deviceId}`)
                .then(response => response.json())
                .then(data => {
                    // Setze vorhandene Werte
                    if (data.inventory) {
                        for (const [productId, qty] of Object.entries(data.inventory)) {
                            const input = document.getElementById(`product_${productId}`);
                            if (input) input.value = qty;
                        }
                    }
                });

            new bootstrap.Modal(document.getElementById('inventoryModal')).show();
        }

        function showChangeMoneyModal(deviceId) {
            document.getElementById('change_device_id').value = deviceId;

            // Lade aktuelle Wechselgeld-Daten
            fetch(`/devices/api/${deviceId}`)
                .then(response => response.json())
                .then(data => {
                    // Setze vorhandene Werte
                    if (data.change_money) {
                        for (const [coin, qty] of Object.entries(data.change_money)) {
                            const input = document.getElementById(`coin_${coin.replace('.', '_')}`);
                            if (input) input.value = qty;
                        }
                    }
                    calculateChangeTotal();
                });

            new bootstrap.Modal(document.getElementById('changeMoneyModal')).show();
        }

        function adjustCoin(coin, delta) {
            const input = document.getElementById(`coin_${coin.replace('.', '_')}`);
            let value = parseInt(input.value || 0) + delta;
            if (value < 0) value = 0;
            if (value > 100) value = 100;
            input.value = value;
            calculateChangeTotal();
        }

        function calculateChangeTotal() {
            let total = 0;
            document.querySelectorAll('.coin-input').forEach(input => {
                const coin = parseFloat(input.dataset.coin);
                const qty = parseInt(input.value || 0);
                total += coin * qty;
            });
            document.getElementById('changeTotalAmount').textContent = total.toFixed(2);
        }

        function deleteDevice(deviceId, deviceName) {
            if (confirm(`Möchten Sie das Gerät "${deviceName}" wirklich löschen?`)) {
                fetch(`/devices/delete/${deviceId}`, { method: 'POST' })
                    .then(() => location.reload());
            }
        }

        // Auto-generate serial number UND name
        document.addEventListener('DOMContentLoaded', function() {
            const typeSelect = document.getElementById('type');
            const manufacturerInput = document.getElementById('manufacturer');
            const serialInput = document.getElementById('serial_number');
            const nameInput = document.getElementById('name');
            const locationInput = document.getElementById('location');

            // Auto-Generate Name vom Server
            function updateDeviceName() {
                const typeSelect = document.getElementById('type');
                const nameInput = document.getElementById('name');

                // Nur wenn Name-Feld leer ist und Typ ausgewählt
                if (!nameInput.value && typeSelect.value) {
                    fetch(`/devices/generate-name?device_type=${typeSelect.value}`)
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                nameInput.placeholder = data.name + ' (automatisch)';
                            }
                        });
                }
            }

            // Serial Number Preview
            function updateSerialPreview() {
                if (!serialInput.value) {
                    const typeMap = {'kaffee': 'KAF', 'getraenke': 'GET', 'snacks': 'SNK', 'kombi': 'KMB'};
                    const type = typeMap[typeSelect.value] || 'DEV';

                    let mfg = 'XXX';
                    if (manufacturerInput.value) {
                        mfg = manufacturerInput.value.toUpperCase().replace(/[^A-Z]/g, '').substr(0, 3).padEnd(3, 'X');
                    }

                    const year = new Date().getFullYear();
                    serialInput.placeholder = `${type}-${mfg}-${year}-XXXXXX (auto)`;
                }
            }

            // Event Listener - NUR auf Typ-Änderung
            if (typeSelect) {
                typeSelect.addEventListener('change', function() {
                    updateSerialPreview();
                    updateDeviceName();  // Name generieren bei Typ-Änderung
                });
            }

            if (manufacturerInput) {
                manufacturerInput.addEventListener('input', updateSerialPreview);
            }  // HIER FEHLTE DIE SCHLIESSENDE KLAMMER!

            // Beim Modal öffnen - Auto-Generate Serial vom Server
            const modal = document.getElementById('deviceModal');
            if (modal) {
                modal.addEventListener('shown.bs.modal', function() {
                    // Nur bei neuem Gerät (nicht beim Editieren)
                    if (!document.getElementById('device_id').value) {
                        // Serial Number generieren
                        if (!serialInput.value) {
                            fetch('/devices/generate-serial')
                                .then(response => response.json())
                                .then(data => {
                                    if (data.success) {
                                        serialInput.value = data.serial;
                                    }
                                });
                        }
                        // Name generieren
                        updateDeviceName();
                    }
                });

                // Reset beim Modal schließen
                modal.addEventListener('hidden.bs.modal', function() {
                    if (!document.getElementById('device_id').value) {
                        document.getElementById('deviceForm').reset();
                        document.getElementById('deviceModalTitle').textContent = 'Neues Gerät hinzufügen';
                        document.getElementById('deviceForm').action = '/devices/add';
                    }
                });
            }
        });
        </script>
        """
    # CSS für erweiterte Geräte-Ansicht
    extra_css = """
    <style>
        .device-card {
            position: relative;
            transition: all 0.3s;
            border-radius: 15px;
            overflow: hidden;
        }
        .device-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.15);
        }
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
        .device-card.status-offline::before { background: #dc3545; }

        .connection-badge {
            position: absolute;
            top: 10px;
            right: 10px;
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .connection-online { background: #d4edda; color: #155724; }
        .connection-offline { background: #f8d7da; color: #721c24; }
        .connection-telemetry { background: #d1ecf1; color: #0c5460; }

        .inventory-bar {
            height: 8px;
            background: #e9ecef;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 5px;
        }
        .inventory-fill {
            height: 100%;
            background: linear-gradient(90deg, #28a745, #20c997);
            transition: width 0.3s;
        }

        .change-money-display {
            display: flex;
            gap: 5px;
            flex-wrap: wrap;
            margin-top: 5px;
        }
        .coin-badge {
            background: #ffc107;
            color: #000;
            padding: 2px 6px;
            border-radius: 10px;
            font-size: 0.7rem;
        }

        .action-buttons {
            display: flex;
            gap: 5px;
            margin-top: 10px;
        }

        .inventory-item, .change-item {
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
            border-bottom: 1px solid #e9ecef;
        }

        .stat-mini {
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
            font-size: 0.9rem;
        }

        .maintenance-badge {
            background: #fff3cd;
            color: #856404;
            padding: 5px 10px;
            border-radius: 10px;
            font-size: 0.8rem;
            margin-top: 10px;
        }
    </style>
    """

    # HTML Content
    content = f"""
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="text-white">
            <i class="bi bi-pc-display"></i> Geräte-Verwaltung
        </h2>
        <button class="btn btn-light" data-bs-toggle="modal" data-bs-target="#deviceModal">
            <i class="bi bi-plus-circle"></i> Gerät hinzufügen
        </button>
    </div>

    <!-- Statistik-Übersicht -->
    <div class="row mb-4">
        <div class="col-md-3">
            <div class="card">
                <div class="card-body text-center">
                    <h4>{len(devices)}</h4>
                    <small class="text-muted">Geräte gesamt</small>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card">
                <div class="card-body text-center">
                    <h4>{len([d for d in devices if d.status == DeviceStatus.ACTIVE])}</h4>
                    <small class="text-muted">Aktiv</small>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card">
                <div class="card-body text-center">
                    <h4>{sum(device_stats[d.id]['month_revenue'] for d in devices):.2f} €</h4>
                    <small class="text-muted">Einnahmen (30 Tage)</small>
                </div>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card">
                <div class="card-body text-center">
                    <h4>{len([d for d in devices if hasattr(d, 'connection_type') and d.connection_type == 'online'])}</h4>
                    <small class="text-muted">Online</small>
                </div>
            </div>
        </div>
    </div>

    <!-- Geräte-Karten -->
    <div class="row">
    """

    if devices:
        for device in devices:
            stats = device_stats.get(device.id, {})
            status_color = {
                'active': 'success',
                'maintenance': 'warning',
                'inactive': 'secondary',
                'offline': 'danger'
            }.get(device.status.value if hasattr(device.status, 'value') else 'inactive', 'secondary')

            # Connection Status
            connection_type = getattr(device, 'connection_type', 'offline')
            connection_badge = f'<span class="connection-badge connection-{connection_type}">'
            if connection_type == 'online':
                connection_badge += '<i class="bi bi-wifi"></i> Online'
            elif connection_type == 'telemetry':
                connection_badge += '<i class="bi bi-broadcast"></i> Telemetrie'
            else:
                connection_badge += '<i class="bi bi-wifi-off"></i> Offline'
            connection_badge += '</span>'

            # Inventar-Anzeige
            inventory_html = ''
            if stats.get('inventory'):
                total_items = sum(stats['inventory'].values())
                inventory_html = f'<div class="stat-mini"><span>Inventar:</span><span>{total_items} Produkte</span></div>'

            # Wechselgeld-Anzeige
            change_html = ''
            if stats.get('change_money'):
                total_change = sum(float(coin) * qty for coin, qty in stats['change_money'].items())
                change_html = f'<div class="stat-mini"><span>Wechselgeld:</span><span>{total_change:.2f} €</span></div>'

            content += f"""
            <div class="col-md-6 col-lg-4 mb-4">
                <div class="card device-card status-{device.status.value if hasattr(device.status, 'value') else 'inactive'}">
                    {connection_badge}
                    <div class="card-body">
                        <h5 class="card-title">{device.name}</h5>
                        <p class="text-muted mb-2">
                            <i class="bi bi-tag"></i> {device.type.value.title() if hasattr(device.type, 'value') else 'Unbekannt'}<br>
                            <i class="bi bi-geo-alt"></i> {device.location or 'Kein Standort'}<br>
                            <i class="bi bi-upc"></i> {device.serial_number or 'Keine SN'}
                        </p>

                        <div class="mb-2">
                            <span class="badge bg-{status_color}">
                                {device.status.value.title() if hasattr(device.status, 'value') else 'Unbekannt'}
                            </span>
                        </div>

                        <div class="stats-section">
                            <div class="stat-mini">
                                <span>Einnahmen (30T):</span>
                                <span class="fw-bold">{stats.get('month_revenue', 0):.2f} €</span>
                            </div>
                            {inventory_html}
                            {change_html}
                        </div>

                        <div class="action-buttons">
                            <button class="btn btn-sm btn-info" onclick="showDeviceDetails({device.id})" title="Details">
                                <i class="bi bi-eye"></i>
                            </button>
                            <button class="btn btn-sm btn-warning" onclick="editDevice({device.id})" title="Bearbeiten">
                                <i class="bi bi-pencil"></i>
                            </button>
                            <button class="btn btn-sm btn-success" onclick="showInventoryModal({device.id})" title="Inventar">
                                <i class="bi bi-box-seam"></i>
                            </button>
                            <button class="btn btn-sm btn-primary" onclick="showChangeMoneyModal({device.id})" title="Wechselgeld">
                                <i class="bi bi-coin"></i>
                            </button>
                            <button class="btn btn-sm btn-danger" onclick="deleteDevice({device.id}, '{device.name}')" title="Löschen">
                                <i class="bi bi-trash"></i>
                            </button>
                        </div>
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

    <!-- Device Modal (Hinzufügen/Bearbeiten) -->
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
                                    <input type="text" id="manufacturer" name="manufacturer" class="form-control">
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="mb-3">
                                    <label class="form-label">Modell</label>
                                    <input type="text" id="model" name="model" class="form-control">
                                </div>
                            </div>
                        </div>

                        <div class="mb-3">
                            <label class="form-label">Seriennummer</label>
                            <input type="text" id="serial_number" name="serial_number" class="form-control">
                        </div>

                        <div class="row">
                            <div class="col-md-6">
                                <div class="mb-3">
                                    <label class="form-label">Standort</label>
                                    <input type="text" id="location" name="location" class="form-control">
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="mb-3">
                                    <label class="form-label">Anschaffungspreis (€)</label>
                                    <input type="number" id="purchase_price" name="purchase_price" 
                                           class="form-control" step="0.01">
                                </div>
                            </div>
                        </div>

                        <div class="row">
                            <div class="col-md-6">
                                <div class="mb-3">
                                    <label class="form-label">Status</label>
                                    <select id="status" name="status" class="form-select">
                                        <option value="active">✅ Aktiv</option>
                                        <option value="maintenance">🔧 Wartung</option>
                                        <option value="inactive">⏸️ Inaktiv</option>
                                        <option value="offline">🔴 Offline</option>
                                    </select>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="mb-3">
                                    <label class="form-label">Datenanbindung</label>
                                    <select id="connection_type" name="connection_type" class="form-select">
                                        <option value="offline">📵 Offline (Manuell)</option>
                                        <option value="online">🌐 Online (API)</option>
                                        <option value="telemetry">📡 Telemetrie</option>
                                    </select>
                                </div>
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

    <!-- Inventar Modal -->
    <div class="modal fade" id="inventoryModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Inventar verwalten</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <form method="POST" action="/devices/update-inventory">
                    <div class="modal-body">
                        <input type="hidden" id="inventory_device_id" name="device_id">

                        <div class="alert alert-info">
                            <i class="bi bi-info-circle"></i> Geben Sie die aktuelle Anzahl der Produkte im Automaten ein
                        </div>
    """

    # Produkte für Inventar laden
    products = Product.query.filter_by(user_id=current_user.id).all()

    if products:
        for product in products:
            content += f"""
                        <div class="mb-2">
                            <label class="form-label">{product.name}</label>
                            <div class="input-group">
                                <span class="input-group-text">{product.unit}</span>
                                <input type="number" id="product_{product.id}" name="product_{product.id}" 
                                       class="form-control" min="0" max="999" value="0">
                                <span class="input-group-text">Stück</span>
                            </div>
                        </div>
            """
    else:
        content += '<p class="text-muted">Keine Produkte vorhanden. Bitte erst Produkte anlegen.</p>'

    content += """
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Abbrechen</button>
                        <button type="submit" class="btn btn-success">
                            <i class="bi bi-save"></i> Inventar speichern
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <!-- Wechselgeld Modal -->
    <div class="modal fade" id="changeMoneyModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Wechselgeld verwalten</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <form method="POST" action="/devices/update-change">
                    <div class="modal-body">
                        <input type="hidden" id="change_device_id" name="device_id">

                        <div class="alert alert-info">
                            <i class="bi bi-info-circle"></i> Anzahl der Münzen im Wechselgeldgeber
                        </div>
    """

    # Wechselgeld-Eingabe
    for coin, info in COIN_DENOMINATIONS.items():
        content += f"""
                        <div class="mb-2">
                            <label class="form-label">{info['name']}</label>
                            <div class="input-group">
                                <button type="button" class="btn btn-outline-secondary" 
                                        onclick="adjustCoin('{coin}', -10)">-10</button>
                                <button type="button" class="btn btn-outline-secondary" 
                                        onclick="adjustCoin('{coin}', -1)">-</button>
                                <input type="number" id="coin_{coin.replace('.', '_')}" 
                                       name="coin_{coin.replace('.', '_')}" 
                                       class="form-control text-center coin-input" 
                                       data-coin="{coin}" value="0" min="0" max="100" 
                                       onchange="calculateChangeTotal()">
                                <button type="button" class="btn btn-outline-secondary" 
                                        onclick="adjustCoin('{coin}', 1)">+</button>
                                <button type="button" class="btn btn-outline-secondary" 
                                        onclick="adjustCoin('{coin}', 10)">+10</button>
                            </div>
                        </div>
        """

    content += """
                        <div class="alert alert-success mt-3">
                            <strong>Gesamt: <span id="changeTotalAmount">0.00</span> €</strong>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Abbrechen</button>
                        <button type="submit" class="btn btn-primary">
                            <i class="bi bi-save"></i> Wechselgeld speichern
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <!-- Details Modal -->
    <div class="modal fade" id="deviceDetailsModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Geräte-Details: <span id="detailDeviceName"></span></h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="row">
                        <div class="col-md-6">
                            <h6>Geräteinformationen</h6>
                            <table class="table table-sm">
                                <tr><td>Typ:</td><td id="detailDeviceType"></td></tr>
                                <tr><td>Status:</td><td id="detailDeviceStatus"></td></tr>
                                <tr><td>Standort:</td><td id="detailDeviceLocation"></td></tr>
                            </table>
                        </div>
                        <div class="col-md-6">
                            <h6>Inventar</h6>
                            <div id="inventoryList"></div>
                        </div>
                    </div>
                    <div class="row mt-3">
                        <div class="col-md-6">
                            <h6>Wechselgeld</h6>
                            <div id="changeList"></div>
                        </div>
                        <div class="col-md-6">
                            <h6>Statistiken</h6>
                            <canvas id="revenueChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """

    return render_template_string(
        render_with_base(
            content,
            active_page='devices',
            title='Geräte - Automaten Manager',
            extra_scripts=extra_scripts,
            extra_css=extra_css
        )
    )

@devices_bp.route('/generate-name')
@login_required
def generate_name():
    """API Route für automatische Namengenerierung"""
    device_type = request.args.get('device_type')

    if device_type:
        name = generate_device_name(device_type)
        return jsonify({'success': True, 'name': name})

    return jsonify({'success': False, 'error': 'Device type required'})


@devices_bp.route('/generate-serial')
@login_required
def generate_serial():
    """API Route für automatische Seriennummer-Generierung"""
    serial = generate_serial_number('unknown')  # Basis-Seriennummer
    return jsonify({'success': True, 'serial': serial})


@devices_bp.route('/add', methods=['POST'])
@login_required
def add_device():
    """Gerät hinzufügen"""
    try:
        # Auto-generate serial number if empty
        serial_number = request.form.get('serial_number')
        if not serial_number:
            serial_number = generate_serial_number(
                request.form.get('type'),
                request.form.get('manufacturer')
            )

        # Auto-generate name if empty  <-- HIER EINFÜGEN
        name = request.form.get('name')
        if not name:
            name = generate_device_name(
                request.form.get('type'),
            )

        device = Device(
            name=name,
            type=DeviceType(request.form.get('type')),
            manufacturer=request.form.get('manufacturer'),
            model=request.form.get('model'),
            serial_number=serial_number,
            location=request.form.get('location'),
            purchase_price=Decimal(request.form.get('purchase_price', 0)),
            status=DeviceStatus(request.form.get('status', 'active')),
            connection_type=request.form.get('connection_type', 'offline'),
            owner_id=current_user.id
        )

        db.session.add(device)
        db.session.commit()

        flash(f'Gerät "{device.name}" wurde hinzugefügt!', 'success')
    except Exception as e:
        flash(f'Fehler: {str(e)}', 'danger')
        db.session.rollback()

    return redirect(url_for('devices.index'))


@devices_bp.route('/edit/<int:device_id>', methods=['POST'])
@login_required
def edit_device(device_id):
    """Gerät bearbeiten"""
    device = Device.query.filter_by(id=device_id, owner_id=current_user.id).first_or_404()

    try:
        device.name = request.form.get('name')
        device.type = DeviceType(request.form.get('type'))
        device.manufacturer = request.form.get('manufacturer')
        device.model = request.form.get('model')
        device.serial_number = request.form.get('serial_number')
        device.location = request.form.get('location')
        device.purchase_price = Decimal(request.form.get('purchase_price', 0))
        device.status = DeviceStatus(request.form.get('status'))
        device.connection_type = request.form.get('connection_type')

        db.session.commit()
        flash(f'Gerät "{device.name}" wurde aktualisiert!', 'success')
    except Exception as e:
        flash(f'Fehler: {str(e)}', 'danger')
        db.session.rollback()

    return redirect(url_for('devices.index'))


@devices_bp.route('/update-inventory', methods=['POST'])
@login_required
def update_inventory():
    """Inventar aktualisieren"""
    device_id = request.form.get('device_id')
    device = Device.query.filter_by(id=device_id, owner_id=current_user.id).first_or_404()

    try:
        inventory = {}
        for key, value in request.form.items():
            if key.startswith('product_'):
                product_id = key.replace('product_', '')
                quantity = int(value)
                if quantity > 0:
                    inventory[product_id] = quantity

        device.inventory_data = json.dumps(inventory)
        device.last_inventory_update = datetime.now()

        db.session.commit()
        flash('Inventar wurde aktualisiert!', 'success')
    except Exception as e:
        flash(f'Fehler: {str(e)}', 'danger')
        db.session.rollback()

    return redirect(url_for('devices.index'))


@devices_bp.route('/update-change', methods=['POST'])
@login_required
def update_change_money():
    """Wechselgeld aktualisieren"""
    device_id = request.form.get('device_id')
    device = Device.query.filter_by(id=device_id, owner_id=current_user.id).first_or_404()

    try:
        change_money = {}
        for coin in COIN_DENOMINATIONS.keys():
            field_name = f"coin_{coin.replace('.', '_')}"
            quantity = int(request.form.get(field_name, 0))
            if quantity > 0:
                change_money[coin] = quantity

        device.change_money = json.dumps(change_money)
        device.last_change_update = datetime.now()

        db.session.commit()
        flash('Wechselgeld wurde aktualisiert!', 'success')
    except Exception as e:
        flash(f'Fehler: {str(e)}', 'danger')
        db.session.rollback()

    return redirect(url_for('devices.index'))


@devices_bp.route('/api/<int:device_id>')
@login_required
def get_device_api(device_id):
    """API Endpoint für Device-Details"""
    device = Device.query.filter_by(id=device_id, owner_id=current_user.id).first_or_404()

    # Inventar laden
    inventory = {}
    product_names = {}
    if hasattr(device, 'inventory_data') and device.inventory_data:
        try:
            inventory = json.loads(device.inventory_data)
            # Produktnamen laden
            for product_id in inventory.keys():
                product = Product.query.get(product_id)
                if product:
                    product_names[product_id] = product.name
        except:
            pass

    # Wechselgeld laden
    change_money = {}
    if hasattr(device, 'change_money') and device.change_money:
        try:
            change_money = json.loads(device.change_money)
        except:
            pass

    return jsonify({
        'id': device.id,
        'name': device.name,
        'type': device.type.value if hasattr(device.type, 'value') else '',
        'manufacturer': getattr(device, 'manufacturer', ''),
        'model': getattr(device, 'model', ''),
        'serial_number': device.serial_number,
        'location': device.location,
        'purchase_price': float(device.purchase_price) if device.purchase_price else 0,
        'status': device.status.value if hasattr(device.status, 'value') else '',
        'connection_type': getattr(device, 'connection_type', 'offline'),
        'inventory': inventory,
        'product_names': product_names,
        'change_money': change_money
    })


@devices_bp.route('/delete/<int:device_id>', methods=['POST'])
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

    return redirect(url_for('devices.index'))