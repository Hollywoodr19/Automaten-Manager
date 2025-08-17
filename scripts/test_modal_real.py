#!/usr/bin/env python
"""Test ob das Modal-Problem an Bootstrap 5 liegt"""

print("""
=== MODAL DEBUG ANLEITUNG ===

1. Öffnen Sie: http://localhost:5000/refills/

2. Drücken Sie F12 für Browser-Konsole

3. Geben Sie in der Konsole ein:
   
   // Test ob Bootstrap geladen ist
   console.log('Bootstrap:', typeof bootstrap);
   
   // Test ob Modal verfügbar ist
   console.log('Modal Element:', document.getElementById('refillModal'));
   
   // Versuche Modal manuell zu öffnen
   var myModal = new bootstrap.Modal(document.getElementById('refillModal'));
   myModal.show();
   
4. Was passiert?
   - Öffnet sich das Modal?
   - Gibt es Fehlermeldungen?
   
5. Prüfen Sie auch:
   - Ist der "Neue Nachfüllung" Button sichtbar?
   - Hat der Button das Attribut: data-bs-toggle="modal" data-bs-target="#refillModal"
   
MÖGLICHE PROBLEME:
- Bootstrap 5 verwendet 'data-bs-' statt 'data-' Präfix
- Modal könnte außerhalb des content-card div sein
- JavaScript-Funktionen könnten nicht im globalen Scope sein
""")