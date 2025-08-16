"""
Selector fallback system for Farm to People scrapers.
ADDS robustness WITHOUT changing existing working scrapers.
"""

from playwright.sync_api import Page
import time

class SelectorFallbacks:
    """
    Fallback selector system that tries multiple approaches.
    Only used if primary selectors fail - never replaces working code.
    """
    
    def __init__(self):
        # Cart item selectors (in order of preference)
        self.cart_item_selectors = [
            "article[class*='cart-order_cartOrderItem']",  # Current working
            "article[class*='cart-item']",                 # Common alternative
            ".cart-container article",                     # Generic fallback
            "[data-testid*='cart']",                       # Data attribute
            "li[class*='cart-line-item']",                 # List item variant
        ]
        
        # Login selectors
        self.login_button_selectors = [
            "button:has-text('Log in')",                   # Current working
            "button:has-text('Login')",                    # Alternative text
            "button:has-text('Sign in')",                  # Common variant
            "input[type='submit'][value*='login' i]",      # Submit input
            "form button[type='submit']",                  # Generic form submit
        ]
        
        # Email input selectors
        self.email_input_selectors = [
            "input[placeholder='Email address']",          # Current working
            "input[type='email']",                         # Generic email
            "input[name='email']",                         # Name attribute
            "input[id='email']",                           # ID attribute
            "#login-email, #user-email, #account-email",  # Common IDs
        ]
        
        # Session indicators
        self.logout_selectors = [
            "a:has-text('Logout')",                        # Current working
            "button:has-text('Logout')",                   # Button variant
            "a:has-text('Log out')",                       # Spaced variant
            "a:has-text('Sign out')",                      # Alternative text
            "[href*='logout'], [href*='signout']",         # URL patterns
        ]
        
        # Cart button selectors
        self.cart_button_selectors = [
            "div.cart-button",                             # Current working
            "button[class*='cart']",                       # Button with cart class
            "a[class*='cart']",                            # Link with cart class
            "[aria-label*='cart' i]",                     # Aria label
            "[data-testid*='cart']",                       # Test ID
        ]
        
        # Customize button selectors
        self.customize_button_selectors = [
            "button:has-text('Customize')",                # Current working
            "button:has-text('CUSTOMIZE')",                # Uppercase
            "a:has-text('Customize')",                     # Link variant
            "button[class*='customize']",                  # Class contains
            "[data-action*='customize']",                  # Data action
        ]
    
    def find_cart_items(self, page: Page) -> list:
        """Find cart items using fallback selectors if needed."""
        for selector in self.cart_item_selectors:
            try:
                items = page.locator(selector).all()
                if len(items) > 0:
                    if selector != self.cart_item_selectors[0]:
                        print(f"⚠️ Used fallback cart selector: {selector}")
                    return items
            except Exception as e:
                print(f"⚠️ Cart selector failed: {selector} - {e}")
                continue
        
        print("❌ All cart item selectors failed")
        return []
    
    def find_login_button(self, page: Page):
        """Find login button using fallback selectors if needed."""
        for selector in self.login_button_selectors:
            try:
                element = page.locator(selector).first
                if element.count() > 0:
                    if selector != self.login_button_selectors[0]:
                        print(f"⚠️ Used fallback login button: {selector}")
                    return element
            except Exception as e:
                print(f"⚠️ Login button selector failed: {selector} - {e}")
                continue
        
        print("❌ All login button selectors failed")
        return None
    
    def find_email_input(self, page: Page):
        """Find email input using fallback selectors if needed."""
        for selector in self.email_input_selectors:
            try:
                element = page.locator(selector).first
                if element.count() > 0:
                    if selector != self.email_input_selectors[0]:
                        print(f"⚠️ Used fallback email input: {selector}")
                    return element
            except Exception as e:
                print(f"⚠️ Email input selector failed: {selector} - {e}")
                continue
        
        print("❌ All email input selectors failed")
        return None
    
    def check_logged_in_status(self, page: Page) -> bool:
        """Check if logged in using fallback selectors if needed."""
        for selector in self.logout_selectors:
            try:
                elements = page.locator(selector).all()
                if len(elements) > 0:
                    if selector != self.logout_selectors[0]:
                        print(f"⚠️ Used fallback logout detector: {selector}")
                    return True
            except Exception as e:
                print(f"⚠️ Logout selector failed: {selector} - {e}")
                continue
        
        return False
    
    def find_cart_button(self, page: Page):
        """Find cart button using fallback selectors if needed."""
        for selector in self.cart_button_selectors:
            try:
                element = page.locator(selector).first
                if element.count() > 0:
                    if selector != self.cart_button_selectors[0]:
                        print(f"⚠️ Used fallback cart button: {selector}")
                    return element
            except Exception as e:
                print(f"⚠️ Cart button selector failed: {selector} - {e}")
                continue
        
        print("❌ All cart button selectors failed")
        return None
    
    def test_all_selectors(self, page: Page) -> dict:
        """Test all selectors and return health report."""
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tests": {},
            "fallbacks_used": [],
            "failed_selectors": []
        }
        
        # Test each selector category
        tests = [
            ("cart_items", self.find_cart_items),
            ("login_button", self.find_login_button),
            ("email_input", self.find_email_input),
            ("logout_status", self.check_logged_in_status),
            ("cart_button", self.find_cart_button)
        ]
        
        for test_name, test_func in tests:
            try:
                start_time = time.time()
                result = test_func(page)
                duration = time.time() - start_time
                
                if result:
                    report["tests"][test_name] = {
                        "status": "pass",
                        "duration": f"{duration:.2f}s",
                        "found": len(result) if isinstance(result, list) else 1
                    }
                else:
                    report["tests"][test_name] = {
                        "status": "fail", 
                        "duration": f"{duration:.2f}s",
                        "found": 0
                    }
                    
            except Exception as e:
                report["tests"][test_name] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return report

