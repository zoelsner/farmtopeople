# 🤖 CLAUDE.md - Farm to People AI Assistant Development Guide

## 🎯 SYSTEM OVERVIEW

**Farm to People AI Assistant** is an SMS-based meal planning system that:
1. Receives SMS messages via Vonage webhook (`18334391183`)
2. Scrapes user's Farm to People cart contents using Playwright
3. Generates sophisticated cart analysis with GPT-5 powered recommendations
4. Provides two-stage confirmation flow (SMS summary → Web view → PDF recipes)
5. Sends professional meal plans with progressive disclosure

### Current Architecture (Refactored August 2025)
```
SMS → FastAPI Server → Background Task → Comprehensive Scraper → Cart Analyzer (GPT-5)
  ↓                                              ↓                        ↓
Supabase (user credentials)              Product Catalog        Web Endpoint (/meal-plan/{id})
                                        (Post-processing)              ↓
                                              ↓                  Professional HTML View
                                        Real Pricing Added               ↓
                                                                   CONFIRM → PDF Recipes
```

### 🚀 LATEST UPDATE: Professional Web Meal Plan Viewer
- **Web Endpoint**: `/meal-plan/{analysis_id}` - Full cart analysis with professional formatting
- **Modular Architecture**: Refactored into cart_analyzer.py, product_catalog.py, file_utils.py
- **Clean Cart Display**: Dynamic product name standardization, proper quantities
- **Progressive Disclosure**: SMS (2-3 segments) → Web (full analysis) → PDF (detailed recipes)
- **Smart Pricing**: Only shows prices on suggested additions, not current cart items

---

## 📊 TWO-STAGE CONFIRMATION SYSTEM

### **✅ PRODUCTION READY: Cart Analysis → Confirmation → Recipes**

**Status**: Complete two-stage flow with web viewer and PDF generation (placeholder)

### **📱 Progressive Disclosure Flow**
```
SMS "plan" → Cart Scraper → GPT-5 Analysis → SMS Summary (2-3 segments)
     ↓                                               ↓
Web Link Included                           "View full analysis: /meal-plan/{id}"
     ↓                                               ↓
User Reply "CONFIRM"                        Professional HTML View
     ↓                                               ↓
PDF Recipe Generation                        Cart Overview + Swaps + Meals
```

**SMS Summary**: ~400 chars with key swaps and meal count
**Web View**: Full analysis with professional formatting
**PDF Recipes**: Detailed cooking instructions after confirmation (pending implementation)

### **✅ COMPLETED IMPROVEMENTS (August 2025)**

**Cart Analysis System**:
- ✅ GPT-5 powered sophisticated meal planning
- ✅ Professional web viewer with HTML formatting
- ✅ Clean product name standardization
- ✅ Two-stage confirmation flow
- ✅ Progressive disclosure for SMS optimization

**Formatting Standards**:
- ✅ Consistent product names with quantities
- ✅ Pricing only on suggested additions
- ✅ Professional swap recommendations with reasoning
- ✅ Meal cards with ingredients and status

### **🎯 PENDING FEATURES**

1. **Cart Total Calculation**:
   - Add total value of current cart
   - Show savings with recommended swaps
   - Calculate cost of suggested additions

2. **Railway Deployment**:
   - Deploy to production with Supabase
   - Configure environment variables
   - Set up proper SMS routing

3. **PDF Recipe Enhancement**:
   - Implement actual PDF generation (currently placeholder)
   - Add detailed cooking instructions
   - Include storage tips and techniques

---

## 🚨 CRITICAL DEVELOPMENT RULES

### **RULE #1: VIRTUAL ENVIRONMENT REQUIRED**
```bash
# ALWAYS activate venv before running:
source venv/bin/activate
cd scrapers
python comprehensive_scraper.py
```

### **RULE #2: MODULAR ARCHITECTURE**
- **cart_analyzer.py**: GPT-5 cart analysis generation
- **product_catalog.py**: Product pricing and matching
- **file_utils.py**: Analysis storage and retrieval
- **meal_planner.py**: Main orchestrator (maintains backward compatibility)

### **RULE #3: AUTHENTICATION IS CRITICAL**  
- **Two-step login:** Email → LOG IN → Password → LOG IN
- **Environment variables:** Check BOTH `EMAIL`/`PASSWORD` AND `FTP_EMAIL`/`FTP_PWD`
- **Diagnostic:** Zipcode modal = authentication failed

