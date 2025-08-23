from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import json
import csv
import re
import time

load_dotenv()

def scrape_farm_to_people_catalog():
    """
    Comprehensive product catalog scraper for Farm to People.
    Scrapes all categories: produce, meat-seafood, dairy-eggs, pantry
    """
    output_dir = Path("farm_box_data")
    output_dir.mkdir(exist_ok=True)
    
    # Categories to scrape - full catalog
    categories = {
        "produce": "https://farmtopeople.com/shop/produce",
        "meat-seafood": "https://farmtopeople.com/shop/meat-seafood",
        "dairy-eggs": "https://farmtopeople.com/shop/dairy-eggs", 
        "pantry": "https://farmtopeople.com/shop/pantry"
    }
    
    # No limit - full scrape
    MAX_PRODUCTS_PER_CATEGORY = None
    
    all_products = []
    
    with sync_playwright() as p:
        user_data_dir = Path("browser_data")
        user_data_dir.mkdir(exist_ok=True)
        
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            viewport={"width": 1920, "height": 1080}
        )
        
        page = context.new_page()
        
        print("🌱 Starting Farm to People Product Catalog Scraper...")
        print(f"📅 Scraping date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 Categories to scrape: {len(categories)}")
        
        # Check if login is required by visiting main site first
        print("🔐 Checking authentication status...")
        try:
            page.goto("https://farmtopeople.com", timeout=30000)
            page.wait_for_timeout(3000)
            
            # Check if we need to login
            if "login" in page.url.lower() or page.locator("input[type='email']").count() > 0:
                print("⚠️ Login required - shop pages may not be accessible without authentication")
            else:
                print("✅ Site accessible without login")
        except Exception as e:
            print(f"⚠️ Could not check main site: {e}")
        
        for category_name, category_url in categories.items():
            print(f"\n🔍 SCRAPING CATEGORY: {category_name.upper()}")
            print(f"🌐 URL: {category_url}")
            
            try:
                print(f"🌐 Navigating to {category_url}...")
                page.goto(category_url, timeout=60000)  # Increased timeout
                page.wait_for_timeout(5000)  # Longer wait for page load
                
                # Check if page loaded correctly
                page_title = page.title()
                print(f"📄 Page title: {page_title}")
                
                # Take screenshot for debugging
                screenshot_file = output_dir / f"category_{category_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                page.screenshot(path=str(screenshot_file))
                print(f"📸 Screenshot saved: {screenshot_file}")
                
                # Wait for main content to load
                try:
                    page.wait_for_selector("main, .main-content, [role='main']", timeout=10000)
                except:
                    print("⚠️ Main content selector not found, proceeding anyway...")
                
                # Scroll to load all products (many sites use lazy loading)
                print("📜 Scrolling to load all products...")
                page.evaluate("""
                    () => {
                        return new Promise((resolve) => {
                            var totalHeight = 0;
                            var distance = 150;
                            var timer = setInterval(() => {
                                var scrollHeight = document.body.scrollHeight;
                                window.scrollBy(0, distance);
                                totalHeight += distance;
                                
                                if(totalHeight >= scrollHeight){
                                    clearInterval(timer);
                                    resolve();
                                }
                            }, 200);  // Slower scrolling
                        })
                    }
                """)
                
                page.wait_for_timeout(5000)  # Longer wait for lazy loading
                
                # Look for product containers with more comprehensive selectors
                product_selectors = [
                    "article[class*='product']",
                    "div[class*='product-item']", 
                    "div[class*='product-card']",
                    ".product-grid .grid__item",
                    "[data-product-id]",
                    ".product-list article",
                    ".grid article",
                    "article",  # Fallback to any article
                    "div[class*='item'][class*='grid']",
                    ".collection article"
                ]
                
                products_found = []
                for selector in product_selectors:
                    products = page.locator(selector).all()
                    if len(products) > 0:
                        print(f"✅ Found {len(products)} products using selector: {selector}")
                        products_found = products
                        break
                
                # If still no products, try a more general approach
                if not products_found:
                    print("🔍 Trying general link-based detection...")
                    product_links = page.locator("a[href*='/product/']").all()
                    if len(product_links) > 0:
                        print(f"✅ Found {len(product_links)} product links")
                        products_found = product_links
                
                if not products_found:
                    print(f"⚠️ No products found for {category_name}. May need to update selectors.")
                    # Save HTML for debugging
                    html_file = output_dir / f"category_{category_name}_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                    with open(html_file, 'w', encoding='utf-8') as f:
                        f.write(page.content())
                    print(f"🛠️ Debug HTML saved: {html_file}")
                    continue
                
                category_products = []
                
                for i, product in enumerate(products_found):
                    # Check if we have a limit and stop if reached
                    if MAX_PRODUCTS_PER_CATEGORY and len(category_products) >= MAX_PRODUCTS_PER_CATEGORY:
                        print(f"⏹️ Reached limit of {MAX_PRODUCTS_PER_CATEGORY} products for {category_name}")
                        break
                        
                    try:
                        # Extract product information with Farm to People specific selectors
                        name_selectors = [
                            ".product-tile_product-name__yMGzm",  # Specific FTP class
                            ".product-name",                      # Generic product name class
                            "a.product-tile_product-name__yMGzm", # Link with specific class
                            "[class*='product-name']",            # Fallback for product name
                            "a[class*='product-name']",           # Product name links
                            ".product-title",                     # Generic title
                            "h3, h4"                             # Header fallbacks
                        ]
                        
                        name = "Unknown Product"
                        for name_selector in name_selectors:
                            name_elem = product.locator(name_selector).first
                            if name_elem.count() > 0:
                                name = name_elem.text_content().strip()
                                if name and name != "":
                                    break
                        
                        # Price extraction with Farm to People specific selectors
                        price_selectors = [
                            "[aria-label='unit price']",             # Specific FTP price selector
                            "span[aria-label='unit price']",         # More specific span with aria-label
                            ".price",                                # Generic price class
                            "[class*='price']",                      # Any class containing 'price'
                            "[data-price]",                          # Data attribute
                            "span:has-text('$')",                    # Any span containing $
                            ".cost, .amount"                        # Fallback cost/amount
                        ]
                        
                        price = "Price not found"
                        for price_selector in price_selectors:
                            price_elem = product.locator(price_selector).first
                            if price_elem.count() > 0:
                                price = price_elem.text_content().strip()
                                if price and "$" in price:
                                    break
                        
                        # Extract weight/unit information
                        unit_selectors = [
                            "p.weight",                              # Specific weight class from example
                            ".weight",                               # Generic weight class
                            "[class*='weight']",                     # Any class containing weight
                            "[class*='unit']",                       # Unit classes
                            "p:has-text('Lbs'), p:has-text('oz')",   # Paragraphs with weight units
                            ".unit, .size"                          # Generic unit/size classes
                        ]
                        
                        unit = ""
                        for unit_selector in unit_selectors:
                            unit_elem = product.locator(unit_selector).first
                            if unit_elem.count() > 0:
                                unit = unit_elem.text_content().strip()
                                if unit and unit != "":
                                    break
                        
                        # Vendor/Producer extraction with Farm to People specific selectors
                        vendor_selectors = [
                            ".name-and-producer .producer",         # Specific FTP producer in name-and-producer section
                            ".product-tile_name-and-producer__9lSea .producer", # More specific FTP selector
                            "[class*='producer']",                   # Any class containing producer
                            ".vendor",                              # Generic vendor class
                            "[class*='vendor']",                    # Any class containing vendor
                            ".brand, .farm, .supplier"             # Other supplier-related classes
                        ]
                        
                        vendor = "Unknown Vendor"
                        for vendor_selector in vendor_selectors:
                            vendor_elem = product.locator(vendor_selector).first
                            if vendor_elem.count() > 0:
                                vendor = vendor_elem.text_content().strip()
                                if vendor and vendor != "":
                                    break
                        
                        # Product URL
                        link_elem = product.locator("a[href*='/product/']").first
                        product_url = link_elem.get_attribute("href") if link_elem.count() > 0 else ""
                        if product_url and not product_url.startswith("http"):
                            product_url = f"https://farmtopeople.com{product_url}"
                        
                        # Check if sold out
                        sold_out_indicators = product.locator(".sold-out, [class*='sold-out'], .unavailable, [class*='out-of-stock']").all()
                        is_sold_out = len(sold_out_indicators) > 0
                        
                        # Enhanced data cleaning
                        name = re.sub(r'\s+', ' ', name).strip()
                        # Only clean if name is empty after basic cleaning
                        if not name or name == "":
                            name = "Unknown Product"
                        
                        # Clean price - handle multiple prices like "$7.64$8.99"
                        price = re.sub(r'\s+', ' ', price).strip()
                        # Extract first price if multiple prices found
                        price_match = re.search(r'\$[\d,]+\.?\d*', price)
                        if price_match:
                            price = price_match.group()
                        
                        # Clean vendor names - fix concatenated vendor+product issue
                        vendor = re.sub(r'\s+', ' ', vendor).strip()
                        
                        # The vendor selector captures "VendorNameVendorNameProductName" pattern
                        # We need to extract just the vendor name
                        if vendor and name != "Unknown Product":
                            # Method 1: Remove the product name from the end if it appears there
                            if name in vendor:
                                # Remove the product name from the vendor string
                                vendor = vendor.replace(name, '').strip()
                            
                            # Method 2: Handle duplicated vendor patterns like "Sun Sprout FarmSun Sprout Farm"
                            # Check for exact duplication (vendor repeated twice)
                            if len(vendor) > 10:  # Only process reasonably long strings
                                # Try different split points to find duplication
                                for split_point in range(len(vendor) // 3, (len(vendor) * 2) // 3):
                                    potential_vendor = vendor[:split_point]
                                    remaining = vendor[split_point:]
                                    
                                    # Check if the remaining part starts with the same vendor name
                                    if remaining.startswith(potential_vendor):
                                        vendor = potential_vendor
                                        break
                        
                        if not vendor or vendor == "":
                            vendor = "Unknown Vendor"
                        
                        # Clean unit information
                        unit = re.sub(r'\s+', ' ', unit).strip()
                        
                        product_data = {
                            "name": name,
                            "category": category_name,
                            "vendor": vendor,
                            "price": price,
                            "unit": unit,
                            "product_url": product_url,
                            "is_sold_out": is_sold_out,
                            "scraped_at": datetime.now().isoformat()
                        }
                        
                        category_products.append(product_data)
                        all_products.append(product_data)
                        
                        print(f"  📦 {i+1:3d}. {name[:50]:<50} | {price:<10} | {vendor[:20]:<20}")
                        
                    except Exception as e:
                        print(f"  ❌ Error processing product {i+1}: {e}")
                        continue
                
                print(f"✅ {category_name}: {len(category_products)} products scraped")
                
            except Exception as e:
                print(f"❌ Error scraping category {category_name}: {e}")
                print(f"⏭️ Continuing with next category...")
                
                # Still save a screenshot for debugging
                try:
                    error_screenshot = output_dir / f"error_{category_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    page.screenshot(path=str(error_screenshot))
                    print(f"📸 Error screenshot saved: {error_screenshot}")
                except:
                    pass
                
                continue
        
        context.close()
    
    # Save results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Save as JSON
    json_file = output_dir / f"product_catalog_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(all_products, f, indent=2, ensure_ascii=False)
    
    # Save as CSV (compatible with existing format)
    csv_file = output_dir / f"farmtopeople_products_{timestamp}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        if all_products:
            fieldnames = ["name", "category", "vendor", "price", "unit", "product_url", "is_sold_out", "scraped_at"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_products)
    
    # Update the main products file
    main_csv_file = Path("../data/farmtopeople_products.csv")
    with open(main_csv_file, 'w', newline='', encoding='utf-8') as f:
        if all_products:
            fieldnames = ["name", "category", "vendor", "price", "unit", "product_url", "is_sold_out", "scraped_at"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_products)
    
    # Print summary
    print(f"\n🎉 SCRAPING COMPLETE!")
    print(f"📊 Total products scraped: {len(all_products)}")
    print(f"📁 Files saved:")
    print(f"   • JSON: {json_file}")
    print(f"   • CSV: {csv_file}")
    print(f"   • Updated main file: {main_csv_file}")
    
    # Category breakdown
    print(f"\n📈 Products by category:")
    category_counts = {}
    for product in all_products:
        cat = product['category']
        category_counts[cat] = category_counts.get(cat, 0) + 1
    
    for cat, count in sorted(category_counts.items()):
        print(f"   • {cat}: {count} products")
    
    return all_products

if __name__ == "__main__":
    scrape_farm_to_people_catalog()
