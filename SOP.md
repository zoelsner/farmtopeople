# Farm to People AI Assistant - Standard Operating Procedure (SOP v3)

_Last Updated: August 16, 2025_

## 🎉 **MAJOR UPDATE - August 16, 2025**
**SCRAPING SYSTEM OVERHAUL COMPLETE:**
- ✅ **Cleaned codebase**: Removed 5 deprecated scrapers (`farmbox_optimizer.py`, `capture_*.py`, `full_scraper.py`, `cart_structure_analyzer.py`)
- ✅ **Production ready**: All working scrapers tested and documented
- ✅ **Git organized**: Created `stable-scrapers` backup branch and `feature/customer-automation` for next phase
- ✅ **Comprehensive docs**: Created complete technical guides and audit documentation
- 🚀 **Ready for Phase 2**: Customer automation (texting, meal suggestions)

## 1. Core Product Vision: "The Thursday Afternoon Magic"

The primary goal of this project is to transform the Farm to People weekly box experience. We will turn the moment of "what do I do with these ingredients?" into an exciting, engaging culinary journey that begins on Thursday afternoon, two days before the box even arrives. Our core strategy is **Reverse Meal Planning**: we start with the user's actual, confirmed box contents and build a personalized, beautiful, and actionable plan around them.

## 2. Technical Architecture & Project Structure

The application is being refactored into a professional, scalable structure to support our long-term vision of a multi-platform service (SMS, Web App, iOS App).

### Current Project Structure:
```
farmtopeople/
├── server.py                          # FastAPI main server
├── meal_planner.py                     # OpenAI recipe generation
├── supabase_client.py                  # User data & preferences
├── complete_cart_scraper.py            # PRIMARY SCRAPER (recommended)
├── weekly_summary_scraper.py           # Customer summary generator
├── customize_scraper.py                # Full customize interface scraper
├── simple_scraper.py                   # Basic cart scraper
├── better_capture.py                   # HTML debugging tool
├── farmbox_optimizer.py                # DEPRECATED - use complete_cart_scraper.py
├── FARM_TO_PEOPLE_SCRAPER_GUIDE.md     # Complete scraping documentation
├── SOP.md                              # This file
└── farm_box_data/                      # Output directory
```

## 3. The "Thursday Magic" User Flow

This is the primary operational flow of the application.

1.  **Thursday 2 PM (Box Lock):** The user's Farm to People box for the upcoming weekend delivery is locked and can no longer be customized.
2.  **Thursday 3 PM (Automated Scrape):** The system automatically triggers the `complete_cart_scraper.py` script for all active users. The scraper logs in, scrapes the final, confirmed contents of each user's boxes and individual items, and saves this data to our Supabase database.
3.  **Thursday 3:05 PM (The Teaser SMS):** Immediately after the scrape, the system sends the first SMS to the user via Twilio.
    *   **Example:** _"🌟 Zach, your Farm to People box is locked in! This week's stars include White Peaches and Organic Green Kale. How's your energy for the week? Reply: 1=Tired 😴, 2=Normal 😊, 3=Ambitious 🚀"_
4.  **Thursday 6 PM (The Plan Delivery):** Based on the user's energy level response, the system sends the main event: a link to a beautifully generated PDF meal plan.
    *   **Example:** _"🍽️ Your adventures await! Based on your 'Normal' energy, your personalized meal plan is ready. It includes a 35-min version of our Peach and Kale Salad. View your full visual guide here: [link-to-pdf]"_
5.  **Weekend (Engagement & Learning):** The system can send follow-up tips and gather feedback on the meals.

## 4. Current State vs. Next Steps

We have successfully built the foundational components for this vision. Now, we will execute a planned refactor to align our existing code with this new architecture.

### **Current State:**
*   ✅ We have a comprehensive scraping system with multiple specialized scrapers.
*   ✅ We have a powerful AI meal planner (`meal_planner.py`).
*   ✅ We have a prototype server (`server.py`) and Supabase connection (`supabase_client.py`).
*   ✅ We have customer-friendly weekly summary generation.

### **Next Steps (The Refactor):**

1.  **Restructure the Project:** Create the new `backend/` sub-directory structure and move the existing `.py` files into their new, logical homes.
2.  **Create the Box Monitor:** Build the `box_monitor.py` script with a scheduler (like `schedule`) to trigger the scraper.
3.  **Integrate Scraper for Automation:** Modify `complete_cart_scraper.py` to run "headless" and be importable as a module, so it can be called by the monitor.
4.  **Integrate the Full SMS Flow:** Upgrade `server.py` to handle the multi-step "Thursday Magic" conversation, including the energy level reply and sending the final plan.

This refactoring process will be our primary focus to transition from a successful prototype to the foundation of a real, scalable product.

## 5. Current Scraping System Architecture

### Core Scraping Logic (STABLE - Reference Implementation)

The scraping system uses **Playwright** with persistent browser sessions and follows this established workflow:

#### **Step 1: Cart Access**
```python
# Open Farm to People website
page.goto("https://farmtopeople.com/home")

# Click cart button to open cart sidebar
cart_btn = page.locator("div.cart-button.ml-auto.cursor-pointer").first
cart_btn.click()
```

#### **Step 2: Cart Item Detection**
```python
# Get all cart items (both boxes and individual items)
articles = page.locator("article[class*='cart-order_cartOrderItem']").all()

# Differentiate between item types:
# - Boxes: Have sub-product lists (ul[class*='cart-order-line-item-subproducts'])
# - Individual items: Have quantity selectors (div[class*='quantity-selector'])
```

