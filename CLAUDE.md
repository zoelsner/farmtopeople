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

## 📄 PDF MEAL PLAN GENERATION SYSTEM

### **✅ PRODUCTION READY: Professional PDF Meal Plans**

**Status**: Complete PDF generation with storage tips and detailed recipes

```bash
# Test PDF generation:
source venv/bin/activate
cd server
python -c "from pdf_meal_planner import generate_pdf_meal_plan; print(generate_pdf_meal_plan())"

# Expected output:
✅ PDF generated successfully: ../pdfs/meal_plan_20250822_225327.pdf
📁 File size: 7,558 bytes
```

### **🎨 PDF Features**
**✅ Professional Design**: Farm to People green branding with clean layout  
**✅ Storage Guide**: Refrigeration tips for every ingredient  
**✅ Recipe Instructions**: Step-by-step cooking directions  
**✅ Cart Recommendations**: Missing ingredients with pricing  
**✅ SMS Integration**: PDF links sent instead of long text messages  

### **📱 Enhanced SMS Flow**
```
SMS "plan" → Cart Scraper → Meal Planner → PDF Generator → SMS with PDF Link
```

**Before**: Long text message with basic meal suggestions  
**After**: Professional PDF link with complete storage + recipe guide  

**SMS Message**:
```
🍽️ Your professional Farm to People meal plan is ready!

📄 View your complete plan with storage tips and recipes: 
http://localhost:8000/pdfs/meal_plan_20250822_225327.pdf

Enjoy your meals!
```

### **🔧 PDF System Architecture**
- **Additive Design**: Builds on existing meal planner, doesn't replace anything
- **Fallback Support**: Text SMS if PDF generation fails  
- **Web Serving**: `/pdfs/{filename}` endpoint serves PDFs via browser
- **ReportLab**: Professional document generation with custom styles

### **⚠️ CURRENT LIMITATIONS & IMPROVEMENT AREAS**

**🚨 Recipe Quality Issues**:
- **Too Simple**: Basic 5-step instructions lack detail
- **Generic Instructions**: "Cook according to preference" needs specificity  
- **Missing Techniques**: No sautéing temps, timing, or cooking methods
- **No Difficulty Levels**: All recipes assume same skill level

**🚨 Interactivity Limitations**:  
- **Static PDF**: No interactive dropdowns or expandable sections
- **No Dynamic Content**: Can't hide/show optional ingredients
- **Browser-Only**: PDFs don't support JavaScript or dynamic elements

**🎯 SUGGESTED IMPROVEMENTS**:
1. **Enhanced Recipe Instructions**:
   - Specific temperatures, times, and techniques
   - Professional cooking tips and troubleshooting
   - Ingredient prep details and knife cuts

2. **Interactive Options**:
   - **Web App**: HTML page with expandable sections
   - **Progressive PDF**: Multi-page with detailed/simple versions
   - **QR Codes**: Link to interactive recipe website

3. **Recipe Database Enhancement**:
   - Technique-specific instructions per cooking method
   - Difficulty levels (Beginner/Intermediate/Advanced)
   - Nutritional information and dietary notes

### **📁 PDF System Files**
```
farmtopeople/
├── server/
│   ├── pdf_meal_planner.py      # ✅ PDF generation system
│   └── server.py                # ✅ Enhanced with PDF SMS integration
├── pdfs/                        # ✅ Generated PDF storage
│   └── meal_plan_*.pdf         # Timestamped meal plans
```

---

## 🚀 FUTURE VISION: FITBOD-STYLE MEAL PLANNING APP

### **💡 Core Concept: Personalized Recipe Filtering**

**Inspiration**: FitBod workout app UX applied to meal planning
- **User Equipment Inventory**: Cast iron, food processor, spices available
- **Skill Level Progression**: Beginner → Intermediate → Advanced over time
- **Time Constraints**: 15min, 30min, 1hr filter options
- **Dietary Preferences**: Stored and applied to all suggestions

### **🎨 Design Vision**

**Color Palette**: Penny Restaurant (East Village) - warm, earthy, sophisticated  
**Layout Style**: FitBod-inspired filter bar + dynamic content below

### **📱 App Interface Concept**
```
┌─────────────────────────────────────┐
│ [⏱️ 30min] [👨‍🍳 Inter] [🍳 Cast Iron] │  ← Filter bar
│ [🌶️ Garlic+Cumin+Paprika]           │
├─────────────────────────────────────┤
│                                     │
│ 🔥 Seared Salmon with Vegetables    │  ← High-level "No Recipe" style
│ "Hot pan + seasoned fish + quick    │
│  vegetables = restaurant dinner"    │
│                                     │
│ ▼ Show detailed steps [expand]      │  ← Progressive disclosure
│                                     │
│ 🥘 Cast Iron Vegetable Medley       │
│ "Seasonal veg + high heat + time    │
│  = caramelized perfection"          │
│                                     │
└─────────────────────────────────────┘
```

