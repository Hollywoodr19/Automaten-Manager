# app/api/v1/__init__.py
"""REST API v1 für Automaten Manager"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, create_access_token, get_jwt_identity
from datetime import datetime, timedelta
from app.models import db, User, Device, Entry, Expense
from app import limiter

api_v1_bp = Blueprint('api_v1', __name__)


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@api_v1_bp.route('/auth/login', methods=['POST'])
@limiter.limit("5 per minute")
def api_login():
    """API Login - JWT Token generieren"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({'error': 'Invalid credentials'}), 401

    if user.is_locked():
        return jsonify({'error': 'Account locked'}), 403

    # JWT Token erstellen
    access_token = create_access_token(
        identity=user.id,
        additional_claims={
            'username': user.username,
            'is_admin': user.is_admin
        }
    )

    user.record_login()

    return jsonify({
        'access_token': access_token,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_admin': user.is_admin
        }
    }), 200


@api_v1_bp.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
def api_refresh():
    """Token erneuern"""
    current_user_id = get_jwt_identity()
    access_token = create_access_token(identity=current_user_id)
    return jsonify({'access_token': access_token}), 200


# ============================================================================
# DEVICE ENDPOINTS
# ============================================================================

@api_v1_bp.route('/devices', methods=['GET'])
@jwt_required()
def get_devices():
    """Alle Geräte abrufen"""
    current_user_id = get_jwt_identity()

    devices = Device.query.filter_by(owner_id=current_user_id).all()

    return jsonify({
        'devices': [{
            'id': d.id,
            'name': d.name,
            'type': d.type.value,
            'status': d.status.value,
            'location': d.location,
            'total_revenue': float(d.get_total_revenue()),
            'total_expenses': float(d.get_total_expenses()),
            'profit': float(d.get_profit()),
            'roi': d.get_roi()
        } for d in devices]
    }), 200


@api_v1_bp.route('/devices/<int:device_id>', methods=['GET'])
@jwt_required()
def get_device(device_id):
    """Einzelnes Gerät abrufen"""
    current_user_id = get_jwt_identity()

    device = Device.query.filter_by(id=device_id, owner_id=current_user_id).first()

    if not device:
        return jsonify({'error': 'Device not found'}), 404

    return jsonify({
        'device': {
            'id': device.id,
            'name': device.name,
            'type': device.type.value,
            'status': device.status.value,
            'serial_number': device.serial_number,
            'location': device.location,
            'purchase_date': device.purchase_date.isoformat() if device.purchase_date else None,
            'purchase_price': float(device.purchase_price),
            'total_revenue': float(device.get_total_revenue()),
            'total_expenses': float(device.get_total_expenses()),
            'profit': float(device.get_profit()),
            'roi': device.get_roi(),
            'daily_average': float(device.get_daily_average()),
            'needs_maintenance': device.needs_maintenance
        }
    }), 200


