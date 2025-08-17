# app/web/expenses.py
"""
Ausgaben-Tracking Modul für Automaten Manager - Mit Münzrollen und Beleg-Upload
"""

from flask import Blueprint, render_template_string, redirect, url_for, flash, request, jsonify, get_flashed_messages
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from decimal import Decimal
from app import db
from app.models import Device, Expense, ExpenseCategory
# Import erfolgt in den Funktionen
import json
import os
import uuid
from werkzeug.utils import secure_filename

expenses_bp = Blueprint('expenses', __name__, url_prefix='/expenses')

# Erlaubte Dateitypen für Belege
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Münzrollen-Definitionen (Sparkasse Standard)
COIN_ROLLS = {
    '2.00': {'name': '2 Euro', 'pieces': 25, 'value': 50.00, 'color': 'gold'},
    '1.00': {'name': '1 Euro', 'pieces': 25, 'value': 25.00, 'color': 'gold-silver'},
    '0.50': {'name': '50 Cent', 'pieces': 40, 'value': 20.00, 'color': 'gold'},
    '0.20': {'name': '20 Cent', 'pieces': 40, 'value': 8.00, 'color': 'gold'},
    '0.10': {'name': '10 Cent', 'pieces': 40, 'value': 4.00, 'color': 'gold'},
    '0.05': {'name': '5 Cent', 'pieces': 50, 'value': 2.50, 'color': 'copper'}
}