# Global instance for use by other scrapers
fallback_system = SelectorFallbacks()

def get_cart_items_robust(page: Page) -> list:
    """
    Robust cart item finder with fallbacks.
    DROP-IN replacement for existing cart item finding.
    """
    try:
        # Try primary method first (current working approach)
        primary_items = page.locator("article[class*='cart-order_cartOrderItem']").all()
        if len(primary_items) > 0:
            return primary_items
        
        # Only use fallbacks if primary fails
        print("⚠️ Primary cart selector found 0 items, trying fallbacks...")
        return fallback_system.find_cart_items(page)
        
    except Exception as e:
        print(f"❌ Cart item detection failed: {e}")
        return fallback_system.find_cart_items(page)

def get_login_button_robust(page: Page):
    """
    Robust login button finder with fallbacks.
    DROP-IN replacement for existing login button finding.
    """
    try:
        # Try primary method first
        primary_btn = page.locator("button:has-text('Log in')").first
        if primary_btn.count() > 0:
            return primary_btn
        
        # Only use fallbacks if primary fails  
        print("⚠️ Primary login button not found, trying fallbacks...")
        return fallback_system.find_login_button(page)
        
    except Exception as e:
        print(f"❌ Login button detection failed: {e}")
        return fallback_system.find_login_button(page)

def check_session_robust(page: Page) -> bool:
    """
    Robust session check with fallbacks.
    DROP-IN replacement for existing session checking.
    """
    try:
        # Try primary method first
        primary_logout = page.locator("a:has-text('Logout')").all()
        if len(primary_logout) > 0:
            return True
        
        # Only use fallbacks if primary fails
        print("⚠️ Primary session check failed, trying fallbacks...")
        return fallback_system.check_logged_in_status(page)
        
    except Exception as e:
        print(f"❌ Session check failed: {e}")
        return fallback_system.check_logged_in_status(page)
