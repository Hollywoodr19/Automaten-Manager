"""
Quick Debug Check
"""
from app import create_app, db
from app.models import User, Device, Product

app = create_app()

with app.app_context():
    print("\n=== AUTOMATEN MANAGER - QUICK CHECK ===\n")
    
    # Database
    try:
        users = User.query.count()
        devices = Device.query.count()
        products = Product.query.count()
        
        print(f"✅ Users: {users}")
        print(f"✅ Devices: {devices}")  
        print(f"✅ Products: {products}")
        
        # Admin
        admin = User.query.filter_by(username='admin').first()
        if admin:
            print(f"✅ Admin exists: {admin.email}")
        else:
            print("❌ No admin user!")
            
    except Exception as e:
        print(f"❌ Database error: {e}")
    
    # Routes
    print("\n=== KEY ROUTES ===")
    important = ['/login', '/modern/dashboard', '/devices/qr-codes', '/refills/']
    
    for route in important:
        found = any(route in str(r) for r in app.url_map.iter_rules())
        status = "✅" if found else "❌"
        print(f"{status} {route}")
    
    print("\n=== BLUEPRINTS ===")
    for name in app.blueprints:
        print(f"✅ {name}")
    
    print("\n✨ Check complete!\n")