@expenses_bp.route('/')
@login_required
def index():
    """Ausgaben-Übersicht mit erweiterten Features"""
    # Aktueller Monat oder aus Query
    month_str = request.args.get('month')
    if month_str:
        current_month = datetime.strptime(month_str, '%Y-%m').date()
    else:
        current_month = date.today().replace(day=1)

    # Monatsanfang und -ende
    next_month = (current_month.replace(day=28) + timedelta(days=4)).replace(day=1)
    month_end = next_month - timedelta(days=1)

    # Geräte des Users
    devices = Device.query.filter_by(owner_id=current_user.id).all()
    device_dict = {d.id: d.name for d in devices}

    # Ausgaben des Monats
    expenses = Expense.query.filter(
        Expense.user_id == current_user.id,
        Expense.date >= current_month,
        Expense.date <= month_end
    ).order_by(Expense.date.desc()).all()

    # Einnahmen des Monats (für Gewinn/Verlust)
    from app.models import Entry
    entries = Entry.query.join(Device).filter(
        Device.owner_id == current_user.id,
        Entry.date >= current_month,
        Entry.date <= month_end
    ).all()

    # Berechnungen
    total_expenses = sum(e.amount for e in expenses)
    total_income = sum(e.amount for e in entries)
    profit = total_income - total_expenses

    # Ausgaben nach Kategorie
    expenses_by_category = {}
    for expense in expenses:
        cat = expense.category.value
        if cat not in expenses_by_category:
            expenses_by_category[cat] = {'amount': 0, 'count': 0}
        expenses_by_category[cat]['amount'] += float(expense.amount)
        expenses_by_category[cat]['count'] += 1

    # JavaScript mit erweiterten Funktionen
    extra_scripts = f"""
    <script>
    // Neue Ausgabe Modal
    function showAddExpenseModal(category = null) {{
        console.log('Opening modal with category:', category);
        if (category) {{
            document.getElementById('category').value = category;
            toggleCategoryFields();
        }}
        new bootstrap.Modal(document.getElementById('addExpenseModal')).show();
    }}

    // Ausgabe bearbeiten
    function editExpense(id) {{
        fetch(`/expenses/get/${{id}}`)
            .then(response => response.json())
            .then(data => {{
                document.getElementById('expense_id').value = data.id;
                document.getElementById('category').value = data.category;
                toggleCategoryFields();

                if (data.category === 'wechselgeld' && data.coin_details) {{
                    // Münzrollen-Details laden
                    for (const [coin, qty] of Object.entries(data.coin_details)) {{
                        const inputId = 'coin_' + coin.replace('.', '_');
                        const input = document.getElementById(inputId);
                        if (input) input.value = qty;
                    }}
                    calculateCoinTotal();
                }} else {{
                    document.getElementById('amount').value = data.amount;
                }}

                document.getElementById('date').value = data.date;
                document.getElementById('device_id').value = data.device_id || '';
                document.getElementById('description').value = data.description || '';
                document.getElementById('is_recurring').checked = data.is_recurring;

                document.getElementById('modalTitle').textContent = 'Ausgabe bearbeiten';
                document.getElementById('expenseForm').action = `/expenses/edit/${{id}}`;
                new bootstrap.Modal(document.getElementById('addExpenseModal')).show();
            }});
    }}

    // Ausgabe löschen
    function deleteExpense(id, description) {{
        if (confirm(`Ausgabe "${{description}}" wirklich löschen?`)) {{
            const form = document.createElement('form');
            form.method = 'POST';
            form.action = `/expenses/delete/${{id}}`;
            document.body.appendChild(form);
            form.submit();
        }}
    }}

    // Kategorie-spezifische Felder umschalten
    function toggleCategoryFields() {{
        const category = document.getElementById('category').value;
        const changeFields = document.getElementById('changeMoneyFields');
        const standardField = document.getElementById('standardAmountField');

        if (category === 'wechselgeld') {{
            changeFields.style.display = 'block';
            standardField.style.display = 'none';
            document.getElementById('amount').required = false;
            calculateCoinTotal();
        }} else {{
            changeFields.style.display = 'none';
            standardField.style.display = 'block';
            document.getElementById('amount').required = true;
            setCategoryDefaults();
        }}
    }}

    // Münzrollen anpassen
    function adjustCoinRoll(coinValue, delta) {{
        const inputId = 'coin_' + coinValue.replace('.', '_');
        const input = document.getElementById(inputId);
        let newValue = parseInt(input.value || 0) + delta;
        if (newValue < 0) newValue = 0;
        if (newValue > 20) newValue = 20;
        input.value = newValue;
        calculateCoinTotal();
    }}

    // Münzrollen-Summe berechnen
    function calculateCoinTotal() {{
        let total = 0;
        let details = [];
        document.querySelectorAll('.coin-input').forEach(input => {{
            const quantity = parseInt(input.value || 0);
            const value = parseFloat(input.dataset.value);
            if (quantity > 0) {{
                total += quantity * value;
                const coinName = input.closest('.card').querySelector('.badge').textContent;
                details.push(`${{quantity}}x ${{coinName}}`);
            }}
        }});
        document.getElementById('coinTotalAmount').textContent = total.toFixed(2);
        document.getElementById('coinDetails').textContent = details.join(', ');
        document.getElementById('amount').value = total.toFixed(2);
    }}

    // Kategorie-Vorschläge
    function setCategoryDefaults() {{
        const category = document.getElementById('category').value;
        const amountField = document.getElementById('amount');
        const descField = document.getElementById('description');

        const suggestions = {{
            'wartung': {{ amount: 150, desc: 'Monatliche Wartung' }},
            'nachfuellung': {{ amount: 50, desc: 'Kaffee/Becher nachfüllen' }},
            'reparatur': {{ amount: 200, desc: 'Reparatur' }},
            'miete': {{ amount: 100, desc: 'Standplatzmiete' }},
            'strom': {{ amount: 30, desc: 'Strom' }},
            'wechselgeld': {{ amount: 0, desc: 'Münzrollen Sparkasse' }},
            'anschaffung': {{ amount: 0, desc: 'Neue Anschaffung' }},
            'versicherung': {{ amount: 50, desc: 'Versicherung' }},
            'reinigung': {{ amount: 25, desc: 'Reinigung' }},
            'sonstiges': {{ amount: 0, desc: '' }}
        }};

        if (suggestions[category] && !amountField.value) {{
            amountField.placeholder = suggestions[category].amount + ' €';
            descField.placeholder = suggestions[category].desc;
        }}
    }}

    // Drag & Drop für Belege
    function handleDragOver(e) {{
        e.preventDefault();
        e.currentTarget.style.background = '#e9ecef';
        e.currentTarget.style.borderColor = '#6c757d';
    }}

    function handleDragLeave(e) {{
        e.currentTarget.style.background = '#f8f9fa';
        e.currentTarget.style.borderColor = '#dee2e6';
    }}

    function handleDrop(e) {{
        e.preventDefault();
        e.currentTarget.style.background = '#f8f9fa';
        e.currentTarget.style.borderColor = '#dee2e6';

        const files = e.dataTransfer.files;
        if (files.length > 0) {{
            document.getElementById('receiptFile').files = files;
            handleFileSelect(document.getElementById('receiptFile'));
        }}
    }}

    function handleFileSelect(input) {{
        const file = input.files[0];
        if (file) {{
            const preview = document.getElementById('filePreview');
            const fileSize = (file.size / 1024 / 1024).toFixed(2);

            if (fileSize > 5) {{
                preview.innerHTML = `
                    <div class="alert alert-danger mt-2">
                        <i class="bi bi-exclamation-triangle"></i> Datei zu groß (max. 5MB)
                    </div>
                `;
                input.value = '';
                return;
            }}

            preview.innerHTML = `
                <div class="alert alert-success mt-2">
                    <i class="bi bi-file-earmark-check"></i> ${{file.name}}
                    <span class="text-muted">(${{fileSize}} MB)</span>
                </div>
            `;
        }}
    }}

    // Modal zurücksetzen
    document.getElementById('addExpenseModal').addEventListener('hidden.bs.modal', function () {{
        document.getElementById('modalTitle').textContent = 'Neue Ausgabe';
        document.getElementById('expenseForm').action = '/expenses/add';
        document.getElementById('expenseForm').reset();
        document.getElementById('expense_id').value = '';
        document.getElementById('filePreview').innerHTML = '';
        toggleCategoryFields();
    }});
    </script>
    """

    # CSS für Ausgaben
    extra_css = """
    <style>
        /* Kategorie-Farben */
        .category-maintenance { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
        .category-refill { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
        .category-repair { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }
        .category-rent { background: linear-gradient(135deg, #30cfd0 0%, #330867 100%); }
        .category-energy { background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%); }
        .category-purchase { background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%); }
        .category-other { background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%); }

        .expense-item {
            border-left: 4px solid;
            margin-bottom: 10px;
            padding: 15px;
            background: white;
            border-radius: 8px;
            transition: all 0.3s;
        }
        .expense-item:hover {
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transform: translateX(5px);
        }
        .expense-item.wartung { border-left-color: #f5576c; }
        .expense-item.nachfuellung { border-left-color: #00f2fe; }
        .expense-item.reparatur { border-left-color: #fee140; }
        .expense-item.miete { border-left-color: #330867; }
        .expense-item.strom { border-left-color: #fed6e3; }
        .expense-item.wechselgeld { border-left-color: #fecfef; }
        .expense-item.anschaffung { border-left-color: #9333ea; }
        .expense-item.versicherung { border-left-color: #06b6d4; }
        .expense-item.reinigung { border-left-color: #84cc16; }
        .expense-item.sonstiges { border-left-color: #fcb69f; }

        .stat-card {
            text-align: center;
            padding: 20px;
            border-radius: 15px;
            color: white;
        }
        .stat-expense { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
        .stat-income { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }
        .stat-profit { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .stat-warning { background: linear-gradient(135deg, #f77062 0%, #fe5196 100%); }

        .month-selector {
            background: white;
            border-radius: 10px;
            padding: 10px 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .category-badge {
            padding: 5px 15px;
            border-radius: 20px;
            color: white;
            font-size: 0.875rem;
            font-weight: 600;
        }

        .quick-add-btn {
            position: fixed;
            bottom: 30px;
            right: 30px;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            box-shadow: 0 5px 20px rgba(0,0,0,0.2);
            z-index: 1000;
        }

        .recurring-badge {
            background: #ffd700;
            color: #333;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.75rem;
            margin-left: 5px;
        }

        .receipt-badge {
            background: #28a745;
            color: white;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.75rem;
            margin-left: 5px;
        }

        #dropZone {
            background: #f8f9fa;
            border: 2px dashed #dee2e6 !important;
            transition: all 0.3s;
            cursor: pointer;
        }

        #dropZone:hover, #dropZone.bg-light {
            background: #e9ecef;
            border-color: #6c757d !important;
        }

        .coin-input {
            font-weight: bold;
        }

        .coin-details {
            font-size: 0.85rem;
            color: #6c757d;
            font-style: italic;
        }
    </style>
    """

    # HTML Content
    content = f"""
    <!-- Header -->
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="text-white">
            <i class="bi bi-wallet2"></i> Ausgaben-Verwaltung
        </h2>
        <div class="month-selector">
            <a href="?month={(current_month - timedelta(days=28)).strftime('%Y-%m')}" class="btn btn-sm btn-outline-primary">
                <i class="bi bi-chevron-left"></i>
            </a>
            <span class="mx-3"><strong>{current_month.strftime('%B %Y')}</strong></span>
            <a href="?month={(next_month).strftime('%Y-%m')}" class="btn btn-sm btn-outline-primary">
                <i class="bi bi-chevron-right"></i>
            </a>
        </div>
    </div>

    <!-- Statistik Cards -->
    <div class="row mb-4">
        <div class="col-md-3">
            <div class="card stat-card stat-expense">
                <h6>Ausgaben</h6>
                <h3>{total_expenses:.2f} €</h3>
                <small>{len(expenses)} Einträge</small>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stat-card stat-income">
                <h6>Einnahmen</h6>
                <h3>{total_income:.2f} €</h3>
                <small>{len(entries)} Einträge</small>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stat-card {'stat-profit' if profit >= 0 else 'stat-warning'}">
                <h6>{'Gewinn' if profit >= 0 else 'Verlust'}</h6>
                <h3>{abs(profit):.2f} €</h3>
                <small>{'+' if profit >= 0 else '-'}{(abs(profit) / total_income * 100 if total_income > 0 else 0):.1f}%</small>
            </div>
        </div>
        <div class="col-md-3">
            <div class="card stat-card stat-warning">
                <h6>Größte Ausgabe</h6>
                <h3>{max([e.amount for e in expenses], default=0):.2f} €</h3>
                <small>{expenses[0].category.value if expenses else '-'}</small>
            </div>
        </div>
    </div>

    <!-- Quick Add Buttons -->
    <div class="row mb-4">
        <div class="col-12">
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title mb-3">Schnell-Erfassung</h5>
                    <div class="d-flex flex-wrap gap-2">
                        <button class="btn btn-outline-danger" onclick="showAddExpenseModal('wartung')">
                            <i class="bi bi-wrench"></i> Wartung
                        </button>
                        <button class="btn btn-outline-info" onclick="showAddExpenseModal('nachfuellung')">
                            <i class="bi bi-cup-fill"></i> Nachfüllung
                        </button>
                        <button class="btn btn-outline-warning" onclick="showAddExpenseModal('reparatur')">
                            <i class="bi bi-tools"></i> Reparatur
                        </button>
                        <button class="btn btn-outline-primary" onclick="showAddExpenseModal('miete')">
                            <i class="bi bi-house"></i> Miete
                        </button>
                        <button class="btn btn-outline-success" onclick="showAddExpenseModal('strom')">
                            <i class="bi bi-lightning"></i> Strom
                        </button>
                        <button class="btn btn-outline-secondary" onclick="showAddExpenseModal('wechselgeld')">
                            <i class="bi bi-cash"></i> Wechselgeld
                        </button>
                        <button class="btn btn-outline-dark" onclick="showAddExpenseModal('anschaffung')">
                            <i class="bi bi-cart"></i> Anschaffung
                        </button>
                        <button class="btn btn-outline-info" onclick="showAddExpenseModal('versicherung')">
                            <i class="bi bi-shield"></i> Versicherung
                        </button>
                        <button class="btn btn-outline-warning" onclick="showAddExpenseModal('reinigung')">
                            <i class="bi bi-droplet"></i> Reinigung
                        </button>
                        <button class="btn btn-outline-dark" onclick="showAddExpenseModal('sonstiges')">
                            <i class="bi bi-three-dots"></i> Sonstiges
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Ausgaben-Liste -->
    <div class="row">
        <div class="col-md-8">
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">
                        <i class="bi bi-list-ul"></i> Ausgaben im {current_month.strftime('%B')}
                    </h5>
                </div>
                <div class="card-body">
    """

    if expenses:
        for expense in expenses:
            device_name = device_dict.get(expense.device_id, 'Allgemein')

            # Münzrollen-Details anzeigen
            coin_details_text = ''
            if expense.category == ExpenseCategory.WECHSELGELD and hasattr(expense, 'details') and expense.details:
                try:
                    coin_details = json.loads(expense.details)
                    details_list = []
                    for coin, qty in coin_details.items():
                        if qty > 0:
                            details_list.append(f"{qty}x {COIN_ROLLS[coin]['name']}")
                    if details_list:
                        coin_details_text = f'<br><small class="coin-details">Münzrollen: {", ".join(details_list)}</small>'
                except:
                    pass

            # Beleg-Badge
            receipt_badge = ''
            if hasattr(expense, 'receipt_path') and expense.receipt_path:
                receipt_badge = '<span class="receipt-badge"><i class="bi bi-paperclip"></i> Beleg</span>'

            content += f"""
                    <div class="expense-item {expense.category.value}">
                        <div class="d-flex justify-content-between align-items-start">
                            <div>
                                <h6 class="mb-1">
                                    {expense.description or expense.category.value.title()}
                                    {'<span class="recurring-badge">Wiederkehrend</span>' if expense.is_recurring else ''}
                                    {receipt_badge}
                                </h6>
                                <small class="text-muted">
                                    <i class="bi bi-calendar"></i> {expense.date.strftime('%d.%m.%Y')}
                                    {'| <i class="bi bi-pc-display"></i> ' + device_name if expense.device_id else ''}
                                </small>
                                {coin_details_text}
                            </div>
                            <div class="text-end">
                                <h5 class="mb-1 text-danger">-{expense.amount:.2f} €</h5>
                                <div class="btn-group btn-group-sm">
                                    <button class="btn btn-outline-warning" onclick="editExpense({expense.id})">
                                        <i class="bi bi-pencil"></i>
                                    </button>
                                    <button class="btn btn-outline-danger" onclick="deleteExpense({expense.id}, '{expense.description or expense.category.value}')">
                                        <i class="bi bi-trash"></i>
                                    </button>
                                </div>
                            </div>
                        </div>
                    </div>
            """
    else:
        content += '<p class="text-muted text-center py-4">Noch keine Ausgaben in diesem Monat</p>'

    content += """
                </div>
            </div>
        </div>

        <!-- Kategorie-Übersicht -->
        <div class="col-md-4">
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">
                        <i class="bi bi-pie-chart"></i> Nach Kategorie
                    </h5>
                </div>
                <div class="card-body">
    """

    if expenses_by_category:
        for cat, data in sorted(expenses_by_category.items(), key=lambda x: x[1]['amount'], reverse=True):
            percentage = (data['amount'] / float(total_expenses)) * 100 if total_expenses > 0 else 0
            content += f"""
                    <div class="mb-3">
                        <div class="d-flex justify-content-between mb-1">
                            <span class="badge category-badge category-{cat}">{cat.title()}</span>
                            <span>{data['amount']:.2f} €</span>
                        </div>
                        <div class="progress" style="height: 10px;">
                            <div class="progress-bar" style="width: {percentage}%; background: linear-gradient(90deg, #667eea, #764ba2);"></div>
                        </div>
                        <small class="text-muted">{data['count']} Einträge ({percentage:.1f}%)</small>
                    </div>
            """
    else:
        content += '<p class="text-muted text-center">Keine Daten vorhanden</p>'

    content += f"""
                </div>
            </div>
        </div>
    </div>

    <!-- Enhanced Add Expense Modal mit Münzrollen und Beleg-Upload -->
    <div class="modal fade" id="addExpenseModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="modalTitle">Neue Ausgabe</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <form id="expenseForm" method="POST" action="/expenses/add" enctype="multipart/form-data">
                    <div class="modal-body">
                        <input type="hidden" id="expense_id" name="expense_id">

                        <div class="mb-3">
                            <label class="form-label">Kategorie *</label>
                            <select id="category" name="category" class="form-select" required onchange="toggleCategoryFields()">
                                <option value="">-- Wählen --</option>
                                <option value="wartung">🔧 Wartung</option>
                                <option value="nachfuellung">☕ Nachfüllung</option>
                                <option value="reparatur">🛠️ Reparatur</option>
                                <option value="miete">🏠 Miete/Standplatz</option>
                                <option value="strom">⚡ Strom/Energie</option>
                                <option value="wechselgeld">🪙 Wechselgeld (Münzrollen)</option>
                                <option value="anschaffung">🛒 Anschaffung</option>
                                <option value="versicherung">🛡️ Versicherung</option>
                                <option value="reinigung">🧹 Reinigung</option>
                                <option value="sonstiges">📌 Sonstiges</option>
                            </select>
                        </div>

                        <!-- Wechselgeld-Spezifische Felder -->
                        <div id="changeMoneyFields" style="display:none;">
                            <div class="alert alert-info">
                                <i class="bi bi-info-circle"></i> Wählen Sie die gekauften Münzrollen aus (Sparkasse Standard)
                            </div>
                            <div class="row">
    """

    # Münzrollen-Auswahl generieren
    for coin_value, coin_info in COIN_ROLLS.items():
        content += f"""
                                <div class="col-md-4 mb-3">
                                    <div class="card">
                                        <div class="card-body p-2">
                                            <label class="form-label mb-1">
                                                <span class="badge bg-warning text-dark">{coin_info['name']}</span>
                                            </label>
                                            <div class="text-muted small mb-2">
                                                {coin_info['pieces']} Stück = {coin_info['value']:.2f} €
                                            </div>
                                            <div class="input-group input-group-sm">
                                                <button type="button" class="btn btn-outline-secondary" 
                                                        onclick="adjustCoinRoll('{coin_value}', -1)">-</button>
                                                <input type="number" 
                                                       id="coin_{coin_value.replace('.', '_')}" 
                                                       name="coin_{coin_value.replace('.', '_')}" 
                                                       class="form-control text-center coin-input" 
                                                       value="0" min="0" max="20"
                                                       data-value="{coin_info['value']}"
                                                       onchange="calculateCoinTotal()">
                                                <button type="button" class="btn btn-outline-secondary" 
                                                        onclick="adjustCoinRoll('{coin_value}', 1)">+</button>
                                            </div>
                                        </div>
                                    </div>
                                </div>
        """

    content += f"""
                            </div>
                            <div class="row mt-3">
                                <div class="col-12">
                                    <div class="alert alert-success">
                                        <h5>Gesamtsumme: <span id="coinTotalAmount">0.00</span> €</h5>
                                        <small id="coinDetails"></small>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Standard-Betrag-Feld -->
                        <div id="standardAmountField">
                            <div class="mb-3">
                                <label class="form-label">Betrag (€) *</label>
                                <input type="number" id="amount" name="amount" class="form-control" 
                                       step="0.01" min="0.01" required>
                            </div>
                        </div>

                        <div class="row">
                            <div class="col-md-6">
                                <div class="mb-3">
                                    <label class="form-label">Datum *</label>
                                    <input type="date" id="date" name="date" class="form-control" 
                                           value="{date.today()}" required>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="mb-3">
                                    <label class="form-label">Gerät (optional)</label>
                                    <select id="device_id" name="device_id" class="form-select">
                                        <option value="">-- Allgemein --</option>
    """

    for device in devices:
        content += f'<option value="{device.id}">{device.name}</option>'

    content += """
                                    </select>
                                </div>
                            </div>
                        </div>

                        <div class="mb-3">
                            <label class="form-label">Beschreibung</label>
                            <textarea id="description" name="description" class="form-control" rows="2"></textarea>
                        </div>

                        <!-- Beleg-Upload mit Drag & Drop -->
                        <div class="mb-3">
                            <label class="form-label">Beleg/Quittung hochladen</label>
                            <div class="border rounded p-3 text-center" id="dropZone" 
                                 ondrop="handleDrop(event)" 
                                 ondragover="handleDragOver(event)"
                                 ondragleave="handleDragLeave(event)"
                                 onclick="document.getElementById('receiptFile').click()">
                                <input type="file" name="receipt" id="receiptFile" 
                                       class="d-none" accept=".pdf,.png,.jpg,.jpeg,.gif"
                                       onchange="handleFileSelect(this)">
                                <div>
                                    <i class="bi bi-cloud-upload" style="font-size: 2rem; color: #6c757d;"></i>
                                    <p class="text-muted mb-0">Datei hier ablegen oder klicken zum Auswählen</p>
                                    <small class="text-muted">PDF, JPG, PNG (max. 5MB)</small>
                                </div>
                                <div id="filePreview"></div>
                            </div>
                        </div>

                        <div class="form-check">
                            <input type="checkbox" id="is_recurring" name="is_recurring" 
                                   class="form-check-input" value="1">
                            <label class="form-check-label" for="is_recurring">
                                Wiederkehrende Ausgabe (monatlich)
                            </label>
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

    <!-- Floating Action Button -->
    <button class="btn btn-primary quick-add-btn" onclick="showAddExpenseModal()">
        <i class="bi bi-plus-lg"></i>
    </button>
    """

    # Use modern template
    from app.web.dashboard_modern import render_modern_template
    
    breadcrumb = [
        {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
        {'text': 'Ausgaben'}
    ]
    
    full_content = extra_css + content + extra_scripts
    
    return render_modern_template(
        full_content,
        title="Ausgabenverwaltung",
        active_module='expenses',
        breadcrumb=breadcrumb
    )


@expenses_bp.route('/add', methods=['POST'])
@login_required
def add_expense():
    """Neue Ausgabe mit Münzrollen und Beleg hinzufügen"""
    try:
        category_value = request.form.get('category')
        if not category_value:
            flash('Bitte wählen Sie eine Kategorie!', 'danger')
            return redirect(url_for('expenses.index'))

        # Münzrollen-Details sammeln wenn Kategorie = wechselgeld
        if category_value == 'wechselgeld':
            coin_details = {}
            total_amount = Decimal('0')

            for coin_value, coin_info in COIN_ROLLS.items():
                field_name = f"coin_{coin_value.replace('.', '_')}"
                quantity = int(request.form.get(field_name, 0))
                if quantity > 0:
                    coin_details[coin_value] = quantity
                    total_amount += Decimal(str(coin_info['value'])) * quantity

            amount = total_amount

            # Automatische Beschreibung generieren
            if not request.form.get('description'):
                coin_list = []
                for coin_value, qty in coin_details.items():
                    coin_list.append(f"{qty}x {COIN_ROLLS[coin_value]['name']}")
                description = f"Münzrollen Sparkasse: {', '.join(coin_list)}"
            else:
                description = request.form.get('description')
        else:
            amount_value = request.form.get('amount')
            if not amount_value:
                flash('Bitte geben Sie einen Betrag ein!', 'danger')
                return redirect(url_for('expenses.index'))

            amount = Decimal(amount_value)
            description = request.form.get('description', '').strip()
            if not description:
                description = category_value.replace('_', ' ').title()

        date_value = request.form.get('date')
        if not date_value:
            flash('Bitte wählen Sie ein Datum!', 'danger')
            return redirect(url_for('expenses.index'))

        # Device ID handling
        device_id = request.form.get('device_id')
        if device_id == '' or device_id == 'None':
            device_id = None
        else:
            device_id = int(device_id) if device_id else None

        # Erstelle neue Ausgabe
        expense = Expense(
            category=ExpenseCategory(category_value),
            amount=amount,
            date=datetime.strptime(date_value, '%Y-%m-%d').date(),
            device_id=device_id,
            description=description,
            is_recurring=bool(request.form.get('is_recurring')),
            user_id=current_user.id
        )

        # Speichere Münzrollen-Details als JSON
        if category_value == 'wechselgeld' and coin_details:
            expense.details = json.dumps(coin_details)

        # Beleg hochladen wenn vorhanden
        if 'receipt' in request.files:
            file = request.files['receipt']
            if file and file.filename and allowed_file(file.filename):
                # Erstelle Upload-Verzeichnis
                upload_dir = f"uploads/receipts/{current_user.id}/{datetime.now().year}/{datetime.now().month:02d}"
                os.makedirs(upload_dir, exist_ok=True)

                # Sichere Dateiname mit UUID
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}.{ext}"
                filepath = os.path.join(upload_dir, filename)

                file.save(filepath)
                expense.receipt_path = filepath

        db.session.add(expense)
        db.session.commit()

        flash(f'Ausgabe "{expense.description}" in Höhe von {expense.amount:.2f} € wurde erfasst!', 'success')

    except Exception as e:
        print(f"Error saving expense: {str(e)}")
        flash(f'Fehler beim Speichern: {str(e)}', 'danger')
        db.session.rollback()

    return redirect(url_for('expenses.index'))


