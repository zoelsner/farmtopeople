"""
Automated verification that core scraping functionality is working.
RUN THIS FIRST before making any changes to scraper code.
"""

import subprocess
import sys
from pathlib import Path
import json
from datetime import datetime

def run_verification():
    """Run comprehensive verification of working scraper state."""
    
    print("🔍 VERIFYING WORKING SCRAPER STATE")
    print("=" * 50)
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "tests": {},
        "overall_status": "unknown"
    }
    
    # Test 1: Verify customize_scraper.py exists and runs
    print("\n✅ TEST 1: Customize Scraper Existence")
    customize_script = Path("customize_scraper.py")
    
    if not customize_script.exists():
        print("❌ customize_scraper.py NOT FOUND")
        results["tests"]["customize_exists"] = False
        results["overall_status"] = "critical"
        return results
    else:
        print("✅ customize_scraper.py found")
        results["tests"]["customize_exists"] = True
    
    # Test 2: Check for recent successful customize output
    print("\n✅ TEST 2: Recent Customize Output")
    output_dir = Path("../farm_box_data")
    
    if output_dir.exists():
        customize_files = list(output_dir.glob("customize_results_*.json"))
        
        if customize_files:
            latest_file = max(customize_files, key=lambda x: x.stat().st_mtime)
            print(f"✅ Found recent output: {latest_file.name}")
            
            # Check if the file has alternatives
            try:
                with open(latest_file) as f:
                    data = json.load(f)
                
                has_alternatives = False
                for box in data:
                    # Check both possible field names
                    alternatives = box.get("available_items", []) or box.get("available_alternatives", [])
                    if len(alternatives) > 0:
                        has_alternatives = True
                        break
                
                if has_alternatives:
                    print("✅ Output contains alternatives - customize working")
                    results["tests"]["has_alternatives"] = True
                else:
                    print("❌ Output missing alternatives - customize broken")
                    results["tests"]["has_alternatives"] = False
                    
            except Exception as e:
                print(f"❌ Error reading output file: {e}")
                results["tests"]["has_alternatives"] = False
        else:
            print("⚠️ No recent customize output found")
            results["tests"]["has_alternatives"] = False
    else:
        print("❌ Output directory not found")
        results["tests"]["has_alternatives"] = False
    
    # Test 3: Quick syntax check
    print("\n✅ TEST 3: Script Syntax Check")
    try:
        result = subprocess.run([
            sys.executable, "-m", "py_compile", "customize_scraper.py"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Syntax check passed")
            results["tests"]["syntax_ok"] = True
        else:
            print(f"❌ Syntax errors: {result.stderr}")
            results["tests"]["syntax_ok"] = False
    except Exception as e:
        print(f"❌ Could not check syntax: {e}")
        results["tests"]["syntax_ok"] = False
    
    # Calculate overall status
    test_results = list(results["tests"].values())
    if all(test_results):
        results["overall_status"] = "healthy"
        print("\n🟢 VERIFICATION PASSED")
        print("✅ Customize scraper appears to be working")
        print("✅ Safe to proceed with changes")
    elif any(test_results):
        results["overall_status"] = "warning" 
        print("\n🟡 VERIFICATION WARNING")
        print("⚠️ Some issues detected - proceed with caution")
    else:
        results["overall_status"] = "critical"
        print("\n🔴 VERIFICATION FAILED")
        print("❌ Critical issues detected")
        print("❌ DO NOT make changes until these are fixed")
    
    return results

def main():
    """Main verification function."""
    results = run_verification()
    
    if results["overall_status"] == "critical":
        print("\n🚨 CRITICAL ISSUES DETECTED")
        print("Fix these issues before making any scraper changes:")
        
        for test_name, passed in results["tests"].items():
            if not passed:
                print(f"  ❌ {test_name}")
        
        print("\nRecommended actions:")
        print("1. Restore from working backup")
        print("2. Run: python customize_scraper.py")
        print("3. Verify browser clicking behavior")
        
        sys.exit(1)
    
    elif results["overall_status"] == "warning":
        print("\n⚠️ WARNINGS DETECTED")
        print("Consider running a full test before proceeding:")
        print("  python customize_scraper.py")
        
    else:
        print("\n🎉 ALL CHECKS PASSED")
        print("Scraper state verified - safe to proceed")

if __name__ == "__main__":
    main()
