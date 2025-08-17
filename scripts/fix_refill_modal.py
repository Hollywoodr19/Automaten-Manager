#!/usr/bin/env python
"""Fix für Refills Modal - Debug-Version mit Console.log"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Erstelle eine Debug-Version der refills.py mit zusätzlichen Console.logs

fix_content = '''
# Füge diese Debug-Ausgaben in das JavaScript ein:

console.log("Refills JavaScript geladen");

// Nach DOMContentLoaded
console.log("DOM geladen, initialisiere Refills");
console.log("Product-Items Element:", document.getElementById('product-items'));
console.log("RefillForm Element:", document.getElementById('refillForm'));

// In addProductLine Funktion
console.log("addProductLine aufgerufen, itemCount:", itemCount);

// In calculateTotal Funktion
console.log("calculateTotal aufgerufen für ID:", id);

// In calculateGrandTotal Funktion  
console.log("calculateGrandTotal aufgerufen");

// Prüfe ob Bootstrap Modal vorhanden
console.log("Bootstrap Modal verfügbar:", typeof bootstrap !== 'undefined' && bootstrap.Modal);

// Modal Event Listener
document.addEventListener('DOMContentLoaded', function() {
    const modalElement = document.getElementById('refillModal');
    if (modalElement) {
        console.log("Modal Element gefunden");
        modalElement.addEventListener('shown.bs.modal', function () {
            console.log("Modal wurde geöffnet");
            if (document.getElementById('product-items').children.length === 0) {
                console.log("Keine Produkt-Zeilen, füge erste hinzu");
                addProductLine();
            }
        });
    } else {
        console.log("FEHLER: Modal Element nicht gefunden!");
    }
});
'''

print(fix_content)
print("\n=== LÖSUNG ===")
print("Das Problem ist wahrscheinlich, dass:")
print("1. Das Modal nicht korrekt initialisiert wird")
print("2. Die JavaScript-Funktionen nicht im globalen Scope sind")
print("3. Bootstrap 5 Modal API anders ist als erwartet")
print("\nÖffnen Sie die Browser-Konsole (F12) und prüfen Sie die Console.log Ausgaben!")
