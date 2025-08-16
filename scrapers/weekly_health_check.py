"""
Weekly health check for Farm to People scrapers.
Runs every Wednesday to ensure everything still works.
Tests with individual items since boxes might be empty.
"""

from playwright.sync_api import sync_playwright
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from auth_helper import ensure_logged_in
from selector_fallbacks import fallback_system

def run_weekly_health_check():
    """
    Comprehensive health check of the scraping system.
    Designed to run every Wednesday morning.
    """
    
    print("🏥 FARM TO PEOPLE WEEKLY HEALTH CHECK")
    print("=" * 50)
    print(f"📅 Date: {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}")
    
    health_report = {
        "timestamp": datetime.now().isoformat(),
        "overall_status": "unknown",
        "tests": {},
        "recommendations": [],
        "next_check_due": (datetime.now() + timedelta(days=7)).isoformat()
    }
    
    with sync_playwright() as p:
        user_data_dir = Path("../browser_data")
        user_data_dir.mkdir(exist_ok=True)
        
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            viewport={"width": 1920, "height": 1080}
        )
        
        page = context.new_page()
        
        try:
            # Test 1: Authentication Health
            print("\n🔐 TEST 1: Authentication System")
            auth_start = time.time()
            
            auth_success = ensure_logged_in(page)
            auth_duration = time.time() - auth_start
            
            health_report["tests"]["authentication"] = {
                "status": "pass" if auth_success else "fail",
                "duration": f"{auth_duration:.1f}s",
                "details": "Session detection and login flow"
            }
            
            if auth_success:
                if auth_duration < 5:
                    print(f"✅ Authentication: EXCELLENT ({auth_duration:.1f}s)")
                elif auth_duration < 10:
                    print(f"✅ Authentication: GOOD ({auth_duration:.1f}s)")
                else:
                    print(f"⚠️ Authentication: SLOW ({auth_duration:.1f}s)")
                    health_report["recommendations"].append("Authentication slower than usual - monitor performance")
            else:
                print("❌ Authentication: FAILED")
                health_report["recommendations"].append("CRITICAL: Authentication system not working")
            
            if not auth_success:
                print("🚨 Cannot continue health check without authentication")
                health_report["overall_status"] = "critical"
                return health_report
            
            # Test 2: Cart Access
            print("\n🛒 TEST 2: Cart Access")
            cart_start = time.time()
            
            # Navigate to home and access cart
            page.goto("https://farmtopeople.com/home")
            page.wait_for_timeout(2000)
            
            cart_btn = page.locator("div.cart-button").first
            cart_accessible = cart_btn.count() > 0
            
            if cart_accessible:
                cart_btn.click()
                page.wait_for_timeout(3000)
                cart_duration = time.time() - cart_start
                
                print(f"✅ Cart Access: SUCCESS ({cart_duration:.1f}s)")
                health_report["tests"]["cart_access"] = {
                    "status": "pass",
                    "duration": f"{cart_duration:.1f}s",
                    "details": "Cart button found and clickable"
                }
            else:
                print("❌ Cart Access: FAILED - Cart button not found")
                health_report["tests"]["cart_access"] = {
                    "status": "fail",
                    "details": "Cart button selector may have changed"
                }
                health_report["recommendations"].append("Cart button selector needs updating")
            
            # Test 3: Selector Health Check
            print("\n🎯 TEST 3: Selector Health Check")
            selector_report = fallback_system.test_all_selectors(page)
            
            passing_tests = sum(1 for test in selector_report["tests"].values() if test["status"] == "pass")
            total_tests = len(selector_report["tests"])
            
            print(f"📊 Selector Health: {passing_tests}/{total_tests} selectors working")
            
            health_report["tests"]["selectors"] = {
                "status": "pass" if passing_tests >= total_tests * 0.8 else "fail",
                "passing": passing_tests,
                "total": total_tests,
                "details": selector_report["tests"]
            }
            
            if passing_tests < total_tests:
                failing_selectors = [name for name, result in selector_report["tests"].items() 
                                   if result["status"] != "pass"]
                health_report["recommendations"].append(f"Selectors failing: {', '.join(failing_selectors)}")
            
            # Test 4: Individual Item Detection (since boxes might be empty)
            print("\n🥑 TEST 4: Individual Item Detection")
            item_start = time.time()
            
            # Look for any individual items in cart
            individual_items = page.locator("article[class*='cart-order_cartOrderItem']").all()
            item_duration = time.time() - item_start
            
            print(f"📦 Found {len(individual_items)} items in cart")
            
            if len(individual_items) > 0:
                # Test parsing first item
                try:
                    first_item = individual_items[0]
                    item_name = first_item.locator("a[class*='subproduct-name'], h3, h4").first.text_content()
                    item_price = first_item.locator("[class*='price']").first.text_content()
                    
                    print(f"✅ Item Parsing: SUCCESS")
                    print(f"   Sample item: {item_name} - {item_price}")
                    
                    health_report["tests"]["item_parsing"] = {
                        "status": "pass",
                        "sample_item": f"{item_name} - {item_price}",
                        "total_items": len(individual_items)
                    }
                    
                except Exception as e:
                    print(f"❌ Item Parsing: FAILED - {e}")
                    health_report["tests"]["item_parsing"] = {
                        "status": "fail",
                        "error": str(e),
                        "total_items": len(individual_items)
                    }
                    health_report["recommendations"].append("Item parsing selectors may need updating")
            else:
                print("ℹ️ No items in cart for testing (expected on Wednesday)")
                health_report["tests"]["item_parsing"] = {
                    "status": "skipped",
                    "reason": "No items in cart to test"
                }
            
            # Test 5: Site Availability & Performance
            print("\n🌐 TEST 5: Site Performance")
            perf_start = time.time()
            
            # Test key pages
            test_pages = [
                ("Home", "https://farmtopeople.com/home"),
                ("Shop", "https://farmtopeople.com/shop/produce"),
                ("Login", "https://farmtopeople.com/login")
            ]
            
            page_performance = {}
            for page_name, url in test_pages:
                try:
                    load_start = time.time()
                    page.goto(url, timeout=10000)
                    load_time = time.time() - load_start
                    
                    page_performance[page_name] = {
                        "status": "pass",
                        "load_time": f"{load_time:.1f}s"
                    }
                    
                    if load_time > 8:
                        health_report["recommendations"].append(f"{page_name} page loading slowly ({load_time:.1f}s)")
                        
                except Exception as e:
                    page_performance[page_name] = {
                        "status": "fail",
                        "error": str(e)
                    }
                    health_report["recommendations"].append(f"{page_name} page failed to load")
            
            health_report["tests"]["site_performance"] = page_performance
            
            avg_load_time = sum(float(p["load_time"].replace("s", "")) 
                              for p in page_performance.values() 
                              if p["status"] == "pass") / len([p for p in page_performance.values() if p["status"] == "pass"])
            
            print(f"📈 Average page load: {avg_load_time:.1f}s")
            
        except Exception as e:
            print(f"🚨 Health check failed with error: {e}")
            health_report["tests"]["critical_error"] = {
                "status": "fail",
                "error": str(e)
            }
            health_report["recommendations"].append("CRITICAL: Health check could not complete")
        
        finally:
            context.close()
    
    # Calculate overall status
    test_results = [test.get("status", "fail") for test in health_report["tests"].values()]
    critical_failures = sum(1 for status in test_results if status == "fail")
    
    if critical_failures == 0:
        health_report["overall_status"] = "healthy"
    elif critical_failures <= 1:
        health_report["overall_status"] = "warning"
    else:
        health_report["overall_status"] = "critical"
    
    # Save health report
    save_health_report(health_report)
    
    # Print summary
    print_health_summary(health_report)
    
    return health_report

