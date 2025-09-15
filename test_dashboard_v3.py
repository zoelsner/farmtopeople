#!/usr/bin/env python3
"""
Test Dashboard v3 functionality
"""

import requests
import time

def test_dashboard_v3():
    """Test that dashboard-v3 loads without errors"""

    base_url = "http://localhost:8000"

    print("Testing Dashboard v3...")
    print("-" * 50)

    # Test 1: Dashboard loads
    try:
        response = requests.get(f"{base_url}/dashboard-v3")
        if response.status_code == 200:
            print("✅ Dashboard v3 loads successfully")

            # Check for key elements
            content = response.text

            checks = [
                ("fitbod_meal_planning.css" in content, "Fitbod CSS loaded"),
                ("boxTab" in content, "Box tab present"),
                ("planTab" in content, "Plan tab present"),
                ("settingsTab" in content, "Settings tab present"),
                ("Cart Analysis" in content, "Header title present"),
                ("deliveryDate" in content, "Delivery date element present"),
                ("bottom-nav" in content, "Bottom navigation present"),
                ("import { appState }" in content, "Modules imported"),
            ]

            for check, description in checks:
                if check:
                    print(f"✅ {description}")
                else:
                    print(f"❌ {description}")

        else:
            print(f"❌ Dashboard v3 returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Error loading dashboard: {e}")

    # Test 2: Check API endpoints
    print("\nTesting API endpoints...")

    endpoints = [
        "/api/health",
        "/api/get-saved-cart",
    ]

    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}")
            if response.status_code in [200, 404]:
                print(f"✅ {endpoint} accessible")
            else:
                print(f"⚠️  {endpoint} returned {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint} error: {e}")

    print("\n" + "=" * 50)
    print("Dashboard v3 test complete!")
    print("Open http://localhost:8000/dashboard-v3 in browser to verify:")
    print("1. Tab switching works without refresh")
    print("2. Settings opens as modal")
    print("3. Cart analysis button works")
    print("=" * 50)

if __name__ == "__main__":
    test_dashboard_v3()