#### **Step 3: Box Content Extraction**
```python
# For boxes with sub-items:
sub_list = article.locator("+ ul[class*='cart-order-line-item-subproducts']").first
sub_items = sub_list.locator("li[class*='cart-order-line-item-subproduct']").all()

# Extract from each sub-item:
# - Name: a[class*='subproduct-name']
# - Quantity: Parsed from name text (e.g. "1 Sugar Cube Cantaloupe")
# - Unit: p element containing size/weight info
```

#### **Step 4: Customize Interface Access (Optional)**
```python
# For customizable boxes, click CUSTOMIZE to get alternatives:
customize_btn = article.locator("button:has-text('CUSTOMIZE')").first
customize_btn.click()

# Wait for modal: aside[aria-label*='Customize']
# Selected items: Have div[class*='quantity-selector'] with numbers
# Available alternatives: Have button:has-text('Add')
```

#### **Step 5: Individual Item Extraction**
```python
# For individual items (no sub-products):
# - Name: a[href*='/product/']
# - Quantity: span[class*='quantity'] in quantity selector
# - Price: p[class*='font-medium']
```

### Current Scraper Modules

#### **1. `complete_cart_scraper.py` - PRIMARY SCRAPER**
- **Status**: ✅ Stable and recommended
- **Purpose**: Handles both boxes and individual items
- **Output**: Complete cart data + customer summary
- **Use Case**: Primary scraper for production automation

#### **2. `weekly_summary_scraper.py` - CUSTOMER COMMUNICATION**
- **Status**: ✅ Stable and ready for SMS/email
- **Purpose**: Generates beautiful customer weekly summaries
- **Output**: Markdown summaries organized by category
- **Use Case**: Send to customers before meal suggestions

#### **3. `customize_scraper.py` - ALTERNATIVE EXPLORATION**
- **Status**: ✅ Stable for customizable boxes
- **Purpose**: Gets both selected items AND available alternatives
- **Output**: Complete customization data with swap options
- **Use Case**: When customers want to see all available options

#### **4. `simple_scraper.py` - BASIC EXTRACTION**
- **Status**: ✅ Stable for quick extraction
- **Purpose**: Fast extraction of selected items only
- **Output**: Selected items from cart sidebar
- **Use Case**: Quick checks without clicking customize

#### **5. `better_capture.py` - DEBUGGING TOOL**
- **Status**: ✅ Stable for debugging
- **Purpose**: Captures HTML when selectors break
- **Output**: Full page HTML + modal HTML
- **Use Case**: When website changes break selectors

### **DEPRECATED:**
- ❌ `farmbox_optimizer.py` - Replaced by `complete_cart_scraper.py`

### Selector Reference (Core Logic)

These selectors are the foundation of our scraping system:

```css
/* Cart Navigation */
div.cart-button.ml-auto.cursor-pointer           /* Cart button */
article[class*='cart-order_cartOrderItem']       /* Cart items */

/* Item Identification */
a[class*='unstyled-link'][href*='/product/']     /* Item name link */
ul[class*='cart-order-line-item-subproducts']    /* Sub-products list */
button:has-text('CUSTOMIZE')                     /* Customize button */

/* Sub-item Extraction */
li[class*='cart-order-line-item-subproduct']     /* Individual sub-items */
a[class*='subproduct-name']                      /* Sub-item name */

/* Customize Modal */
aside[aria-label*='Customize']                   /* Customize modal */
article[aria-label]                              /* Items in modal */
div[class*='quantity-selector']                  /* Selected items */
button:has-text('Add')                           /* Available alternatives */

/* Individual Items */
div[class*='quantity-selector']                  /* Quantity controls */
span[class*='quantity']                          /* Quantity number */
p[class*='font-medium']                          /* Price */
```

### Error Handling & Reliability

The scraping system includes robust error handling:

1. **Viewport Management**: `scroll_into_view_if_needed()` for buttons
2. **Wait Strategies**: Appropriate timeouts for modal loading
3. **Fallback Clicking**: JavaScript click when regular click fails
4. **Persistent Sessions**: Browser context reuse to maintain login
5. **Debug Output**: Extensive logging for troubleshooting

### Data Structure Output

```json
{
  "name": "Seasonal Produce Box - Small",
  "type": "box",
  "price": "$25.00", 
  "customizable": true,
  "selected_items": [
    {
      "name": "Sugar Cube Cantaloupe",
      "quantity": 1,
      "unit": "1 piece",
      "selected": true
    }
  ],
  "available_alternatives": [
    {
      "name": "White Peaches", 
      "quantity": 0,
      "unit": "2 pieces",
      "selected": false
    }
  ]
}
```

**Reference Documentation**: See `FARM_TO_PEOPLE_SCRAPER_GUIDE.md` for complete technical documentation.

# Product Architecture
- **Boxes**: Customizable boxes like "The Farmer's Box - Paleo" contain sub-items (e.g., "1 Local Yellow Peaches", "2 Organic Red Plums").
- **Customization Availability**: Customization opens on Thursday. Before then, the "CUSTOMIZE" button is disabled, but current contents can still be scraped from the cart sidebar list.
- **Sub-item Format**: Sub-items are typically listed as "Quantity Name" (e.g., "1 Local Yellow Peaches"), sometimes with unit info like "2 pieces".
- **Selected vs Alternatives**: When customization is open, selected items have quantity controls (+/-), alternatives have "ADD" buttons.