def save_health_report(report):
    """Save health report to file with timestamp."""
    output_dir = Path("../farm_box_data")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = output_dir / f"health_check_{timestamp}.json"
    
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📁 Health report saved: {report_file}")

def print_health_summary(report):
    """Print human-readable health summary."""
    print("\n" + "=" * 50)
    print("🏥 HEALTH CHECK SUMMARY")
    print("=" * 50)
    
    status_emoji = {
        "healthy": "🟢",
        "warning": "🟡", 
        "critical": "🔴"
    }
    
    overall = report["overall_status"]
    print(f"\n{status_emoji.get(overall, '❓')} Overall Status: {overall.upper()}")
    
    print(f"\n📊 Test Results:")
    for test_name, result in report["tests"].items():
        status = result.get("status", "unknown")
        emoji = "✅" if status == "pass" else "⚠️" if status == "skipped" else "❌"
        print(f"   {emoji} {test_name.replace('_', ' ').title()}: {status}")
    
    if report["recommendations"]:
        print(f"\n💡 Recommendations:")
        for rec in report["recommendations"]:
            print(f"   • {rec}")
    
    next_check = datetime.fromisoformat(report["next_check_due"]).strftime("%A, %B %d")
    print(f"\n📅 Next check due: {next_check}")
    
    if overall == "healthy":
        print("\n🎉 All systems working normally!")
    elif overall == "warning":
        print("\n⚠️ Minor issues detected - monitor closely")
    else:
        print("\n🚨 Critical issues require immediate attention!")

def setup_weekly_schedule():
    """Helper to show how to set up weekly scheduling."""
    print("📅 WEEKLY HEALTH CHECK SETUP")
    print("=" * 40)
    print("To run this automatically every Wednesday:")
    print()
    print("1. MacOS/Linux (crontab):")
    print("   0 9 * * 3 cd /path/to/farmtopeople/scrapers && python weekly_health_check.py")
    print()
    print("2. Manual run:")
    print("   python weekly_health_check.py")
    print()
    print("3. Test run (anytime):")
    print("   python -c \"from weekly_health_check import run_weekly_health_check; run_weekly_health_check()\"")

if __name__ == "__main__":
    run_weekly_health_check()