### **RULE #4: SERVER RESTART REQUIRED**
- **After code changes:** Kill server process and restart
- **Check processes:** `ps aux | grep "python.*server.py"`
- **Python caches modules:** Running servers don't see file changes

---

## 📱 CURRENT SMS FLOW

### **Vonage Configuration**
- **Phone Number:** `18334391183`
- **Webhook Endpoint:** `/sms/incoming` (GET/POST)
- **Two-Stage Flow:** SMS Summary → Web Link → CONFIRM → PDF

### **Message Routing (server.py:215-239)**
```python
if "hello" in user_message:
    reply = "Hi there! I'm your Farm to People meal planning assistant."

elif "plan" in user_message:
    # Generates cart analysis with web link
    reply = "We are preparing your personalized meal plan now..."
    background_tasks.add_task(run_full_meal_plan_flow, user_phone_number)

elif "confirm" in user_message and user_state == 'awaiting_confirmation':
    # User confirmed - generate detailed PDF recipes
    background_tasks.add_task(generate_confirmed_meal_plan, phone_number)
```

### **Progress SMS Updates**
```python
# Background flow sends these messages:
1. "🔍 Looking up your account..."
2. "🔐 Found your account! Logging into Farm to People..."  
3. "📦 Analyzing your current cart and customizable boxes..."
4. "📋 Analyzing your cart and creating strategic meal plan..."
5. [Cart Analysis Summary with Web Link]

# After user views web analysis and replies CONFIRM:
6. "🍽️ Your personalized meal plan is ready! [PDF Link]"
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

---

## 🎯 FILE STRUCTURE & STATUS

```
farmtopeople/
├── venv/                      # Virtual environment (MUST ACTIVATE)
├── server/
│   ├── server.py              # FastAPI webhook + web endpoints
│   ├── cart_analyzer.py       # ✅ GPT-5 cart analysis generation
│   ├── product_catalog.py     # ✅ Product pricing post-processor
│   ├── file_utils.py          # ✅ Analysis storage/retrieval
│   ├── meal_planner.py        # ✅ Main orchestrator (refactored)
│   └── supabase_client.py     # Database operations  
├── scrapers/
│   ├── comprehensive_scraper.py # ✅ PRIMARY PRODUCTION SCRAPER
│   └── complete_cart_scraper.py # ✅ WORKING BACKUP SCRAPER
├── analyses/                  # JSON analysis storage
├── farm_box_data/             # JSON outputs (customize_results_*.json)
└── CLAUDE.md                  # THIS FILE - Primary documentation
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

# Test web endpoint:
curl http://localhost:8000/meal-plan/c95d0afd

# Start server:
python server/server.py
```

### **Environment Variables**
```bash
# Required .env variables:
EMAIL=your@email.com           # OR FTP_EMAIL  
PASSWORD=yourpassword          # OR FTP_PWD
VONAGE_API_KEY=xxx
VONAGE_API_SECRET=xxx  
VONAGE_PHONE_NUMBER=18334391183
OPENAI_API_KEY=xxx
SUPABASE_URL=xxx
SUPABASE_KEY=xxx
```

---

## 🚨 DEBUGGING PROTOCOL

### **Before Making ANY Changes:**
1. **Activate venv:** `source venv/bin/activate`
2. **Test current functionality:** `python comprehensive_scraper.py`
3. **Check server:** `ps aux | grep "python.*server.py"`
4. **Verify web endpoint:** `curl http://localhost:8000/meal-plan/{id}`

### **Common Issues:**
- ❌ `command not found: python` → venv not activated
- ❌ Zipcode modal appears → auth failure  
- ❌ Empty cart overview → parsing issue with GPT output
- ❌ Server doesn't see changes → restart required

---

## 🎯 CURRENT SYSTEM STATUS

### **✅ WORKING COMPONENTS:**
- **Scraper:** comprehensive_scraper.py (all cart types)
- **Analysis:** GPT-5 powered cart analysis
- **Web Viewer:** Professional HTML formatting
- **SMS Flow:** Two-stage confirmation system
- **Modular Architecture:** Clean separation of concerns

### **🔧 PENDING IMPLEMENTATION:**
- **PDF Generation:** Currently returns placeholder
- **Cart Totals:** Need to calculate current cart value
- **Production Deploy:** Railway + Supabase configuration

---

**Last Updated:** August 23, 2025  
**Primary Maintainer:** Farm to People AI Team
**Status:** ✅ Production Ready (pending PDF implementation)

*This is the primary documentation. All other .md files are archived or redundant.*