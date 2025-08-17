#!/usr/bin/env python
"""Debug-Script für Nachfüllungs-Problem"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, Product, Supplier, Device, Refill
from datetime import date
from decimal import Decimal

app = create_app()

with app.app_context():
    print("\n=== REFILLS DEBUG ===")
    
    # Get user
    user = User.query.filter_by(username='Thomas').first()
    if not user:
        user = User.query.first()
    
    if user:
        print(f"User: {user.username} (ID: {user.id})")
        
        # Check if we can create a test refill
        try:
            test_refill = Refill(
                date=date.today(),
                invoice_number=f"TEST-MANUAL-{date.today().strftime('%Y%m%d')}",
                subtotal=Decimal('50.00'),
                tax_amount=Decimal('10.00'),
                total_amount=Decimal('60.00'),
                tax_rate=Decimal('20'),
                prices_include_tax=True,
                user_id=user.id
            )
            db.session.add(test_refill)
            db.session.commit()
            print(f"✅ Test-Nachfüllung erstellt: ID {test_refill.id}")
            
            # Cleanup
            db.session.delete(test_refill)
            db.session.commit()
            print("✅ Test-Nachfüllung wieder gelöscht")
            
        except Exception as e:
            print(f"❌ Fehler beim Erstellen: {e}")
            db.session.rollback()
        
        # Check products and suppliers
        products = Product.query.filter_by(user_id=user.id).count()
        suppliers = Supplier.query.filter_by(user_id=user.id).count()
        devices = Device.query.filter_by(owner_id=user.id).count()
        
        print(f"Produkte: {products}")
        print(f"Lieferanten: {suppliers}")
        print(f"Geräte: {devices}")
        
        if products == 0:
            print("⚠️ Keine Produkte vorhanden - Modal wird leer sein!")
        if suppliers == 0:
            print("⚠️ Keine Lieferanten vorhanden - Dropdown wird leer sein!")
    else:
        print("❌ Kein User gefunden!")
    
    print("\n=== CHECK COMPLETE ===")