### **🔧 Technical Architecture**
- **User Profile Storage**: Equipment, spices, skill level, dietary restrictions
- **Dynamic Recipe Filtering**: Real-time menu updates based on selected preferences  
- **Progressive Recipe Complexity**: NYT "Cooking: No Recipe Recipes" approach
- **Skill Level Adaptation**: Same recipe, different instruction detail levels
- **Equipment-Aware Suggestions**: Only show recipes for owned equipment

### **📊 User Preference Categories**
```
🍳 EQUIPMENT OWNED:
□ Cast Iron Skillet    □ Food Processor    □ Immersion Blender
□ Dutch Oven          □ Stand Mixer       □ Mandoline
□ Wok                 □ Mortar & Pestle   □ Thermometer

🌶️ SPICE CABINET:
□ Garlic              □ Cumin             □ Paprika  
□ Fresh Herbs         □ Soy Sauce         □ Fish Sauce
□ Quality Olive Oil   □ Vinegars          □ Hot Sauce

⏱️ TIME PREFERENCES:
○ Quick (15 minutes)   ○ Standard (30 min)  ○ Leisurely (1+ hour)

👨‍🍳 SKILL LEVEL:
○ Beginner (detailed)  ○ Intermediate      ○ Advanced (concise)

🥗 DIETARY:
□ Vegetarian          □ Gluten-Free       □ Dairy-Free
□ Low-Carb            □ High-Protein      □ Pescatarian
```

### **🎯 Implementation Phases**
1. **Phase 1**: Current SMS system with basic preference collection
2. **Phase 2**: Web app prototype with filter interface
3. **Phase 3**: Full FitBod-style progressive web app
4. **Phase 4**: Mobile app with offline recipe storage

---

## 📱 ENHANCED SMS PREFERENCE SYSTEM

### **🔄 Updated SMS Flow with Preferences**
```
1. SMS "plan" received → Immediate acknowledgment
2. Cart scraping completes
3. ✅ NEW: "Quick question! What's your cooking experience? 
   Text: 1=Beginner 2=Intermediate 3=Advanced"
4. User responds with preference
5. ✅ NEW: "Got it! Any equipment preferences? 
   Text: cast iron, food processor, etc. (or 'basic' for stovetop only)"
6. User responds with equipment
7. Generate personalized meal plan based on preferences
8. Send professional PDF with appropriate complexity level
```

### **💾 Preference Storage in Supabase**
```sql
-- Add to existing users table:
ALTER TABLE users ADD COLUMN cooking_skill_level VARCHAR(20) DEFAULT 'intermediate';
ALTER TABLE users ADD COLUMN available_equipment TEXT[];
ALTER TABLE users ADD COLUMN dietary_restrictions TEXT[];
ALTER TABLE users ADD COLUMN preferred_cooking_time INTEGER DEFAULT 30;
ALTER TABLE users ADD COLUMN spice_preferences TEXT[];
```

### **🤖 Smart Preference Learning**
- **Initial Setup**: Ask 2-3 key questions via SMS
- **Progressive Learning**: Update preferences based on user feedback over time
- **Equipment Detection**: Infer equipment from chosen recipes
- **Skill Progression**: Gradually suggest more advanced techniques

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
│   ├── server.py              # FastAPI webhook + PDF SMS integration
│   ├── supabase_client.py     # Database operations  
│   ├── meal_planner.py        # ✅ ENHANCED: 958 products, real pricing
│   └── pdf_meal_planner.py    # ✅ NEW: Professional PDF generation
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
├── pdfs/                          # ✅ NEW: Generated meal plan PDFs
│   └── meal_plan_*.pdf           # Professional PDF meal plans
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

## 🔄 ENHANCED DATA FLOW (With PDF Generation)

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
   ├─ Call meal_planner.run_main_planner()
   ├─ ✅ NEW: Generate PDF with storage tips & recipes
   └─ ✅ NEW: PDF URL generation
   ↓
5. ✅ ENHANCED: SMS with professional PDF link instead of text
```

### **✅ NEW SMS Output:**
**Before**: Long text with basic meal suggestions  
**After**: Clean PDF link message
```
🍽️ Your professional Farm to People meal plan is ready!

📄 View your complete plan with storage tips and recipes: 
http://localhost:8000/pdfs/meal_plan_20250822_225327.pdf

Enjoy your meals!
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

---

## 🧭 OUTPUT STRATEGY, TOKEN OPTIMIZATION, AND NEXT STEPS (Aug 23, 2025)

### Goals
- Deliver professional, strategic meal plans without overwhelming users via SMS
- Keep OpenAI costs predictable by avoiding large prompt contexts (no full catalog in prompts)
- Preserve detail and quality via web/PDF while using SMS as a lightweight notification and control channel

