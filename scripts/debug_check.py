#!/usr/bin/env python
"""
Debug-Check für Automaten Manager
Überprüft alle Routen und Funktionalitäten
"""

import sys
import os

# Python-Pfad korrekt setzen für Docker-Container
sys.path.insert(0, '/app')

from app import create_app, db
from app.models import User, Device, Product, Supplier

def check_system():
    """Systemcheck durchführen"""
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*60)
        print("AUTOMATEN MANAGER - SYSTEM CHECK")
        print("="*60)
        
        # 1. Datenbank Check
        print("\n📊 DATENBANK STATUS:")
        print("-" * 40)
        try:
            user_count = User.query.count()
            device_count = Device.query.count()
            product_count = Product.query.count()
            supplier_count = Supplier.query.count()
            
            print(f"✅ Benutzer: {user_count}")
            print(f"✅ Geräte: {device_count}")
            print(f"✅ Produkte: {product_count}")
            print(f"✅ Lieferanten: {supplier_count}")
        except Exception as e:
            print(f"❌ Datenbankfehler: {e}")
        
        # 2. Admin User Check
        print("\n👤 ADMIN USER:")
        print("-" * 40)
        admin = User.query.filter_by(username='admin').first()
        if admin:
            print(f"✅ Admin existiert: {admin.email}")
            print(f"   - 2FA aktiviert: {admin.two_factor_enabled}")
            print(f"   - API Key: {'Ja' if admin.api_key else 'Nein'}")
        else:
            print("❌ Kein Admin-User gefunden!")
        
        # 3. Routes Check
        print("\n🛣️ REGISTRIERTE ROUTEN:")
        print("-" * 40)
        
        important_routes = [
            '/login',
            '/dashboard',
            '/modern/dashboard',
            '/devices',
            '/devices/qr-codes',
            '/devices/maintenance',
            '/refills/',
            '/income/',
            '/settings/',
            '/settings/security',
        ]
        
        for route_path in important_routes:
            # Prüfe ob Route existiert
            found = False
            for rule in app.url_map.iter_rules():
                rule_str = str(rule)
                # Vereinfachte Prüfung
                if route_path in rule_str or route_path.rstrip('/') in rule_str:
                    found = True
                    break
            
            if found:
                print(f"✅ {route_path}")
            else:
                print(f"❌ {route_path} - NICHT GEFUNDEN!")
        
        # 4. Blueprint Check
        print("\n📦 BLUEPRINTS:")
        print("-" * 40)
        for name, blueprint in app.blueprints.items():
            print(f"✅ {name}: {blueprint.url_prefix or '/'}")
        
        # 5. Test-Daten erstellen
        print("\n🔧 TEST-DATEN:")
        print("-" * 40)
        
        # Test-Gerät
        if device_count == 0 and admin:
            from app.models import DeviceType, DeviceStatus
            test_device = Device(
                name="Test-Automat",
                type=DeviceType.KAFFEE,
                status=DeviceStatus.ACTIVE,
                serial_number="TEST-001",
                location="Teststandort",
                owner_id=admin.id
            )
            db.session.add(test_device)
            db.session.commit()
            print("✅ Test-Gerät erstellt")
        else:
            print(f"ℹ️ {device_count} Geräte vorhanden")
        
        # Test-Produkte
        if product_count == 0 and admin:
            from app.models import ProductUnit, ProductCategory
            products = [
                Product(
                    name="Kaffee",
                    unit=ProductUnit.STUECK,
                    category=ProductCategory.HEISSGETRAENKE,
                    default_price=2.50,
                    reorder_point=50,
                    max_stock=200,
                    user_id=admin.id
                ),
                Product(
                    name="Cola",
                    unit=ProductUnit.STUECK,
                    category=ProductCategory.KALTGETRAENKE,
                    default_price=3.00,
                    reorder_point=30,
                    max_stock=150,
                    user_id=admin.id
                ),
            ]
            for p in products:
                db.session.add(p)
            db.session.commit()
            print("✅ Test-Produkte erstellt")
        else:
            print(f"ℹ️ {product_count} Produkte vorhanden")
        
        # Test-Lieferant
        if supplier_count == 0 and admin:
            test_supplier = Supplier(
                name="Test-Lieferant GmbH",
                contact_person="Max Mustermann",
                email="test@lieferant.de",
                phone="+43 123 456789",
                user_id=admin.id
            )
            db.session.add(test_supplier)
            db.session.commit()
            print("✅ Test-Lieferant erstellt")
        else:
            print(f"ℹ️ {supplier_count} Lieferanten vorhanden")
        
        print("\n" + "="*60)
        print("SYSTEM CHECK ABGESCHLOSSEN")
        print("="*60)
        print("\n📌 EMPFOHLENE AKTIONEN:")
        print("-" * 40)
        print("1. Browser öffnen: http://localhost:5000/modern/dashboard")
        print("2. Login: admin / admin123")
        print("3. Browser-Cache leeren: Strg+Shift+F5")
        print("\n")

if __name__ == '__main__':
    check_system()
