#!/usr/bin/env python
"""Korrigiert alle JavaScript geschweiften Klammern für Python f-strings"""

# Lade die refills.py
file_path = "H:\\Projekt\\Automaten\\app\\web\\refills.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Wir sind im JavaScript Bereich zwischen Zeile 46 und 411 (extra_scripts)
in_js = False
js_start_line = None
fixed_lines = []

for i, line in enumerate(lines):
    # Start des JavaScript-Bereichs
    if 'extra_scripts = """' in line:
        in_js = True
        js_start_line = i
        fixed_lines.append(line)
        continue
    
    # Ende des JavaScript-Bereichs (das schließende """)
    if in_js and line.strip() == '"""' and i > js_start_line + 1:
        in_js = False
        fixed_lines.append(line)
        continue
    
    # Innerhalb des JavaScript-Bereichs: Ersetze { mit {{ und } mit }}
    # ABER nur wenn sie NICHT bereits verdoppelt sind
    if in_js and '    <script>' not in line and '</script>' not in line:
        # Ersetze einzelne { und } mit {{ und }}
        # Aber nicht {{{ oder }}}
        fixed_line = line
        
        # Einfache Ersetzung - ersetze alle einzelnen { und }
        import re
        # Ersetze { mit {{ wenn nicht bereits {{
        fixed_line = re.sub(r'(?<!\{)\{(?!\{)', '{{', fixed_line)
        # Ersetze } mit }} wenn nicht bereits }}
        fixed_line = re.sub(r'(?<!\})\}(?!\})', '}}', fixed_line)
        
        fixed_lines.append(fixed_line)
    else:
        fixed_lines.append(line)

# Schreibe die korrigierte Datei
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print("✅ JavaScript geschweiften Klammern korrigiert!")
print("Alle einzelnen { wurden zu {{ und } zu }}")
print("\nBitte Docker neu starten:")
print("docker-compose restart app")
