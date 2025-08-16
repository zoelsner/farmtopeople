from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime

load_dotenv()

def better_capture_customize():
    output_dir = Path("farm_box_data")
    output_dir.mkdir(exist_ok=True)
    
    with sync_playwright() as p:
        user_data_dir = Path("browser_data")
        user_data_dir.mkdir(exist_ok=True)
        
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            viewport={"width": 1920, "height": 1080}
        )
        
        page = context.new_page()
        
        print("Opening Farm to People...")
        page.goto("https://farmtopeople.com/home")
        page.wait_for_timeout(3000)
        
        # Click cart button
        print("Opening cart...")
        cart_btn = page.locator("div.cart-button.ml-auto.cursor-pointer").first
        if cart_btn.count() > 0:
            cart_btn.click()
            page.wait_for_timeout(2000)
        
        print("Clicking CUSTOMIZE on the first box...")
        customize_btns = page.locator("button:has-text('CUSTOMIZE'), button:has-text('Customize')").all()
        
        if len(customize_btns) > 0:
            first_btn = customize_btns[0]
            first_btn.scroll_into_view_if_needed()
            page.wait_for_timeout(500)
            
            try:
                first_btn.click()
                print("CUSTOMIZE clicked! Waiting longer for modal to load...")
                page.wait_for_timeout(5000)  # Wait 5 seconds instead of 3
            except Exception as e:
                print(f"Regular click failed, trying JS click: {e}")
                first_btn.evaluate("element => element.click()")
                page.wait_for_timeout(5000)
        
        print("\n" + "="*60)
        print("Please wait for the customize interface to fully load...")
        print("Look for the interface with individual items and +/- buttons")
        print("="*60)
        
        input("\nPress ENTER when you see the full customize modal with all items...")
        
        # Take screenshot first
        screenshot_file = output_dir / f"better_capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        page.screenshot(path=str(screenshot_file))
        print(f"Screenshot saved: {screenshot_file}")
        
        # Save full page HTML
        html_file = output_dir / f"better_page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        page_html = page.content()
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(page_html)
        print(f"Full page HTML saved: {html_file}")
        
        # Try multiple selectors to find the modal
        modal_selectors = [
            # Most specific first
            "aside[aria-label*='Customize']",
            "div[class*='customize-farmbox']",
            "div[class*='customize']",
            "[role='dialog']",
            "[role='modal']",
            # Less specific
            "aside",
            "div[class*='modal']",
            "div[class*='overlay']"
        ]
        
        modal_found = False
        for i, selector in enumerate(modal_selectors):
            try:
                modal = page.locator(selector).first
                if modal.count() > 0 and modal.is_visible():
                    modal_file = output_dir / f"modal_{i}_{selector.replace('[', '').replace(']', '').replace('*=', '_').replace("'", '').replace(':', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                    modal_html = modal.inner_html()
                    with open(modal_file, 'w', encoding='utf-8') as f:
                        f.write(modal_html)
                    print(f"Modal HTML saved: {modal_file}")
                    
                    # Print preview
                    modal_text = modal.text_content()[:500]
                    print(f"\nModal preview (selector: {selector}):")
                    print(modal_text)
                    print("="*50)
                    
                    modal_found = True
            except Exception as e:
                print(f"Error with selector {selector}: {e}")
        
        if not modal_found:
            print("No modal found with any selector!")
        
        print(f"\n=== CAPTURE COMPLETE ===")
        input("Press ENTER to close...")
        context.close()

if __name__ == "__main__":
    better_capture_customize()
