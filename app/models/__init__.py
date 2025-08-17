# app/models/__init__.py
"""
Datenbank-Models für Automaten Manager v2.0
Vollständige Implementation mit korrekten Relationships
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from enum import Enum
import uuid
import secrets
from typing import Optional, List, Dict, Any

from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, extract, and_, or_, desc, asc, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import validates
import pyotp
import qrcode
from io import BytesIO
import base64

# Import db from app
from app import db

# Inventur Import
from .inventory import (
    Product,
    ProductUnit,
    ProductCategory,
    Supplier,
    Refill,
    RefillItem,
    InventoryMovement
)


# ============================================================================
# ENUMS
# ============================================================================

class DeviceType(Enum):
    """Gerätetypen"""
    KAFFEE = 'kaffee'
    GETRAENKE = 'getraenke'
    SNACKS = 'snacks'
    KOMBI = 'kombi'


class DeviceStatus(Enum):
    """Gerätestatus"""
    ACTIVE = 'active'
    MAINTENANCE = 'maintenance'
    INACTIVE = 'inactive'
    DEFECT = 'defect'


class ExpenseCategory(Enum):
    """Ausgabenkategorien"""
    ANSCHAFFUNG = 'anschaffung'
    WECHSELGELD = 'wechselgeld'
    WARTUNG = 'wartung'
    REPARATUR = 'reparatur'
    NACHFUELLUNG = 'nachfuellung'
    STROM = 'strom'
    MIETE = 'miete'
    VERSICHERUNG = 'versicherung'
    REINIGUNG = 'reinigung'
    SONSTIGES = 'sonstiges'


class NotificationType(Enum):
    """Benachrichtigungstypen"""
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    SUCCESS = 'success'
    MAINTENANCE = 'maintenance'
    REPORT = 'report'


class AuditAction(Enum):
    """Audit-Aktionen"""
    CREATE = 'create'
    UPDATE = 'update'
    DELETE = 'delete'
    LOGIN = 'login'
    LOGOUT = 'logout'
    EXPORT = 'export'
    IMPORT = 'import'


class LoginLog(db.Model):
    """Login-Historie für Sicherheits-Tracking"""
    __tablename__ = 'login_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    success = db.Column(db.Boolean, default=True, nullable=False)
    ip_address = db.Column(db.String(45))  # IPv6 ready
    user_agent = db.Column(db.String(200))
    failure_reason = db.Column(db.String(100))  # z.B. "wrong_password", "account_locked"

    # Relationship
    user = db.relationship('User', backref=db.backref('login_logs', lazy='dynamic'))

    def __repr__(self):
        return f'<LoginLog {self.user_id} at {self.timestamp}>'

# ============================================================================
# MIXINS
# ============================================================================

class TimestampMixin:
    """Mixin für automatische Zeitstempel"""
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)


class UUIDMixin:
    """Mixin für UUID"""
    uuid = db.Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False, index=True)


# ============================================================================
# USER MODEL
# ============================================================================

class User(UserMixin, TimestampMixin, UUIDMixin, db.Model):
    """Benutzer-Model mit erweiterten Features"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # Profile
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    avatar_url = db.Column(db.String(255))

    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)

    # Security
    last_login = db.Column(db.DateTime)
    login_count = db.Column(db.Integer, default=0)
    failed_login_count = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime)
    password_changed_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 2FA
    two_factor_secret = db.Column(db.String(32))
    two_factor_enabled = db.Column(db.Boolean, default=False)
    backup_codes = db.Column(db.Text)  # JSON string

    # API
    api_key = db.Column(db.String(64), unique=True, index=True)
    api_key_created_at = db.Column(db.DateTime)

    # Preferences
    language = db.Column(db.String(5), default='de')
    timezone = db.Column(db.String(50), default='Europe/Berlin')
    theme = db.Column(db.String(20), default='light')

    # Relationships - KORREKT MIT foreign_keys SPEZIFIZIERT
    devices = db.relationship('Device', back_populates='owner', lazy='dynamic')

    # Entries mit zwei verschiedenen Beziehungen
    entries_created = db.relationship(
        'Entry',
        foreign_keys='Entry.user_id',
        back_populates='creator',
        lazy='dynamic'
    )

    entries_validated = db.relationship(
        'Entry',
        foreign_keys='Entry.validated_by_id',
        back_populates='validator',
        lazy='dynamic'
    )

    expenses = db.relationship('Expense', back_populates='user', lazy='dynamic')
    audit_logs = db.relationship('AuditLog', back_populates='user', lazy='dynamic')
    notifications = db.relationship('Notification', back_populates='user', lazy='dynamic')
    reports = db.relationship('Report', back_populates='user', lazy='dynamic')

    def set_password(self, password: str):
        """Passwort hashen und speichern"""
        self.password_hash = generate_password_hash(password)
        self.password_changed_at = datetime.utcnow()

    def check_password(self, password: str) -> bool:
        """Passwort verifizieren"""
        return check_password_hash(self.password_hash, password)

    def is_password_expired(self, days: int = 90) -> bool:
        """Prüfen ob Passwort abgelaufen ist"""
        if not self.password_changed_at:
            return True
        return (datetime.utcnow() - self.password_changed_at).days > days

    def is_locked(self) -> bool:
        """Prüfen ob Account gesperrt ist"""
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False

    def lock_account(self, hours: int = 1):
        """Account sperren"""
        self.locked_until = datetime.utcnow() + timedelta(hours=hours)
        db.session.commit()

    def unlock_account(self):
        """Account entsperren"""
        self.locked_until = None
        self.failed_login_count = 0
        db.session.commit()

    def record_login(self):
        """Login aufzeichnen"""
        self.last_login = datetime.utcnow()
        self.login_count += 1
        self.failed_login_count = 0
        db.session.commit()

    def record_failed_login(self):
        """Fehlgeschlagenen Login aufzeichnen"""
        self.failed_login_count += 1
        if self.failed_login_count >= 5:
            self.lock_account()
        db.session.commit()

    def generate_api_key(self) -> str:
        """API Key generieren"""
        self.api_key = secrets.token_urlsafe(48)
        self.api_key_created_at = datetime.utcnow()
        db.session.commit()
        return self.api_key

    def setup_2fa(self) -> str:
        """2FA einrichten"""
        secret = pyotp.random_base32()
        self.two_factor_secret = secret
        return secret

    def get_2fa_qr_code(self) -> str:
        """2FA QR-Code generieren"""
        if not self.two_factor_secret:
            return None

        totp_uri = pyotp.totp.TOTP(self.two_factor_secret).provisioning_uri(
            name=self.email,
            issuer_name='Automaten Manager'
        )

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buf = BytesIO()
        img.save(buf, format='PNG')

        return base64.b64encode(buf.getvalue()).decode()

    def verify_2fa_token(self, token: str) -> bool:
        """2FA Token verifizieren"""
        if not self.two_factor_secret:
            return False

        totp = pyotp.TOTP(self.two_factor_secret)
        return totp.verify(token, valid_window=1)

    def generate_backup_codes(self) -> List[str]:
        """Backup-Codes generieren"""
        import json
        codes = [secrets.token_hex(4) for _ in range(10)]
        self.backup_codes = json.dumps(codes)
        db.session.commit()
        return codes

    @property
    def full_name(self):
        """Vollständiger Name"""
        parts = [p for p in [self.first_name, self.last_name] if p]
        return ' '.join(parts) if parts else self.username

    def __repr__(self):
        return f'<User {self.username}>'


