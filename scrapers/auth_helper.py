"""
Authentication helper for Farm to People scrapers.
Handles login functionality for all scrapers.
"""

import os
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
        page.wait_for_timeout(2000)
        
        # Based on the actual page, look for email input with placeholder "Email address"
        email_input = page.locator("input[placeholder='Email address']").first
        
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

def ensure_logged_in(page):
    """
    Ensure the user is logged in to Farm to People.
    If not logged in, attempt to log in.
    
    Args:
        page: Playwright page object
        
    Returns:
        bool: True if logged in (or login successful), False otherwise
    """
    try:
        print("🔍 Checking existing login status...")
        
        # First, go to the homepage and wait longer for session to load
        page.goto("https://farmtopeople.com/home")
        print("⏳ Waiting for page and session to fully load...")
        
        # Wait for page to be fully loaded including network requests
        page.wait_for_load_state("networkidle", timeout=15000)
        
        # Additional wait for session restoration and dynamic content
        page.wait_for_timeout(4000)
        
        print("🔍 Analyzing login status...")
        
        # Check for positive logged-in indicators first (more reliable)
        logged_in_indicators = [
            "button:has-text('Account')",
            "a:has-text('Account')",
            "div[class*='user-menu']",
            "button:has-text('Logout')",
            "a:has-text('Logout')",
            "[data-testid*='account']",
            "[aria-label*='account' i]"
        ]
        
        for indicator in logged_in_indicators:
            elements = page.locator(indicator).all()
            if len(elements) > 0:
                print(f"✅ Already logged in (found: {indicator})")
                return True
        
        # If no positive indicators, check for login requirement indicators
        login_required_indicators = [
            "button:has-text('Log in')",
            "a:has-text('Log in')",
            "button:has-text('Join')",
            "a:has-text('Join')"
        ]
        
        login_required = False
        for indicator in login_required_indicators:
            elements = page.locator(indicator).all()
            if len(elements) > 0:
                print(f"🔐 Login required (found: {indicator})")
                login_required = True
                break
        
        # Final check: try to access cart (requires login)
        if not login_required:
            print("🛒 Testing cart access to verify login status...")
            cart_btn = page.locator("div.cart-button, button[class*='cart'], a[class*='cart']").first
            
            if cart_btn.count() > 0:
                print("✅ Cart button found - likely logged in")
                return True
            else:
                print("⚠️ No cart button found - assuming login required")
                login_required = True
        
        # If login is required, attempt login
        if login_required:
            print("🔐 Not logged in, attempting to log in...")
            return login_to_farm_to_people(page)
        else:
            # If we reach here, assume logged in
            print("✅ Login status verified")
            return True
        
    except Exception as e:
        print(f"❌ Error checking login status: {e}")
        return False
