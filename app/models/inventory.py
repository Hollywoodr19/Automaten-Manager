# app/models/inventory.py
"""
Erweiterte Models für Warenwirtschaft und Nachfüllungen
"""

from app import db
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
import uuid


class ProductUnit(Enum):
    """Einheiten für Produkte"""
    piece = 'piece'  # Stück
    kg = 'kg'       # Kilogramm
    liter = 'liter' # Liter
    pack = 'pack'   # Packung
    box = 'box'     # Kiste
    gram = 'gram'   # Gramm
    ml = 'ml'       # Milliliter


class ProductCategory(Enum):
    """Produkt-Kategorien (Deutsch, lowercase)"""
    kaffee = 'kaffee'
    becher = 'becher'
    zucker = 'zucker'
    milch = 'milch'
    snacks = 'snacks'
    getraenke = 'getraenke'
    sonstiges = 'sonstiges'
    ruehrstaebchen = 'ruehrstaebchen'
    kakao = 'kakao'
    tee = 'tee'
    reinigung = 'reinigung'


class Product(db.Model):
    """Produkt-Stammdaten"""
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))

    # Basis-Informationen
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.Enum(ProductCategory), nullable=False)
    unit = db.Column(db.Enum(ProductUnit), nullable=False)

    # Beschreibung & Details
    description = db.Column(db.Text)
    barcode = db.Column(db.String(50))  # EAN/Barcode
    article_number = db.Column(db.String(50))  # Artikel-Nr beim Lieferanten

    # Preise & Kosten
    default_price = db.Column(db.Numeric(10, 2))  # Standard-Einkaufspreis
    min_price = db.Column(db.Numeric(10, 2))  # Bester Preis bisher
    max_price = db.Column(db.Numeric(10, 2))  # Höchster Preis bisher

    # Lagerbestands-Grenzen
    min_stock = db.Column(db.Numeric(10, 2), default=0)  # Mindestbestand
    reorder_point = db.Column(db.Numeric(10, 2))  # Nachbestellpunkt
    max_stock = db.Column(db.Numeric(10, 2))  # Maximalbestand

    # Verbrauch pro Portion (z.B. 7g Kaffee pro Tasse)
    usage_per_serving = db.Column(db.Numeric(10, 3))

    # Lieferant (Standard)
    default_supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'))

    # Meta
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    refill_items = db.relationship('RefillItem', backref='product', lazy='dynamic')
    inventory_movements = db.relationship('InventoryMovement', backref='product', lazy='dynamic')

    def get_current_stock(self, device_id=None):
        """Aktueller Lagerbestand (gesamt oder pro Gerät)"""
        query = InventoryMovement.query.filter_by(product_id=self.id)
        if device_id:
            query = query.filter_by(device_id=device_id)

        movements = query.all()
        return sum(m.quantity if m.type == 'IN' else -m.quantity for m in movements)

    def get_average_price(self):
        """Durchschnittlicher Einkaufspreis"""
        items = RefillItem.query.filter_by(product_id=self.id).all()
        if not items:
            return self.default_price or 0

        total_value = sum(item.total_price for item in items)
        total_quantity = sum(item.quantity for item in items)

        return total_value / total_quantity if total_quantity > 0 else 0


class Supplier(db.Model):
    """Lieferanten"""
    __tablename__ = 'suppliers'

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))

    # Basis-Informationen
    name = db.Column(db.String(100), nullable=False)
    contact_person = db.Column(db.String(100))
    phone = db.Column(db.String(50))
    email = db.Column(db.String(100))
    website = db.Column(db.String(200))

    # Adresse
    address = db.Column(db.Text)

    # Konditionen
    customer_number = db.Column(db.String(50))  # Unsere Kundennummer
    payment_terms = db.Column(db.String(100))  # Zahlungsziel
    delivery_time = db.Column(db.Integer)  # Lieferzeit in Tagen
    min_order_value = db.Column(db.Numeric(10, 2))  # Mindestbestellwert

    # Meta
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    products = db.relationship('Product', backref='default_supplier', lazy='dynamic')
    refills = db.relationship('Refill', backref='supplier', lazy='dynamic')


