# app/web/refills.py
"""
Warenwirtschafts-Modul für Automaten Manager - Mit Zeilen-Rabatt und Kassenbon-Upload
"""

from flask import Blueprint, render_template_string, redirect, url_for, flash, request, jsonify, get_flashed_messages
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from decimal import Decimal
from app import db
from app.models import (
    Device, Expense, ExpenseCategory,
    Product, ProductUnit, ProductCategory,
    Supplier, Refill, RefillItem, InventoryMovement
)
from app.web.navigation import render_with_base_new as render_with_base
import json
import base64

refills_bp = Blueprint('refills', __name__, url_prefix='/refills')


@refills_bp.route('/')
@login_required
def index():
    """Warenwirtschafts-Übersicht"""
    # Letzte Nachfüllungen
    refills = Refill.query.filter_by(user_id=current_user.id) \
        .order_by(Refill.date.desc()) \
        .limit(10).all()

    # Produkte mit niedrigem Bestand
    products = Product.query.filter_by(user_id=current_user.id).all()
    low_stock_products = []

    for product in products:
        current_stock = product.get_current_stock()
        if product.reorder_point and current_stock <= product.reorder_point:
            low_stock_products.append({
                'product': product,
                'current_stock': current_stock,
                'percentage': (current_stock / product.reorder_point * 100) if product.reorder_point > 0 else 0
            })

    # JavaScript mit verbesserter Berechnung und Upload
    extra_scripts = """
    <script>
    let itemCount = 0;

    function addProductLine() {
        itemCount++;
        const template = `
            <div class="product-row" id="item-${itemCount}">
                <div class="row align-items-center">
                    <div class="col-md-3">
                        <label class="form-label small mb-1">Produkt</label>
                        <select class="form-select product-select" name="product_id[]" required onchange="updatePrice(${itemCount})">
                            <option value="">-- Wählen --</option>
    """

    # Produkte für JavaScript
    for product in products:
        unit_price = product.default_price or 0
        extra_scripts += f"""
                            <option value="{product.id}" data-price="{unit_price}" data-unit="{product.unit.value}">
                                {product.name} ({product.unit.value})
                            </option>
        """

    extra_scripts += f"""
                        </select>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label small mb-1">Menge</label>
                        <input type="number" class="form-control quantity-input" name="quantity[]" 
                               placeholder="0" step="0.001" required onchange="calculateTotal(${{itemCount}})">
                    </div>
                    <div class="col-md-2">
                        <label class="form-label small mb-1">Stückpreis €</label>
                        <input type="number" class="form-control price-input" name="unit_price[]" 
                               placeholder="0.00" step="0.01" required onchange="calculateTotal(${{itemCount}})">
                    </div>
                    <div class="col-md-2">
                        <label class="form-label small mb-1">Rabatt €</label>
                        <input type="number" class="form-control discount-input bg-warning bg-opacity-10" 
                               name="line_discount[]" placeholder="0.00" step="0.01" value="0" 
                               onchange="calculateTotal(${{itemCount}})" title="Rabatt für diese Position">
                    </div>
                    <div class="col-md-2">
                        <label class="form-label small mb-1">Gesamt €</label>
                        <input type="text" class="form-control total-input fw-bold" name="total_price[]" 
                               placeholder="0.00" readonly>
                    </div>
                    <div class="col-md-1 text-center">
                        <label class="form-label small mb-1">&nbsp;</label><br>
                        <button type="button" class="btn btn-sm btn-danger" onclick="removeItem(${{itemCount}})">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
                <div class="row mt-1">
                    <div class="col-md-11">
                        <input type="text" class="form-control form-control-sm" name="line_discount_reason[]" 
                               placeholder="Rabatt-Grund (optional, z.B. Mengenrabatt, Aktion)">
                    </div>
                </div>
            </div>
        `;

        document.getElementById('product-items').insertAdjacentHTML('beforeend', template);
    }}

    function removeItem(id) {{
        document.getElementById(`item-${{id}}`).remove();
        calculateGrandTotal();
    }}

    function updatePrice(id) {{
        const select = document.querySelector(`#item-${{id}} .product-select`);
        const priceInput = document.querySelector(`#item-${{id}} .price-input`);
        const selectedOption = select.options[select.selectedIndex];

        if (selectedOption.dataset.price) {{
            priceInput.value = selectedOption.dataset.price;
            calculateTotal(id);
        }}
    }}

    function calculateTotal(id) {{
        const quantity = parseFloat(document.querySelector(`#item-${{id}} .quantity-input`).value) || 0;
        const price = parseFloat(document.querySelector(`#item-${{id}} .price-input`).value) || 0;
        const discount = parseFloat(document.querySelector(`#item-${{id}} .discount-input`).value) || 0;

        // Berechnung: (Menge × Preis) - Rabatt
        const grossTotal = quantity * price;
        const netTotal = grossTotal - discount;

        // Visual feedback wenn Rabatt vorhanden
        const discountInput = document.querySelector(`#item-${{id}} .discount-input`);
        if (discount > 0) {{
            discountInput.classList.add('border-warning');
            // Zeige Ersparnis in Prozent
            if (grossTotal > 0) {{
                const savedPercent = ((discount / grossTotal) * 100).toFixed(1);
                discountInput.title = `Ersparnis: ${{savedPercent}}%`;
            }}
        }} else {{
            discountInput.classList.remove('border-warning');
        }}

        document.querySelector(`#item-${{id}} .total-input`).value = netTotal.toFixed(2);
        calculateGrandTotal();
    }}

    function calculateGrandTotal() {{
        let grandTotal = 0;
        let totalLineDiscounts = 0;

        // Summiere alle Zeilen-Rabatte
        document.querySelectorAll('.discount-input').forEach(input => {{
            totalLineDiscounts += parseFloat(input.value) || 0;
        }});

        // Summiere alle Zeilen-Totale (bereits mit Rabatt)
        document.querySelectorAll('.total-input').forEach(input => {{
            grandTotal += parseFloat(input.value) || 0;
        }});

        const taxRate = parseFloat(document.getElementById('taxRate').value) || 20;
        const pricesIncludeTax = document.getElementById('pricesIncludeTax').checked;
        const shipping = parseFloat(document.querySelector('[name="shipping_cost"]').value) || 0;
        const deposit = parseFloat(document.querySelector('[name="deposit_amount"]').value) || 0;
        const globalDiscount = parseFloat(document.querySelector('[name="discount_amount"]').value) || 0;

        // Globaler Rabatt zusätzlich
        grandTotal = grandTotal - globalDiscount;

        let subtotal, tax, total;

        if (pricesIncludeTax) {{
            // Preise enthalten bereits MwSt - herausrechnen
            total = grandTotal;
            subtotal = total / (1 + taxRate/100);
            tax = total - subtotal;
        }} else {{
            // Nettopreise - MwSt draufrechnen
            subtotal = grandTotal;
            tax = subtotal * (taxRate/100);
            total = subtotal + tax;
        }}

        // Versand und Pfand hinzufügen
        const finalTotal = total + shipping + deposit;

        // Anzeige aktualisieren
        document.getElementById('subtotal').innerHTML = `
            <small class="text-muted">Warenwert netto:</small><br>
            <strong>${{subtotal.toFixed(2)}} €</strong>
        `;
        document.getElementById('tax').innerHTML = `
            <small class="text-muted">MwSt (${{taxRate}}%):</small><br>
            <strong>${{tax.toFixed(2)}} €</strong>
        `;

        // Zeilen-Rabatte anzeigen
        if (totalLineDiscounts > 0) {{
            document.getElementById('line-discounts-row').style.display = 'flex';
            document.getElementById('line-discounts-display').innerHTML = `
                <span class="text-warning">- ${{totalLineDiscounts.toFixed(2)}} €</span>
            `;
        }} else {{
            document.getElementById('line-discounts-row').style.display = 'none';
        }}

        // Globaler Rabatt
        if (globalDiscount > 0) {{
            document.getElementById('discount-row').style.display = 'flex';
            document.getElementById('discount-display').textContent = '- ' + globalDiscount.toFixed(2) + ' €';
        }} else {{
            document.getElementById('discount-row').style.display = 'none';
        }}

        // Versandzeile
        if (shipping > 0) {{
            document.getElementById('shipping-row').style.display = 'flex';
            document.getElementById('shipping-amount').textContent = shipping.toFixed(2) + ' €';
        }} else {{
            document.getElementById('shipping-row').style.display = 'none';
        }}

        // Pfandzeile
        if (deposit > 0) {{
            document.getElementById('deposit-row').style.display = 'flex';
            document.getElementById('deposit-amount').textContent = deposit.toFixed(2) + ' €';
        }} else {{
            document.getElementById('deposit-row').style.display = 'none';
        }}

        // Gesamtersparnis anzeigen
        const totalSavings = totalLineDiscounts + globalDiscount;
        if (totalSavings > 0) {{
            document.getElementById('savings-info').style.display = 'block';
            document.getElementById('total-savings').textContent = totalSavings.toFixed(2);
        }} else {{
            document.getElementById('savings-info').style.display = 'none';
        }}

        document.getElementById('grand-total').innerHTML = `<strong>${{finalTotal.toFixed(2)}} €</strong>`;
    }}

    // Drag & Drop für Kassenbon
    function setupDragDrop() {{
        const dropZone = document.getElementById('receipt-drop-zone');
        const fileInput = document.getElementById('receipt-file');
        const preview = document.getElementById('receipt-preview');

        if (!dropZone) return;

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {{
            dropZone.addEventListener(eventName, preventDefaults, false);
        }});

        function preventDefaults(e) {{
            e.preventDefault();
            e.stopPropagation();
        }}

        ['dragenter', 'dragover'].forEach(eventName => {{
            dropZone.addEventListener(eventName, () => {{
                dropZone.classList.add('drag-over');
            }}, false);
        }});

        ['dragleave', 'drop'].forEach(eventName => {{
            dropZone.addEventListener(eventName, () => {{
                dropZone.classList.remove('drag-over');
            }}, false);
        }});

        dropZone.addEventListener('drop', handleDrop, false);
        fileInput.addEventListener('change', handleFileSelect, false);

        function handleDrop(e) {{
            const files = e.dataTransfer.files;
            handleFiles(files);
        }}

        function handleFileSelect(e) {{
            const files = e.target.files;
            handleFiles(files);
        }}

        function handleFiles(files) {{
            if (files.length > 0) {{
                const file = files[0];
                if (file.type.match('image.*') || file.type === 'application/pdf') {{
                    const reader = new FileReader();
                    reader.onload = function(e) {{
                        uploadedReceipt = {{
                            name: file.name,
                            type: file.type,
                            data: e.target.result
                        }};
                        showPreview(file, e.target.result);
                    }};
                    reader.readAsDataURL(file);
                }} else {{
                    alert('Bitte nur Bilder oder PDFs hochladen!');
                }}
            }}
        }}

        function showPreview(file, dataUrl) {{
            preview.innerHTML = '';
            if (file.type.match('image.*')) {{
                preview.innerHTML = `
                    <div class="receipt-preview-container">
                        <img src="${{dataUrl}}" class="img-fluid rounded" style="max-height: 200px;">
                        <p class="mt-2 mb-0"><small>${{file.name}}</small></p>
                        <button type="button" class="btn btn-sm btn-danger mt-2" onclick="removeReceipt()">
                            <i class="bi bi-trash"></i> Entfernen
                        </button>
                    </div>
                `;
            }} else {{
                preview.innerHTML = `
                    <div class="receipt-preview-container">
                        <i class="bi bi-file-pdf display-1 text-danger"></i>
                        <p class="mt-2 mb-0"><small>${{file.name}}</small></p>
                        <button type="button" class="btn btn-sm btn-danger mt-2" onclick="removeReceipt()">
                            <i class="bi bi-trash"></i> Entfernen
                        </button>
                    </div>
                `;
            }}

            // Hidden fields für Form Submit
            if (!document.getElementById('receipt_data')) {{
                const hiddenData = document.createElement('input');
                hiddenData.type = 'hidden';
                hiddenData.id = 'receipt_data';
                hiddenData.name = 'receipt_data';
                hiddenData.value = dataUrl;
                document.getElementById('refillForm').appendChild(hiddenData);

                const hiddenName = document.createElement('input');
                hiddenName.type = 'hidden';
                hiddenName.id = 'receipt_filename';
                hiddenName.name = 'receipt_filename';
                hiddenName.value = file.name;
                document.getElementById('refillForm').appendChild(hiddenName);
            }} else {{
                document.getElementById('receipt_data').value = dataUrl;
                document.getElementById('receipt_filename').value = file.name;
            }}
        }}
    }}

    let uploadedReceipt = null;

    function removeReceipt() {{
        uploadedReceipt = null;
        document.getElementById('receipt-preview').innerHTML = '';
        document.getElementById('receipt-file').value = '';
        if (document.getElementById('receipt_data')) {{
            document.getElementById('receipt_data').remove();
            document.getElementById('receipt_filename').remove();
        }}
    }}

    // Event Listener
    document.addEventListener('DOMContentLoaded', function() {{
        const taxRateInput = document.getElementById('taxRate');
        const pricesIncludeTaxCheckbox = document.getElementById('pricesIncludeTax');
        const shippingInput = document.querySelector('[name="shipping_cost"]');
        const depositInput = document.querySelector('[name="deposit_amount"]');
        const discountInput = document.querySelector('[name="discount_amount"]');

        if (taxRateInput) taxRateInput.addEventListener('change', calculateGrandTotal);
        if (pricesIncludeTaxCheckbox) pricesIncludeTaxCheckbox.addEventListener('change', calculateGrandTotal);
        if (shippingInput) shippingInput.addEventListener('input', calculateGrandTotal);
        if (depositInput) depositInput.addEventListener('input', calculateGrandTotal);
        if (discountInput) discountInput.addEventListener('input', calculateGrandTotal);

        setupDragDrop();

        // Erste Zeile hinzufügen
        if (document.getElementById('product-items')) {{
            addProductLine();
        }}
    }});

    function viewRefill(id) {{
        window.location.href = `/refills/view/${{id}}`;
    }}

    // Click handler für Drop Zone
    document.addEventListener('DOMContentLoaded', function() {{
        const dropZone = document.getElementById('receipt-drop-zone');
        if (dropZone) {{
            dropZone.addEventListener('click', function() {{
                document.getElementById('receipt-file').click();
            }});
        }}
    }});
    </script>
    """

    # CSS für Warenwirtschaft und Upload
    extra_css = """
    <style>
        .product-row {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            border: 1px solid #dee2e6;
        }

        .product-row:hover {
            background: #e9ecef;
            border-color: #adb5bd;
        }

        .remove-item {
            cursor: pointer;
            color: #dc3545;
        }

        .remove-item:hover {
            color: #a02030;
        }

        .total-row {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin-top: 20px;
        }

        .stock-badge {
            font-size: 0.75rem;
            padding: 2px 8px;
            border-radius: 12px;
        }

        .stock-low { background: #ffebee; color: #c62828; }
        .stock-ok { background: #e8f5e9; color: #2e7d32; }
        .stock-high { background: #e3f2fd; color: #1565c0; }

        .tax-info-box {
            background: #e3f2fd;
            border-left: 4px solid #1976d2;
            padding: 10px;
            border-radius: 4px;
        }

        /* Drag & Drop Styles */
        .drop-zone {
            border: 2px dashed #ccc;
            border-radius: 8px;
            padding: 30px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
            background: #fafafa;
        }

        .drop-zone:hover {
            border-color: #999;
            background: #f0f0f0;
        }

        .drop-zone.drag-over {
            border-color: #4CAF50;
            background: #e8f5e9;
        }

        .receipt-preview-container {
            text-align: center;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 8px;
            background: white;
        }

        .discount-info {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 10px;
            border-radius: 4px;
        }

        .discount-input.border-warning {
            border-width: 2px !important;
        }

        .savings-badge {
            background: #d4edda;
            color: #155724;
            padding: 10px;
            border-radius: 8px;
            border: 1px solid #c3e6cb;
        }

        .form-label.small {
            font-size: 0.8rem;
            color: #6c757d;
        }
    </style>
    """

    # HTML Content
    content = """
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="text-white">
            <i class="bi bi-box-seam-fill"></i> Warenwirtschaft
        </h2>
        <div>
            <a href="/products" class="btn btn-outline-light me-2">
                <i class="bi bi-box"></i> Produkte verwalten
            </a>
            <button class="btn btn-light" data-bs-toggle="modal" data-bs-target="#refillModal">
                <i class="bi bi-plus-circle"></i> Neue Nachfüllung
            </button>
        </div>
    </div>

    <!-- Niedrige Bestände Warnung -->
    """

    if low_stock_products:
        content += """
        <div class="alert alert-warning">
            <h6><i class="bi bi-exclamation-triangle"></i> Niedrige Bestände - Nachbestellen empfohlen:</h6>
            <ul class="mb-0">
        """
        for item in low_stock_products:
            content += f"""
                <li>{item['product'].name}: {item['current_stock']:.1f} {item['product'].unit.value} 
                    (nur noch {item['percentage']:.0f}% vom Nachbestellpunkt)</li>
            """
        content += """
            </ul>
        </div>
        """

    content += """
    <div class="row">
        <!-- Letzte Nachfüllungen -->
        <div class="col-md-8">
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">
                        <i class="bi bi-clock-history"></i> Letzte Nachfüllungen
                    </h5>
                </div>
                <div class="card-body">
    """

    if refills:
        content += """
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Datum</th>
                                <th>Lieferant</th>
                                <th>Positionen</th>
                                <th>Gesamt</th>
                                <th>Beleg</th>
                                <th>Aktionen</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        for refill in refills:
            supplier_name = refill.supplier.name if refill.supplier else 'Unbekannt'
            item_count = refill.items.count()
            has_receipt = '✅' if hasattr(refill, 'receipt_filename') and refill.receipt_filename else '—'
            content += f"""
                            <tr>
                                <td>{refill.date.strftime('%d.%m.%Y')}</td>
                                <td>{supplier_name}</td>
                                <td>{item_count} Artikel</td>
                                <td>{refill.total_amount:.2f} €</td>
                                <td>{has_receipt}</td>
                                <td>
                                    <button class="btn btn-sm btn-info" onclick="viewRefill({refill.id})">
                                        <i class="bi bi-eye"></i>
                                    </button>
                                </td>
                            </tr>
            """
        content += """
                        </tbody>
                    </table>
        """
    else:
        content += '<p class="text-muted text-center">Noch keine Nachfüllungen erfasst</p>'

    content += """
                </div>
            </div>
        </div>

        <!-- Lagerbestand -->
        <div class="col-md-4">
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">
                        <i class="bi bi-box"></i> Aktueller Bestand
                    </h5>
                </div>
                <div class="card-body">
    """

    for product in products[:5]:  # Nur die ersten 5 zeigen
        stock = product.get_current_stock()
        if product.max_stock:
            percentage = (stock / product.max_stock) * 100
            badge_class = 'stock-high' if percentage > 60 else 'stock-ok' if percentage > 30 else 'stock-low'
        else:
            badge_class = 'stock-ok'

        content += f"""
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <span>{product.name}</span>
                        <span class="stock-badge {badge_class}">
                            {stock:.1f} {product.unit.value}
                        </span>
                    </div>
        """

    content += """
                    <a href="/products" class="btn btn-sm btn-outline-primary w-100 mt-3">
                        Alle Produkte anzeigen
                    </a>
                </div>
            </div>
        </div>
    </div>

    <!-- Neue Nachfüllung Modal -->
    <div class="modal fade" id="refillModal" tabindex="-1">
        <div class="modal-dialog modal-xl">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Neue Nachfüllung erfassen</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <form method="POST" action="/refills/add" id="refillForm" enctype="multipart/form-data">
                    <div class="modal-body">
                        <!-- Kassenbon Upload -->
                        <div class="row mb-3">
                            <div class="col-12">
                                <label class="form-label">📸 Kassenbon / Rechnung</label>
                                <div id="receipt-drop-zone" class="drop-zone">
                                    <i class="bi bi-cloud-upload display-4 text-muted"></i>
                                    <p class="mt-2">Kassenbon hier ablegen oder klicken zum Auswählen</p>
                                    <small class="text-muted">Unterstützt: JPG, PNG, PDF (max. 10MB)</small>
                                    <input type="file" id="receipt-file" accept="image/*,application/pdf" style="display: none;">
                                </div>
                                <div id="receipt-preview" class="mt-3"></div>
                            </div>
                        </div>

                        <hr>

                        <div class="row mb-3">
                            <div class="col-md-4">
                                <label class="form-label">Datum</label>
                                <input type="date" name="date" class="form-control" value="{date.today()}" required>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">Lieferant</label>
                                <select name="supplier_id" class="form-select">
                                    <option value="">-- Wählen --</option>
    """

    # Lieferanten
    suppliers = Supplier.query.filter_by(user_id=current_user.id).all()
    for supplier in suppliers:
        content += f'<option value="{supplier.id}">{supplier.name}</option>'

    content += """
                                </select>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">Gerät</label>
                                <select name="device_id" class="form-select">
                                    <option value="">-- Allgemein --</option>
    """

    # Geräte
    devices = Device.query.filter_by(owner_id=current_user.id).all()
    for device in devices:
        content += f'<option value="{device.id}">{device.name}</option>'

    content += """
                                </select>
                            </div>
                        </div>

                        <div class="row mb-3">
                            <div class="col-md-3">
                                <label class="form-label">Rechnungsnummer</label>
                                <input type="text" name="invoice_number" class="form-control" placeholder="RE-2025-001">
                            </div>
                            <div class="col-md-3">
                                <label class="form-label">Lieferschein</label>
                                <input type="text" name="delivery_note" class="form-control" placeholder="LS-2025-001">
                            </div>
                            <div class="col-md-2">
                                <label class="form-label">Versand (€)</label>
                                <input type="number" name="shipping_cost" class="form-control" step="0.01" value="0.00">
                            </div>
                            <div class="col-md-2">
                                <label class="form-label">Pfand (€)</label>
                                <input type="number" name="deposit_amount" class="form-control" step="0.01" value="0.00"
                                       title="Pfand wird mit 0% MwSt berechnet">
                            </div>
                            <div class="col-md-2">
                                <label class="form-label">Zusatz-Rabatt (€)</label>
                                <input type="number" name="discount_amount" class="form-control" step="0.01" value="0.00"
                                       title="Zusätzlicher Rabatt zum Zeilen-Rabatt">
                            </div>
                        </div>

                        <div class="row mb-3">
                            <div class="col-md-6">
                                <label class="form-label">Zusatz-Rabatt Grund (optional)</label>
                                <input type="text" name="discount_reason" class="form-control" 
                                       placeholder="z.B. Gutschein, Treuerabatt, Sonderaktion">
                            </div>
                            <div class="col-md-2">
                                <label class="form-label">MwSt (%)</label>
                                <input type="number" name="tax_rate" class="form-control" step="0.1" value="20" id="taxRate">
                            </div>
                            <div class="col-md-4">
                                <div class="form-check mt-4">
                                    <input class="form-check-input" type="checkbox" id="pricesIncludeTax" 
                                           name="prices_include_tax" checked>
                                    <label class="form-check-label" for="pricesIncludeTax">
                                        Preise inkl. MwSt
                                    </label>
                                </div>
                            </div>
                        </div>

                        <div class="row mb-3">
                            <div class="col-md-12">
                                <div class="tax-info-box">
                                    <small>
                                        <i class="bi bi-info-circle"></i> 
                                        <strong>✅ Markiert:</strong> Preise enthalten MwSt (wird herausgerechnet) | 
                                        <strong>⬜ Nicht markiert:</strong> Nettopreise (MwSt wird hinzugerechnet) | 
                                        <strong>💰 Zeilen-Rabatt:</strong> Rabatt pro Artikel direkt in der Zeile
                                    </small>
                                </div>
                            </div>
                        </div>

                        <hr>

                        <h6>Produkte</h6>
                        <div id="product-items"></div>

                        <button type="button" class="btn btn-sm btn-success mt-2" onclick="addProductLine()">
                            <i class="bi bi-plus"></i> Produkt hinzufügen
                        </button>

                        <div class="total-row">
                            <!-- Ersparnis-Info -->
                            <div id="savings-info" class="savings-badge mb-3" style="display:none;">
                                <i class="bi bi-piggy-bank"></i> 
                                <strong>Ihre Gesamt-Ersparnis: <span id="total-savings">0.00</span> €</strong>
                            </div>

                            <div class="row">
                                <div class="col-md-6 text-end" id="subtotal">
                                    <small class="text-muted">Warenwert netto:</small><br>
                                    <strong>0.00 €</strong>
                                </div>
                                <div class="col-md-6" id="tax">
                                    <small class="text-muted">MwSt:</small><br>
                                    <strong>0.00 €</strong>
                                </div>
                            </div>
                            <div class="row mt-2" id="line-discounts-row" style="display:none;">
                                <div class="col-md-6 text-end">
                                    <span class="text-warning">Zeilen-Rabatte gesamt:</span>
                                </div>
                                <div class="col-md-6" id="line-discounts-display">0.00 €</div>
                            </div>
                            <div class="row mt-2" id="discount-row" style="display:none;">
                                <div class="col-md-6 text-end">
                                    <span class="text-warning">Zusätzlicher Rabatt:</span>
                                </div>
                                <div class="col-md-6 text-warning" id="discount-display">0.00 €</div>
                            </div>
                            <div class="row mt-2" id="shipping-row" style="display:none;">
                                <div class="col-md-6 text-end">Versandkosten:</div>
                                <div class="col-md-6" id="shipping-amount">0.00 €</div>
                            </div>
                            <div class="row mt-2" id="deposit-row" style="display:none;">
                                <div class="col-md-6 text-end">
                                    <span class="text-info">Pfand (0% MwSt):</span>
                                </div>
                                <div class="col-md-6" id="deposit-amount">0.00 €</div>
                            </div>
                            <div class="row mt-3 pt-3 border-top">
                                <div class="col-md-6 text-end"><h5>Gesamt:</h5></div>
                                <div class="col-md-6"><h5 id="grand-total"><strong>0.00 €</strong></h5></div>
                            </div>
                        </div>
                    </div>

                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Abbrechen</button>
                        <button type="submit" class="btn btn-primary">
                            <i class="bi bi-save"></i> Nachfüllung speichern
                        </button>
                    </div>
                </form>
            </div>
        </div>
    </div>
    """

    return render_template_string(
        render_with_base(
            content,
            active_page='refills',
            title='Warenwirtschaft - Automaten Manager',
            extra_scripts=extra_scripts,
            extra_css=extra_css
        )
    )


@refills_bp.route('/add', methods=['POST'])
@login_required
def add_refill():
    """Neue Nachfüllung hinzufügen - Mit Zeilen-Rabatt"""
    try:
        # MwSt-Optionen
        tax_rate = Decimal(request.form.get('tax_rate', '20'))
        prices_include_tax = request.form.get('prices_include_tax') == 'on'
        deposit_amount = Decimal(request.form.get('deposit_amount', 0))
        discount_amount = Decimal(request.form.get('discount_amount', 0))
        discount_reason = request.form.get('discount_reason', '')

        # Kassenbon-Daten
        receipt_data = request.form.get('receipt_data')
        receipt_filename = request.form.get('receipt_filename')

        # Refill erstellen
        refill = Refill(
            date=datetime.strptime(request.form.get('date'), '%Y-%m-%d').date(),
            supplier_id=request.form.get('supplier_id') or None,
            device_id=request.form.get('device_id') or None,
            invoice_number=request.form.get('invoice_number'),
            delivery_note=request.form.get('delivery_note'),
            shipping_cost=Decimal(request.form.get('shipping_cost', 0)),
            deposit_amount=deposit_amount,
            tax_rate=tax_rate,
            prices_include_tax=prices_include_tax,
            discount_amount=discount_amount,
            discount_reason=discount_reason,
            user_id=current_user.id
        )

        # Kassenbon speichern
        if receipt_data:
            refill.receipt_filename = receipt_filename
            refill.receipt_data = receipt_data

        db.session.add(refill)
        db.session.flush()  # ID generieren

        # Produkte hinzufügen
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')
        unit_prices = request.form.getlist('unit_price[]')
        line_discounts = request.form.getlist('line_discount[]')
        line_discount_reasons = request.form.getlist('line_discount_reason[]')

        items_total = Decimal('0')
        total_line_discount = Decimal('0')

        for i in range(len(product_ids)):
            if product_ids[i]:  # Nur wenn Produkt ausgewählt
                quantity = Decimal(quantities[i])
                unit_price = Decimal(unit_prices[i])
                line_discount = Decimal(line_discounts[i] if i < len(line_discounts) and line_discounts[i] else 0)
                line_discount_reason = line_discount_reasons[i] if i < len(line_discount_reasons) else ''

                # Berechnung mit Zeilen-Rabatt
                gross_price = quantity * unit_price
                net_price = gross_price - line_discount

                item = RefillItem(
                    refill_id=refill.id,
                    product_id=int(product_ids[i]),
                    quantity=quantity,
                    unit_price=unit_price,
                    total_price=net_price,  # Nach Rabatt
                    line_discount=line_discount,
                    line_discount_reason=line_discount_reason
                )
                db.session.add(item)
                items_total += net_price
                total_line_discount += line_discount

                # Lagerbewegung erstellen
                movement = InventoryMovement(
                    product_id=int(product_ids[i]),
                    device_id=refill.device_id,
                    refill_item_id=item.id,
                    type='IN',
                    quantity=quantity,
                    reason='Nachfüllung',
                    user_id=current_user.id
                )
                db.session.add(movement)

        # Gesamtsummen berechnen (mit allen Rabatten)
        items_total_after_global_discount = items_total - discount_amount

        if prices_include_tax:
            # Preise enthalten MwSt - herausrechnen
            total_with_tax = items_total_after_global_discount
            subtotal = total_with_tax / (1 + tax_rate / 100)
            refill.tax_amount = total_with_tax - subtotal
        else:
            # Nettopreise - MwSt draufrechnen
            subtotal = items_total_after_global_discount
            refill.tax_amount = subtotal * (tax_rate / 100)

        refill.subtotal = subtotal
        refill.total_amount = subtotal + refill.tax_amount + refill.shipping_cost + deposit_amount

        # Als Ausgabe erfassen
        expense = Expense(
            category=ExpenseCategory('nachfuellung'),
            amount=refill.total_amount,
            date=refill.date,
            device_id=refill.device_id,
            description=f"Nachfüllung - {len([p for p in product_ids if p])} Produkte",
            supplier=refill.supplier.name if refill.supplier else None,
            invoice_number=refill.invoice_number,
            user_id=current_user.id
        )
        db.session.add(expense)
        refill.expense_id = expense.id

        db.session.commit()

        # Detaillierte Erfolgsmeldung
        total_savings = total_line_discount + discount_amount
        flash_msg = f'Nachfüllung erfasst! Gesamt: {refill.total_amount:.2f} € '
        flash_msg += f'(Netto: {refill.subtotal:.2f} €, MwSt {tax_rate}%: {refill.tax_amount:.2f} €'
        if total_savings > 0:
            flash_msg += f', Gesamtersparnis: {total_savings:.2f} €'
        if deposit_amount > 0:
            flash_msg += f', Pfand: {deposit_amount:.2f} €'
        if receipt_filename:
            flash_msg += f', Beleg: ✅'
        flash_msg += ')'

        flash(flash_msg, 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Speichern: {str(e)}', 'danger')
        print(f"DEBUG ERROR: {str(e)}")
        import traceback
        print(traceback.format_exc())

    return redirect(url_for('refills.index'))


@refills_bp.route('/view/<int:refill_id>')
@login_required
def view_refill(refill_id):
    """Nachfüllung Details anzeigen"""
    refill = Refill.query.filter_by(id=refill_id, user_id=current_user.id).first_or_404()

    content = f"""
    <div class="container">
        <h2 class="text-white mb-4">
            <i class="bi bi-receipt"></i> Nachfüllung vom {refill.date.strftime('%d.%m.%Y')}
        </h2>

        <div class="row">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header">
                        <h5>Details</h5>
                    </div>
                    <div class="card-body">
                        <table class="table">
                            <tr>
                                <th>Lieferant:</th>
                                <td>{refill.supplier.name if refill.supplier else 'Nicht angegeben'}</td>
                            </tr>
                            <tr>
                                <th>Rechnungsnr:</th>
                                <td>{refill.invoice_number or '—'}</td>
                            </tr>
                            <tr>
                                <th>Netto:</th>
                                <td>{refill.subtotal:.2f} €</td>
                            </tr>
                            <tr>
                                <th>MwSt ({refill.tax_rate}%):</th>
                                <td>{refill.tax_amount:.2f} €</td>
                            </tr>
    """

    if hasattr(refill, 'discount_amount') and refill.discount_amount > 0:
        content += f"""
                            <tr>
                                <th>Zusatz-Rabatt:</th>
                                <td>-{refill.discount_amount:.2f} € ({refill.discount_reason or 'Kein Grund'})</td>
                            </tr>
        """

    if refill.deposit_amount > 0:
        content += f"""
                            <tr>
                                <th>Pfand:</th>
                                <td>{refill.deposit_amount:.2f} €</td>
                            </tr>
        """

    content += f"""
                            <tr>
                                <th>Gesamt:</th>
                                <td><strong>{refill.total_amount:.2f} €</strong></td>
                            </tr>
                        </table>

                        <h6 class="mt-4">Positionen:</h6>
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Produkt</th>
                                    <th>Menge</th>
                                    <th>Preis/Einheit</th>
                                    <th>Rabatt</th>
                                    <th>Gesamt</th>
                                </tr>
                            </thead>
                            <tbody>
    """

    total_line_discount = 0
    for item in refill.items:
        line_discount = item.line_discount if hasattr(item, 'line_discount') else 0
        total_line_discount += line_discount

        content += f"""
                                <tr>
                                    <td>{item.product.name}</td>
                                    <td>{item.quantity} {item.product.unit.value}</td>
                                    <td>{item.unit_price:.2f} €</td>
                                    <td>{'—' if line_discount == 0 else f'-{line_discount:.2f} €'}</td>
                                    <td>{item.total_price:.2f} €</td>
                                </tr>
        """

        if hasattr(item, 'line_discount_reason') and item.line_discount_reason:
            content += f"""
                                <tr>
                                    <td colspan="5" class="text-muted small ps-4">
                                        → Rabatt-Grund: {item.line_discount_reason}
                                    </td>
                                </tr>
            """

    if total_line_discount > 0:
        content += f"""
                                <tr class="table-info">
                                    <td colspan="3"><strong>Zeilen-Rabatte gesamt:</strong></td>
                                    <td><strong>-{total_line_discount:.2f} €</strong></td>
                                    <td></td>
                                </tr>
        """

    content += """
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <div class="col-md-4">
    """

    # Kassenbon anzeigen wenn vorhanden
    if hasattr(refill, 'receipt_data') and refill.receipt_data:
        content += f"""
                <div class="card">
                    <div class="card-header">
                        <h5>📸 Kassenbon</h5>
                    </div>
                    <div class="card-body text-center">
        """

        if refill.receipt_data.startswith('data:image'):
            content += f"""
                        <img src="{refill.receipt_data}" class="img-fluid rounded" style="max-width: 100%;">
                        <p class="mt-2"><small>{refill.receipt_filename}</small></p>
            """
        else:
            content += f"""
                        <i class="bi bi-file-pdf display-1 text-danger"></i>
                        <p class="mt-2"><small>{refill.receipt_filename}</small></p>
                        <a href="{refill.receipt_data}" download="{refill.receipt_filename}" 
                           class="btn btn-sm btn-primary">
                            <i class="bi bi-download"></i> Herunterladen
                        </a>
            """

        content += """
                    </div>
                </div>
        """

    content += """
                <a href="/refills" class="btn btn-secondary mt-3">
                    <i class="bi bi-arrow-left"></i> Zurück zur Übersicht
                </a>
            </div>
        </div>
    </div>
    """

    return render_template_string(
        render_with_base(
            content,
            active_page='refills',
            title=f'Nachfüllung #{refill.id} - Automaten Manager'
        )
    )