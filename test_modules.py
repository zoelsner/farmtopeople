#!/usr/bin/env python3
"""
Test script to verify all dashboard v3 modules exist and are accessible
"""

import os
import json
import re
from pathlib import Path

def check_file_exists(filepath):
    """Check if a file exists and return its size"""
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        return True, size
    return False, 0

def check_js_syntax(filepath):
    """Basic syntax check for JavaScript files"""
    errors = []
    with open(filepath, 'r') as f:
        content = f.read()

        # Check for balanced braces
        open_braces = content.count('{')
        close_braces = content.count('}')
        if open_braces != close_braces:
            errors.append(f"Unbalanced braces: {open_braces} open, {close_braces} close")

        # Check for balanced parentheses
        open_parens = content.count('(')
        close_parens = content.count(')')
        if open_parens != close_parens:
            errors.append(f"Unbalanced parentheses: {open_parens} open, {close_parens} close")

        # Check for export statements
        exports = re.findall(r'export\s+(class|default|const|function)\s+(\w+)', content)

        # Check for import statements
        imports = re.findall(r'import\s+.*\s+from\s+[\'"](.+?)[\'"]', content)

    return errors, exports, imports

def main():
    base_path = Path("/Users/zach/Projects/farmtopeople")

    # Define all required files
    files_to_check = {
        "HTML": [
            "server/templates/dashboard-v3.html",
        ],
        "Core Modules": [
            "server/static/js/modules/core.js",
            "server/static/js/modules/navigation-v2.js",
            "server/static/js/modules/api-client.js",
        ],
        "Feature Modules": [
            "server/static/js/modules/cart-v3.js",
            "server/static/js/modules/settings-v3.js",
            "server/static/js/modules/meals-v3.js",
        ],
        "CSS Files": [
            "server/static/css/dashboard-base.css",
            "server/static/css/dashboard-components.css",
            "server/static/css/dashboard-modules.css",
        ]
    }

    print("=" * 60)
    print("Dashboard v3 Module Verification")
    print("=" * 60)

    all_good = True

    for category, files in files_to_check.items():
        print(f"\n{category}:")
        print("-" * 40)

        for file in files:
            filepath = base_path / file
            exists, size = check_file_exists(filepath)

            if exists:
                print(f"✅ {file} ({size:,} bytes)")

                # Check JS files for syntax
                if file.endswith('.js'):
                    errors, exports, imports = check_js_syntax(filepath)
                    if errors:
                        print(f"   ⚠️  Syntax issues: {', '.join(errors)}")
                        all_good = False
                    if exports:
                        print(f"   📤 Exports: {', '.join([e[1] for e in exports[:3]])}")
                    if imports:
                        print(f"   📥 Imports from: {', '.join(set(imports[:3]))}")
            else:
                print(f"❌ {file} - NOT FOUND")
                all_good = False

    print("\n" + "=" * 60)
    if all_good:
        print("✅ All files present and valid!")
    else:
        print("⚠️  Some issues found - review above")
    print("=" * 60)

    # Check for cross-references
    print("\n🔍 Checking module dependencies...")
    js_files = [f for cat in files_to_check.values() for f in cat if f.endswith('.js')]

    for file in js_files:
        filepath = base_path / file
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                content = f.read()

                # Check for window references
                window_refs = re.findall(r'window\.([\w]+)', content)
                if window_refs:
                    print(f"\n{file}:")
                    print(f"  Window refs: {', '.join(set(window_refs[:5]))}")

if __name__ == "__main__":
    main()