# ============================================================================
# DEVICE MODEL
# ============================================================================

class Device(TimestampMixin, UUIDMixin, db.Model):
    """Geräte-Model"""
    __tablename__ = 'devices'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.Enum(DeviceType), nullable=False, index=True)
    status = db.Column(db.Enum(DeviceStatus), default=DeviceStatus.ACTIVE, index=True)

    # Details
    serial_number = db.Column(db.String(100), unique=True)
    manufacturer = db.Column(db.String(100))
    model = db.Column(db.String(100))
    purchase_date = db.Column(db.Date, default=date.today)
    purchase_price = db.Column(db.Numeric(10, 2), default=Decimal('0.00'))
    warranty_until = db.Column(db.Date)

    # Location
    location = db.Column(db.String(200))
    floor = db.Column(db.String(20))
    room = db.Column(db.String(50))
    gps_latitude = db.Column(db.Float)
    gps_longitude = db.Column(db.Float)

    # Configuration
    capacity = db.Column(db.Integer)  # Maximale Anzahl Produkte
    temperature_min = db.Column(db.Float)  # Minimale Temperatur
    temperature_max = db.Column(db.Float)  # Maximale Temperatur

    # Telemetry (für IoT)
    last_heartbeat = db.Column(db.DateTime)
    firmware_version = db.Column(db.String(20))
    ip_address = db.Column(db.String(45))

    # Owner
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    owner = db.relationship('User', back_populates='devices')

    # Relationships
    entries = db.relationship('Entry', back_populates='device', lazy='dynamic', cascade='all, delete-orphan')
    expenses = db.relationship('Expense', back_populates='device', lazy='dynamic', cascade='all, delete-orphan')
    maintenance_logs = db.relationship('MaintenanceLog', back_populates='device', lazy='dynamic',
                                       cascade='all, delete-orphan')

    # Notes
    notes = db.Column(db.Text)

    # Erweiterte Felder für Inventar und Wechselgeld
    connection_type = db.Column(db.String(20), default='offline')  # offline, online, telemetry
    inventory_data = db.Column(db.JSON)  # Produkt-Bestand als JSON
    change_money = db.Column(db.JSON)  # Wechselgeld-Bestand als JSON
    last_inventory_update = db.Column(db.DateTime)
    last_change_update = db.Column(db.DateTime)
    maintenance_date = db.Column(db.Date)

    @hybrid_property
    def is_active(self):
        """Ist das Gerät aktiv?"""
        return self.status == DeviceStatus.ACTIVE

    @hybrid_property
    def needs_maintenance(self):
        """Braucht das Gerät Wartung?"""
        if not self.maintenance_logs.count():
            return True

        last_maintenance = self.maintenance_logs.order_by(desc(MaintenanceLog.date)).first()
        if not last_maintenance:
            return True

        days_since = (date.today() - last_maintenance.date).days
        return days_since > 90  # Wartung alle 90 Tage

    def get_total_revenue(self) -> Decimal:
        """Gesamteinnahmen"""
        result = db.session.query(func.sum(Entry.amount)).filter(
            Entry.device_id == self.id
        ).scalar()
        return result or Decimal('0.00')

    def get_total_expenses(self) -> Decimal:
        """Gesamtausgaben"""
        result = db.session.query(func.sum(Expense.amount)).filter(
            Expense.device_id == self.id
        ).scalar()
        return result or Decimal('0.00')

    def get_profit(self) -> Decimal:
        """Gewinn berechnen"""
        return self.get_total_revenue() - self.get_total_expenses()

    def get_roi(self) -> float:
        """Return on Investment berechnen"""
        expenses = self.get_total_expenses()
        if expenses == 0:
            return 0
        profit = self.get_profit()
        return float((profit / expenses) * 100)

    def get_daily_average(self, days: int = 30) -> Decimal:
        """Durchschnittliche Tageseinnahmen"""
        start_date = date.today() - timedelta(days=days)
        result = db.session.query(func.avg(Entry.amount)).filter(
            Entry.device_id == self.id,
            Entry.date >= start_date
        ).scalar()
        return result or Decimal('0.00')

    def __repr__(self):
        return f'<Device {self.name} ({self.type.value})>'