@api_v1_bp.route('/devices', methods=['POST'])
@jwt_required()
def create_device():
    """Neues Gerät erstellen"""
    current_user_id = get_jwt_identity()
    data = request.get_json()

    from app.models import DeviceType, DeviceStatus

    try:
        device = Device(
            name=data.get('name'),
            type=DeviceType(data.get('type')),
            status=DeviceStatus(data.get('status', 'active')),
            serial_number=data.get('serial_number'),
            location=data.get('location'),
            owner_id=current_user_id
        )

        if data.get('purchase_price'):
            device.purchase_price = data.get('purchase_price')

        db.session.add(device)
        db.session.commit()

        return jsonify({
            'message': 'Device created successfully',
            'device_id': device.id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@api_v1_bp.route('/devices/<int:device_id>', methods=['PUT'])
@jwt_required()
def update_device(device_id):
    """Gerät aktualisieren"""
    current_user_id = get_jwt_identity()

    device = Device.query.filter_by(id=device_id, owner_id=current_user_id).first()

    if not device:
        return jsonify({'error': 'Device not found'}), 404

    data = request.get_json()

    try:
        if 'name' in data:
            device.name = data['name']
        if 'location' in data:
            device.location = data['location']
        if 'status' in data:
            from app.models import DeviceStatus
            device.status = DeviceStatus(data['status'])

        db.session.commit()

        return jsonify({'message': 'Device updated successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@api_v1_bp.route('/devices/<int:device_id>', methods=['DELETE'])
@jwt_required()
def delete_device(device_id):
    """Gerät löschen"""
    current_user_id = get_jwt_identity()

    device = Device.query.filter_by(id=device_id, owner_id=current_user_id).first()

    if not device:
        return jsonify({'error': 'Device not found'}), 404

    try:
        db.session.delete(device)
        db.session.commit()

        return jsonify({'message': 'Device deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


# ============================================================================
# ENTRY ENDPOINTS
# ============================================================================

@api_v1_bp.route('/entries', methods=['GET'])
@jwt_required()
def get_entries():
    """Einnahmen abrufen"""
    current_user_id = get_jwt_identity()

    # Query-Parameter
    device_id = request.args.get('device_id', type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    # Query aufbauen
    query = Entry.query.join(Device).filter(Device.owner_id == current_user_id)

    if device_id:
        query = query.filter(Entry.device_id == device_id)

    if start_date:
        query = query.filter(Entry.date >= datetime.fromisoformat(start_date).date())

    if end_date:
        query = query.filter(Entry.date <= datetime.fromisoformat(end_date).date())

    # Pagination
    pagination = query.order_by(Entry.date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        'entries': [{
            'id': e.id,
            'device_id': e.device_id,
            'device_name': e.device.name,
            'amount': float(e.amount),
            'date': e.date.isoformat(),
            'description': e.description,
            'is_validated': e.is_validated
        } for e in pagination.items],
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'pages': pagination.pages
        }
    }), 200


@api_v1_bp.route('/entries', methods=['POST'])
@jwt_required()
def create_entry():
    """Neue Einnahme erstellen"""
    current_user_id = get_jwt_identity()
    data = request.get_json()

    # Prüfen ob Gerät dem Benutzer gehört
    device = Device.query.filter_by(
        id=data.get('device_id'),
        owner_id=current_user_id
    ).first()

    if not device:
        return jsonify({'error': 'Device not found or access denied'}), 404

    try:
        entry = Entry(
            device_id=device.id,
            amount=data.get('amount'),
            date=datetime.fromisoformat(data.get('date')).date() if data.get('date') else None,
            description=data.get('description'),
            user_id=current_user_id
        )

        db.session.add(entry)
        db.session.commit()

        return jsonify({
            'message': 'Entry created successfully',
            'entry_id': entry.id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


# ============================================================================
# STATISTICS ENDPOINTS
# ============================================================================

@api_v1_bp.route('/statistics/overview', methods=['GET'])
@jwt_required()
def get_statistics_overview():
    """Statistik-Übersicht"""
    current_user_id = get_jwt_identity()

    from datetime import date, timedelta
    from sqlalchemy import func

    # Zeiträume
    today = date.today()
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    # Queries
    total_devices = Device.query.filter_by(owner_id=current_user_id).count()
    active_devices = Device.query.filter_by(owner_id=current_user_id, status='active').count()

    total_revenue = db.session.query(func.sum(Entry.amount)).join(Device).filter(
        Device.owner_id == current_user_id
    ).scalar() or 0

    month_revenue = db.session.query(func.sum(Entry.amount)).join(Device).filter(
        Device.owner_id == current_user_id,
        Entry.date >= month_start
    ).scalar() or 0

    total_expenses = db.session.query(func.sum(Expense.amount)).filter(
        Expense.user_id == current_user_id
    ).scalar() or 0

    return jsonify({
        'devices': {
            'total': total_devices,
            'active': active_devices
        },
        'revenue': {
            'total': float(total_revenue),
            'month': float(month_revenue),
            'average_per_device': float(total_revenue / total_devices) if total_devices > 0 else 0
        },
        'expenses': {
            'total': float(total_expenses)
        },
        'profit': {
            'total': float(total_revenue - total_expenses),
            'margin': float((total_revenue - total_expenses) / total_revenue * 100) if total_revenue > 0 else 0
        }
    }), 200


@api_v1_bp.route('/statistics/chart/<period>', methods=['GET'])
@jwt_required()
def get_chart_data(period):
    """Chart-Daten für verschiedene Zeiträume"""
    current_user_id = get_jwt_identity()

    from datetime import date, timedelta
    from sqlalchemy import func, extract

    if period == 'week':
        # Letzte 7 Tage
        start_date = date.today() - timedelta(days=6)

        data = db.session.query(
            Entry.date,
            func.sum(Entry.amount).label('revenue')
        ).join(Device).filter(
            Device.owner_id == current_user_id,
            Entry.date >= start_date
        ).group_by(Entry.date).order_by(Entry.date).all()

        return jsonify({
            'labels': [d.date.isoformat() for d in data],
            'data': [float(d.revenue) for d in data]
        }), 200

    elif period == 'month':
        # Letzte 30 Tage
        start_date = date.today() - timedelta(days=29)

        data = db.session.query(
            Entry.date,
            func.sum(Entry.amount).label('revenue')
        ).join(Device).filter(
            Device.owner_id == current_user_id,
            Entry.date >= start_date
        ).group_by(Entry.date).order_by(Entry.date).all()

        return jsonify({
            'labels': [d.date.isoformat() for d in data],
            'data': [float(d.revenue) for d in data]
        }), 200

    elif period == 'year':
        # Letzte 12 Monate
        data = db.session.query(
            extract('month', Entry.date).label('month'),
            extract('year', Entry.date).label('year'),
            func.sum(Entry.amount).label('revenue')
        ).join(Device).filter(
            Device.owner_id == current_user_id,
            Entry.date >= date.today() - timedelta(days=365)
        ).group_by('year', 'month').order_by('year', 'month').all()

        return jsonify({
            'labels': [f"{int(d.month)}/{int(d.year)}" for d in data],
            'data': [float(d.revenue) for d in data]
        }), 200

    return jsonify({'error': 'Invalid period'}), 400


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@api_v1_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404


@api_v1_bp.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500