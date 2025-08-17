from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import json
import re
import sys
sys.path.append(os.path.dirname(__file__))
from auth_helper import ensure_logged_in, login_to_farm_to_people

# Load .env from project root
project_root = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=project_root / '.env', override=True)

def scrape_customize_modal(page):
    """Scrape both selected and available items from the customize modal."""
    
    # Wait for the customize modal to be fully loaded
    page.wait_for_selector("aside[aria-label*='Customize']", timeout=10000)
    
    # Find the customize modal container
    modal = page.locator("aside[aria-label*='Customize']").first
    
    # Get all articles (individual items)
    articles = modal.locator("article[aria-label]").all()
    
    selected_items = []
    available_alternatives = []
    
    print(f"Found {len(articles)} total items in customize modal")
    
    for article in articles:
        try:
            # Get item name from aria-label
            item_name = article.get_attribute("aria-label")
            
            # Get producer info
            producer_elem = article.locator("p[class*='producer'] a").first
            producer = ""
            if producer_elem.count() > 0:
                producer = producer_elem.text_content().strip()
            
            # Get unit/details info
            details_elem = article.locator("div[class*='item-details'] p").first
            unit_info = ""
            if details_elem.count() > 0:
                unit_info = details_elem.text_content().strip()
            
            # Check if item is selected (has quantity selector) or available (has Add button)
            quantity_selector = article.locator("div[class*='quantity-selector']").first
            add_button = article.locator("button:has-text('Add')").first
            
            if quantity_selector.count() > 0:
                # This is a selected item - get the quantity
                quantity_span = quantity_selector.locator("span[class*='quantity']").first
                quantity = 1
                if quantity_span.count() > 0:
                    try:
                        quantity = int(quantity_span.text_content().strip())
                    except:
                        quantity = 1
                
                selected_items.append({
                    "name": item_name,
                    "producer": producer,
                    "unit": unit_info,
                    "quantity": quantity,
                    "selected": True
                })
                print(f"  ✅ Selected: {item_name} (qty: {quantity}) - {unit_info}")
                
            elif add_button.count() > 0:
                # This is an available alternative
                available_alternatives.append({
                    "name": item_name,
                    "producer": producer,
                    "unit": unit_info,
                    "quantity": 0,
                    "selected": False
                })
                print(f"  🔄 Available: {item_name} - {unit_info}")
                
        except Exception as e:
            print(f"  ❌ Error processing article: {e}")
            continue
    
    return {
        "selected_items": selected_items,
        "available_alternatives": available_alternatives,
        "total_items": len(articles),
        "selected_count": len(selected_items),
        "alternatives_count": len(available_alternatives)
    }

