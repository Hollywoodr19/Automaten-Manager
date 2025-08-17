# app/web/inventory.py
"""
Inventur-Modul für Automaten Manager - Lagerbestand direkt bearbeiten
"""

from flask import Blueprint, render_template_string, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, date
from decimal import Decimal
from app import db
from app.models import Product, InventoryMovement, Device

inventory_bp = Blueprint('inventory', __name__, url_prefix='/inventory')


@inventory_bp.route('/stocktaking')
@login_required
def stocktaking():
    """Inventur - Lagerbestand anpassen"""
    products = Product.query.filter_by(user_id=current_user.id).all()
    devices = Device.query.filter_by(owner_id=current_user.id).all()
    
    # JavaScript für Inventur
    extra_scripts = """
    <script>
    function updateStock(productId) {
        const newStock = document.getElementById(`stock_${productId}`).value;
        const currentStock = document.getElementById(`current_${productId}`).textContent;
        const difference = parseFloat(newStock) - parseFloat(currentStock);
        
        // Zeige Differenz
        const diffElement = document.getElementById(`diff_${productId}`);
        if (difference > 0) {
            diffElement.innerHTML = `<span class="text-success">+${difference.toFixed(2)}</span>`;
        } else if (difference < 0) {
            diffElement.innerHTML = `<span class="text-danger">${difference.toFixed(2)}</span>`;
        } else {
            diffElement.innerHTML = `<span class="text-muted">0.00</span>`;
        }
    }
    
    function saveInventory() {
        const form = document.getElementById('inventoryForm');
        const formData = new FormData(form);
        
        // Sammle alle Änderungen
        const changes = [];
        const inputs = document.querySelectorAll('.stock-input');
        
        inputs.forEach(input => {
            const productId = input.dataset.productId;
            const currentStock = parseFloat(document.getElementById(`current_${productId}`).textContent);
            const newStock = parseFloat(input.value);
            
            if (newStock !== currentStock) {
                changes.push({
                    product_id: productId,
                    old_stock: currentStock,
                    new_stock: newStock,
                    difference: newStock - currentStock
                });
            }
        });
        
        if (changes.length === 0) {
            alert('Keine Änderungen vorgenommen.');
            return;
        }
        
        // Bestätigung
        if (!confirm(`${changes.length} Produkt(e) werden angepasst. Fortfahren?`)) {
            return;
        }
        
        // Sende Änderungen
        fetch('/inventory/update_stock', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                changes: changes,
                reason: document.getElementById('reason').value,
                device_id: document.getElementById('device_id').value
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('Inventur erfolgreich gespeichert!');
                window.location.reload();
            } else {
                alert('Fehler: ' + data.message);
            }
        })
        .catch(error => {
            alert('Fehler beim Speichern: ' + error);
        });
    }
    
    function quickAdjust(productId, amount) {
        const input = document.getElementById(`stock_${productId}`);
        const currentValue = parseFloat(input.value) || 0;
        input.value = Math.max(0, currentValue + amount).toFixed(2);
        updateStock(productId);
    }
    </script>
    """
    
    # CSS
    extra_css = """
    <style>
        .inventory-table {
            background: white;
            border-radius: 10px;
            overflow: hidden;
        }
        
        .inventory-table th {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px;
        }
        
        .inventory-table td {
            padding: 10px;
            vertical-align: middle;
        }
        
        .stock-input {
            max-width: 120px;
        }
        
        .quick-adjust {
            display: flex;
            gap: 5px;
        }
        
        .quick-adjust button {
            padding: 2px 8px;
            font-size: 12px;
        }
        
        .stock-status {
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
        }
        
        .stock-critical { background: #ffebee; color: #c62828; }
        .stock-low { background: #fff3cd; color: #856404; }
        .stock-ok { background: #d4edda; color: #155724; }
    </style>
    """
    
    # HTML Content
    content = """
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="text-white">
            <i class="bi bi-clipboard-check"></i> Inventur / Lagerbestand anpassen
        </h2>
        <a href="/refills" class="btn btn-outline-light">
            <i class="bi bi-arrow-left"></i> Zurück
        </a>
    </div>
    
    <div class="card mb-3">
        <div class="card-body">
            <div class="row">
                <div class="col-md-6">
                    <label class="form-label">Grund für Inventur</label>
                    <input type="text" id="reason" class="form-control" 
                           placeholder="z.B. Monatliche Inventur, Korrektur, Schwund" value="Manuelle Inventur">
                </div>
                <div class="col-md-6">
                    <label class="form-label">Gerät (optional)</label>
                    <select id="device_id" class="form-select">
                        <option value="">-- Alle Geräte --</option>
    """
    
    for device in devices:
        content += f'<option value="{device.id}">{device.name}</option>'
    
    content += """
                    </select>
                </div>
            </div>
        </div>
    </div>
    
    <div class="card">
        <div class="card-header">
            <h5 class="mb-0">Produkte</h5>
        </div>
        <div class="card-body">
            <form id="inventoryForm">
                <table class="table inventory-table">
                    <thead>
                        <tr>
                            <th>Produkt</th>
                            <th>Kategorie</th>
                            <th>Aktueller Bestand</th>
                            <th>Neuer Bestand</th>
                            <th>Differenz</th>
                            <th>Schnellanpassung</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
    """
    
    for product in products:
        current_stock = product.get_current_stock()
        
        # Status berechnen
        if product.min_stock:
            if current_stock <= 0:
                status = '<span class="stock-status stock-critical">Leer</span>'
            elif current_stock <= product.min_stock:
                status = '<span class="stock-status stock-low">Niedrig</span>'
            else:
                status = '<span class="stock-status stock-ok">OK</span>'
        else:
            status = '<span class="stock-status stock-ok">OK</span>'
        
        category_name = product.category.value if product.category else 'Keine'
        
        content += f"""
                        <tr>
                            <td><strong>{product.name}</strong></td>
                            <td>{category_name}</td>
                            <td>
                                <span id="current_{product.id}">{current_stock:.2f}</span> {product.unit.value}
                            </td>
                            <td>
                                <input type="number" 
                                       id="stock_{product.id}" 
                                       class="form-control stock-input" 
                                       data-product-id="{product.id}"
                                       value="{current_stock:.2f}" 
                                       step="0.01" 
                                       min="0"
                                       onchange="updateStock({product.id})">
                            </td>
                            <td id="diff_{product.id}">
                                <span class="text-muted">0.00</span>
                            </td>
                            <td>
                                <div class="quick-adjust">
                                    <button type="button" class="btn btn-sm btn-outline-danger" 
                                            onclick="quickAdjust({product.id}, -10)">-10</button>
                                    <button type="button" class="btn btn-sm btn-outline-warning" 
                                            onclick="quickAdjust({product.id}, -1)">-1</button>
                                    <button type="button" class="btn btn-sm btn-outline-success" 
                                            onclick="quickAdjust({product.id}, 1)">+1</button>
                                    <button type="button" class="btn btn-sm btn-outline-primary" 
                                            onclick="quickAdjust({product.id}, 10)">+10</button>
                                </div>
                            </td>
                            <td>{status}</td>
                        </tr>
        """
    
    content += """
                    </tbody>
                </table>
            </form>
            
            <div class="mt-4">
                <button type="button" class="btn btn-primary btn-lg" onclick="saveInventory()">
                    <i class="bi bi-save"></i> Inventur speichern
                </button>
                <button type="button" class="btn btn-secondary btn-lg ms-2" onclick="window.location.reload()">
                    <i class="bi bi-arrow-clockwise"></i> Zurücksetzen
                </button>
            </div>
            
            <div class="alert alert-info mt-3">
                <i class="bi bi-info-circle"></i> 
                <strong>Hinweis:</strong> Änderungen werden als Inventurbewegungen gespeichert und sind nachvollziehbar.
            </div>
        </div>
    </div>
    """
    
    # Use modern template
    from app.web.dashboard_modern import render_modern_template
    
    full_content = extra_css + content + extra_scripts
    
    return render_modern_template(
        content=full_content,
        title='Inventur',
        active_module='inventory',
        active_submodule='stocktaking',
        breadcrumb=[
            {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
            {'text': 'Warenwirtschaft', 'url': url_for('dashboard_modern.inventory')},
            {'text': 'Inventur'}
        ]
    )


@inventory_bp.route('/update_stock', methods=['POST'])
@login_required
def update_stock():
    """Lagerbestand aktualisieren (AJAX)"""
    try:
        data = request.get_json()
        changes = data.get('changes', [])
        reason = data.get('reason', 'Manuelle Inventur')
        device_id = data.get('device_id') or None
        
        for change in changes:
            product_id = int(change['product_id'])
            new_stock = Decimal(str(change['new_stock']))
            difference = Decimal(str(change['difference']))
            
            # Erstelle Inventurbewegung
            movement = InventoryMovement(
                product_id=product_id,
                device_id=device_id,
                type='ADJUSTMENT' if difference > 0 else 'CORRECTION',
                quantity=abs(difference),
                reason=reason,
                user_id=current_user.id
            )
            db.session.add(movement)
            
            # Optional: Direkte Aktualisierung des Produktbestands
            # (nur wenn das Modell ein current_stock Feld hat)
            product = Product.query.get(product_id)
            if hasattr(product, 'current_stock'):
                product.current_stock = new_stock
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'{len(changes)} Produkte aktualisiert'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@inventory_bp.route('/quick_view')
@login_required  
def quick_view():
    """Schnellansicht des Lagerbestands"""
    products = Product.query.filter_by(user_id=current_user.id).all()
    
    # Gruppiere nach Kategorien
    by_category = {}
    for product in products:
        category = product.category.value if product.category else 'Sonstige'
        if category not in by_category:
            by_category[category] = []
        
        stock = product.get_current_stock()
        status = 'ok'
        if product.min_stock:
            if stock <= 0:
                status = 'empty'
            elif stock <= product.min_stock:
                status = 'low'
        
        by_category[category].append({
            'name': product.name,
            'stock': stock,
            'unit': product.unit.value,
            'status': status
        })
    
    content = """
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="text-white">
            <i class="bi bi-boxes"></i> Lagerbestand Schnellansicht
        </h2>
        <div>
            <a href="/inventory/stocktaking" class="btn btn-warning">
                <i class="bi bi-clipboard-check"></i> Inventur durchführen
            </a>
            <a href="/refills" class="btn btn-success ms-2">
                <i class="bi bi-plus-circle"></i> Nachfüllung
            </a>
        </div>
    </div>
    
    <div class="row">
    """
    
    for category, items in by_category.items():
        # Zähle Status
        empty_count = sum(1 for i in items if i['status'] == 'empty')
        low_count = sum(1 for i in items if i['status'] == 'low')
        
        content += f"""
        <div class="col-md-6 mb-3">
            <div class="card">
                <div class="card-header bg-primary text-white">
                    <h6 class="mb-0">{category}</h6>
                    {f'<span class="badge bg-danger">{empty_count} leer</span>' if empty_count > 0 else ''}
                    {f'<span class="badge bg-warning">{low_count} niedrig</span>' if low_count > 0 else ''}
                </div>
                <div class="card-body">
                    <table class="table table-sm">
        """
        
        for item in items:
            badge = ''
            if item['status'] == 'empty':
                badge = '<span class="badge bg-danger">Leer</span>'
            elif item['status'] == 'low':
                badge = '<span class="badge bg-warning">Niedrig</span>'
            
            content += f"""
                        <tr>
                            <td>{item['name']}</td>
                            <td class="text-end">{item['stock']:.1f} {item['unit']}</td>
                            <td>{badge}</td>
                        </tr>
            """
        
        content += """
                    </table>
                </div>
            </div>
        </div>
        """
    
    content += """
    </div>
    """
    
    # Use modern template
    from app.web.dashboard_modern import render_modern_template
    
    return render_modern_template(
        content=content,
        title='Lagerbestand',
        active_module='inventory',
        active_submodule='stock',
        breadcrumb=[
            {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
            {'text': 'Warenwirtschaft', 'url': url_for('dashboard_modern.inventory')},
            {'text': 'Lagerbestand'}
        ]
    )
