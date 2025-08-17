from flask import Blueprint, render_template_string, jsonify, request, redirect, url_for
from flask_login import login_required, current_user
from app.models import Device, Entry, Expense, Refill, RefillItem, Product, DeviceStatus
from sqlalchemy import func, extract, and_
from datetime import datetime, timedelta, date
from decimal import Decimal
import json

dashboard_modern_bp = Blueprint('dashboard_modern', __name__)

def get_navigation_config(active_module='dashboard', active_submodule=None):
    """Generate navigation configuration based on current module"""
    
    configs = {
        'dashboard': [
            {'icon': 'bi-speedometer2', 'text': 'Dashboard', 'active': True, 'route': 'dashboard_modern.dashboard'},
            {'divider': True},
            {'icon': 'bi-cpu', 'text': 'Geräte', 'route': 'dashboard_modern.devices'},
            {'icon': 'bi-cash-stack', 'text': 'Einnahmen', 'route': 'dashboard_modern.income'},
            {'icon': 'bi-receipt', 'text': 'Ausgaben', 'route': 'dashboard_modern.expenses'},
            {'icon': 'bi-box-seam', 'text': 'Warenwirtschaft', 'route': 'dashboard_modern.inventory'},
            {'icon': 'bi-arrow-repeat', 'text': 'Automatisierungen', 'route': 'automations.index'},
            {'icon': 'bi-graph-up', 'text': 'Berichte', 'route': 'dashboard_modern.reports'},
            {'icon': 'bi-gear', 'text': 'Einstellungen', 'route': 'dashboard_modern.settings'},
            {'divider': True},
            {'icon': 'bi-person-circle', 'text': 'Profil', 'route': 'dashboard_modern.profile'},
            {'icon': 'bi-box-arrow-right', 'text': 'Logout', 'route': 'auth.logout'}
        ],
        'devices': [
            {'icon': 'bi-arrow-left', 'text': 'Dashboard', 'route': 'dashboard_modern.dashboard', 'is_back': True},
            {'divider': True},
            {'section': 'GERÄTE'},
            {'icon': 'bi-grid', 'text': 'Übersicht', 'active': active_submodule == 'overview' or not active_submodule, 'route': 'dashboard_modern.devices'},
            {'icon': 'bi-plus-circle', 'text': 'Neues Gerät', 'active': active_submodule == 'new', 'route': 'dashboard_modern.devices_new'},
            {'icon': 'bi-map', 'text': 'Standorte', 'active': active_submodule == 'locations', 'route': 'dashboard_modern.devices_locations'},
            {'icon': 'bi-tools', 'text': 'Wartungsplan', 'active': active_submodule == 'maintenance', 'route': 'dashboard_modern.devices_maintenance'},
            {'icon': 'bi-qr-code', 'text': 'QR-Codes', 'active': active_submodule == 'qrcodes', 'route': 'dashboard_modern.devices_qrcodes'},
            {'icon': 'bi-bar-chart', 'text': 'Auslastung', 'active': active_submodule == 'utilization', 'route': 'dashboard_modern.devices_utilization'}
        ],
        'inventory': [
            {'icon': 'bi-arrow-left', 'text': 'Dashboard', 'route': 'dashboard_modern.dashboard', 'is_back': True},
            {'divider': True},
            {'section': 'WARENWIRTSCHAFT'},
            {'icon': 'bi-boxes', 'text': 'Lagerbestand', 'active': active_submodule == 'stock' or not active_submodule, 'route': 'dashboard_modern.inventory'},
            {'icon': 'bi-arrow-down-circle', 'text': 'Nachfüllungen', 'active': active_submodule == 'refills', 'route': 'dashboard_modern.inventory_refills'},
            {'icon': 'bi-clipboard-check', 'text': 'Inventur', 'active': active_submodule == 'stocktaking', 'route': 'dashboard_modern.inventory_stocktaking'},
            {'icon': 'bi-truck', 'text': 'Lieferanten', 'active': active_submodule == 'suppliers', 'route': 'dashboard_modern.inventory_suppliers'},
            {'icon': 'bi-box', 'text': 'Produkte', 'active': active_submodule == 'products', 'route': 'dashboard_modern.inventory_products'},
            {'icon': 'bi-graph-down', 'text': 'Verbrauch', 'active': active_submodule == 'consumption', 'route': 'dashboard_modern.inventory_consumption'},
            {'icon': 'bi-calendar-check', 'text': 'Bestellungen', 'active': active_submodule == 'orders', 'route': 'dashboard_modern.inventory_orders'}
        ],
        'income': [
            {'icon': 'bi-arrow-left', 'text': 'Dashboard', 'route': 'dashboard_modern.dashboard', 'is_back': True},
            {'divider': True},
            {'section': 'EINNAHMEN'},
            {'icon': 'bi-list', 'text': 'Übersicht', 'active': active_submodule == 'overview' or not active_submodule, 'route': 'dashboard_modern.income'},
            {'icon': 'bi-plus-circle', 'text': 'Neue Einnahme', 'active': active_submodule == 'new', 'route': 'dashboard_modern.income_new'},
            {'icon': 'bi-calendar', 'text': 'Tagesabschluss', 'active': active_submodule == 'daily', 'route': 'dashboard_modern.income_daily'},
            {'icon': 'bi-cpu', 'text': 'Nach Gerät', 'active': active_submodule == 'by_device', 'route': 'dashboard_modern.income_by_device'},
            {'icon': 'bi-box', 'text': 'Nach Produkt', 'active': active_submodule == 'by_product', 'route': 'dashboard_modern.income_by_product'},
            {'icon': 'bi-graph-up', 'text': 'Statistiken', 'active': active_submodule == 'statistics', 'route': 'dashboard_modern.income_statistics'}
        ],
        'expenses': [
            {'icon': 'bi-arrow-left', 'text': 'Dashboard', 'route': 'dashboard_modern.dashboard', 'is_back': True},
            {'divider': True},
            {'section': 'AUSGABEN'},
            {'icon': 'bi-list', 'text': 'Übersicht', 'active': active_submodule == 'overview' or not active_submodule, 'route': 'dashboard_modern.expenses'},
            {'icon': 'bi-plus-circle', 'text': 'Neue Ausgabe', 'active': active_submodule == 'new', 'route': 'dashboard_modern.expenses_new'},
            {'icon': 'bi-tags', 'text': 'Kategorien', 'active': active_submodule == 'categories', 'route': 'dashboard_modern.expenses_categories'},
            {'icon': 'bi-calendar', 'text': 'Wiederkehrend', 'active': active_submodule == 'recurring', 'route': 'dashboard_modern.expenses_recurring'},
            {'icon': 'bi-file-earmark', 'text': 'Belege', 'active': active_submodule == 'receipts', 'route': 'dashboard_modern.expenses_receipts'},
            {'icon': 'bi-graph-down', 'text': 'Analyse', 'active': active_submodule == 'analysis', 'route': 'dashboard_modern.expenses_analysis'}
        ],
        'reports': [
            {'icon': 'bi-arrow-left', 'text': 'Dashboard', 'route': 'dashboard_modern.dashboard', 'is_back': True},
            {'divider': True},
            {'section': 'BERICHTE'},
            {'icon': 'bi-calendar-month', 'text': 'Monatsberichte', 'active': active_submodule == 'monthly' or not active_submodule, 'route': 'dashboard_modern.reports'},
            {'icon': 'bi-calendar-year', 'text': 'Jahresberichte', 'active': active_submodule == 'yearly', 'route': 'dashboard_modern.reports_yearly'},
            {'icon': 'bi-cpu', 'text': 'Geräte-Analyse', 'active': active_submodule == 'devices', 'route': 'dashboard_modern.reports_devices'},
            {'icon': 'bi-box', 'text': 'Produkt-Analyse', 'active': active_submodule == 'products', 'route': 'dashboard_modern.reports_products'},
            {'icon': 'bi-cash', 'text': 'Cashflow', 'active': active_submodule == 'cashflow', 'route': 'dashboard_modern.reports_cashflow'},
            {'icon': 'bi-download', 'text': 'Export', 'active': active_submodule == 'export', 'route': 'dashboard_modern.reports_export'}
        ],
        'settings': [
            {'icon': 'bi-arrow-left', 'text': 'Dashboard', 'route': 'dashboard_modern.dashboard', 'is_back': True},
            {'divider': True},
            {'section': 'EINSTELLUNGEN'},
            {'icon': 'bi-building', 'text': 'Unternehmen', 'active': active_submodule == 'company' or not active_submodule, 'route': 'dashboard_modern.settings'},
            {'icon': 'bi-envelope', 'text': 'E-Mail', 'active': active_submodule == 'email', 'route': 'settings.email_settings'},
            {'icon': 'bi-people', 'text': 'Benutzer', 'active': active_submodule == 'users', 'route': 'dashboard_modern.settings_users'},
            {'icon': 'bi-shield-lock', 'text': 'Sicherheit', 'active': active_submodule == 'security', 'route': 'dashboard_modern.settings_security'},
            {'icon': 'bi-database', 'text': 'Backup', 'active': active_submodule == 'backup', 'route': 'dashboard_modern.settings_backup'},
            {'icon': 'bi-bell', 'text': 'Benachrichtigungen', 'active': active_submodule == 'notifications', 'route': 'dashboard_modern.settings_notifications'},
            {'icon': 'bi-gear', 'text': 'System', 'active': active_submodule == 'system', 'route': 'dashboard_modern.settings_system'}
        ]
    }
    
    return configs.get(active_module, configs['dashboard'])

