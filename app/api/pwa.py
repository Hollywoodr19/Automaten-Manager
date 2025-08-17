# app/api/pwa.py
"""
PWA API Endpoints für Automaten Manager
Handles Push Notifications, Background Sync und Offline Support
"""

from flask import Blueprint, jsonify, request, send_file, current_app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import json
import os

pwa_bp = Blueprint('pwa_api', __name__, url_prefix='/api/pwa')

# Push Notification Subscriptions Storage (sollte in DB gespeichert werden)
push_subscriptions = {}

@pwa_bp.route('/ping', methods=['GET', 'HEAD'])
def ping():
    """Simple ping endpoint für Online-Check"""
    return jsonify({'status': 'online', 'timestamp': datetime.now().isoformat()})


@pwa_bp.route('/manifest.json')
def manifest():
    """Dynamisches Manifest basierend auf User-Settings"""
    # Basis-Manifest laden
    manifest_path = os.path.join(current_app.static_folder, 'manifest.json')
    with open(manifest_path, 'r') as f:
        manifest_data = json.load(f)
    
    # Personalisierung basierend auf User (wenn eingeloggt)
    if current_user.is_authenticated:
        manifest_data['name'] = f"Automaten Manager - {current_user.username}"
        # Theme aus User-Preferences
        if hasattr(current_user, 'theme_color'):
            manifest_data['theme_color'] = current_user.theme_color
    
    return jsonify(manifest_data)


@pwa_bp.route('/push/subscribe', methods=['POST'])
@login_required
def subscribe_push():
    """Push Notification Subscription speichern"""
    subscription = request.json
    
    if not subscription:
        return jsonify({'error': 'No subscription data'}), 400
    
    # In Production: In Datenbank speichern
    push_subscriptions[current_user.id] = subscription
    
    # Test-Notification senden
    send_test_notification(current_user.id)
    
    return jsonify({'success': True, 'message': 'Push notifications enabled'})


@pwa_bp.route('/push/unsubscribe', methods=['POST'])
@login_required
def unsubscribe_push():
    """Push Notification Subscription entfernen"""
    if current_user.id in push_subscriptions:
        del push_subscriptions[current_user.id]
    
    return jsonify({'success': True, 'message': 'Push notifications disabled'})


@pwa_bp.route('/sync/entries', methods=['POST'])
@login_required
def sync_entries():
    """Offline erfasste Einträge synchronisieren"""
    entries = request.json.get('entries', [])
    synced = []
    failed = []
    
    for entry_data in entries:
        try:
            # Eintrag in DB speichern
            from app.models import Entry, Device
            
            device = Device.query.get(entry_data['device_id'])
            if not device or device.owner_id != current_user.id:
                failed.append({'id': entry_data.get('temp_id'), 'error': 'Invalid device'})
                continue
            
            entry = Entry(
                device_id=entry_data['device_id'],
                amount=entry_data['amount'],
                date=datetime.fromisoformat(entry_data['date']),
                description=entry_data.get('description'),
                user_id=current_user.id
            )
            
            from app import db
            db.session.add(entry)
            db.session.commit()
            
            synced.append({
                'temp_id': entry_data.get('temp_id'),
                'id': entry.id,
                'synced_at': datetime.now().isoformat()
            })
            
        except Exception as e:
            failed.append({
                'id': entry_data.get('temp_id'),
                'error': str(e)
            })
    
    return jsonify({
        'synced': synced,
        'failed': failed,
        'total': len(entries)
    })


@pwa_bp.route('/cache/dashboard', methods=['GET'])
@login_required
def cache_dashboard():
    """Dashboard-Daten für Offline-Cache"""
    from app.models import Device, Entry, Expense
    from sqlalchemy import func
    
    # Aktuelle Statistiken
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    # Einnahmen
    daily_income = Entry.query.join(Device).filter(
        Device.owner_id == current_user.id,
        Entry.date == today
    ).with_entities(func.sum(Entry.amount)).scalar() or 0
    
    weekly_income = Entry.query.join(Device).filter(
        Device.owner_id == current_user.id,
        Entry.date >= week_start
    ).with_entities(func.sum(Entry.amount)).scalar() or 0
    
    monthly_income = Entry.query.join(Device).filter(
        Device.owner_id == current_user.id,
        Entry.date >= month_start
    ).with_entities(func.sum(Entry.amount)).scalar() or 0
    
    # Geräte
    devices = Device.query.filter_by(owner_id=current_user.id).all()
    device_data = [{
        'id': d.id,
        'name': d.name,
        'status': d.status.value if hasattr(d.status, 'value') else str(d.status),
        'location': d.location
    } for d in devices]
    
    # Letzte Einträge
    recent_entries = Entry.query.join(Device).filter(
        Device.owner_id == current_user.id
    ).order_by(Entry.date.desc()).limit(10).all()
    
    entries_data = [{
        'id': e.id,
        'device_name': e.device.name,
        'amount': float(e.amount),
        'date': e.date.isoformat(),
        'description': e.description
    } for e in recent_entries]
    
    return jsonify({
        'cached_at': datetime.now().isoformat(),
        'statistics': {
            'daily_income': float(daily_income),
            'weekly_income': float(weekly_income),
            'monthly_income': float(monthly_income),
            'active_devices': len([d for d in devices if d.status.value == 'active']) if devices else 0,
            'total_devices': len(devices)
        },
        'devices': device_data,
        'recent_entries': entries_data
    })


@pwa_bp.route('/cache/products', methods=['GET'])
@login_required
def cache_products():
    """Produkt-Daten für Offline-Cache"""
    from app.models import Product
    
    products = Product.query.filter_by(user_id=current_user.id).all()
    
    product_data = [{
        'id': p.id,
        'name': p.name,
        'category': p.category.value if p.category else None,
        'unit': p.unit.value if p.unit else None,
        'current_stock': p.get_current_stock() if hasattr(p, 'get_current_stock') else 0,
        'reorder_point': p.reorder_point,
        'default_price': float(p.default_price) if p.default_price else 0
    } for p in products]
    
    return jsonify({
        'cached_at': datetime.now().isoformat(),
        'products': product_data,
        'total': len(product_data)
    })


@pwa_bp.route('/updates/check', methods=['GET'])
def check_updates():
    """Prüft ob App-Updates verfügbar sind"""
    current_version = request.args.get('version', '1.0.0')
    latest_version = '1.0.0'  # In Production: Aus Config oder DB
    
    return jsonify({
        'current_version': current_version,
        'latest_version': latest_version,
        'update_available': current_version != latest_version,
        'update_url': '/static/sw.js' if current_version != latest_version else None
    })


# Helper Functions
def send_test_notification(user_id):
    """Test Push Notification senden"""
    if user_id not in push_subscriptions:
        return False
    
    # In Production: Web Push Library verwenden
    # from pywebpush import webpush
    
    subscription = push_subscriptions[user_id]
    
    # webpush(
    #     subscription_info=subscription,
    #     data=json.dumps({
    #         'title': 'Willkommen bei Automaten Manager!',
    #         'body': 'Push Notifications sind aktiviert',
    #         'icon': '/static/icons/icon-192x192.png',
    #         'badge': '/static/icons/badge-72x72.png'
    #     }),
    #     vapid_private_key=VAPID_PRIVATE_KEY,
    #     vapid_claims={
    #         'sub': 'mailto:admin@automaten-manager.de'
    #     }
    # )
    
    return True


def send_notification(user_id, title, body, data=None):
    """Push Notification an User senden"""
    if user_id not in push_subscriptions:
        return False
    
    # Implementation mit pywebpush
    # ...
    
    return True
