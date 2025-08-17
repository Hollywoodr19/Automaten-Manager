#!/usr/bin/env python
"""
2FA Status Check
"""

import sys
sys.path.insert(0, '/app')

from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    print("\n=== 2FA STATUS CHECK ===\n")
    
    # Alle User mit 2FA Status anzeigen
    users = User.query.all()
    
    for user in users:
        print(f"User: {user.username}")
        print(f"  Email: {user.email}")
        print(f"  2FA Enabled: {user.two_factor_enabled}")
        print(f"  Has Secret: {bool(user.two_factor_secret)}")
        print("-" * 40)
    
    # Admin spezifisch prüfen
    admin = User.query.filter_by(username='admin').first()
    if admin:
        print(f"\nAdmin 2FA Details:")
        print(f"  two_factor_enabled: {admin.two_factor_enabled}")
        print(f"  two_factor_secret exists: {bool(admin.two_factor_secret)}")
        
        # Wenn 2FA aktiv ist, aber Anzeige nicht stimmt
        if admin.two_factor_secret and not admin.two_factor_enabled:
            print("\n⚠️ INKONSISTENZ GEFUNDEN!")
            print("Secret vorhanden, aber Flag nicht gesetzt. Korrigiere...")
            admin.two_factor_enabled = True
            db.session.commit()
            print("✅ Korrigiert!")
    
    print("\n✅ Check abgeschlossen\n")