class Refill(db.Model):
    """Nachfüllungen (erweitert die bestehende Expense)"""
    __tablename__ = 'refills'

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, default=lambda: str(uuid.uuid4()))

    # Verknüpfung mit Expense (wenn als Ausgabe erfasst)
    expense_id = db.Column(db.Integer, db.ForeignKey('expenses.id'))

    # Basis-Informationen
    date = db.Column(db.Date, nullable=False, default=date.today)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'))
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'))

    # Bestellung & Lieferung
    order_number = db.Column(db.String(50))
    invoice_number = db.Column(db.String(50))
    delivery_note = db.Column(db.String(50))

    # Kosten
    subtotal = db.Column(db.Numeric(10, 2), default=0)
    tax_amount = db.Column(db.Numeric(10, 2), default=0)
    shipping_cost = db.Column(db.Numeric(10, 2), default=0)
    total_amount = db.Column(db.Numeric(10, 2), default=0)

    # NEUE FELDER - Diese fehlen noch!
    deposit_amount = db.Column(db.Numeric(10, 2), default=0)
    tax_rate = db.Column(db.Numeric(5, 2), default=20)
    prices_include_tax = db.Column(db.Boolean, default=True)
    discount_amount = db.Column(db.Numeric(10, 2), default=0)
    discount_reason = db.Column(db.String(100))
    receipt_filename = db.Column(db.String(255))
    receipt_data = db.Column(db.Text)

    # Meta
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    items = db.relationship('RefillItem', backref='refill', lazy='dynamic', cascade='all, delete-orphan')

    def calculate_totals(self):
        """Berechnet Gesamtsummen mit flexibler MwSt"""
        items_total = sum(item.total_price for item in self.items)

        if self.prices_include_tax:
            # Preise enthalten MwSt - herausrechnen
            self.subtotal = items_total / (1 + self.tax_rate / 100)
            self.tax_amount = items_total - self.subtotal
        else:
            # Nettopreise - MwSt draufrechnen
            self.subtotal = items_total
            self.tax_amount = self.subtotal * (self.tax_rate / 100)

        self.total_amount = self.subtotal + self.tax_amount + self.shipping_cost + self.deposit_amount


class RefillItem(db.Model):
    """Einzelne Positionen einer Nachfüllung"""
    __tablename__ = 'refill_items'

    id = db.Column(db.Integer, primary_key=True)

    # Verknüpfungen
    refill_id = db.Column(db.Integer, db.ForeignKey('refills.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)

    # Mengen & Preise
    quantity = db.Column(db.Numeric(10, 3), nullable=False)
    unit_price = db.Column(db.Numeric(10, 4), nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)

    # NEUE FELDER für Zeilen-Rabatt
    line_discount = db.Column(db.Numeric(10, 2), default=0)
    line_discount_reason = db.Column(db.String(100))

    # Optional
    batch_number = db.Column(db.String(50))
    expiry_date = db.Column(db.Date)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def calculate_total(self):
        """Berechnet Gesamtpreis mit Rabatt"""
        gross = self.quantity * self.unit_price
        self.total_price = gross - (self.line_discount or 0)


class InventoryMovement(db.Model):
    """Lagerbewegungen (Ein/Aus)"""
    __tablename__ = 'inventory_movements'

    id = db.Column(db.Integer, primary_key=True)

    # Verknüpfungen
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'))  # Optional: für welches Gerät
    refill_item_id = db.Column(db.Integer, db.ForeignKey('refill_items.id'))  # Bei Eingang

    # Bewegung
    type = db.Column(db.String(10), nullable=False)  # IN (Eingang) / OUT (Verbrauch)
    quantity = db.Column(db.Numeric(10, 3), nullable=False)

    # Grund
    reason = db.Column(db.String(100))  # z.B. "Nachfüllung", "Verbrauch", "Inventur"

    # Meta
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)

    def __repr__(self):
        return f'<Movement {self.type} {self.quantity} of {self.product_id}>'