# ============================================================================
# ENTRY MODEL (Einnahmen)
# ============================================================================

class Entry(TimestampMixin, UUIDMixin, db.Model):
    """Einnahmen-Model"""
    __tablename__ = 'entries'

    id = db.Column(db.Integer, primary_key=True)

    # Device
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False, index=True)
    device = db.relationship('Device', back_populates='entries')

    # Amount
    amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))

    # Date
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    time = db.Column(db.Time, default=datetime.now().time)

    # Details
    product_count = db.Column(db.Integer)
    cash_amount = db.Column(db.Numeric(10, 2))
    card_amount = db.Column(db.Numeric(10, 2))

    # Reference
    reference = db.Column(db.String(50), unique=True, index=True)
    description = db.Column(db.Text)

    # User Relationships - KORREKT SPEZIFIZIERT
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    creator = db.relationship(
        'User',
        foreign_keys=[user_id],
        back_populates='entries_created'
    )

    # Validated
    is_validated = db.Column(db.Boolean, default=False)
    validated_at = db.Column(db.DateTime)
    validated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    validator = db.relationship(
        'User',
        foreign_keys=[validated_by_id],
        back_populates='entries_validated'
    )

    # Indexes
    __table_args__ = (
        db.Index('idx_entry_date_device', 'date', 'device_id'),
        db.Index('idx_entry_year_month', extract('year', date), extract('month', date)),
    )

    @validates('amount')
    def validate_amount(self, key, value):
        """Betrag validieren"""
        if value is None:
            return Decimal('0.00')
        value = Decimal(str(value))
        if value < 0:
            raise ValueError("Betrag darf nicht negativ sein")
        return value.quantize(Decimal('0.01'))

    @hybrid_property
    def week(self):
        """Kalenderwoche"""
        return self.date.isocalendar()[1] if self.date else None

    @hybrid_property
    def year(self):
        """Jahr"""
        return self.date.year if self.date else None

    @hybrid_property
    def month(self):
        """Monat"""
        return self.date.month if self.date else None

    def __repr__(self):
        return f'<Entry {self.device_id}: {self.amount} on {self.date}>'


# ============================================================================
# EXPENSE MODEL (Ausgaben)
# ============================================================================

