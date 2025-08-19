"""
Authentication helper for Farm to People scrapers.
Handles login functionality for all scrapers.
"""

import os
import time
import random
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

def login_to_farm_to_people(page):
    """
    Log in to Farm to People using credentials from environment variables.
    
    Args:
        page: Playwright page object
        
    Returns:
        bool: True if login successful, False otherwise
    """
    email = os.getenv("EMAIL")
    password = os.getenv("PASSWORD")
    
    if not email or not password:
        print("❌ No login credentials found in environment variables")
        print("   Need EMAIL and PASSWORD in .env file")
        return False
    
    try:
        print(f"🔐 Attempting to log in with email: {email}")
        
        # Go to the actual login page
        page.goto("https://farmtopeople.com/login")
        page.wait_for_timeout(2500)
        
        # Based on the actual page, look for email input with placeholder "Email address"
        email_input = page.locator("input[type='email'][placeholder='Email address']").first
        
        if email_input.count() == 0:
            # Fallback selectors
            email_input = page.locator("input[type='email']").first
            
        if email_input.count() > 0:
            email_input.fill(email)
            print("✅ Email filled")
            
            # Click the "Log in" button (the form appears to submit with just email)
            login_button = page.locator("button:has-text('Log in')").first
            
            if login_button.count() > 0:
                login_button.click()
                print("✅ Log in button clicked")
                page.wait_for_timeout(3000)
                
                # After clicking, check if we need to enter password or if we're redirected
                # Look for password field that might appear
                password_input = page.locator("input[type='password']").first
                
                if password_input.count() > 0:
                    print("🔑 Password field appeared, filling password...")
                    password_input.fill(password)
                    
                    # Look for submit button after password
                    submit_button = page.locator("button[type='submit'], button:has-text('Log in'), button:has-text('Submit')").first
                    if submit_button.count() > 0:
                        submit_button.click()
                        print("✅ Password submitted")
                    else:
                        # Try pressing Enter on password field
                        password_input.press("Enter")
                        print("✅ Pressed Enter on password field")
                else:
                    print("ℹ️ No password field found - checking if login completed...")
            else:
                print("❌ Could not find 'Log in' button")
                return False
        else:
            print("❌ Could not find email input field")
            return False
        
        # Wait for login to complete
        page.wait_for_timeout(3000)
        
        # Check if we're logged in by looking for account-specific elements
        # or checking if we're no longer on the login page
        current_url = page.url
        if "login" not in current_url.lower():
            print("✅ Login successful - redirected from login page")
            return True
        
        # Also check for common logged-in indicators
        logged_in_indicators = [
            "button:has-text('Account')",
            "a:has-text('Account')", 
            "button:has-text('Logout')",
            "a:has-text('Logout')",
            ".user-menu",
            "[class*='user-nav']"
        ]
        
        for indicator in logged_in_indicators:
            if page.locator(indicator).count() > 0:
                print("✅ Login successful - found logged-in indicator")
                return True
        
        print("⚠️ Login status unclear - proceeding anyway")
        return True
        
    except Exception as e:
        print(f"❌ Login failed with error: {e}")
        return False

def ensure_logged_in(page, fast_check=True):
    """
    Ensure the user is logged in to Farm to People.
    If not logged in, attempt to log in.
    
    Args:
        page: Playwright page object
        fast_check: bool, if True tries fast check first
        
    Returns:
        bool: True if logged in (or login successful), False otherwise
    """
    try:
        if fast_check:
            # Try fast session check first (under 3 seconds)
            fast_result = _fast_session_check(page)
            if fast_result is not None:
                return fast_result
            print("❓ Fast check inconclusive, falling back to comprehensive check...")
        
        return _comprehensive_session_check(page)
        
    except Exception as e:
        print(f"❌ Error checking login status: {e}")
        # Last resort: try login anyway
        return _retry_login(page)

