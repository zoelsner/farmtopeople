# 🤖 CLAUDE.md - Farm to People AI Assistant Development Guide

## 🎯 SYSTEM OVERVIEW

**Farm to People AI Assistant** is an SMS-based meal planning system that:
1. Receives SMS messages via Vonage webhook (`18334391183`)
2. Scrapes user's Farm to People cart contents using Playwright
3. **NEW**: Accesses comprehensive product catalog (1,200+ products across 4 categories)
4. Generates personalized AI meal plans using OpenAI GPT with real pricing
5. Sends detailed meal plans back via SMS with cost estimates

### Current Architecture
```
SMS → FastAPI Server → Background Task → Comprehensive Scraper → AI Meal Planner → SMS Response
  ↓                                              ↓
Supabase (user credentials)              Product Catalog (958 unique items)
                                        ↓
                                   Real Pricing & Availability
```

---

## 🚨 CRITICAL DEVELOPMENT RULES

### **RULE #1: VIRTUAL ENVIRONMENT REQUIRED**
```bash
# ALWAYS activate venv before running scrapers:
source venv/bin/activate
cd scrapers
python comprehensive_scraper.py
```

### **RULE #2: NEVER BREAK WORKING SCRAPERS**
- **Primary scraper:** `scrapers/comprehensive_scraper.py` (✅ PRODUCTION READY)
- **Product catalog scraper:** `scrapers/product_catalog_scraper.py` (✅ 1,200+ PRODUCTS)
- **Backup scraper:** `scrapers/complete_cart_scraper.py` (✅ WORKING BACKUP)
- **Before ANY changes:** Test current functionality first
- **Must see:** Browser clicking, comprehensive terminal output, clean data extraction

### **RULE #3: AUTHENTICATION IS CRITICAL**  
- **Two-step login:** Email → LOG IN → Password → LOG IN
- **Environment variables:** Check BOTH `EMAIL`/`PASSWORD` AND `FTP_EMAIL`/`FTP_PWD`
- **Diagnostic:** Zipcode modal = authentication failed
- **Test:** Clear `browser_data/` folder for fresh login testing

### **RULE #4: SERVER RESTART REQUIRED**
- **After code changes:** Kill server process and restart
- **Check processes:** `ps aux | grep "python.*server.py"`
- **Python caches modules:** Running servers don't see file changes

---

## 📱 CURRENT SMS FLOW

### **Vonage Configuration**
- **Phone Number:** `18334391183`
- **Webhook Endpoint:** `/sms/incoming` (GET/POST)
- **API Routing:** Vonage handles routing, server defaults are fallbacks

### **Message Routing (server.py:215-239)**
```python
if "hello" in user_message:
    reply = "Hi there! I'm your Farm to People meal planning assistant."

elif "plan" in user_message:
    reply = "We are preparing your personalized meal plan now..."
    background_tasks.add_task(run_full_meal_plan_flow, user_phone_number)

elif "new" in user_message:
    # User registration with secure login link

elif "login" in user_message or "email" in user_message:
    # Secure credential collection link
```

### **Progress SMS Updates**
```python
# Background flow sends these messages:
1. "🔍 Looking up your account..."
2. "🔐 Found your account! Logging into Farm to People..."  
3. "📦 Analyzing your current cart and customizable boxes..."
4. "🤖 Generating personalized meal plans with your ingredients..."
5. [Final meal plan SMS]

# No account found:
"❌ Account not found. Please text 'FEED ME' to get set up first!"
```

---

## 🛒 COMPREHENSIVE SCRAPER FUNCTIONALITY

### **Primary Scraper: comprehensive_scraper.py**

