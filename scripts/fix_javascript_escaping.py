#!/usr/bin/env python
"""Kompletter Fix für alle JavaScript Escaping-Probleme in refills.py"""

import re
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Lade die refills.py
file_path = "H:\\Projekt\\Automaten\\app\\web\\refills.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Ersetze alle doppelten geschweiften Klammern {{ und }} mit einfachen { und }
# ABER nur im JavaScript-Bereich zwischen <script> und </script>

# Finde den JavaScript-Bereich
script_start = content.find('extra_scripts = """')
script_end = content.find('"""', script_start + 20)

if script_start != -1 and script_end != -1:
    # Extrahiere den JavaScript-Teil
    js_part = content[script_start:script_end + 3]
    
    # Ersetze alle {{ mit { und }} mit }
    js_part_fixed = js_part.replace('{{', '{').replace('}}', '}')
    
    # Setze den korrigierten Teil wieder ein
    content_fixed = content[:script_start] + js_part_fixed + content[script_end + 3:]
    
    # Speichere die korrigierte Datei
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content_fixed)
    
    print("✅ JavaScript Escaping-Probleme behoben!")
    print("Alle {{ wurden zu { und }} wurden zu }")
    print("\nBitte starten Sie Docker neu:")
    print("docker-compose restart app")
else:
    print("❌ JavaScript-Bereich nicht gefunden!")
