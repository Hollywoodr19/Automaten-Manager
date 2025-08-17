#!/usr/bin/env python
"""
Erstellt eine vollständige Test-Nachfüllung mit Items
"""

import sys
sys.path.insert(0, '/app')

from app import create_app, db
from app.models import Product, Supplier, Refill, RefillItem, User, Device, Expense, ExpenseCategory
from datetime import date
from decimal import Decimal

app = create_app()

with app.app_context():
    print("\n=== VOLLSTÄNDIGE TEST-NACHFÜLLUNG ===\n")
    
    # Get Thomas user (ID 2)
    user = User.query.filter_by(id=2).first()
    if not user:
        print("❌ User Thomas nicht gefunden!")
        exit(1)
    
    print(f"User: {user.username}")
    
    # Get his products and suppliers
    products = Product.query.filter_by(user_id=user.id).all()
    suppliers = Supplier.query.filter_by(user_id=user.id).all()
    
    if not products:
        print("❌ Keine Produkte für User Thomas!")
        # Erstelle Test-Produkte für Thomas
        from app.models import ProductUnit, ProductCategory
        
        test_products = [
            Product(
                name="Test-Kaffee",
                unit=ProductUnit.STUECK,
                category=ProductCategory.HEISSGETRAENKE,
                default_price=2.50,
                reorder_point=20,
                max_stock=100,
                user_id=user.id
            ),
            Product(
                name="Test-Cola",
                unit=ProductUnit.STUECK,
                category=ProductCategory.KALTGETRAENKE,
                default_price=3.00,
                reorder_point=15,
                max_stock=80,
                user_id=user.id
            ),
        ]
        
        for p in test_products:
            db.session.add(p)
        db.session.commit()
        products = test_products
        print("✅ Test-Produkte für Thomas erstellt")
    
    if not suppliers:
        print("❌ Keine Lieferanten für User Thomas!")
        exit(1)
    
    print(f"Produkte: {len(products)}")
    print(f"Lieferanten: {len(suppliers)}")
    
    # Erstelle komplette Nachfüllung
    try:
        print("\n📝 Erstelle Nachfüllung...")
        
        # Nachfüllung
        refill = Refill(
            date=date.today(),
            supplier_id=suppliers[0].id if suppliers else None,
            invoice_number=f"FULL-TEST-{date.today().strftime('%Y%m%d-%H%M%S')}",
            subtotal=Decimal('50.00'),
            tax_amount=Decimal('10.00'),
            total_amount=Decimal('60.00'),
            tax_rate=Decimal('20'),
            prices_include_tax=True,
            shipping_cost=Decimal('5.00'),
            user_id=user.id
        )
        db.session.add(refill)
        db.session.flush()  # Get ID
        
        print(f"✅ Nachfüllung ID {refill.id} erstellt")
        
        # Items hinzufügen
        for i, product in enumerate(products[:2], 1):  # Erste 2 Produkte
            item = RefillItem(
                refill_id=refill.id,
                product_id=product.id,
                quantity=Decimal(str(10 * i)),  # 10, 20
                unit_price=Decimal(str(product.default_price or 2.50)),
                total_price=Decimal(str(10 * i * float(product.default_price or 2.50)))
            )
            db.session.add(item)
            print(f"  ✅ Item {i}: {product.name} - {item.quantity} Stück")
        
        # Als Ausgabe erfassen
        expense = Expense(
            category=ExpenseCategory.NACHFUELLUNG,
            amount=refill.total_amount,
            date=refill.date,
            description=f"Nachfüllung {refill.invoice_number}",
            supplier=suppliers[0].name if suppliers else None,
            invoice_number=refill.invoice_number,
            user_id=user.id
        )
        db.session.add(expense)
        refill.expense_id = expense.id
        
        db.session.commit()
        
        print(f"\n✅ ERFOLG! Nachfüllung #{refill.id} mit {len(refill.items.all())} Items erstellt!")
        print(f"   Rechnungsnr: {refill.invoice_number}")
        print(f"   Lieferant: {suppliers[0].name if suppliers else 'Keiner'}")
        print(f"   Total: {refill.total_amount} €")
        
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ FEHLER: {e}")
        import traceback
        traceback.print_exc()
    
    # Zeige alle Nachfüllungen
    print("\n=== ALLE NACHFÜLLUNGEN ===")
    all_refills = Refill.query.filter_by(user_id=user.id).all()
    for r in all_refills:
        print(f"  - {r.date} | {r.invoice_number} | {r.total_amount} € | Items: {r.items.count()}")
    
    print("\n=== ENDE ===\n")
