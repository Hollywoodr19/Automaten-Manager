#!/usr/bin/env python
"""
Debug Refills - Überprüft Nachfüllungs-Funktionalität
"""

import sys
sys.path.insert(0, '/app')

from app import create_app, db
from app.models import Product, Supplier, Refill, RefillItem, User

app = create_app()

with app.app_context():
    print("\n=== REFILLS DEBUG CHECK ===\n")
    
    # User Check
    users = User.query.all()
    print("USERS:")
    for user in users:
        print(f"  - {user.username} (ID: {user.id})")
    
    # Products Check
    products = Product.query.all()
    print(f"\nPRODUKTE: {len(products)}")
    for p in products[:5]:  # Erste 5 anzeigen
        print(f"  - {p.name} (ID: {p.id}, User: {p.user_id})")
    
    # Suppliers Check
    suppliers = Supplier.query.all()
    print(f"\nLIEFERANTEN: {len(suppliers)}")
    for s in suppliers:
        print(f"  - {s.name} (ID: {s.id}, User: {s.user_id})")
    
    # Refills Check
    refills = Refill.query.all()
    print(f"\nNACHFÜLLUNGEN: {len(refills)}")
    for r in refills[:5]:
        print(f"  - {r.date} - {r.invoice_number} (ID: {r.id})")
    
    # Check Routes
    print("\n=== REFILLS ROUTES ===")
    from flask import current_app
    for rule in current_app.url_map.iter_rules():
        if 'refill' in str(rule):
            print(f"  ✓ {rule}")
    
    print("\n✅ Debug complete!\n")
