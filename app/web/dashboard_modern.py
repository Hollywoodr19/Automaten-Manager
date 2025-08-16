# app/web/dashboard_modern.py
"""
Modernes Dashboard mit Sidebar und erweiterten Features
"""

from flask import Blueprint, render_template_string, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
from decimal import Decimal
from app import db
from app.models import User, Device, Entry, Expense, DeviceType, DeviceStatus

dashboard_modern_bp = Blueprint('dashboard_modern', __name__)

def get_sidebar_html(active_section='overview'):
    """Generiert die Sidebar für das Dashboard"""
    sections = [
        {'id': 'overview', 'icon': 'bi-grid-3x3-gap', 'text': 'Übersicht'},
        {'id': 'revenue', 'icon': 'bi-graph-up', 'text': 'Einnahmen'},
        {'id': 'expenses', 'icon': 'bi-graph-down', 'text': 'Ausgaben'},
        {'id': 'devices', 'icon': 'bi-cpu', 'text': 'Geräte-Status'},
        {'id': 'analytics', 'icon': 'bi-bar-chart', 'text': 'Analysen'},
        {'id': 'alerts', 'icon': 'bi-bell', 'text': 'Benachrichtigungen'},
    ]
    
    sidebar_html = f"""
    <div class="sidebar">
        <div class="sidebar-header">
            <i class="bi bi-robot"></i>
            <span class="ms-2">Automaten Manager</span>
        </div>
        <div class="sidebar-menu">
    """
    
    for section in sections:
        active = 'active' if section['id'] == active_section else ''
        sidebar_html += f"""
            <a href="#" class="sidebar-item {active}" data-section="{section['id']}">
                <i class="{section['icon']}"></i>
                <span>{section['text']}</span>
            </a>
        """
    
    sidebar_html += """
        </div>
        <div class="sidebar-footer">
            <div class="user-info">
                <i class="bi bi-person-circle"></i>
                <span>""" + current_user.username + """</span>
            </div>
            <a href="/logout" class="logout-btn">
                <i class="bi bi-box-arrow-left"></i>
                <span>Abmelden</span>
            </a>
        </div>
    </div>
    """
    
    return sidebar_html

