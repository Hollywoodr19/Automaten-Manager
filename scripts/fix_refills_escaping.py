#!/usr/bin/env python3
"""Fix JavaScript escaping in refills.py"""

import re

# Read the file
with open('/app/app/web/refills.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the extra_scripts section
start_marker = 'extra_scripts = """'
end_marker = '"""'

# Find start and end positions
start_pos = content.find(start_marker)
if start_pos == -1:
    print("ERROR: Could not find extra_scripts start!")
    exit(1)

# Find the corresponding end (not the next one after start)
search_start = start_pos + len(start_marker)
end_pos = content.find(end_marker, search_start)
if end_pos == -1:
    print("ERROR: Could not find extra_scripts end!")
    exit(1)

# Extract the JavaScript section
js_section = content[start_pos:end_pos + len(end_marker)]

# Count braces
open_braces = js_section.count('{')
close_braces = js_section.count('}')
single_open = len(re.findall(r'(?<!\{)\{(?!\{)', js_section))
single_close = len(re.findall(r'(?<!\})\}(?!\})', js_section))

print(f"Total open braces: {open_braces}")
print(f"Total close braces: {close_braces}")
print(f"Single open braces: {single_open}")
print(f"Single close braces: {single_close}")

# Check if we need to fix anything
if single_open > 0 or single_close > 0:
    print(f"\nFound {single_open} single open and {single_close} single close braces that need fixing!")
    
    # Create a backup
    import shutil
    shutil.copy('/app/app/web/refills.py', '/app/app/web/refills.py.backup_escaping')
    print("Backup created: refills.py.backup_escaping")
    
    # Fix by carefully replacing only single braces
    # This is complex because we need to avoid replacing already doubled braces
    
    # Replace single { with {{ (but not if already doubled)
    fixed_content = re.sub(r'(?<!\{)\{(?!\{)', '{{', content)
    # Replace single } with }} (but not if already doubled)
    fixed_content = re.sub(r'(?<!\})\}(?!\})', '}}', content)
    
    # Write the fixed content
    with open('/app/app/web/refills.py', 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print("File fixed and saved!")
    
    # Verify
    with open('/app/app/web/refills.py', 'r', encoding='utf-8') as f:
        new_content = f.read()
    
    new_single_open = len(re.findall(r'(?<!\{)\{(?!\{)', new_content))
    new_single_close = len(re.findall(r'(?<!\})\}(?!\})', new_content))
    
    print(f"\nAfter fix:")
    print(f"Single open braces: {new_single_open}")
    print(f"Single close braces: {new_single_close}")
    
    if new_single_open == 0 and new_single_close == 0:
        print("✅ All braces are now properly doubled!")
    else:
        print("⚠️ Still some single braces remaining - manual fix needed")
else:
    print("\n✅ No single braces found - file is already correct!")