class Expense(TimestampMixin, UUIDMixin, db.Model):
    """Ausgaben-Model"""
    __tablename__ = 'expenses'

    id = db.Column(db.Integer, primary_key=True)

    # Device (optional)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), index=True)
    device = db.relationship('Device', back_populates='expenses')

    # Category
    category = db.Column(db.Enum(ExpenseCategory), nullable=False, index=True)

    # Amount
    amount = db.Column(db.Numeric(10, 2), nullable=False, default=Decimal('0.00'))

    # Date
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)

    # Details
    description = db.Column(db.Text, nullable=False)
    supplier = db.Column(db.String(100))
    invoice_number = db.Column(db.String(50), unique=True, index=True)
    receipt_url = db.Column(db.String(255))

    # User
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('User', back_populates='expenses')

    # Recurring
    is_recurring = db.Column(db.Boolean, default=False)
    recurring_interval = db.Column(db.String(20))  # daily, weekly, monthly, yearly
    recurring_until = db.Column(db.Date)

    # NEUE FELDER:
    details = db.Column(db.JSON)  # Für Münzrollen-Details
    receipt_path = db.Column(db.String(255))  # Für Beleg-Pfad

    @validates('amount')
    def validate_amount(self, key, value):
        """Betrag validieren"""
        if value is None:
            return Decimal('0.00')
        value = Decimal(str(value))
        if value < 0:
            raise ValueError("Betrag darf nicht negativ sein")
        return value.quantize(Decimal('0.01'))

    def __repr__(self):
        return f'<Expense {self.category.value}: {self.amount} on {self.date}>'


# ============================================================================
# WEITERE MODELS
# ============================================================================

class MaintenanceRecord(TimestampMixin, db.Model):
    """Wartungsaufzeichnungen für Geräte"""
    __tablename__ = 'maintenance_records'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    maintenance_type = db.Column(db.String(50))  # routine, repair, cleaning, inspection, upgrade
    technician = db.Column(db.String(100))
    cost = db.Column(db.Numeric(10, 2), default=0)
    notes = db.Column(db.Text)
    next_maintenance = db.Column(db.Date)
    
    # Relationships
    device = db.relationship('Device', backref='maintenance_records')


class MaintenanceLog(TimestampMixin, db.Model):
    """Wartungsprotokoll"""
    __tablename__ = 'maintenance_logs'

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False)
    device = db.relationship('Device', back_populates='maintenance_logs')

    date = db.Column(db.Date, nullable=False, default=date.today)
    type = db.Column(db.String(50), nullable=False)  # cleaning, repair, inspection
    description = db.Column(db.Text)
    technician = db.Column(db.String(100))
    cost = db.Column(db.Numeric(10, 2))
    next_maintenance = db.Column(db.Date)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))


class AuditLog(TimestampMixin, db.Model):
    """Audit-Log für Compliance"""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('User', back_populates='audit_logs')

    action = db.Column(db.Enum(AuditAction), nullable=False, index=True)
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.Integer)
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)


class Notification(TimestampMixin, db.Model):
    """Benachrichtigungen"""
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', back_populates='notifications')

    type = db.Column(db.Enum(NotificationType), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    data = db.Column(db.JSON)

    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime)

    # Email/SMS/Push sent status
    email_sent = db.Column(db.Boolean, default=False)
    sms_sent = db.Column(db.Boolean, default=False)
    push_sent = db.Column(db.Boolean, default=False)


class Report(TimestampMixin, db.Model):
    """Generierte Reports"""
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('User', back_populates='reports')

    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # daily, weekly, monthly, custom
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)

    file_path = db.Column(db.String(255))
    file_size = db.Column(db.Integer)

    parameters = db.Column(db.JSON)
    statistics = db.Column(db.JSON)

    generated_at = db.Column(db.DateTime, default=datetime.utcnow)


# ============================================================================
# STATISTICS METHODS
# ============================================================================

class Statistics:
    """Statistische Methoden"""

    @staticmethod
    def get_revenue_by_period(start_date: date, end_date: date, device_id: Optional[int] = None):
        """Einnahmen nach Zeitraum"""
        query = db.session.query(
            func.date(Entry.date).label('date'),
            func.sum(Entry.amount).label('total')
        ).filter(
            Entry.date.between(start_date, end_date)
        )

        if device_id:
            query = query.filter(Entry.device_id == device_id)

        return query.group_by(func.date(Entry.date)).all()

    @staticmethod
    def get_top_devices(limit: int = 5):
        """Top Geräte nach Umsatz"""
        return db.session.query(
            Device,
            func.sum(Entry.amount).label('total_revenue')
        ).join(Entry).group_by(Device.id).order_by(desc('total_revenue')).limit(limit).all()

    @staticmethod
    def get_expense_breakdown():
        """Ausgaben-Aufschlüsselung"""
        return db.session.query(
            Expense.category,
            func.sum(Expense.amount).label('total')
        ).group_by(Expense.category).all()