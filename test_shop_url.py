from playwright.sync_api import sync_playwright
from pathlib import Path
from datetime import datetime

def test_shop_url():
    """Quick test to see what's on the shop/produce page"""
    with sync_playwright() as p:
        # Use a new browser context to avoid conflicts
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        print("🌐 Navigating to https://farmtopeople.com/shop/produce")
        page.goto("https://farmtopeople.com/shop/produce")
        page.wait_for_timeout(5000)  # Wait 5 seconds for page to load
        
        # Take screenshot
        screenshot_file = Path("farm_box_data") / f"test_shop_produce_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        page.screenshot(path=str(screenshot_file))
        print(f"📸 Screenshot saved: {screenshot_file}")
        
        # Check page title
        title = page.title()
        print(f"📄 Page title: {title}")
        
        # Check for common product selectors
        selectors_to_try = [
            "div[data-testid*='product']",
            "article",
            "div[class*='product']",
            ".product-card",
            "[data-product]",
            "div[class*='grid'] > div",
            "ul > li",
            "main div > div"
        ]
        
        for selector in selectors_to_try:
            elements = page.locator(selector).all()
            if len(elements) > 0:
                print(f"✅ Found {len(elements)} elements with selector: {selector}")
                # Get text from first few elements
                for i, elem in enumerate(elements[:3]):
                    text = elem.text_content()
                    if text and len(text.strip()) > 0:
                        print(f"  Element {i+1}: {text[:100]}...")
            else:
                print(f"❌ No elements found for: {selector}")
        
        print("\n🔍 Let me check if this is a dynamic page...")
        # Wait for any dynamic content
        page.wait_for_timeout(3000)
        
        # Check if there's a "loading" state
        loading_elements = page.locator("div[class*='loading'], div[class*='spinner'], .loader").all()
        if len(loading_elements) > 0:
            print("⏳ Found loading indicators, waiting longer...")
            page.wait_for_timeout(5000)
        
        # Try one more time with different selectors
        print("\n🔄 Trying again after waiting...")
        all_text = page.locator("body").text_content()
        if "produce" in all_text.lower() or "product" in all_text.lower():
            print("✅ Page contains produce/product related text")
        else:
            print("⚠️ Page doesn't seem to contain product information")
        
        print("\nPress ENTER to close browser...")
        input()
        
        browser.close()

if __name__ == "__main__":
    test_shop_url()