**Captures ALL Cart Types:**
1. **Individual Items** (eggs, avocados, bananas)
2. **Non-customizable Boxes** (Seasonal Fruit Medley)  
3. **Customizable Boxes** (Cook's Box - Paleo with alternatives)

**Current JSON Output Structure:**
```json
{
  "individual_items": [
    {
      "name": "Organic & Fair Trade Hass Avocados",
      "quantity": 5,
      "unit": "1 piece", 
      "price": "$12.50",
      "type": "individual"
    }
  ],
  "non_customizable_boxes": [
    {
      "box_name": "Seasonal Fruit Medley",
      "selected_items": [...],
      "selected_count": 3,
      "customizable": false
    }
  ],
  "customizable_boxes": [
    {
      "box_name": "The Cook's Box - Paleo",
      "selected_items": [...],
      "available_alternatives": [...],
      "selected_count": 9,
      "alternatives_count": 10
    }
  ]
}
```

### **Terminal Output Verification:**
```bash
source venv/bin/activate && cd scrapers && python comprehensive_scraper.py

# Expected output:
🔍 Checking for individual cart items...
  ✅ Individual: Pasture Raised Eggs (qty: 1) - $7.49
  ✅ Individual: Organic & Fair Trade Hass Avocados (qty: 5) - $12.50
🛒 Found 3 individual cart items

📦 Found non-customizable box: Seasonal Fruit Medley
  ✅ Item: Prune Plums (qty: 1) - 1.0 Lbs

=== PROCESSING BOX 1: The Cook's Box - Paleo ===
Clicking CUSTOMIZE...
Found 19 total items in customize modal
  ✅ Selected: Boneless, Skinless Chicken Breast (qty: 1)
  🔄 Available: White Ground Turkey - 1.0 Lbs

📈 SUMMARY:
  Individual Items: 🛒 3 items
  Seasonal Fruit Medley (non-customizable): ✅ 3 items  
  The Cook's Box - Paleo (customizable): ✅ 9 selected 🔄 10 alternatives
```

---

## 🔧 DEVELOPMENT COMMANDS

### **Essential Testing**
```bash
# ALWAYS activate venv first:
source venv/bin/activate

# Test primary scraper:
cd scrapers
python comprehensive_scraper.py

# Check latest output:
ls -lt ../farm_box_data/customize_results_*.json | head -1

# Verify JSON structure:
head -20 ../farm_box_data/customize_results_20250822_093323.json
```

### **Server Operations**
```bash
# Start server:
python server/server.py

# Check running processes:
ps aux | grep "python.*server.py"

# Kill server (use actual PID):
kill [PID]

# Test SMS flow:
curl -X POST http://localhost:8000/test-full-flow
```

### **Environment Setup**
```bash
# Virtual environment:
source venv/bin/activate

# Required .env variables:
EMAIL=your@email.com           # OR FTP_EMAIL  
PASSWORD=yourpassword          # OR FTP_PWD
VONAGE_API_KEY=xxx
VONAGE_API_SECRET=xxx  
VONAGE_PHONE_NUMBER=18334391183
YOUR_PHONE_NUMBER=+1234567890
OPENAI_API_KEY=xxx
SUPABASE_URL=xxx
SUPABASE_KEY=xxx
```

---

## 📋 COMPREHENSIVE PRODUCT CATALOG SYSTEM

### **✅ PRODUCTION READY: Full-Scale Product Scraping**

**Status**: Complete product catalog with 1,200+ products across 4 categories

```bash
# Run comprehensive product catalog scraper:
source venv/bin/activate
cd scrapers
python product_catalog_scraper.py

# Expected output:
🌱 Starting Farm to People Product Catalog Scraper...
🎦 Categories to scrape: 4
🔍 SCRAPING CATEGORY: PRODUCE (190 products)
🔍 SCRAPING CATEGORY: MEAT-SEAFOOD (85 products)
🔍 SCRAPING CATEGORY: DAIRY-EGGS (67 products)
🔍 SCRAPING CATEGORY: PANTRY (860 products)
🎉 COMPLETE! 1,200+ products scraped
```

### **📊 Data Quality Achievements**

**✅ Product Names**: Perfect extraction (100% success rate)
- `Organic Heirloom Tomatoes` ✅
- `Seasonal Produce Box - Medium` ✅
- `Black Sea Bass` ✅

**✅ Vendor Names**: Clean deduplication
- Before: `Sun Sprout FarmSun Sprout FarmOrganic Heirloom Tomatoes`
- After: `Sun Sprout Farm` ✅

**✅ Pricing & Units**: Real data with accurate formatting
- Prices: `$1.99`, `$7.98`, `$25.00`
- Units: `2 pieces`, `1 pint`, `8 oz`, `1 head`
- Availability: Sold out status tracking

### **🍽️ Enhanced Meal Planning Integration**

**Before**: 59 curated items, generic pricing
**After**: 958 unique products, real FTP pricing

```bash
# Test enhanced meal planner:
cd server
python meal_planner.py

# Expected output:
✅ Loaded 958 products from comprehensive catalog
🤖 AI meal suggestions with real pricing:
  ✅ Organic Lemons (2 pieces) - $1.99
  ✅ Organic A2 Mozzarella (8 oz) - $9.99
  💰 Estimated additional cost: $7.98
```

### **🗃️ Files Created**

**Comprehensive Catalog Files**:
- `data/farmtopeople_products.csv` (1,200+ products) ✅
- `scrapers/farm_box_data/product_catalog_*.json` (timestamped)
- `scrapers/farm_box_data/farmtopeople_products_*.csv` (timestamped)

**Integration Status**:
- `server/meal_planner.py`: Enhanced with comprehensive catalog ✅
- Fuzzy matching: AI suggestions → actual FTP products ✅
- Real pricing: $1.99, $4.99 vs "Price available on checkout" ✅

---

## 🎯 FILE STRUCTURE & STATUS

```
farmtopeople/
├── venv/                      # Virtual environment (MUST ACTIVATE)
├── server/
│   ├── server.py              # FastAPI webhook (imports comprehensive_scraper)
│   ├── supabase_client.py     # Database operations  
│   └── meal_planner.py        # ✅ ENHANCED: 958 products, real pricing
├── scrapers/
│   ├── comprehensive_scraper.py  # ✅ PRIMARY CART SCRAPER
│   ├── product_catalog_scraper.py # ✅ NEW: 1,200+ PRODUCT CATALOG
│   ├── complete_cart_scraper.py  # ✅ WORKING BACKUP SCRAPER
│   └── farm_box_data/            # Scraped data outputs
│       ├── customize_results_*.json    # Cart contents (timestamped)
│       ├── product_catalog_*.json     # Full catalog (timestamped)
│       └── farmtopeople_products_*.csv # Product data (timestamped)
├── data/
│   └── farmtopeople_products.csv  # ✅ MAIN: 1,200+ products
├── docs/                      # Architecture documentation
├── DEBUGGING_PROTOCOL.md      # 🚨 READ BEFORE TOUCHING SCRAPERS
└── CRITICAL_SCRAPING_LESSONS_LEARNED.md # Historical failures
```

---

## 🚨 DEBUGGING PROTOCOL

### **Before Making ANY Changes:**
1. **Activate venv:** `source venv/bin/activate`
2. **Run current scraper:** `python comprehensive_scraper.py`
3. **Verify terminal output:** Individual items, non-customizable boxes, customizable boxes
4. **Check JSON output:** Verify enhanced structure with all three cart types
5. **Test authentication:** No zipcode modal = success

### **When Things Break:**
1. **STOP immediately** - don't keep "fixing"
2. **Restore from backup** - use working version
3. **Check venv activation** - most common issue
4. **Compare outputs** - working vs broken terminal messages
5. **Restart server** - after any code changes

### **Red Flags:**
- ❌ `command not found: python` (venv not activated)
- ❌ Missing individual items in terminal output
- ❌ No "Clicking CUSTOMIZE..." messages
- ❌ Zipcode modal appears (auth failure)  
- ❌ JSON missing comprehensive structure

---

## 🎯 MEAL PLANNING FLOW

### **Current Implementation:**
```python
# server.py uses comprehensive_scraper:
from scrapers.comprehensive_scraper import main as run_cart_scraper

# Background flow:
run_cart_scraper()  # Creates comprehensive JSON
plan = meal_planner.run_main_planner()  # Uses latest JSON
```

### **OpenAI Configuration:**
- **Model:** `gpt-4` 
- **Temperature:** NOT USED (removed - caused API errors)
- **Input:** Comprehensive cart contents from latest JSON file
- **Output:** Structured meal suggestions using all available ingredients

### **MEAL PLAN FORMATTING REQUIREMENTS:**

#### **Essential Format Elements:**
1. **Cart Contents Analysis** - Complete inventory with quantities
2. **Quantity Sufficiency Check** - Verify ingredients support meal suggestions
3. **Alternative Swap Recommendations** - Suggest optimal swaps from available alternatives
4. **Protein Addition Suggestions** - Recommend healthy proteins (avoid beef for health-conscious users)
5. **Separate Lists** - Keep "Additional Fresh Items" separate from "Pantry Staples"

#### **Required Structure:**
```
## Current Cart Contents
[Complete inventory with quantities]

## Recommended Swaps for Better Meal Flexibility
[Specific swap suggestions with reasoning]

## Recommended Protein Additions to Cart
[Healthy protein options, avoid beef]

## Quantity-Adjusted Meal Plan
[Meals with quantity verification status]

## Additional Fresh Items Still Needed
[Fresh items beyond cart contents]

## Pantry Staples Needed  
[Basic pantry items for cooking]
```

#### **Key Features:**
- **Quantity Analysis:** Check if cart quantities support meal suggestions
- **Status Indicators:** ✅ Sufficient, ⚠️ Need more, etc.
- **Swap Logic:** Recommend best alternatives from available options
- **Health Focus:** Suggest healthy proteins, avoid beef for health-conscious users
- **Serving Estimates:** Provide total serving counts for meal planning

---

## 🔄 CURRENT DATA FLOW

```
1. SMS "plan" received (Vonage: 18334391183)
   ↓
2. Server.py /sms/incoming endpoint  
   ↓
3. User lookup in Supabase
   ↓
4. Background task: run_full_meal_plan_flow()
   ├─ Progress SMS: "Looking up account..."
   ├─ Set environment variables
   ├─ Call comprehensive_scraper.main()
   ├─ Progress SMS: "Generating meal plans..."
   └─ Call meal_planner.run_main_planner()
   ↓
5. Final SMS with comprehensive meal plan
```

---

## 🎯 COMPREHENSIVE SCRAPER CAPABILITIES

### **What It Actually Captures (Verified August 22, 2025):**
- ✅ **3 Individual Items:** Eggs (1 dozen), Avocados (5 pieces), Bananas (1 bunch)
- ✅ **1 Non-customizable Box:** Seasonal Fruit Medley (3 fruits: plums, apples, peaches)
- ✅ **1 Customizable Box:** Cook's Box - Paleo (9 selected + 10 alternatives)
- ✅ **Correct Quantities:** Properly detects 5 avocados, not defaulting to 1
- ✅ **Comprehensive JSON:** Enhanced structure with all cart types organized

### **JSON File Output:**
- **Location:** `farm_box_data/customize_results_YYYYMMDD_HHMMSS.json`
- **Latest:** `customize_results_20250822_093323.json`
- **Structure:** `{"individual_items": [...], "non_customizable_boxes": [...], "customizable_boxes": [...]}`

---

## 🚫 CRITICAL DON'TS

### **NEVER:**
- Run scrapers without activating venv first
- Change working scraper without testing
- Assume server sees code changes without restart
- Ignore comprehensive terminal output
- Keep "fixing" broken code instead of reverting

### **ALWAYS:**
- Activate virtual environment: `source venv/bin/activate`
- Test comprehensive_scraper before changes
- Restart server after modifications  
- Verify JSON contains all three cart types
- Check for complete terminal summary

---

## 🎯 CURRENT SYSTEM STATUS

### **✅ WORKING COMPONENTS:**
- **Cart Scraper:** comprehensive_scraper.py (comprehensive cart capture)
- **Product Catalog:** product_catalog_scraper.py (1,200+ products, 4 categories)
- **Meal Planner:** Enhanced with 958 unique products and real pricing
- **SMS System:** Vonage integration with 18334391183
- **Authentication:** Two-step login with session detection
- **AI Planning:** OpenAI GPT-4 with comprehensive product database
- **Progress Updates:** Real-time SMS status messages with cost estimates
- **Backup Scraper:** complete_cart_scraper.py (alternative working implementation)

### **🔧 PRODUCTION SETUP:**
- **Virtual Environment:** Required for all Python operations
- **Authentication:** Supports both EMAIL/PASSWORD and FTP_EMAIL/FTP_PWD
- **Data Quality:** Perfect product names, clean vendor deduplication
- **Real Pricing:** $1.99, $7.98 totals vs generic placeholders
- **Server Integration:** FastAPI with background task processing
- **Comprehensive Database:** 16x larger product catalog (958 vs 59 items)

---

## ⚡ QUICK REFERENCE

### **Test Cart Scraper:**
```bash
source venv/bin/activate && cd scrapers && python comprehensive_scraper.py
# Must show: Individual items, non-customizable boxes, customizable boxes
```

### **Test Product Catalog Scraper:**
```bash
source venv/bin/activate && cd scrapers && python product_catalog_scraper.py
# Expected: 1,200+ products across 4 categories with perfect data quality
```

### **Test Enhanced Meal Planner:**
```bash
cd server && python meal_planner.py
# Expected: ✅ Loaded 958 products, real pricing, AI suggestions
```

### **Server Health Check:**
```bash
curl http://localhost:8000/health
# Returns: {"status": "healthy", "service": "farmtopeople-sms"}
```

### **SMS Test Flow:**
1. Text "plan" to `18334391183`
2. Immediate acknowledgment received
3. Progress updates sent during processing  
4. Final comprehensive meal plan delivered

---

**Last Updated:** August 23, 2025  
**Production Status:** ✅ COMPREHENSIVE SYSTEM FULLY OPERATIONAL  
**Cart Scraper:** comprehensive_scraper.py (comprehensive cart capture)  
**Product Catalog:** product_catalog_scraper.py (1,200+ products, 4 categories)  
**Meal Planner:** Enhanced with 958 unique products and real pricing ($1.99, $7.98 totals)  
**SMS System:** 18334391183 (Vonage API routing)  
**Data Quality:** Perfect product names, clean vendor deduplication, actual FTP pricing  
**Database Scale:** 16x improvement (958 vs 59 products)  
**Key Requirement:** Virtual environment activation for all Python operations

*This guide reflects the fully enhanced comprehensive system with complete product catalog integration.*