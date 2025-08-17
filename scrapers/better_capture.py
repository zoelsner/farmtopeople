from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scrapers.auth_helper import login_to_farm_to_people

load_dotenv()

def capture_fresh_login_attempt():
    output_dir = Path("debug_captures")
    output_dir.mkdir(exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )
        
        page = context.new_page()
        
        print(" S T E P  1 :  P E R F O R M I N G  A  F R E S H  L O G I N ")
        print("="*60)
        # We call the login function directly. We expect to see it print its progress.
        login_successful = login_to_farm_to_people(page)
        print("="*60)

        if not login_successful:
            print("❌ LOGIN FAILED. The browser will remain open for inspection.")
            print("A screenshot named 'debug_login_failure.png' should be in the root directory.")
        else:
            print("✅ LOGIN SUCCEEDED. The page should now be showing the home page as a logged-in user.")
            print("The zip code modal may be visible. This is expected.")

        print("\n" + "="*60)
        print(" S T E P  2 :  C A P T U R I N G  P A G E  S T A T E")
        print("The script will now capture the page. Please do not interact with the browser.")
        print("="*60)
        
        # Wait for the page to settle after the login attempt
        page.wait_for_timeout(3000)
        
        # --- Capture everything ---
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 1. Save Screenshot
        screenshot_file = output_dir / f"fresh_login_screenshot_{timestamp}.png"
        page.screenshot(path=str(screenshot_file))
        print(f"\n📸 Screenshot saved: {screenshot_file}")

        # 2. Save Full Page HTML
        html_file = output_dir / f"fresh_login_page_{timestamp}.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(page.content())
        print(f"📄 Full page HTML saved: {html_file}")
        
        print("\n" + "="*60)
        print("🕵️  ANALYSIS COMPLETE")
        print("Please check the files in the 'debug_captures' directory.")
        print("The screenshot is the most important piece of evidence.")
        print("="*60)
        
        print("Capture complete. Closing browser.")
        context.close()
        browser.close()


if __name__ == "__main__":
    capture_fresh_login_attempt()
