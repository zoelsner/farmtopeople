"""
Test session persistence edge cases for Farm to People authentication.
Specifically tests scenarios where existing sessions should be detected.
"""

from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import time
from auth_helper import ensure_logged_in

load_dotenv()

def test_session_persistence():
    """Test various session persistence scenarios."""
    
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
        
        print("🧪 SESSION PERSISTENCE TESTING")
        print("=" * 50)
        
        # Test 1: Fresh browser start with existing session
        print("\n🔍 TEST 1: Fresh Browser Start (Existing Session)")
        try:
            start_time = time.time()
            login_status = ensure_logged_in(page)
            check_time = time.time() - start_time
            
            print(f"   ⏱️ Session check took: {check_time:.2f} seconds")
            
            if login_status:
                if check_time < 10:  # Should be fast if session exists
                    print("   ✅ Existing session detected quickly")
                    test_results.append("✅ Fast session detection")
                else:
                    print("   ⚠️ Session detected but took too long")
                    test_results.append("⚠️ Slow session detection")
            else:
                print("   ❌ Failed to detect or establish session")
                test_results.append("❌ Session detection failed")
                
        except Exception as e:
            print(f"   ❌ Session test failed: {e}")
            test_results.append(f"❌ Session error: {str(e)[:50]}")
        
        # Test 2: Multiple page navigations
        print("\n🔍 TEST 2: Session Persistence Across Pages")
        try:
            pages_to_test = [
                "https://farmtopeople.com/home",
                "https://farmtopeople.com/shop/produce", 
                "https://farmtopeople.com/home"
            ]
            
            session_persistent = True
            for i, url in enumerate(pages_to_test, 1):
                print(f"   📄 Testing page {i}: {url}")
                page.goto(url)
                page.wait_for_timeout(3000)
                
                # Quick check for login status
                logout_btn = page.locator("a:has-text('Logout'), button:has-text('Logout')").all()
                login_btn = page.locator("a:has-text('Log in'), button:has-text('Log in')").all()
                
                if len(logout_btn) > 0:
                    print(f"      ✅ Session active on page {i}")
                elif len(login_btn) > 0:
                    print(f"      ❌ Session lost on page {i}")
                    session_persistent = False
                    break
                else:
                    print(f"      ❓ Session status unclear on page {i}")
            
            if session_persistent:
                print("   ✅ Session persisted across all pages")
                test_results.append("✅ Multi-page session persistence")
            else:
                print("   ❌ Session lost during navigation")
                test_results.append("❌ Session lost during navigation")
                
        except Exception as e:
            print(f"   ❌ Multi-page test failed: {e}")
            test_results.append(f"❌ Multi-page error: {str(e)[:50]}")
        
        # Test 3: Cart access without re-authentication
        print("\n🔍 TEST 3: Direct Cart Access")
        try:
            page.goto("https://farmtopeople.com/home")
            page.wait_for_timeout(2000)
            
            # Try to access cart directly
            cart_btn = page.locator("div.cart-button").first
            if cart_btn.count() > 0:
                cart_btn.click()
                page.wait_for_timeout(3000)
                
                # Check if we're in the cart or redirected to login
                current_url = page.url
                if "login" in current_url.lower():
                    print("   ❌ Cart access required re-authentication")
                    test_results.append("❌ Cart access failed")
                else:
                    print("   ✅ Cart accessible without re-authentication")
                    test_results.append("✅ Direct cart access")
            else:
                print("   ❌ Cart button not found")
                test_results.append("❌ Cart button missing")
                
        except Exception as e:
            print(f"   ❌ Cart access test failed: {e}")
            test_results.append(f"❌ Cart access error: {str(e)[:50]}")
        
        # Test 4: Session timeout simulation
        print("\n🔍 TEST 4: Session Timeout Handling")
        try:
            # Clear cookies to simulate timeout
            print("   🧹 Simulating session timeout...")
            context.clear_cookies()
            
            # Try the authentication flow
            start_time = time.time()
            login_status = ensure_logged_in(page)
            auth_time = time.time() - start_time
            
            print(f"   ⏱️ Re-authentication took: {auth_time:.2f} seconds")
            
            if login_status:
                print("   ✅ Successfully handled session timeout")
                test_results.append("✅ Session timeout recovery")
            else:
                print("   ❌ Failed to handle session timeout")
                test_results.append("❌ Session timeout failed")
                
        except Exception as e:
            print(f"   ❌ Timeout test failed: {e}")
            test_results.append(f"❌ Timeout error: {str(e)[:50]}")
        
        # Test 5: Network interruption simulation
        print("\n🔍 TEST 5: Network Interruption Recovery")
        try:
            # Go offline briefly
            context.set_offline(True)
            page.wait_for_timeout(2000)
            
            # Go back online
            context.set_offline(False)
            
            # Test if session recovery works
            start_time = time.time()
            login_status = ensure_logged_in(page)
            recovery_time = time.time() - start_time
            
            print(f"   ⏱️ Network recovery took: {recovery_time:.2f} seconds")
            
            if login_status:
                print("   ✅ Session recovered after network interruption")
                test_results.append("✅ Network interruption recovery")
            else:
                print("   ❌ Failed to recover from network interruption")
                test_results.append("❌ Network recovery failed")
                
        except Exception as e:
            print(f"   ❌ Network test failed: {e}")
            test_results.append(f"❌ Network error: {str(e)[:50]}")
        
        context.close()
    
    # Summary Report
    print("\n" + "=" * 50)
    print("📊 SESSION PERSISTENCE TEST SUMMARY")
    print("=" * 50)
    
    for i, result in enumerate(test_results, 1):
        print(f"{i:2d}. {result}")
    
    # Count results
    success_count = len([r for r in test_results if r.startswith("✅")])
    warning_count = len([r for r in test_results if r.startswith("⚠️")])
    error_count = len([r for r in test_results if r.startswith("❌")])
    
    print(f"\n📈 SUMMARY: {success_count} ✅ | {warning_count} ⚠️ | {error_count} ❌")
    
    # Determine overall status
    total_tests = len(test_results)
    if total_tests > 0:
        success_rate = (success_count / total_tests) * 100
        print(f"📊 Success rate: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print("\n🎉 EXCELLENT: Session persistence is highly robust!")
        elif success_rate >= 75:
            print("\n👍 GOOD: Session persistence works well in most scenarios.")
        elif success_rate >= 50:
            print("\n⚠️ FAIR: Some session persistence issues need attention.")
        else:
            print("\n🚨 POOR: Critical session persistence problems detected.")
    
    return test_results

if __name__ == "__main__":
    test_session_persistence()
