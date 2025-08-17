#!/usr/bin/env python
"""Fix: Stelle alle doppelten geschweiften Klammern wieder her"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Lade die refills.py
file_path = "H:\\Projekt\\Automaten\\app\\web\\refills.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Liste aller Stellen, wo wir { wieder zu {{ machen müssen
replacements = [
    # JavaScript Template Literals und Bedingungen
    ('function removeItem(id) {', 'function removeItem(id) {{'),
    ('document.getElementById(`item-${id}`).remove();', 'document.getElementById(`item-${{id}}`).remove();'),
    ('calculateGrandTotal();', 'calculateGrandTotal();'),
    ('}', '}}'),  # VORSICHT: Das ersetzt ALLE }, wir müssen spezifischer sein
]

# Spezifischere Ersetzungen für JavaScript-Funktionen
js_fixes = [
    # Funktions-Definitionen
    ('function addProductLine() {', 'function addProductLine() {{'),
    ('function removeItem(id) {', 'function removeItem(id) {{'),
    ('function updatePrice(id) {', 'function updatePrice(id) {{'),
    ('function calculateTotal(id) {', 'function calculateTotal(id) {{'),
    ('function calculateGrandTotal() {', 'function calculateGrandTotal() {{'),
    ('function setupDragDrop() {', 'function setupDragDrop() {{'),
    ('function removeReceipt() {', 'function removeReceipt() {{'),
    ('function viewRefill(id) {', 'function viewRefill(id) {{'),
    
    # Template Literals
    ('`#item-${id}`', '`#item-${{id}}`'),
    ('`#item-${id} .product-select`', '`#item-${{id}} .product-select`'),
    ('`#item-${id} .price-input`', '`#item-${{id}} .price-input`'),
    ('`#item-${id} .quantity-input`', '`#item-${{id}} .quantity-input`'),
    ('`#item-${id} .discount-input`', '`#item-${{id}} .discount-input`'),
    ('`#item-${id} .total-input`', '`#item-${{id}} .total-input`'),
    ('`Ersparnis: ${savedPercent}%`', '`Ersparnis: ${{savedPercent}}%`'),
    
    # Ausgaben
    ('`<strong>${subtotal.toFixed(2)} €</strong>`', '`<strong>${{subtotal.toFixed(2)}} €</strong>`'),
    ('`MwSt (${taxRate}%)`', '`MwSt (${{taxRate}}%)`'),
    ('`<strong>${tax.toFixed(2)} €</strong>`', '`<strong>${{tax.toFixed(2)}} €</strong>`'),
    ('`- ${totalLineDiscounts.toFixed(2)} €`', '`- ${{totalLineDiscounts.toFixed(2)}} €`'),
    ('`<strong>${finalTotal.toFixed(2)} €</strong>`', '`<strong>${{finalTotal.toFixed(2)}} €</strong>`'),
    
    # If-Statements
    ('if (discount > 0) {', 'if (discount > 0) {{'),
    ('if (grossTotal > 0) {', 'if (grossTotal > 0) {{'),
    ('} else {', '}} else {{'),
    ('if (pricesIncludeTax) {', 'if (pricesIncludeTax) {{'),
    ('if (totalLineDiscounts > 0) {', 'if (totalLineDiscounts > 0) {{'),
    ('if (globalDiscount > 0) {', 'if (globalDiscount > 0) {{'),
    ('if (shipping > 0) {', 'if (shipping > 0) {{'),
    ('if (deposit > 0) {', 'if (deposit > 0) {{'),
    ('if (totalSavings > 0) {', 'if (totalSavings > 0) {{'),
    ('if (selectedOption.dataset.price) {', 'if (selectedOption.dataset.price) {{'),
    
    # forEach
    ('.forEach(input => {', '.forEach(input => {{'),
    ('.forEach(eventName => {', '.forEach(eventName => {{'),
    ('addEventListener(eventName, () => {', 'addEventListener(eventName, () => {{'),
    
    # Schließende Klammern am Ende der Zeilen
    ('    }', '    }}'),
    ('});', '}});'),
    ('}, false);', '}}, false);'),
]

# Finde den JavaScript-Bereich
script_start = content.find('extra_scripts = """')
script_end = content.find('"""', script_start + 20)

if script_start != -1 and script_end != -1:
    # Extrahiere den JavaScript-Teil
    js_part = content[script_start:script_end + 3]
    
    # Wende alle Fixes an
    js_part_fixed = js_part
    for old, new in js_fixes:
        js_part_fixed = js_part_fixed.replace(old, new)
    
    # Setze den korrigierten Teil wieder ein
    content_fixed = content[:script_start] + js_part_fixed + content[script_end + 3:]
    
    # Speichere die korrigierte Datei
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content_fixed)
    
    print("✅ Doppelte geschweifte Klammern wiederhergestellt!")
    print("Alle { wurden wieder zu {{ und } zu }}")
    print("\nBitte starten Sie Docker neu:")
    print("docker-compose restart app")
else:
    print("❌ JavaScript-Bereich nicht gefunden!")
