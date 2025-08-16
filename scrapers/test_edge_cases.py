"""
Edge case testing for Farm to People authentication and scraping.
This script tests various scenarios that could break our scrapers.
"""

from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
from auth_helper import ensure_logged_in, login_to_farm_to_people

load_dotenv()

def test_edge_cases():
    """Test various edge cases for authentication and scraping."""
    
    output_dir = Path("../farm_box_data")
    output_dir.mkdir(exist_ok=True)
    
    test_results = []
    
    with sync_playwright() as p:
        user_data_dir = Path("../browser_data")
        user_data_dir.mkdir(exist_ok=True)
        
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            viewport={"width": 1920, "height": 1080}
        )
        
        page = context.new_page()
        
        print("🧪 FARM TO PEOPLE EDGE CASE TESTING")
        print("=" * 50)
        
        # Test Case 1: Multiple email inputs confusion
        print("\n🔍 TEST 1: Multiple Email Inputs")
        try:
            page.goto("https://farmtopeople.com/login")
            page.wait_for_timeout(2000)
            
            all_email_inputs = page.locator("input[type='email']").all()
            print(f"   Found {len(all_email_inputs)} email inputs on login page")
            
            for i, inp in enumerate(all_email_inputs):
                placeholder = inp.get_attribute("placeholder") or ""
                inp_id = inp.get_attribute("id") or ""
                inp_class = inp.get_attribute("class") or ""
                print(f"   {i+1}. id='{inp_id}' placeholder='{placeholder}' class='{inp_class[:50]}'")
            
            test_results.append("✅ Multiple email inputs identified")
        except Exception as e:
            test_results.append(f"❌ Multiple email test failed: {e}")
        
        # Test Case 2: Session timeout simulation
        print("\n🔍 TEST 2: Session Timeout Detection")
        try:
            page.goto("https://farmtopeople.com/home")
            page.wait_for_timeout(2000)
            
            # Check current login status
            login_indicators = page.locator("button:has-text('Log in'), a:has-text('Log in')").all()
            account_indicators = page.locator("button:has-text('Account'), a:has-text('Account')").all()
            
            print(f"   Login buttons found: {len(login_indicators)}")
            print(f"   Account buttons found: {len(account_indicators)}")
            
            if len(login_indicators) > 0:
                print("   ⚠️ Session appears expired (login required)")
                test_results.append("⚠️ Session expired - login needed")
            else:
                print("   ✅ Session appears active")
                test_results.append("✅ Session active")
                
        except Exception as e:
            test_results.append(f"❌ Session test failed: {e}")
        
        # Test Case 3: Empty cart handling
        print("\n🔍 TEST 3: Empty Cart Handling")
        try:
            if ensure_logged_in(page):
                page.goto("https://farmtopeople.com/home")
                page.wait_for_timeout(2000)
                
                cart_btn = page.locator("div.cart-button").first
                if cart_btn.count() > 0:
                    cart_btn.click()
                    page.wait_for_timeout(2000)
                    
                    cart_items = page.locator("article[class*='cart-order_cartOrderItem']").all()
                    print(f"   Cart items found: {len(cart_items)}")
                    
                    if len(cart_items) == 0:
                        print("   ℹ️ Cart is empty (expected for testing)")
                        test_results.append("ℹ️ Empty cart handled correctly")
                    else:
                        print(f"   ✅ Cart has {len(cart_items)} items")
                        test_results.append(f"✅ Cart has {len(cart_items)} items")
                else:
                    print("   ❌ Cart button not found")
                    test_results.append("❌ Cart button not accessible")
            else:
                test_results.append("❌ Could not log in for cart test")
                
        except Exception as e:
            test_results.append(f"❌ Cart test failed: {e}")
        
        # Test Case 4: Network connectivity issues
        print("\n🔍 TEST 4: Page Load Timeouts")
        try:
            start_time = datetime.now()
            page.goto("https://farmtopeople.com/home", timeout=10000)
            load_time = (datetime.now() - start_time).total_seconds()
            
            print(f"   Page load time: {load_time:.2f} seconds")
            
            if load_time > 8:
                print("   ⚠️ Slow page load detected")
                test_results.append("⚠️ Slow network conditions")
            else:
                print("   ✅ Normal page load speed")
                test_results.append("✅ Normal network speed")
                
        except Exception as e:
            print(f"   ❌ Page load timeout: {e}")
            test_results.append("❌ Network timeout issues")
        
        # Test Case 5: Missing credentials
        print("\n🔍 TEST 5: Credential Validation")
        try:
            email = os.getenv("EMAIL")
            password = os.getenv("PASSWORD")
            
            if not email:
                print("   ❌ EMAIL environment variable missing")
                test_results.append("❌ Missing EMAIL credential")
            elif not "@" in email:
                print("   ❌ EMAIL format appears invalid")
                test_results.append("❌ Invalid EMAIL format")
            else:
                print(f"   ✅ EMAIL configured: {email[:3]}***{email[-10:]}")
                test_results.append("✅ EMAIL credential valid")
            
            if not password:
                print("   ❌ PASSWORD environment variable missing")
                test_results.append("❌ Missing PASSWORD credential")
            elif len(password) < 6:
                print("   ⚠️ PASSWORD appears too short")
                test_results.append("⚠️ PASSWORD may be too short")
            else:
                print(f"   ✅ PASSWORD configured ({len(password)} chars)")
                test_results.append("✅ PASSWORD credential present")
                
        except Exception as e:
            test_results.append(f"❌ Credential test failed: {e}")
        
        # Test Case 6: CAPTCHA or bot detection
        print("\n🔍 TEST 6: Bot Detection Check")
        try:
            page.goto("https://farmtopeople.com/login")
            page.wait_for_timeout(2000)
            
            # Look for common bot detection indicators
            captcha_indicators = [
                "iframe[src*='recaptcha']",
                "div[class*='captcha']",
                "div[class*='challenge']",
                "div:has-text('verify you are human')",
                "div:has-text('robot')"
            ]
            
            captcha_found = False
            for indicator in captcha_indicators:
                if page.locator(indicator).count() > 0:
                    print(f"   ⚠️ Potential bot detection: {indicator}")
                    captcha_found = True
                    
            if not captcha_found:
                print("   ✅ No bot detection mechanisms found")
                test_results.append("✅ No CAPTCHA/bot detection")
            else:
                test_results.append("⚠️ CAPTCHA/bot detection present")
                
        except Exception as e:
            test_results.append(f"❌ Bot detection test failed: {e}")
        
        context.close()
    
    # Summary Report
    print("\n" + "=" * 50)
    print("🧪 EDGE CASE TEST RESULTS SUMMARY")
    print("=" * 50)
    
    for i, result in enumerate(test_results, 1):
        print(f"{i:2d}. {result}")
    
    # Count results
    success_count = len([r for r in test_results if r.startswith("✅")])
    warning_count = len([r for r in test_results if r.startswith("⚠️")])
    error_count = len([r for r in test_results if r.startswith("❌")])
    info_count = len([r for r in test_results if r.startswith("ℹ️")])
    
    print(f"\n📊 SUMMARY: {success_count} ✅ | {warning_count} ⚠️ | {error_count} ❌ | {info_count} ℹ️")
    
    if error_count > 0:
        print("\n🚨 CRITICAL ISSUES FOUND - Need immediate attention")
    elif warning_count > 0:
        print("\n⚠️ WARNINGS FOUND - Monitor these conditions")
    else:
        print("\n🎉 ALL TESTS PASSED - System robust against edge cases")
    
    return test_results

if __name__ == "__main__":
    test_edge_cases()