def render_modern_template(content, title="Dashboard", active_module='dashboard', active_submodule=None, breadcrumb=None):
    """Render template with modern design and contextual navigation"""
    
    navigation = get_navigation_config(active_module, active_submodule)
    
    template = '''
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - Automaten Manager</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            overflow-x: hidden;
        }

        /* Sidebar */
        .sidebar {
            position: fixed;
            top: 0;
            left: 0;
            height: 100vh;
            width: 60px;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-right: 1px solid rgba(255, 255, 255, 0.2);
            transition: width 0.3s ease;
            z-index: 1000;
            overflow: hidden;
        }

        .sidebar:hover {
            width: 260px !important;
        }

        .sidebar-header {
            padding: 20px 15px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .sidebar-header i {
            font-size: 24px;
            color: white;
            min-width: 30px;
        }

        .sidebar-header span {
            color: white;
            font-weight: 600;
            font-size: 18px;
            white-space: nowrap;
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .sidebar:hover .sidebar-header span {
            opacity: 1;
        }

        .nav-section-title {
            padding: 10px 18px;
            color: rgba(255, 255, 255, 0.5);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 10px;
            white-space: nowrap;
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .sidebar:hover .nav-section-title {
            opacity: 1;
        }

        .nav-divider {
            height: 1px;
            background: rgba(255, 255, 255, 0.2);
            margin: 10px 0;
        }

        .nav-item {
            position: relative;
        }

        .nav-link {
            display: flex;
            align-items: center;
            padding: 15px 18px;
            color: rgba(255, 255, 255, 0.9);
            text-decoration: none;
            transition: all 0.3s ease;
            gap: 15px;
        }

        .nav-link:hover {
            background: rgba(255, 255, 255, 0.2);
            color: white;
        }

        .nav-link.active {
            background: rgba(255, 255, 255, 0.25);
            color: white;
            border-left: 3px solid white;
        }

        .nav-link.back-link {
            background: rgba(255, 255, 255, 0.1);
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
            margin-bottom: 10px;
        }

        .nav-link.back-link:hover {
            background: rgba(255, 255, 255, 0.3);
        }

        .nav-link i {
            font-size: 20px;
            min-width: 24px;
        }

        .nav-link span {
            white-space: nowrap;
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .sidebar:hover .nav-link span {
            opacity: 1;
        }

        /* Main Content */
        .main-content {
            margin-left: 60px;
            padding: 20px;
            transition: margin-left 0.3s ease;
            min-height: 100vh;
        }

        .sidebar:hover ~ .main-content {
            margin-left: 260px;
        }

        /* Content Card */
        .content-card {
            background: white;
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
            margin-bottom: 20px;
        }

        /* Breadcrumb */
        .breadcrumb-nav {
            display: flex;
            gap: 10px;
            align-items: center;
            color: #666;
            font-size: 14px;
            margin-bottom: 10px;
        }

        .breadcrumb-nav a {
            color: #667eea;
            text-decoration: none;
        }

        .breadcrumb-nav a:hover {
            text-decoration: underline;
        }

        /* Page Header */
        .page-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #f0f0f0;
        }

        .page-title {
            font-size: 28px;
            font-weight: 600;
            color: #333;
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .page-title i {
            color: #667eea;
            font-size: 32px;
        }

        /* Action Buttons */
        .btn-action {
            padding: 10px 20px;
            border-radius: 10px;
            border: none;
            font-weight: 500;
            transition: all 0.3s ease;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            text-decoration: none;
            color: white;
        }

        .btn-primary-action {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }

        .btn-primary-action:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
            color: white;
        }

        .btn-success-action {
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
        }

        .btn-danger-action {
            background: linear-gradient(135deg, #dc3545 0%, #f86734 100%);
        }

        /* Stats Cards */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            border-radius: 15px;
            color: white;
            position: relative;
            overflow: hidden;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }

        .stat-card.success {
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
        }

        .stat-card.danger {
            background: linear-gradient(135deg, #dc3545 0%, #f86734 100%);
        }

        .stat-card.warning {
            background: linear-gradient(135deg, #ffc107 0%, #ff9800 100%);
        }

        .stat-value {
            font-size: 32px;
            font-weight: bold;
            margin-bottom: 5px;
        }

        .stat-label {
            font-size: 14px;
            opacity: 0.9;
        }

        .stat-icon {
            position: absolute;
            right: 20px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 40px;
            opacity: 0.3;
        }

        /* Module Cards */
        .module-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .module-card {
            background: white;
            border-radius: 15px;
            padding: 30px 20px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            border: 2px solid transparent;
            text-decoration: none;
            color: inherit;
        }

        .module-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
            border-color: #667eea;
            text-decoration: none;
            color: inherit;
        }

        .module-card i {
            font-size: 48px;
            color: #667eea;
            margin-bottom: 15px;
        }

        .module-card h4 {
            font-size: 18px;
            font-weight: 600;
            color: #333;
            margin-bottom: 5px;
        }

        .module-card p {
            font-size: 14px;
            color: #666;
            margin: 0;
        }

        /* Tables */
        .modern-table {
            width: 100%;
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.05);
        }

        .modern-table thead {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .modern-table th {
            padding: 15px;
            font-weight: 500;
            text-align: left;
            border: none;
        }

        .modern-table td {
            padding: 15px;
            border-bottom: 1px solid #f0f0f0;
        }

        .modern-table tbody tr:hover {
            background: #f8f9fa;
        }

        .modern-table tbody tr:last-child td {
            border-bottom: none;
        }

        /* Quick Actions */
        .quick-actions {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }

        .quick-action-card {
            flex: 1;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            color: inherit;
        }

        .quick-action-card:hover {
            background: #e9ecef;
            transform: translateY(-2px);
            text-decoration: none;
            color: inherit;
        }

        .quick-action-card i {
            font-size: 32px;
            color: #667eea;
            margin-bottom: 10px;
        }

        .quick-action-card h5 {
            font-size: 16px;
            color: #333;
            margin: 0;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .stats-grid {
                grid-template-columns: 1fr;
            }
            
            .module-grid {
                grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            }
        }
    </style>
</head>
<body>
    <!-- Sidebar with Dynamic Navigation -->
    <div class="sidebar">
        <div class="sidebar-header">
            <i class="bi bi-cpu-fill"></i>
            <span>Automaten Manager</span>
        </div>
        <nav>
            {% for item in navigation %}
                {% if item.divider %}
                    <div class="nav-divider"></div>
                {% elif item.section %}
                    <div class="nav-section-title">{{ item.section }}</div>
                {% else %}
                    <div class="nav-item">
                        <a href="{{ url_for(item.route) if item.route else '#' }}" 
                           class="nav-link {% if item.active %}active{% endif %} {% if item.is_back %}back-link{% endif %}">
                            <i class="bi {{ item.icon }}"></i>
                            <span>{{ item.text }}</span>
                        </a>
                    </div>
                {% endif %}
            {% endfor %}
        </nav>
    </div>

    <!-- Main Content -->
    <div class="main-content">
        <div class="content-card">
            {% if breadcrumb %}
            <div class="breadcrumb-nav">
                {% for crumb in breadcrumb %}
                    {% if not loop.last %}
                        <a href="{{ crumb.url }}">{{ crumb.text }}</a>
                        <span>›</span>
                    {% else %}
                        <span>{{ crumb.text }}</span>
                    {% endif %}
                {% endfor %}
            </div>
            {% endif %}
            
            {{ content|safe }}
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
    '''
    
    return render_template_string(template, 
                                  content=content, 
                                  title=title, 
                                  navigation=navigation,
                                  breadcrumb=breadcrumb,
                                  url_for=url_for)

