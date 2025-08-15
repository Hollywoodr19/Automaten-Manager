#!/usr/bin/env python
"""
Migration Script für Inventory/Warenwirtschaft Tabellen
Führen Sie dies aus dem Container aus!
"""

from app import create_app, db
from app.models import Product, Supplier, Refill, RefillItem, InventoryMovement


def migrate_database():
    """Erstellt die neuen Tabellen"""
    app = create_app()

    with app.app_context():
        print("🔄 Starte Datenbank-Migration...")

        # Neue Tabellen erstellen
        print("📊 Erstelle neue Tabellen...")

        # Prüfe ob Tabellen existieren
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()

        tables_to_create = [
            ('products', Product.__table__),
            ('suppliers', Supplier.__table__),
            ('refills', Refill.__table__),
            ('refill_items', RefillItem.__table__),
            ('inventory_movements', InventoryMovement.__table__)
        ]

        for table_name, table_obj in tables_to_create:
            if table_name not in existing_tables:
                table_obj.create(db.engine)
                print(f"  ✅ Tabelle '{table_name}' erstellt")
            else:
                print(f"  ⚠️  Tabelle '{table_name}' existiert bereits")

        db.session.commit()

        print("\n🎉 Migration erfolgreich abgeschlossen!")

        # Beispiel-Produkte anlegen
        if Product.query.count() == 0:
            print("\n📦 Lege Beispiel-Produkte an...")

            sample_products = [
                {
                    'name': 'Kaffeebohnen Premium',
                    'category': 'coffee',
                    'unit': 'kg',
                    'default_price': 18.50,
                    'usage_per_serving': 0.007,  # 7g pro Tasse
                    'min_stock': 5,
                    'reorder_point': 10
                },
                {
                    'name': 'Kaffeebecher 200ml',
                    'category': 'cups',
                    'unit': 'piece',
                    'default_price': 0.05,
                    'usage_per_serving': 1,
                    'min_stock': 500,
                    'reorder_point': 1000
                },
                {
                    'name': 'Zucker Sticks',
                    'category': 'sugar',
                    'unit': 'piece',
                    'default_price': 0.02,
                    'usage_per_serving': 1,
                    'min_stock': 200,
                    'reorder_point': 500
                },
                {
                    'name': 'Milchpulver',
                    'category': 'milk',
                    'unit': 'kg',
                    'default_price': 12.00,
                    'usage_per_serving': 0.003,  # 3g pro Portion
                    'min_stock': 2,
                    'reorder_point': 5
                },
                {
                    'name': 'Rührstäbchen Holz',
                    'category': 'stirrer',
                    'unit': 'piece',
                    'default_price': 0.01,
                    'usage_per_serving': 1,
                    'min_stock': 500,
                    'reorder_point': 1000
                }
            ]

            from app.models import ProductCategory, ProductUnit, User

            # Admin User für Beispieldaten
            admin_user = User.query.filter_by(username='admin').first()
            if admin_user:
                for prod_data in sample_products:
                    product = Product(
                        name=prod_data['name'],
                        category=ProductCategory(prod_data['category']),
                        unit=ProductUnit(prod_data['unit']),
                        default_price=prod_data['default_price'],
                        usage_per_serving=prod_data.get('usage_per_serving'),
                        min_stock=prod_data.get('min_stock', 0),
                        reorder_point=prod_data.get('reorder_point'),
                        user_id=admin_user.id
                    )
                    db.session.add(product)
                    print(f"  ✅ Produkt '{prod_data['name']}' angelegt")

                db.session.commit()

            # Beispiel-Lieferant
            print("\n🚚 Lege Beispiel-Lieferanten an...")

            supplier = Supplier(
                name='Kaffee-Großhandel Schmidt GmbH',
                contact_person='Max Mustermann',
                phone='+49 123 456789',
                email='bestellung@kaffee-schmidt.de',
                website='www.kaffee-schmidt.de',
                customer_number='KD-12345',
                payment_terms='30 Tage netto',
                delivery_time=2,
                min_order_value=100.00,
                user_id=admin_user.id if admin_user else 1
            )
            db.session.add(supplier)
            db.session.commit()
            print("  ✅ Beispiel-Lieferant angelegt")

        print("\n✨ Alles bereit für die Warenwirtschaft!")


if __name__ == '__main__':
    migrate_database()