#!/usr/bin/env python
"""
Test Refill Creation - Testet das Anlegen einer Nachfüllung
"""

import sys
sys.path.insert(0, '/app')

from app import create_app, db
from app.models import Product, Supplier, Refill, RefillItem, User, Device
from datetime import date
from decimal import Decimal

app = create_app()

with app.app_context():
    print("\n=== TEST REFILL CREATION ===\n")
    
    # Get test data
    user = User.query.filter_by(username='Thomas').first()
    if not user:
        user = User.query.first()
    
    product = Product.query.filter_by(user_id=user.id).first()
    supplier = Supplier.query.filter_by(user_id=user.id).first()
    device = Device.query.filter_by(owner_id=user.id).first()
    
    print(f"User: {user.username if user else 'None'}")
    print(f"Product: {product.name if product else 'None'}")
    print(f"Supplier: {supplier.name if supplier else 'None'}")
    print(f"Device: {device.name if device else 'None'}")
    
    if not all([user, product, supplier]):
        print("\n❌ Fehlende Test-Daten! Erstelle welche...")
        
        # Create test supplier if missing
        if not supplier and user:
            from app.models import Supplier
            supplier = Supplier(
                name="Test-Lieferant GmbH",
                contact_person="Max Mustermann",
                email="test@lieferant.de",
                phone="+43 123 456789",
                user_id=user.id
            )
            db.session.add(supplier)
            db.session.commit()
            print("✅ Test-Lieferant erstellt")
        
        # Create test product if missing
        if not product and user:
            from app.models import Product, ProductUnit, ProductCategory
            product = Product(
                name="Test-Produkt",
                unit=ProductUnit.STUECK,
                category=ProductCategory.SNACKS,
                default_price=2.50,
                reorder_point=10,
                max_stock=100,
                user_id=user.id
            )
            db.session.add(product)
            db.session.commit()
            print("✅ Test-Produkt erstellt")
    
    # Try to create a test refill
    if user and product and supplier:
        print("\n📝 Versuche Test-Nachfüllung zu erstellen...")
        
        try:
            # Create refill
            refill = Refill(
                date=date.today(),
                supplier_id=supplier.id,
                device_id=device.id if device else None,
                invoice_number=f"TEST-{date.today().strftime('%Y%m%d')}",
                subtotal=Decimal('10.00'),
                tax_amount=Decimal('2.00'),
                total_amount=Decimal('12.00'),
                tax_rate=Decimal('20'),
                prices_include_tax=True,
                user_id=user.id
            )
            db.session.add(refill)
            db.session.flush()
            
            # Add item
            item = RefillItem(
                refill_id=refill.id,
                product_id=product.id,
                quantity=Decimal('5'),
                unit_price=Decimal('2.00'),
                total_price=Decimal('10.00')
            )
            db.session.add(item)
            
            db.session.commit()
            print(f"✅ Test-Nachfüllung erstellt! ID: {refill.id}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Fehler beim Erstellen: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n=== ENDE ===\n")
