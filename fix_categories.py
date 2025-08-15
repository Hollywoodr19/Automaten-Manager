# fix_categories.py
from app import create_app, db
from app.models import Product

app = create_app()

with app.app_context():
    # Mapping alte -> neue Werte
    mapping = {
        'COFFEE': 'kaffee',
        'CUPS': 'becher',
        'SUGAR': 'zucker',
        'MILK': 'milch',
        'SNACKS': 'snacks',
        'DRINKS': 'getraenke',
        'GETRÄNKE': 'getraenke',
        'OTHER': 'sonstiges',
        'STIRRER': 'ruehrstaebchen',
        'CLEANING': 'reinigung',
    }

    products = Product.query.all()
    for product in products:
        old_cat = str(product.category.value) if product.category else None
        if old_cat in mapping:
            # Update direkt in DB
            db.session.execute(
                f"UPDATE products SET category = '{mapping[old_cat]}' WHERE id = {product.id}"
            )

    db.session.commit()
    print("✅ Kategorien erfolgreich migriert!")