@expenses_bp.route('/edit/<int:expense_id>', methods=['POST'])
@login_required
def edit_expense(expense_id):
    """Ausgabe bearbeiten"""
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()

    try:
        expense.category = ExpenseCategory(request.form.get('category'))

        # Münzrollen-Update bei Wechselgeld
        if request.form.get('category') == 'wechselgeld':
            coin_details = {}
            total_amount = Decimal('0')

            for coin_value, coin_info in COIN_ROLLS.items():
                field_name = f"coin_{coin_value.replace('.', '_')}"
                quantity = int(request.form.get(field_name, 0))
                if quantity > 0:
                    coin_details[coin_value] = quantity
                    total_amount += Decimal(str(coin_info['value'])) * quantity

            expense.amount = total_amount
            expense.details = json.dumps(coin_details) if coin_details else None
        else:
            expense.amount = Decimal(request.form.get('amount'))
            expense.details = None

        expense.date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()

        # Device ID handling
        device_id = request.form.get('device_id')
        if device_id == '' or device_id == 'None':
            expense.device_id = None
        else:
            expense.device_id = int(device_id) if device_id else None

        # Description handling
        description = request.form.get('description', '').strip()
        if not description:
            description = request.form.get('category', '').replace('_', ' ').title()
        expense.description = description

        expense.is_recurring = bool(request.form.get('is_recurring'))

        # Beleg-Update
        if 'receipt' in request.files:
            file = request.files['receipt']
            if file and file.filename and allowed_file(file.filename):
                # Lösche alten Beleg wenn vorhanden
                if hasattr(expense, 'receipt_path') and expense.receipt_path and os.path.exists(expense.receipt_path):
                    try:
                        os.remove(expense.receipt_path)
                    except:
                        pass

                # Neuen Beleg speichern
                upload_dir = f"uploads/receipts/{current_user.id}/{datetime.now().year}/{datetime.now().month:02d}"
                os.makedirs(upload_dir, exist_ok=True)

                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}.{ext}"
                filepath = os.path.join(upload_dir, filename)

                file.save(filepath)
                expense.receipt_path = filepath

        db.session.commit()
        flash('Ausgabe wurde aktualisiert!', 'success')
    except Exception as e:
        print(f"Error editing expense: {str(e)}")
        flash(f'Fehler beim Aktualisieren: {str(e)}', 'danger')
        db.session.rollback()

    return redirect(url_for('expenses.index'))