@dashboard_modern_bp.route('/dashboard')
@login_required
def dashboard():
    """Main Dashboard View"""
    
    # Get statistics
    current_year = datetime.now().year
    current_month = datetime.now().month
    
    # Year statistics
    year_income = Entry.query.filter(
        extract('year', Entry.date) == current_year
    ).with_entities(func.sum(Entry.amount)).scalar() or 0
    
    year_expenses = Expense.query.filter(
        extract('year', Expense.date) == current_year
    ).with_entities(func.sum(Expense.amount)).scalar() or 0
    
    year_profit = year_income - year_expenses
    
    # Active devices
    active_devices = Device.query.filter_by(status=DeviceStatus.ACTIVE).count()
    total_devices = Device.query.count()
    
    # Month statistics for module cards
    month_income = Entry.query.filter(
        extract('year', Entry.date) == current_year,
        extract('month', Entry.date) == current_month
    ).with_entities(func.sum(Entry.amount)).scalar() or 0
    
    month_expenses = Expense.query.filter(
        extract('year', Expense.date) == current_year,
        extract('month', Expense.date) == current_month
    ).with_entities(func.sum(Expense.amount)).scalar() or 0
    
    # Product count
    product_count = Product.query.count()
    
    content = f'''
    <div class="page-header">
        <div class="page-title">
            <i class="bi bi-speedometer2"></i>
            Dashboard
        </div>
        <div>
            <a href="{url_for('income.index')}" class="btn-action btn-success-action">
                <i class="bi bi-plus-circle"></i> Einnahme erfassen
            </a>
            <a href="{url_for('expenses.index')}" class="btn-action btn-danger-action">
                <i class="bi bi-dash-circle"></i> Ausgabe erfassen
            </a>
        </div>
    </div>

    <!-- Stats Overview -->
    <div class="stats-grid">
        <div class="stat-card success">
            <div class="stat-value">€ {year_income:,.2f}</div>
            <div class="stat-label">Jahreseinnahmen</div>
            <i class="bi bi-graph-up-arrow stat-icon"></i>
        </div>
        <div class="stat-card danger">
            <div class="stat-value">€ {year_expenses:,.2f}</div>
            <div class="stat-label">Jahresausgaben</div>
            <i class="bi bi-graph-down-arrow stat-icon"></i>
        </div>
        <div class="stat-card {'success' if year_profit >= 0 else 'danger'}">
            <div class="stat-value">€ {year_profit:,.2f}</div>
            <div class="stat-label">Jahresgewinn</div>
            <i class="bi bi-trophy stat-icon"></i>
        </div>
        <div class="stat-card warning">
            <div class="stat-value">{active_devices}</div>
            <div class="stat-label">Aktive Geräte</div>
            <i class="bi bi-cpu stat-icon"></i>
        </div>
    </div>

    <!-- Module Cards -->
    <h4 style="margin-bottom: 20px; color: #333;">Module</h4>
    <div class="module-grid">
    <a href="{url_for('dashboard_modern.devices')}" class="module-card">
    <i class="bi bi-cpu"></i>
    <h4>Geräte</h4>
    <p>{active_devices} von {total_devices} aktiv</p>
    </a>
    <a href="{url_for('dashboard_modern.income')}" class="module-card">
    <i class="bi bi-cash-stack"></i>
    <h4>Einnahmen</h4>
    <p>€ {month_income:,.2f} diesen Monat</p>
    </a>
    <a href="{url_for('dashboard_modern.expenses')}" class="module-card">
    <i class="bi bi-receipt"></i>
    <h4>Ausgaben</h4>
    <p>€ {month_expenses:,.2f} diesen Monat</p>
    </a>
    <a href="{url_for('dashboard_modern.inventory')}" class="module-card">
    <i class="bi bi-box-seam"></i>
    <h4>Warenwirtschaft</h4>
    <p>{product_count} Produkte</p>
    </a>
    <a href="{url_for('dashboard_modern.reports')}" class="module-card">
    <i class="bi bi-graph-up"></i>
    <h4>Berichte</h4>
    <p>Analysen & Export</p>
    </a>
    <a href="{url_for('dashboard_modern.settings')}" class="module-card">
    <i class="bi bi-gear"></i>
    <h4>Einstellungen</h4>
    <p>System konfigurieren</p>
    </a>
    </div>
    '''
    
    return render_modern_template(content, title="Dashboard", active_module='dashboard')

