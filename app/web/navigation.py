# app/web/navigation.py
"""
Zentrale Navigation für konsistente Menüführung
"""

from flask_login import current_user

def get_navigation_items():
    """
    Zentrale Definition aller Navigations-Items
    """
    items = [
        {'url': '/dashboard', 'icon': 'bi-speedometer2', 'text': 'Dashboard', 'id': 'dashboard'},
        {'url': '/devices', 'icon': 'bi-pc-display', 'text': 'Geräte', 'id': 'devices'},
        {'url': '/entries', 'icon': 'bi-cash-stack', 'text': 'Einnahmen', 'id': 'entries'},
        {'url': '/expenses', 'icon': 'bi-wallet2', 'text': 'Ausgaben', 'id': 'expenses'},
        {'url': '/refills', 'icon': 'bi-box-seam-fill', 'text': 'Warenwirtschaft', 'id': 'refills'},
        {'url': '/products', 'icon': 'bi-box', 'text': 'Produkte', 'id': 'products'},
        {'url': '/suppliers', 'icon': 'bi-truck', 'text': 'Lieferanten', 'id': 'suppliers'},
        {'url': '/users', 'icon': 'bi-people', 'text': 'Benutzer', 'id': 'users', 'admin_only': True},

        # Zukünftige Menüpunkte:

        # {'url': '/reports', 'icon': 'bi-file-earmark-bar-graph', 'text': 'Reports', 'id': 'reports'},
        # {'url': '/settings', 'icon': 'bi-gear', 'text': 'Einstellungen', 'id': 'settings'},
    ]
    return items


def get_navigation_html(active_page=None):
    """
    Generiert die komplette Navigation als HTML-String
    Für render_template_string
    """
    items = get_navigation_items()

    nav_html = """
    <nav class="navbar navbar-expand-lg navbar-light mb-4">
        <div class="container">
            <a class="navbar-brand" href="/dashboard">
                <i class="bi bi-box-seam"></i> Automaten Manager
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <div class="navbar-nav ms-auto">
    """

    # Menü-Items
    for item in items:
        # Prüfen ob Admin-only
        if item.get('admin_only') and not current_user.is_admin:
            continue

        active_class = 'active' if item['id'] == active_page else ''
        nav_html += f"""
            <a class="nav-link {active_class}" href="{item['url']}">
                <i class="bi {item['icon']}"></i> {item['text']}
            </a>
        """

    # User-Bereich
    if current_user.is_authenticated:
        nav_html += f"""
                    <span class="nav-link">
                        <i class="bi bi-person-circle"></i> {current_user.username}
                    </span>
                    <a class="nav-link text-danger" href="/logout">
                        <i class="bi bi-box-arrow-right"></i> Logout
                    </a>
        """

    nav_html += """
                </div>
            </div>
        </div>
    </nav>
    """

    return nav_html


def render_with_base_new(content_template, active_page=None, **kwargs):
    """
    Verbesserte render_with_base Funktion mit zentraler Navigation
    Ersetzt die alte Funktion in allen Modulen
    """
    from flask import get_flashed_messages

    # Base HTML
    base_html = f"""
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{kwargs.get('title', 'Automaten Manager')}</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.0/font/bootstrap-icons.css">
        <style>
            body {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }}
            .navbar {{ background: rgba(255,255,255,0.95); backdrop-filter: blur(10px); }}
            .navbar-nav .nav-link.active {{ 
                color: #667eea !important; 
                font-weight: 600;
                border-bottom: 2px solid #667eea;
            }}
            .card {{ border: none; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }}
            .stat-card {{ transition: transform 0.3s; }}
            .stat-card:hover {{ transform: translateY(-5px); }}

            /* Device Cards */
            .device-card {{ position: relative; transition: all 0.3s; }}
            .device-card:hover {{ transform: translateY(-5px); box-shadow: 0 15px 40px rgba(0,0,0,0.15); }}
            .device-card::before {{
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 5px;
                background: linear-gradient(90deg, #667eea, #764ba2);
            }}
            .device-card.status-active::before {{ background: #28a745; }}
            .device-card.status-maintenance::before {{ background: #ffc107; }}
            .device-card.status-inactive::before {{ background: #6c757d; }}

            .action-buttons {{
                position: absolute;
                top: 1rem;
                right: 1rem;
                opacity: 0;
                transition: opacity 0.3s;
            }}
            .device-card:hover .action-buttons {{ opacity: 1; }}

            /* Weitere Styles aus dem Original */
            .modal-content {{ border-radius: 15px; }}
            .modal-header {{ border-bottom: 1px solid #dee2e6; }}
            .modal-footer {{ border-top: 1px solid #dee2e6; }}
        </style>
        {kwargs.get('extra_css', '')}
    </head>
    <body>
    """

    # Navigation einfügen (zentral!)
    if current_user.is_authenticated:
        base_html += get_navigation_html(active_page)

    base_html += '<div class="container-fluid px-4">'

    # Flash Messages
    with_messages = kwargs.get('with_messages', True)
    if with_messages:
        for category, message in get_flashed_messages(with_categories=True):
            if category == 'message':
                category = 'info'
            base_html += f"""
            <div class="alert alert-{category} alert-dismissible fade show">
                {message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
            """

    # Custom messages (legacy support)
    messages = kwargs.get('messages', [])
    for category, message in messages:
        base_html += f"""
        <div class="alert alert-{category} alert-dismissible fade show">
            {message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
        """

    # Content
    base_html += content_template

    # Footer
    base_html += """
        </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
        """ + kwargs.get('extra_scripts', '') + """
    </body>
    </html>
    """

    return base_html