### Delivery Architecture
- SMS as notification + lightweight controls:
  - Immediate acknowledgement and progress updates
  - Short summary + link to full plan when content is long
  - Conversational shortcuts: "MEALS", "SHOP", "CONFIRM", "MODIFY"
- Web view for full cart analysis:
  - Structured sections: Overview, Smart Swaps, Meals (5), Shopping Lists (Proteins, Fresh, Pantry), Summary, CTA
  - Single shareable link per analysis (e.g., `/meal-plan/{analysis_id}`)
- PDF for recipe depth and offline consumption:
  - One meal per page with mise en place, technique, timing, sensory cues
  - Final pages for additions and pantry staples

### SMS Length Strategy (Progressive Disclosure)
- When analysis ≤ ~1,500 chars: send directly via SMS
- When analysis > ~1,500 chars: send highlights + link to full web view
- Optional staged SMS flow on request:
  - "MEALS" → 5 meal titles only
  - "SHOP" → concise shopping highlights (proteins + top fresh items)
  - "CONFIRM" → generate PDF with detailed recipes

### Token/Cost Optimization (No Catalog Prompt Stuffing)
- Do not embed the full product catalog in any prompt
- Use a pricing enrichment pass after the model response:
  - Fuzzy-match only referenced items (cart items, suggested proteins, top box alternatives) to the local catalog
  - Replace generic names with FTP item names + prices where confidently matched
- Maintain a small curated map for high-frequency items (e.g., preferred proteins, common aromatics)
- Cache weekly pricing lookups by SKU/name to avoid repeat work
- Log token usage and maintain a weekly budget view; expose simple cost telemetry

### Cart Analysis Structure (Current Best Practice)
- Sections (fixed order):
  1) Current Cart Overview (tight bullets)
  2) Recommended Swaps (max 3, only from same-box alternatives)
  3) Recommended Protein Additions (healthy options, no beef bias)
  4) Strategic Meal Plan (5 meals, each with Using/Status lines)
  5) Additional Fresh Items Needed (concise)
  6) Pantry Staples Needed (concise)
  7) Summary (servings, variety, waste reduction)
- Keep line length and bullet density tuned for readability; use emojis sparingly for scanning

### Recipe Generation Quality (Restaurant-Level)
- Keep Stage 1 (planning) lightweight; Stage 2 generates professional recipes with:
  - Mise en place (knife cuts, measurements, organization)
  - Temperatures, precise timing, sensory cues, troubleshooting
  - Chef notes (make-ahead, variations, plating)
- Personalize by skill level (beginner/intermediate/advanced) pulled from user preferences
- Do not add catalog context to recipe prompts; recipes are technique-forward and ingredient-aware

### PDF Experience Improvements
- Visual hierarchy and scannability:
  - Larger meal titles, consistent color accents, section icons
  - One meal per page; last page for additions and pantry staples
  - Short callouts for technique tips; minimize body text density
- Optional: QR link to the web view per meal for interactive timers and variations

### Weekly Reminder Flow (Opt-In)
- Thursday afternoon reminder via SMS:
  - Short nudge: "Your weekly plan is ready based on your current cart. Reply PLAN to review."
  - Respect opt-out and quiet hours; retry rules with backoff

### Data & Privacy
- Phone numbers and messages are transactional only; no marketing
- Pricing enrichment uses local data; no catalog dump to LLMs
- Store generated analyses with minimal PII; token usage telemetry anonymized

### Operational Next Steps
- Build minimal web view for analyses (`/meal-plan/{id}`) with clean sections and CTA
- Persist analyses and associate with phone numbers; expire after N days
- Add SMS dispatcher that selects between: full SMS vs summary + link
- Implement pricing cache layer keyed by normalized product name
- Surface skill level from Supabase and apply to recipe generation
- Add weekly reminder job (Thursday cadence), opt-in/out flags in user profile

### Guardrails & SLAs
- Timeouts per LLM call; graceful fallbacks and user messaging
- Max token budget per request; refuse/trim politely when exceeded
- Observability: log tokens, latency, enrichment hit-rate, SMS send success

### File Pointers
- Cart analysis generation: `server/meal_planner.py` (cart summary, swaps policy)
- Pricing enrichment (post-processing): `server/meal_planner.py` (add-pricing helpers)
- Recipe detail generation (professional level): `server/recipe_generator.py`
- PDF generation (layout and sections): `server/pdf_meal_planner.py`
- Server flow, confirmation states, SMS routing: `server/server.py`

This section codifies the output strategy and cost controls: SMS remains the notification layer and command surface, while the web view and PDF carry the full fidelity experience. Pricing precision is achieved via post-processing against the local catalog, avoiding prompt bloat and containing costs.