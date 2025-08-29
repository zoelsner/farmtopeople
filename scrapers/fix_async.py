#!/usr/bin/env python3
"""
Script to automatically add 'await' keywords to comprehensive_scraper.py
"""

import re

# Read the file
with open('comprehensive_scraper.py', 'r') as f:
    lines = f.readlines()

# Patterns that need await (if not already present)
patterns_needing_await = [
    r'\.click\(\)',
    r'\.fill\(',
    r'\.count\(\)',
    r'\.text_content\(\)',
    r'\.get_attribute\(',
    r'\.all\(\)',
    r'page\.goto\(',
    r'page\.wait_for',
    r'context\.close\(',
    r'browser\.close\(',
    r'\.evaluate\(',
]

# Process each line
new_lines = []
for line in lines:
    # Skip if already has await
    if 'await' in line:
        new_lines.append(line)
        continue
    
    # Check if line needs await
    needs_await = False
    for pattern in patterns_needing_await:
        if re.search(pattern, line):
            needs_await = True
            break
    
    if needs_await:
        # Find the indentation
        indent = len(line) - len(line.lstrip())
        
        # Special handling for if statements with method calls
        if re.match(r'\s*if\s+.*\.(count|text_content|get_attribute)\(\)', line):
            # Add await after 'if'
            line = line[:indent] + re.sub(r'if\s+', 'if await ', line[indent:], count=1)
        # Handle regular statements
        elif not line.lstrip().startswith('#'):
            # Add await at the beginning of the statement
            stripped = line.lstrip()
            # Handle variable assignments
            if '=' in stripped and not stripped.startswith('if'):
                parts = stripped.split('=', 1)
                if len(parts) == 2:
                    var_part = parts[0]
                    expr_part = parts[1]
                    # Add await to the expression part
                    line = ' ' * indent + var_part + '= await' + expr_part
            else:
                # Just add await at the beginning
                line = ' ' * indent + 'await ' + stripped
    
    new_lines.append(line)

# Write the updated file
with open('comprehensive_scraper.py', 'w') as f:
    f.writelines(new_lines)

print("✅ Added await keywords to comprehensive_scraper.py")