@expenses_bp.route('/delete/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):
    """Ausgabe löschen"""
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()

    try:
        # Beleg-Datei löschen falls vorhanden
        if hasattr(expense, 'receipt_path') and expense.receipt_path and os.path.exists(expense.receipt_path):
            try:
                os.remove(expense.receipt_path)
            except:
                pass

        description = expense.description or expense.category.value
        db.session.delete(expense)
        db.session.commit()
        flash(f'Ausgabe "{description}" wurde gelöscht!', 'warning')
    except Exception as e:
        print(f"Error deleting expense: {str(e)}")
        flash(f'Fehler beim Löschen: {str(e)}', 'danger')
        db.session.rollback()

    return redirect(url_for('expenses.index'))


@expenses_bp.route('/get/<int:expense_id>')
@login_required
def get_expense(expense_id):
    """Ausgabe-Daten für Modal mit Münzrollen-Details"""
    expense = Expense.query.filter_by(id=expense_id, user_id=current_user.id).first_or_404()

    response_data = {
        'id': expense.id,
        'category': expense.category.value,
        'amount': float(expense.amount),
        'date': expense.date.isoformat(),
        'device_id': expense.device_id,
        'description': expense.description,
        'is_recurring': expense.is_recurring
    }

    # Münzrollen-Details hinzufügen
    if expense.category == ExpenseCategory.WECHSELGELD and hasattr(expense, 'details') and expense.details:
        try:
            response_data['coin_details'] = json.loads(expense.details)
        except:
            pass

    # Beleg-Status
    if hasattr(expense, 'receipt_path'):
        response_data['has_receipt'] = bool(expense.receipt_path)

    return jsonify(response_data)