@dashboard_modern_bp.route('/dashboard')
@login_required
def dashboard():
    """Modernes Dashboard mit Sidebar"""
    
    # Daten sammeln
    devices = Device.query.filter_by(owner_id=current_user.id).all()
    total_devices = len(devices)
    active_devices = len([d for d in devices if d.status == DeviceStatus.ACTIVE])
    
    # Zeiträume
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    last_month_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    
    # Einnahmen berechnen
    today_revenue = db.session.query(db.func.sum(Entry.amount)).join(Device).filter(
        Device.owner_id == current_user.id,
        Entry.date == today
    ).scalar() or 0
    
    week_revenue = db.session.query(db.func.sum(Entry.amount)).join(Device).filter(
        Device.owner_id == current_user.id,
        Entry.date >= week_start
    ).scalar() or 0
    
    month_revenue = db.session.query(db.func.sum(Entry.amount)).join(Device).filter(
        Device.owner_id == current_user.id,
        Entry.date >= month_start
    ).scalar() or 0
    
    last_month_revenue = db.session.query(db.func.sum(Entry.amount)).join(Device).filter(
        Device.owner_id == current_user.id,
        Entry.date >= last_month_start,
        Entry.date < month_start
    ).scalar() or 0
    
    # Ausgaben berechnen
    today_expenses = db.session.query(db.func.sum(Expense.amount)).filter(
        Expense.user_id == current_user.id,
        Expense.date == today
    ).scalar() or 0
    
    week_expenses = db.session.query(db.func.sum(Expense.amount)).filter(
        Expense.user_id == current_user.id,
        Expense.date >= week_start
    ).scalar() or 0
    
    month_expenses = db.session.query(db.func.sum(Expense.amount)).filter(
        Expense.user_id == current_user.id,
        Expense.date >= month_start
    ).scalar() or 0
    
    # Gewinn/Verlust
    today_profit = float(today_revenue) - float(today_expenses)
    week_profit = float(week_revenue) - float(week_expenses)
    month_profit = float(month_revenue) - float(month_expenses)
    
    # Wachstumsrate
    growth_rate = 0
    if last_month_revenue > 0:
        growth_rate = ((float(month_revenue) - float(last_month_revenue)) / float(last_month_revenue)) * 100
    
    # Letzte Transaktionen
    recent_entries = Entry.query.join(Device).filter(
        Device.owner_id == current_user.id
    ).order_by(Entry.created_at.desc()).limit(5).all()
    
    recent_expenses = Expense.query.filter_by(
        user_id=current_user.id
    ).order_by(Expense.created_at.desc()).limit(5).all()
    
    # HTML Template
    html = f"""
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Dashboard - Automaten Manager</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
        <style>
            :root {{
                --sidebar-width: 260px;
                --header-height: 0px;
                --primary: #667eea;
                --primary-dark: #5a67d8;
                --secondary: #764ba2;
                --success: #48bb78;
                --danger: #f56565;
                --warning: #ed8936;
                --dark: #1a202c;
                --gray: #718096;
                --light-gray: #e2e8f0;
                --white: #ffffff;
            }}
            
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: #f7fafc;
                overflow-x: hidden;
            }}
            
            /* Sidebar */
            .sidebar {{
                position: fixed;
                left: 0;
                top: 0;
                bottom: 0;
                width: var(--sidebar-width);
                background: linear-gradient(180deg, var(--primary) 0%, var(--secondary) 100%);
                color: white;
                display: flex;
                flex-direction: column;
                box-shadow: 2px 0 10px rgba(0,0,0,0.1);
                z-index: 1000;
            }}
            
            .sidebar-header {{
                padding: 1.5rem;
                font-size: 1.25rem;
                font-weight: bold;
                border-bottom: 1px solid rgba(255,255,255,0.1);
                display: flex;
                align-items: center;
            }}
            
            .sidebar-header i {{
                font-size: 1.5rem;
            }}
            
            .sidebar-menu {{
                flex: 1;
                padding: 1rem 0;
            }}
            
            .sidebar-item {{
                display: flex;
                align-items: center;
                padding: 0.75rem 1.5rem;
                color: rgba(255,255,255,0.8);
                text-decoration: none;
                transition: all 0.3s;
                position: relative;
            }}
            
            .sidebar-item:hover {{
                background: rgba(255,255,255,0.1);
                color: white;
            }}
            
            .sidebar-item.active {{
                background: rgba(255,255,255,0.15);
                color: white;
            }}
            
            .sidebar-item.active::before {{
                content: '';
                position: absolute;
                left: 0;
                top: 0;
                bottom: 0;
                width: 4px;
                background: white;
            }}
            
            .sidebar-item i {{
                margin-right: 0.75rem;
                font-size: 1.1rem;
            }}
            
            .sidebar-footer {{
                padding: 1rem;
                border-top: 1px solid rgba(255,255,255,0.1);
            }}
            
            .user-info {{
                display: flex;
                align-items: center;
                padding: 0.5rem;
                margin-bottom: 0.5rem;
                background: rgba(255,255,255,0.1);
                border-radius: 8px;
            }}
            
            .user-info i {{
                margin-right: 0.5rem;
                font-size: 1.2rem;
            }}
            
            .logout-btn {{
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 0.5rem;
                background: rgba(255,255,255,0.2);
                color: white;
                text-decoration: none;
                border-radius: 8px;
                transition: all 0.3s;
            }}
            
            .logout-btn:hover {{
                background: rgba(255,255,255,0.3);
                color: white;
            }}
            
            .logout-btn i {{
                margin-right: 0.5rem;
            }}
            
            /* Main Content */
            .main-content {{
                margin-left: var(--sidebar-width);
                padding: 2rem;
                min-height: 100vh;
            }}
            
            /* Top Bar */
            .top-bar {{
                background: white;
                padding: 1.5rem;
                border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                margin-bottom: 2rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            
            .page-title {{
                font-size: 1.75rem;
                font-weight: bold;
                color: var(--dark);
            }}
            
            .date-time {{
                color: var(--gray);
                font-size: 0.9rem;
            }}
            
            /* Stats Grid */
            .stats-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 1.5rem;
                margin-bottom: 2rem;
            }}
            
            .stat-card {{
                background: white;
                padding: 1.5rem;
                border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                transition: all 0.3s;
                position: relative;
                overflow: hidden;
            }}
            
            .stat-card:hover {{
                transform: translateY(-5px);
                box-shadow: 0 5px 20px rgba(0,0,0,0.1);
            }}
            
            .stat-card::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 4px;
                background: linear-gradient(90deg, var(--primary), var(--secondary));
            }}
            
            .stat-card.success::before {{ background: var(--success); }}
            .stat-card.danger::before {{ background: var(--danger); }}
            .stat-card.warning::before {{ background: var(--warning); }}
            
            .stat-label {{
                color: var(--gray);
                font-size: 0.875rem;
                margin-bottom: 0.5rem;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }}
            
            .stat-value {{
                font-size: 1.75rem;
                font-weight: bold;
                color: var(--dark);
                margin-bottom: 0.5rem;
            }}
            
            .stat-change {{
                font-size: 0.875rem;
                display: flex;
                align-items: center;
            }}
            
            .stat-change.positive {{ color: var(--success); }}
            .stat-change.negative {{ color: var(--danger); }}
            
            .stat-icon {{
                width: 40px;
                height: 40px;
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1.25rem;
            }}
            
            .stat-icon.revenue {{ background: rgba(72, 187, 120, 0.1); color: var(--success); }}
            .stat-icon.expense {{ background: rgba(245, 101, 101, 0.1); color: var(--danger); }}
            .stat-icon.profit {{ background: rgba(102, 126, 234, 0.1); color: var(--primary); }}
            .stat-icon.devices {{ background: rgba(237, 137, 54, 0.1); color: var(--warning); }}
            
            /* Content Cards */
            .content-card {{
                background: white;
                border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                margin-bottom: 1.5rem;
            }}
            
            .content-card-header {{
                padding: 1.25rem 1.5rem;
                border-bottom: 1px solid var(--light-gray);
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            
            .content-card-title {{
                font-size: 1.1rem;
                font-weight: 600;
                color: var(--dark);
                display: flex;
                align-items: center;
            }}
            
            .content-card-title i {{
                margin-right: 0.5rem;
                color: var(--primary);
            }}
            
            .content-card-body {{
                padding: 1.5rem;
            }}
            
            /* Transactions */
            .transaction-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.75rem 0;
                border-bottom: 1px solid var(--light-gray);
            }}
            
            .transaction-item:last-child {{
                border-bottom: none;
            }}
            
            .transaction-info {{
                display: flex;
                align-items: center;
            }}
            
            .transaction-icon {{
                width: 36px;
                height: 36px;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                margin-right: 1rem;
            }}
            
            .transaction-icon.income {{
                background: rgba(72, 187, 120, 0.1);
                color: var(--success);
            }}
            
            .transaction-icon.expense {{
                background: rgba(245, 101, 101, 0.1);
                color: var(--danger);
            }}
            
            .transaction-details h6 {{
                margin: 0;
                font-size: 0.9rem;
                font-weight: 600;
                color: var(--dark);
            }}
            
            .transaction-details small {{
                color: var(--gray);
            }}
            
            .transaction-amount {{
                font-weight: 600;
                font-size: 0.95rem;
            }}
            
            .transaction-amount.income {{ color: var(--success); }}
            .transaction-amount.expense {{ color: var(--danger); }}
            
            /* Responsive */
            @media (max-width: 768px) {{
                .sidebar {{
                    transform: translateX(-100%);
                }}
                
                .main-content {{
                    margin-left: 0;
                }}
                
                .stats-grid {{
                    grid-template-columns: 1fr;
                }}
            }}
        </style>
    </head>
    <body>
        {get_sidebar_html('overview')}
        
        <div class="main-content">
            <div class="top-bar">
                <h1 class="page-title">Dashboard</h1>
                <div class="date-time">
                    <i class="bi bi-calendar3"></i> {datetime.now().strftime('%d.%m.%Y %H:%M')}
                </div>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card success">
                    <div class="stat-label">
                        <span>Einnahmen (Monat)</span>
                        <div class="stat-icon revenue">
                            <i class="bi bi-arrow-up-circle"></i>
                        </div>
                    </div>
                    <div class="stat-value">{month_revenue:.2f} €</div>
                    <div class="stat-change {'positive' if growth_rate > 0 else 'negative'}">
                        <i class="bi bi-{'arrow-up' if growth_rate > 0 else 'arrow-down'}"></i>
                        <span>{abs(growth_rate):.1f}% zum Vormonat</span>
                    </div>
                </div>
                
                <div class="stat-card danger">
                    <div class="stat-label">
                        <span>Ausgaben (Monat)</span>
                        <div class="stat-icon expense">
                            <i class="bi bi-arrow-down-circle"></i>
                        </div>
                    </div>
                    <div class="stat-value">{month_expenses:.2f} €</div>
                    <div class="stat-change">
                        <span>Diese Woche: {week_expenses:.2f} €</span>
                    </div>
                </div>
                
                <div class="stat-card {'success' if month_profit > 0 else 'danger'}">
                    <div class="stat-label">
                        <span>Gewinn/Verlust (Monat)</span>
                        <div class="stat-icon profit">
                            <i class="bi bi-{'graph-up' if month_profit > 0 else 'graph-down'}"></i>
                        </div>
                    </div>
                    <div class="stat-value">{month_profit:.2f} €</div>
                    <div class="stat-change">
                        <span>Heute: {today_profit:+.2f} €</span>
                    </div>
                </div>
                
                <div class="stat-card warning">
                    <div class="stat-label">
                        <span>Aktive Geräte</span>
                        <div class="stat-icon devices">
                            <i class="bi bi-cpu"></i>
                        </div>
                    </div>
                    <div class="stat-value">{active_devices}/{total_devices}</div>
                    <div class="stat-change">
                        <span>{(active_devices/total_devices*100) if total_devices > 0 else 0:.0f}% Verfügbarkeit</span>
                    </div>
                </div>
            </div>
            
            <div class="row">
                <div class="col-lg-6">
                    <div class="content-card">
                        <div class="content-card-header">
                            <h5 class="content-card-title">
                                <i class="bi bi-arrow-up-circle"></i> Letzte Einnahmen
                            </h5>
                            <a href="/entries" class="btn btn-sm btn-outline-primary">Alle anzeigen</a>
                        </div>
                        <div class="content-card-body">
    """
    
    if recent_entries:
        for entry in recent_entries:
            html += f"""
                            <div class="transaction-item">
                                <div class="transaction-info">
                                    <div class="transaction-icon income">
                                        <i class="bi bi-plus-circle"></i>
                                    </div>
                                    <div class="transaction-details">
                                        <h6>{entry.device.name}</h6>
                                        <small>{entry.date.strftime('%d.%m.%Y')}</small>
                                    </div>
                                </div>
                                <div class="transaction-amount income">+{entry.amount:.2f} €</div>
                            </div>
            """
    else:
        html += '<p class="text-muted text-center">Keine Einnahmen vorhanden</p>'
    
    html += """
                        </div>
                    </div>
                </div>
                
                <div class="col-lg-6">
                    <div class="content-card">
                        <div class="content-card-header">
                            <h5 class="content-card-title">
                                <i class="bi bi-arrow-down-circle"></i> Letzte Ausgaben
                            </h5>
                            <a href="/expenses" class="btn btn-sm btn-outline-danger">Alle anzeigen</a>
                        </div>
                        <div class="content-card-body">
    """
    
    if recent_expenses:
        for expense in recent_expenses:
            html += f"""
                            <div class="transaction-item">
                                <div class="transaction-info">
                                    <div class="transaction-icon expense">
                                        <i class="bi bi-dash-circle"></i>
                                    </div>
                                    <div class="transaction-details">
                                        <h6>{expense.category.value}</h6>
                                        <small>{expense.date.strftime('%d.%m.%Y')}</small>
                                    </div>
                                </div>
                                <div class="transaction-amount expense">-{expense.amount:.2f} €</div>
                            </div>
            """
    else:
        html += '<p class="text-muted text-center">Keine Ausgaben vorhanden</p>'
    
    html += """
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            // Sidebar Navigation
            document.querySelectorAll('.sidebar-item').forEach(item => {
                item.addEventListener('click', function(e) {
                    e.preventDefault();
                    document.querySelectorAll('.sidebar-item').forEach(i => i.classList.remove('active'));
                    this.classList.add('active');
                    // Hier könnte Content dynamisch geladen werden
                });
            });
        </script>
    </body>
    </html>
    """
    
    return render_template_string(html)