@dashboard_modern_bp.route('/devices')
@login_required
def devices():
    """Devices Overview"""
    
    devices = Device.query.all()
    active_count = sum(1 for d in devices if d.status == DeviceStatus.ACTIVE)
    maintenance_count = sum(1 for d in devices if d.status == DeviceStatus.MAINTENANCE)
    inactive_count = sum(1 for d in devices if d.status == DeviceStatus.INACTIVE)
    
    breadcrumb = [
        {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
        {'text': 'Geräte'}
    ]
    
    content = f'''
    <div class="page-header">
        <div class="page-title">
            <i class="bi bi-cpu"></i>
            Geräteverwaltung
        </div>
        <a href="{url_for('devices.index')}" class="btn-action btn-primary-action">
            <i class="bi bi-plus-circle"></i> Neues Gerät
        </a>
    </div>

    <div class="stats-grid">
        <div class="stat-card success">
            <div class="stat-value">{active_count}</div>
            <div class="stat-label">Aktive Geräte</div>
            <i class="bi bi-check-circle stat-icon"></i>
        </div>
        <div class="stat-card warning">
            <div class="stat-value">{maintenance_count}</div>
            <div class="stat-label">In Wartung</div>
            <i class="bi bi-tools stat-icon"></i>
        </div>
        <div class="stat-card danger">
            <div class="stat-value">{inactive_count}</div>
            <div class="stat-label">Inaktiv</div>
            <i class="bi bi-x-circle stat-icon"></i>
        </div>
    </div>

    <table class="modern-table">
        <thead>
            <tr>
                <th>Geräte-ID</th>
                <th>Name</th>
                <th>Standort</th>
                <th>Status</th>
                <th>Aktionen</th>
            </tr>
        </thead>
        <tbody>
    '''
    
    for device in devices:
        status_class = {
            DeviceStatus.ACTIVE: 'success',
            DeviceStatus.MAINTENANCE: 'warning',
            DeviceStatus.INACTIVE: 'danger'
        }.get(device.status, 'secondary')
        
        # Get status display value
        status_display = device.status.value if hasattr(device.status, 'value') else str(device.status)
        
        # Get device ID (might be 'id' or 'serial_number' depending on your model)
        device_id = getattr(device, 'serial_number', device.id)
        
        content += f'''
            <tr>
                <td>{device_id}</td>
                <td>{device.name}</td>
                <td>{device.location or '-'}</td>
                <td><span class="badge bg-{status_class}">{status_display}</span></td>
                <td>
                    <a href="{url_for('devices.index')}" 
                       class="btn btn-sm btn-outline-primary">Details</a>
                </td>
            </tr>
        '''
    
    content += '''
        </tbody>
    </table>
    '''
    
    return render_modern_template(content, title="Geräte", active_module='devices', breadcrumb=breadcrumb)

@dashboard_modern_bp.route('/inventory')
@login_required
def inventory():
    """Inventory Overview"""
    
    products = Product.query.all()
    
    # Count low stock - using safe attribute access
    low_stock = 0
    for p in products:
        current = getattr(p, 'current_stock', None) or getattr(p, 'quantity', 0)
        minimum = getattr(p, 'min_stock', None) or getattr(p, 'minimum_stock', 0)
        if current <= minimum:
            low_stock += 1
    
    breadcrumb = [
        {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
        {'text': 'Warenwirtschaft'}
    ]
    
    content = f'''
    <div class="page-header">
        <div class="page-title">
            <i class="bi bi-box-seam"></i>
            Warenwirtschaft
        </div>
        <div>
            <a href="{url_for('refills.index')}" class="btn-action btn-primary-action">
                <i class="bi bi-plus-circle"></i> Nachfüllung
            </a>
            <a href="#" class="btn-action btn-success-action">
                <i class="bi bi-clipboard-check"></i> Inventur
            </a>
        </div>
    </div>

    <div class="quick-actions">
        <a href="{url_for('dashboard_modern.inventory')}" class="quick-action-card">
            <i class="bi bi-boxes"></i>
            <h5>Lagerbestand</h5>
        </a>
        <a href="{url_for('dashboard_modern.inventory_refills')}" class="quick-action-card">
            <i class="bi bi-arrow-down-circle"></i>
            <h5>Nachfüllungen</h5>
        </a>
        <a href="{url_for('dashboard_modern.inventory_suppliers')}" class="quick-action-card">
            <i class="bi bi-truck"></i>
            <h5>Lieferanten</h5>
        </a>
        <a href="{url_for('dashboard_modern.inventory_products')}" class="quick-action-card">
            <i class="bi bi-box"></i>
            <h5>Produkte</h5>
        </a>
    </div>

    <h4 style="margin-top: 30px; margin-bottom: 20px;">Niedrige Lagerbestände ({low_stock} Produkte)</h4>
    <table class="modern-table">
        <thead>
            <tr>
                <th>Produkt</th>
                <th>Aktueller Bestand</th>
                <th>Mindestbestand</th>
                <th>Status</th>
                <th>Aktion</th>
            </tr>
        </thead>
        <tbody>
    '''
    
    for product in products:
        # Safe attribute access with fallbacks
        current_stock = getattr(product, 'current_stock', None) or getattr(product, 'quantity', 0)
        min_stock = getattr(product, 'min_stock', None) or getattr(product, 'minimum_stock', 0)
        unit = getattr(product, 'unit', 'Stück')
        
        if current_stock <= min_stock:
            status = 'danger' if current_stock == 0 else 'warning'
            content += f'''
                <tr>
                    <td>{product.name}</td>
                    <td>{current_stock} {unit}</td>
                    <td>{min_stock} {unit}</td>
                    <td><span class="badge bg-{status}">{'Leer' if current_stock == 0 else 'Niedrig'}</span></td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="alert('Nachbestellen - In Entwicklung'); return false;">Nachbestellen</button>
                    </td>
                </tr>
            '''
    
    content += '''
        </tbody>
    </table>
    '''
    
    return render_modern_template(content, title="Warenwirtschaft", active_module='inventory', breadcrumb=breadcrumb)

# Rest of the routes remain the same...
# [All other route definitions from the previous file continue here unchanged]

# Stub routes for other modules
@dashboard_modern_bp.route('/income')
@login_required
def income():
    # Redirect zum echten Income-Modul
    return redirect(url_for('income.index'))

@dashboard_modern_bp.route('/expenses')
@login_required
def expenses():
    # Redirect zum echten Expenses-Modul
    return redirect(url_for('expenses.index'))

@dashboard_modern_bp.route('/reports')
@login_required
def reports():
    # Redirect zum echten Reports-Modul
    return redirect(url_for('reports.index'))

@dashboard_modern_bp.route('/settings')
@login_required
def settings():
    # Redirect zum echten Settings-Modul
    return redirect(url_for('settings.index'))

@dashboard_modern_bp.route('/profile')
@login_required
def profile():
    content = '''
    <div class="page-header">
        <div class="page-title">
            <i class="bi bi-person-circle"></i>
            Mein Profil
        </div>
    </div>
    <p>Profil-Einstellungen hier...</p>
    '''
    
    return render_modern_template(content, title="Profil", active_module='dashboard')

# Add stub routes for sub-modules
@dashboard_modern_bp.route('/devices/new')
@login_required
def devices_new():
    return redirect(url_for('devices.index'))  # Öffnet devices mit Modal

# Geräte sub-routes mit echten Implementierungen
@dashboard_modern_bp.route('/devices/qrcodes')
@login_required
def devices_qrcodes():
    return redirect(url_for('device_extensions.qr_codes'))

@dashboard_modern_bp.route('/devices/maintenance')
@login_required
def devices_maintenance():
    return redirect(url_for('device_extensions.maintenance'))

@dashboard_modern_bp.route('/devices/locations')
@login_required
def devices_locations():
    return redirect(url_for('device_extensions.locations'))

@dashboard_modern_bp.route('/devices/utilization')
@login_required
def devices_utilization():
    return redirect(url_for('device_extensions.utilization'))

# Inventory sub-routes
@dashboard_modern_bp.route('/inventory/refills')
@login_required
def inventory_refills():
    # Redirect zu refills.index falls es existiert, sonst zeige eigene Seite
    try:
        return redirect(url_for('refills.index'))
    except:
        breadcrumb = [
            {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
            {'text': 'Warenwirtschaft', 'url': url_for('dashboard_modern.inventory')},
            {'text': 'Nachfüllungen'}
        ]
        content = '<div class="page-header"><div class="page-title"><i class="bi bi-arrow-down-circle"></i> Nachfüllungen</div></div><p>Nachfüllungen-Verwaltung in Entwicklung...</p>'
        return render_modern_template(content, title="Nachfüllungen", active_module='inventory', active_submodule='refills', breadcrumb=breadcrumb)

@dashboard_modern_bp.route('/inventory/stocktaking')
@login_required
def inventory_stocktaking():
    # Redirect zur neuen Inventur-Seite
    return redirect(url_for('inventory.stocktaking'))

@dashboard_modern_bp.route('/inventory/suppliers')
@login_required
def inventory_suppliers():
    # Redirect zu suppliers.index falls es existiert, sonst zeige Platzhalter
    try:
        return redirect(url_for('suppliers.index'))
    except:
        breadcrumb = [
            {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
            {'text': 'Warenwirtschaft', 'url': url_for('dashboard_modern.inventory')},
            {'text': 'Lieferanten'}
        ]
        content = '<div class="page-header"><div class="page-title"><i class="bi bi-truck"></i> Lieferanten</div></div><p>Lieferanten-Verwaltung in Entwicklung...</p>'
        return render_modern_template(content, title="Lieferanten", active_module='inventory', active_submodule='suppliers', breadcrumb=breadcrumb)

@dashboard_modern_bp.route('/inventory/products')
@login_required
def inventory_products():
    # Redirect zu products.index falls es existiert, sonst zeige Platzhalter
    try:
        return redirect(url_for('products.index'))
    except:
        breadcrumb = [
            {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
            {'text': 'Warenwirtschaft', 'url': url_for('dashboard_modern.inventory')},
            {'text': 'Produkte'}
        ]
        content = '<div class="page-header"><div class="page-title"><i class="bi bi-box"></i> Produkte</div></div><p>Produkt-Verwaltung in Entwicklung...</p>'
        return render_modern_template(content, title="Produkte", active_module='inventory', active_submodule='products', breadcrumb=breadcrumb)

@dashboard_modern_bp.route('/inventory/consumption')
@login_required
def inventory_consumption():
    breadcrumb = [
        {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
        {'text': 'Warenwirtschaft', 'url': url_for('dashboard_modern.inventory')},
        {'text': 'Verbrauch'}
    ]
    content = '<div class="page-header"><div class="page-title"><i class="bi bi-graph-down"></i> Verbrauch</div></div><p>Verbrauchsanalyse in Entwicklung...</p>'
    return render_modern_template(content, title="Verbrauch", active_module='inventory', active_submodule='consumption', breadcrumb=breadcrumb)

@dashboard_modern_bp.route('/inventory/orders')
@login_required
def inventory_orders():
    breadcrumb = [
        {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
        {'text': 'Warenwirtschaft', 'url': url_for('dashboard_modern.inventory')},
        {'text': 'Bestellungen'}
    ]
    content = '<div class="page-header"><div class="page-title"><i class="bi bi-calendar-check"></i> Bestellungen</div></div><p>Bestellverwaltung in Entwicklung...</p>'
    return render_modern_template(content, title="Bestellungen", active_module='inventory', active_submodule='orders', breadcrumb=breadcrumb)

# Income sub-routes
@dashboard_modern_bp.route('/income/new')
@login_required
def income_new():
    # Redirect zur Income-Seite mit Modal-Öffnung
    from flask import flash
    flash('open_income_modal', 'info')  # Signal zum Öffnen des Modals
    return redirect(url_for('income.index'))

@dashboard_modern_bp.route('/income/daily')
@login_required
def income_daily():
    breadcrumb = [
        {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
        {'text': 'Einnahmen', 'url': url_for('dashboard_modern.income')},
        {'text': 'Tagesabschluss'}
    ]
    content = '<div class="page-header"><div class="page-title"><i class="bi bi-calendar"></i> Tagesabschluss</div></div><p>Tagesabschluss in Entwicklung...</p>'
    return render_modern_template(content, title="Tagesabschluss", active_module='income', active_submodule='daily', breadcrumb=breadcrumb)

@dashboard_modern_bp.route('/income/by-device')
@login_required
def income_by_device():
    breadcrumb = [
        {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
        {'text': 'Einnahmen', 'url': url_for('dashboard_modern.income')},
        {'text': 'Nach Gerät'}
    ]
    content = '<div class="page-header"><div class="page-title"><i class="bi bi-cpu"></i> Einnahmen nach Gerät</div></div><p>Geräte-Analyse in Entwicklung...</p>'
    return render_modern_template(content, title="Nach Gerät", active_module='income', active_submodule='by_device', breadcrumb=breadcrumb)

@dashboard_modern_bp.route('/income/by-product')
@login_required
def income_by_product():
    breadcrumb = [
        {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
        {'text': 'Einnahmen', 'url': url_for('dashboard_modern.income')},
        {'text': 'Nach Produkt'}
    ]
    content = '<div class="page-header"><div class="page-title"><i class="bi bi-box"></i> Einnahmen nach Produkt</div></div><p>Produkt-Analyse in Entwicklung...</p>'
    return render_modern_template(content, title="Nach Produkt", active_module='income', active_submodule='by_product', breadcrumb=breadcrumb)

@dashboard_modern_bp.route('/income/statistics')
@login_required
def income_statistics():
    breadcrumb = [
        {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
        {'text': 'Einnahmen', 'url': url_for('dashboard_modern.income')},
        {'text': 'Statistiken'}
    ]
    content = '<div class="page-header"><div class="page-title"><i class="bi bi-graph-up"></i> Einnahmen-Statistiken</div></div><p>Statistiken in Entwicklung...</p>'
    return render_modern_template(content, title="Statistiken", active_module='income', active_submodule='statistics', breadcrumb=breadcrumb)

# Expenses sub-routes
@dashboard_modern_bp.route('/expenses/new')
@login_required
def expenses_new():
    breadcrumb = [
        {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
        {'text': 'Ausgaben', 'url': url_for('dashboard_modern.expenses')},
        {'text': 'Neue Ausgabe'}
    ]
    content = '<div class="page-header"><div class="page-title"><i class="bi bi-plus-circle"></i> Neue Ausgabe</div></div><p>Ausgabe erfassen in Entwicklung...</p>'
    return render_modern_template(content, title="Neue Ausgabe", active_module='expenses', active_submodule='new', breadcrumb=breadcrumb)

@dashboard_modern_bp.route('/expenses/categories')
@login_required
def expenses_categories():
    breadcrumb = [
        {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
        {'text': 'Ausgaben', 'url': url_for('dashboard_modern.expenses')},
        {'text': 'Kategorien'}
    ]
    content = '<div class="page-header"><div class="page-title"><i class="bi bi-tags"></i> Kategorien</div></div><p>Kategorien-Verwaltung in Entwicklung...</p>'
    return render_modern_template(content, title="Kategorien", active_module='expenses', active_submodule='categories', breadcrumb=breadcrumb)

@dashboard_modern_bp.route('/expenses/recurring')
@login_required
def expenses_recurring():
    breadcrumb = [
        {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
        {'text': 'Ausgaben', 'url': url_for('dashboard_modern.expenses')},
        {'text': 'Wiederkehrend'}
    ]
    content = '<div class="page-header"><div class="page-title"><i class="bi bi-calendar"></i> Wiederkehrende Ausgaben</div></div><p>Wiederkehrende Ausgaben in Entwicklung...</p>'
    return render_modern_template(content, title="Wiederkehrend", active_module='expenses', active_submodule='recurring', breadcrumb=breadcrumb)

@dashboard_modern_bp.route('/expenses/receipts')
@login_required
def expenses_receipts():
    breadcrumb = [
        {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
        {'text': 'Ausgaben', 'url': url_for('dashboard_modern.expenses')},
        {'text': 'Belege'}
    ]
    content = '<div class="page-header"><div class="page-title"><i class="bi bi-file-earmark"></i> Belege</div></div><p>Belegverwaltung in Entwicklung...</p>'
    return render_modern_template(content, title="Belege", active_module='expenses', active_submodule='receipts', breadcrumb=breadcrumb)

@dashboard_modern_bp.route('/expenses/analysis')
@login_required
def expenses_analysis():
    breadcrumb = [
        {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
        {'text': 'Ausgaben', 'url': url_for('dashboard_modern.expenses')},
        {'text': 'Analyse'}
    ]
    content = '<div class="page-header"><div class="page-title"><i class="bi bi-graph-down"></i> Ausgaben-Analyse</div></div><p>Ausgaben-Analyse in Entwicklung...</p>'
    return render_modern_template(content, title="Analyse", active_module='expenses', active_submodule='analysis', breadcrumb=breadcrumb)

# Reports sub-routes
@dashboard_modern_bp.route('/reports/yearly')
@login_required
def reports_yearly():
    breadcrumb = [
        {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
        {'text': 'Berichte', 'url': url_for('dashboard_modern.reports')},
        {'text': 'Jahresberichte'}
    ]
    content = '<div class="page-header"><div class="page-title"><i class="bi bi-calendar-year"></i> Jahresberichte</div></div><p>Jahresberichte in Entwicklung...</p>'
    return render_modern_template(content, title="Jahresberichte", active_module='reports', active_submodule='yearly', breadcrumb=breadcrumb)

@dashboard_modern_bp.route('/reports/devices')
@login_required
def reports_devices():
    breadcrumb = [
        {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
        {'text': 'Berichte', 'url': url_for('dashboard_modern.reports')},
        {'text': 'Geräte-Analyse'}
    ]
    content = '<div class="page-header"><div class="page-title"><i class="bi bi-cpu"></i> Geräte-Analyse</div></div><p>Geräte-Analyse in Entwicklung...</p>'
    return render_modern_template(content, title="Geräte-Analyse", active_module='reports', active_submodule='devices', breadcrumb=breadcrumb)

@dashboard_modern_bp.route('/reports/products')
@login_required
def reports_products():
    breadcrumb = [
        {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
        {'text': 'Berichte', 'url': url_for('dashboard_modern.reports')},
        {'text': 'Produkt-Analyse'}
    ]
    content = '<div class="page-header"><div class="page-title"><i class="bi bi-box"></i> Produkt-Analyse</div></div><p>Produkt-Analyse in Entwicklung...</p>'
    return render_modern_template(content, title="Produkt-Analyse", active_module='reports', active_submodule='products', breadcrumb=breadcrumb)

@dashboard_modern_bp.route('/reports/cashflow')
@login_required
def reports_cashflow():
    breadcrumb = [
        {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
        {'text': 'Berichte', 'url': url_for('dashboard_modern.reports')},
        {'text': 'Cashflow'}
    ]
    content = '<div class="page-header"><div class="page-title"><i class="bi bi-cash"></i> Cashflow</div></div><p>Cashflow-Analyse in Entwicklung...</p>'
    return render_modern_template(content, title="Cashflow", active_module='reports', active_submodule='cashflow', breadcrumb=breadcrumb)

@dashboard_modern_bp.route('/reports/export')
@login_required
def reports_export():
    breadcrumb = [
        {'text': 'Dashboard', 'url': url_for('dashboard_modern.dashboard')},
        {'text': 'Berichte', 'url': url_for('dashboard_modern.reports')},
        {'text': 'Export'}
    ]
    content = '<div class="page-header"><div class="page-title"><i class="bi bi-download"></i> Export</div></div><p>Export-Funktionen in Entwicklung...</p>'
    return render_modern_template(content, title="Export", active_module='reports', active_submodule='export', breadcrumb=breadcrumb)

# Settings sub-routes
@dashboard_modern_bp.route('/settings/users')
@login_required
def settings_users():
    return redirect(url_for('users.index'))

# Settings sub-routes mit echten Implementierungen
@dashboard_modern_bp.route('/settings/security')
@login_required
def settings_security():
    return redirect(url_for('settings.security'))

@dashboard_modern_bp.route('/settings/backup')
@login_required
def settings_backup():
    return redirect(url_for('settings.backup'))

@dashboard_modern_bp.route('/settings/notifications')
@login_required
def settings_notifications():
    return redirect(url_for('settings.notifications'))

@dashboard_modern_bp.route('/settings/system')
@login_required
def settings_system():
    return redirect(url_for('settings.system'))
