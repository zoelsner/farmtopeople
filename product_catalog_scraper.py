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
    
    # Categories to scrape (based on current site structure)
    categories = {
        "produce": "https://farmtopeople.com/shop/produce",
        "meat-seafood": "https://farmtopeople.com/shop/meat-seafood", 
        "dairy-eggs": "https://farmtopeople.com/shop/dairy-eggs",
        "pantry": "https://farmtopeople.com/shop/pantry"
    }
    
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
        
        for category_name, category_url in categories.items():
            print(f"\n🔍 SCRAPING CATEGORY: {category_name.upper()}")
            print(f"🌐 URL: {category_url}")
            
            try:
                page.goto(category_url)
                page.wait_for_timeout(3000)  # Wait for page load
                
                # Take screenshot for debugging
                screenshot_file = output_dir / f"category_{category_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                page.screenshot(path=str(screenshot_file))
                print(f"📸 Screenshot saved: {screenshot_file}")
                
                # Scroll to load all products (many sites use lazy loading)
                print("📜 Scrolling to load all products...")
                page.evaluate("""
                    () => {
                        return new Promise((resolve) => {
                            var totalHeight = 0;
                            var distance = 100;
                            var timer = setInterval(() => {
                                var scrollHeight = document.body.scrollHeight;
                                window.scrollBy(0, distance);
                                totalHeight += distance;
                                
                                if(totalHeight >= scrollHeight){
                                    clearInterval(timer);
                                    resolve();
                                }
                            }, 100);
                        })
                    }
                """)
                
                page.wait_for_timeout(2000)  # Wait for lazy loading
                
                # Look for product containers (these selectors may need adjustment)
                product_selectors = [
                    "article[class*='product']",
                    "div[class*='product-item']", 
                    "div[class*='product-card']",
                    ".product-grid .grid__item",
                    "[data-product-id]"
                ]
                
                products_found = []
                for selector in product_selectors:
                    products = page.locator(selector).all()
                    if len(products) > 0:
                        print(f"✅ Found {len(products)} products using selector: {selector}")
                        products_found = products
                        break
                
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
                    try:
                        # Extract product information (selectors may need adjustment)
                        name_elem = product.locator("h3, h4, .product-title, [class*='product-name'], a[href*='/product/']").first
                        name = name_elem.text_content().strip() if name_elem.count() > 0 else "Unknown Product"
                        
                        # Price extraction
                        price_elem = product.locator(".price, [class*='price'], [data-price]").first
                        price = price_elem.text_content().strip() if price_elem.count() > 0 else "Price not found"
                        
                        # Vendor/Producer extraction
                        vendor_elem = product.locator(".vendor, [class*='vendor'], [class*='producer'], .brand").first
                        vendor = vendor_elem.text_content().strip() if vendor_elem.count() > 0 else "Unknown Vendor"
                        
                        # Product URL
                        link_elem = product.locator("a[href*='/product/']").first
                        product_url = link_elem.get_attribute("href") if link_elem.count() > 0 else ""
                        if product_url and not product_url.startswith("http"):
                            product_url = f"https://farmtopeople.com{product_url}"
                        
                        # Check if sold out
                        sold_out_indicators = product.locator(".sold-out, [class*='sold-out'], .unavailable").all()
                        is_sold_out = len(sold_out_indicators) > 0
                        
                        # Clean up extracted data
                        name = re.sub(r'\s+', ' ', name)
                        price = re.sub(r'\s+', ' ', price)
                        vendor = re.sub(r'\s+', ' ', vendor)
                        
                        product_data = {
                            "name": name,
                            "category": category_name,
                            "vendor": vendor,
                            "price": price,
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
            fieldnames = ["name", "category", "vendor", "price", "product_url", "is_sold_out", "scraped_at"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(all_products)
    
    # Update the main products file
    main_csv_file = Path("farmtopeople_products.csv")
    with open(main_csv_file, 'w', newline='', encoding='utf-8') as f:
        if all_products:
            fieldnames = ["name", "category", "vendor", "price", "product_url", "is_sold_out", "scraped_at"]
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