def main():
    output_dir = Path("../farm_box_data")
    output_dir.mkdir(exist_ok=True)
    
    with sync_playwright() as p:
        # Always use fresh browser session for multi-user support
        print("🌐 Starting fresh browser session...")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1920, "height": 1080})
        
        page = context.new_page()

        # Navigate to home where header/cart lives
        page.goto("https://farmtopeople.com/home")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(2000)  # Give page time to settle

        # Check if we're on a login page or if login elements are visible
        current_url = page.url
        login_form_visible = page.locator("input[placeholder='Enter email address']").count() > 0
        
        # Also check if we see a "Log in" link/button which indicates we're not logged in
        login_link_visible = page.locator("a:has-text('Log in'), button:has-text('Log in')").count() > 0
        
        if "login" in current_url or login_form_visible or login_link_visible:
            print("🔐 Login page detected. Performing login...")
            
            # Get credentials - try both variable names
            email = os.getenv("EMAIL") or os.getenv("FTP_EMAIL")
            password = os.getenv("PASSWORD") or os.getenv("FTP_PWD")
            
            if not email or not password:
                print("❌ No credentials found in environment (EMAIL/PASSWORD)")
                print("   Looking in .env at:", project_root / '.env')
                context.close()
                return
                
            try:
                # Fill email
                email_input = page.locator("input[placeholder='Enter email address']").first
                if email_input.count() > 0:
                    email_input.fill(email)
                    print(f"✅ Email entered: {email}")
                    
                    # Click LOG IN to proceed to password
                    login_btn = page.locator("button:has-text('LOG IN')").first
                    if login_btn.count() > 0:
                        login_btn.click()
                        page.wait_for_timeout(2000)
                        
                        # Now fill password
                        password_input = page.locator("input[type='password']").first
                        if password_input.count() > 0:
                            password_input.fill(password)
                            print("✅ Password entered")
                            
                            # Click LOG IN again
                            final_login_btn = page.locator("button:has-text('LOG IN')").first
                            if final_login_btn.count() > 0:
                                final_login_btn.click()
                                print("✅ Login submitted, waiting for navigation...")
                                page.wait_for_timeout(5000)
                                
                                # Verify we're logged in
                                if "login" not in page.url:
                                    print("✅ Login successful!")
                                else:
                                    print("⚠️ Still on login page, may have failed")
                            
            except Exception as e:
                print(f"❌ Login error: {e}")
        else:
            # Not on login page, use the auth helper to verify session
            print("🔐 Checking session status...")
            ensure_logged_in(page)
        
        # The scraper can now proceed assuming it's logged in.
        print("Opening cart...")
        
        # Prefer a cart button that isn’t inside any dialog
        cart_btn = page.locator("body > div:not([role='dialog']) >> div.cart-button.ml-auto.cursor-pointer").first
        
        if cart_btn.is_visible():
            print("✅ Cart button is visible and not in a modal. Clicking it.")
            cart_btn.click()
            page.wait_for_timeout(3000) # Wait for cart to open
        else:
            print("❌ Cart button not found or not visible. Trying direct navigation.")
            page.goto("https://farmtopeople.com/cart")
            page.wait_for_timeout(3000)

        # Get all CUSTOMIZE buttons
        customize_btns = page.locator("button:has-text('CUSTOMIZE'), button:has-text('Customize')").all()
        
        all_box_data = []
        
        for i, customize_btn in enumerate(customize_btns):
            try:
                # Get box name from the parent article
                article = customize_btn.locator("xpath=ancestor::article").first
                box_name = "Unknown Box"
                if article.count() > 0:
                    name_link = article.locator("a[href*='/product/']").first
                    if name_link.count() > 0:
                        box_name = name_link.text_content().strip()
                
                print(f"\n=== PROCESSING BOX {i+1}: {box_name} ===")
                
                # Scroll button into view and click
                customize_btn.scroll_into_view_if_needed()
                page.wait_for_timeout(500)
                
                print(f"Clicking CUSTOMIZE...")
                try:
                    customize_btn.click()
                    page.wait_for_timeout(3000)
                except Exception as e:
                    print(f"Regular click failed, trying JS: {e}")
                    customize_btn.evaluate("element => element.click()")
                    page.wait_for_timeout(3000)
                
                # Scrape the customize modal
                box_data = scrape_customize_modal(page)
                box_data["box_name"] = box_name
                box_data["box_index"] = i + 1
                
                all_box_data.append(box_data)
                
                print(f"\n📊 RESULTS for {box_name}:")
                print(f"  • {box_data['selected_count']} selected items")
                print(f"  • {box_data['alternatives_count']} available alternatives")
                print(f"  • {box_data['total_items']} total items")
                
                # Close the modal (look for Close button)
                close_btn = page.locator("button:has-text('Close')").first
                if close_btn.count() > 0:
                    close_btn.click()
                    page.wait_for_timeout(1000)
                else:
                    # Try ESC key
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(1000)
                
            except Exception as e:
                print(f"❌ Error processing box {i+1}: {e}")
                continue
        
        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_dir / f"customize_results_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(all_box_data, f, indent=2)
        
        print(f"\n🎉 COMPLETE! Results saved to: {output_file}")
        print(f"\n📈 SUMMARY:")
        for box_data in all_box_data:
            print(f"  {box_data['box_name']}:")
            print(f"    ✅ {box_data['selected_count']} selected")
            print(f"    🔄 {box_data['alternatives_count']} alternatives")
        
        context.close()
        browser.close()

if __name__ == "__main__":
    main()