def _fast_session_check(page):
    """Fast session check (under 3 seconds). Returns None if inconclusive."""
    try:
        print("⚡ Fast session check...")
        start_time = time.time()
        
        # Quick navigation with shorter timeout
        page.goto("https://farmtopeople.com/home", timeout=8000)
        page.wait_for_timeout(3000)  # Give session 3 seconds to load
        
        # Check for multiple session indicators (more robust)
        session_indicators = [
            ("a:has-text('Logout'), button:has-text('Logout')", "logout"),
            ("a:has-text('Account'), button:has-text('Account')", "account"),
            ("div.cart-button", "cart")
        ]
        
        for selector, indicator_name in session_indicators:
            elements = page.locator(selector).all()
            if len(elements) > 0:
                check_time = time.time() - start_time
                print(f"✅ Fast session confirmed via {indicator_name} in {check_time:.1f}s")
                return True
        
        # Check for login requirement indicators
        login_indicators = [
            "a:has-text('Log in'), button:has-text('Log in')",
            "a:has-text('Join'), button:has-text('Join')"
        ]
        
        login_required = False
        for selector in login_indicators:
            elements = page.locator(selector).all()
            if len(elements) > 0:
                login_required = True
                break
        
        check_time = time.time() - start_time
        
        if login_required:
            print(f"🔐 Login required (fast check: {check_time:.1f}s)")
            return _retry_login(page)
        else:
            # Inconclusive - need comprehensive check
            print(f"❓ Fast check inconclusive ({check_time:.1f}s)")
            return None
        
    except Exception as e:
        print(f"⚠️ Fast check failed: {e}")
        return None

def _comprehensive_session_check(page):
    """Comprehensive session check with full page load."""
    try:
        print("🔍 Comprehensive session check...")
        
        # Full page load with all resources
        page.goto("https://farmtopeople.com/home")
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(2000)  # Reduced from 4s
        
        print("🔍 Analyzing login status...")
        
        # Priority-ordered indicators (most reliable first)
        session_indicators = [
            ("a:has-text('Logout')", "logout_link"),
            ("button:has-text('Logout')", "logout_button"),
            ("a:has-text('Account')", "account_link"),
            ("button:has-text('Account')", "account_button"),
            ("div.cart-button", "cart_button")
        ]
        
        for selector, indicator_type in session_indicators:
            elements = page.locator(selector).all()
            if len(elements) > 0:
                print(f"✅ Session confirmed via {indicator_type}")
                return True
        
        # Check for login requirements
        login_indicators = [
            "button:has-text('Log in')",
            "a:has-text('Log in')",
            "button:has-text('Join')",
            "a:has-text('Join')"
        ]
        
        for indicator in login_indicators:
            elements = page.locator(indicator).all()
            if len(elements) > 0:
                print(f"🔐 Login required (found: {indicator})")
                return _retry_login(page)
        
        # If we reach here, assume logged in
        print("✅ Login status verified")
        return True
        
    except Exception as e:
        print(f"❌ Comprehensive check failed: {e}")
        return _retry_login(page)

def _retry_login(page, max_retries=3):
    """Login with retry logic and exponential backoff."""
    
    for attempt in range(max_retries):
        try:
            print(f"🔐 Login attempt {attempt + 1}/{max_retries}")
            
            # Add progressive delay with randomization
            if attempt > 0:
                delay = min(2 ** attempt + random.uniform(1, 3), 10)
                print(f"⏳ Waiting {delay:.1f}s before retry...")
                time.sleep(delay)
            
            # Clear any existing page state
            page.goto("about:blank")
            page.wait_for_timeout(1000)
            
            # Attempt login
            login_success = login_to_farm_to_people(page)
            
            if login_success:
                print(f"✅ Login successful on attempt {attempt + 1}")
                return True
            else:
                print(f"❌ Login failed on attempt {attempt + 1}")
                
        except Exception as e:
            print(f"❌ Login attempt {attempt + 1} error: {e}")
    
    print(f"🚨 All {max_retries} login attempts failed")
    return False
