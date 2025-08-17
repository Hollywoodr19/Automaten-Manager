#!/usr/bin/env python
"""Test-Script für Nachfüllungs-Modal"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, Product, Supplier, Device, Refill, RefillItem

app = create_app()

with app.app_context():
    print("\n=== REFILLS MODAL TEST ===")
    
    # Check User
    user = User.query.filter_by(username='Thomas').first()
    if not user:
        user = User.query.first()
    print(f"User: {user.username if user else 'None'}")
    
    # Check Products
    products = Product.query.filter_by(user_id=user.id).all() if user else []
    print(f"Products: {len(products)}")
    for p in products[:3]:
        print(f"  - {p.name} (ID: {p.id}, Price: {p.default_price})")
    
    # Check Suppliers
    suppliers = Supplier.query.filter_by(user_id=user.id).all() if user else []
    print(f"Suppliers: {len(suppliers)}")
    for s in suppliers:
        print(f"  - {s.name} (ID: {s.id})")
    
    # Check Devices
    devices = Device.query.filter_by(owner_id=user.id).all() if user else []
    print(f"Devices: {len(devices)}")
    for d in devices:
        print(f"  - {d.name} (ID: {d.id})")
    
    # Check Refills
    refills = Refill.query.filter_by(user_id=user.id).all() if user else []
    print(f"\nExisting Refills: {len(refills)}")
    for r in refills[-3:]:
        print(f"  - ID: {r.id}, Date: {r.date}, Total: {r.total_amount}")
    
    print("\n=== CHECK COMPLETE ===")
