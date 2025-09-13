# 🤖 CLAUDE.md - Farm to People AI Assistant Development Guide

## 🎯 PROJECT OVERVIEW

**Farm to People AI Assistant** transforms weekly produce boxes into personalized meal plans through intelligent SMS conversations. The system learns user preferences, analyzes cart contents, and delivers actionable cooking guidance.

**Current Status:** Dashboard Modularized - Clean JS modules, real ingredient tracking, proper state management  
**Last Updated:** September 4, 2025  
**Version:** 5.0.0 (Modular Dashboard + Real Ingredient Tracking)  
**Branch:** `feature/customer-automation`  
**Primary Contact:** SMS `18334391183` (Vonage)  
**Live URL:** https://farmtopeople-production.up.railway.app

---

## 🚀 QUICK START

### **Test the System**
```bash
# 1. Production Web App (LIVE)
open https://farmtopeople-production.up.railway.app/onboard

# 2. Local Development
source venv/bin/activate
python server/server.py
open http://localhost:8000/onboard

# 3. Test cart scraping with real data
cd scrapers && python comprehensive_scraper.py

# 4. Dashboard testing (requires onboarding first)
open http://localhost:8000/dashboard
```

### **Critical Development Rules**
- ✅ ALWAYS activate venv before running Python code
- ✅ Use GPT-5 (model="gpt-5") - it works in production!
- ✅ Test comprehensive_scraper.py before making changes
- ✅ Restart server after code modifications
- ✅ Best PDF design: `generators/templates/meal_plan_minimal.html` (Penny-style)
- ✅ **Protein in titles:** "38g protein" must be prominent under each meal name
- ✅ NEVER use GPT-3.5 - use GPT-5 or gpt-4o-mini only

---

## 📚 DOCUMENTATION INDEX

### **Business & Product Docs**
- [`docs/complete_business_flow.md`](docs/complete_business_flow.md) - End-to-end customer journey with confirmation flow
- [`docs/updated_business_flow.md`](docs/updated_business_flow.md) - Latest requirements (high-protein, meal calendar)
- [`docs/system_gap_analysis.md`](docs/system_gap_analysis.md) - Current gaps and improvement roadmap
- [`docs/ONBOARDING_SYSTEM.md`](docs/ONBOARDING_SYSTEM.md) - Preference collection implementation

### **Technical Documentation**
- [`docs/MEAL_CALENDAR_IMPLEMENTATION_PLAN.md`](docs/MEAL_CALENDAR_IMPLEMENTATION_PLAN.md) - **NEW:** Complete meal planning system design
- [`docs/CODEBASE_AUDIT_REPORT_AUG31.md`](docs/CODEBASE_AUDIT_REPORT_AUG31.md) - **NEW:** Comprehensive architecture audit
- [`database/meal_planning_schema.sql`](database/meal_planning_schema.sql) - **NEW:** Database schema for meal planning
- [`docs/refactoring_opportunities.md`](docs/refactoring_opportunities.md) - Architecture improvements & conversation state management
- [`docs/conversational_ai_architecture.md`](docs/conversational_ai_architecture.md) - AI system design patterns
- [`DEBUGGING_PROTOCOL.md`](DEBUGGING_PROTOCOL.md) - Scraper troubleshooting guide
- [`CRITICAL_SCRAPING_LESSONS_LEARNED.md`](CRITICAL_SCRAPING_LESSONS_LEARNED.md) - Historical failures & solutions

---

## 🏗️ SYSTEM ARCHITECTURE

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   WEB APP    │────▶│   DASHBOARD  │────▶│ MEAL CALENDAR│
│ (7-step flow)│     │ (Live Cart)  │     │ (Drag & Drop)│
└──────────────┘     └──────────────┘     └──────────────┘
        │                    │                     │
        ▼                    ▼                     ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   SUPABASE   │◀────│   SCRAPER    │────▶│ STORAGE LAYER│
│(Users+Meals) │     │ (Real Cart)  │     │ (Abstraction)│
└──────────────┘     └──────────────┘     └──────────────┘
        │                    │                     │
        ▼                    ▼                     ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   SESSIONS   │     │   AI MODELS  │     │    REDIS     │
│ (Cross-device)│     │  (GPT-5)     │     │  (Future)    │
└──────────────┘     └──────────────┘     └──────────────┘
```

---

## 🌐 PRIMARY WEB APP FLOW

### **7-Step Onboarding (Phone Number First)**
```
Step 1: Phone Number Entry
  ├─ Existing User? → Skip to Step 7 (FTP)
  └─ New User? → Continue to Step 2

Step 2: Household Size + Meal Timing
Step 3: Meal Preferences (pick 3+ dishes)
Step 4: Cooking Styles (optional, 2+ methods)
Step 5: Dietary Restrictions (multiple selection)
Step 6: Health Goals (up to 2 outcomes)
Step 7: FTP Account Credentials → Dashboard
```

### **Dashboard Navigation**
- **Cart Tab:** Live cart analysis with delivery date
- **Meals Tab:** Weekly meal calendar with drag-and-drop (Monday-Friday)
- **Settings Tab:** Update any preferences via modal editing

### **Important Business Rules**
- **Cart Lock Time:** Carts lock at 11:59 AM ET the day before delivery
- **Fallback Logic:** When cart is locked, system uses stored cart data with complete boxes
- **Phone Format Handling:** System tries multiple formats: `phone`, `+phone`, `+1phone`, `1phone`
- **Delivery Date Display:** Green text in top-right of cart analysis showing delivery date
- **Customizable Box Detection:** Uses `customizable` flag regardless of storage array
- **Protein Requirements:** Women: 30g minimum, Men: 35-40g minimum per meal

### **Settings System (Full CRUD)**
- **Household Size:** 1-7+ people grid selection
- **Meal Preferences:** Familiar vs adventurous dishes
- **Cooking Style:** Quick, comfort, international methods
- **Dietary Restrictions:** Allergies, lifestyle choices
- **Health Goals:** Quick dinners, family meals, etc.

---

## 📱 SMS FLOW (Secondary - Future Enhancement)

### **Message Routing (server.py:455-498)**
```python
if "hello" in user_message:
    reply = format_sms_with_help(
        "Hi there! I'm your Farm to People meal planning assistant.", 
        'greeting'
    )

elif "plan" in user_message:
    reply = format_sms_with_help(
        "📦 Analyzing your Farm to People cart...", 
        'analyzing'
    )
    background_tasks.add_task(run_full_meal_plan_flow, user_phone_number)

elif "new" in user_message:
    # User registration with secure login link + onboarding help

elif "login" in user_message or "email" in user_message:
    # Secure credential collection link + login help
```

### **SMS Help Text System (NEW - Aug 26, 2025)**
Every SMS now includes contextual help text to guide users:

**Example Output:**
```
📦 Analyzing your cart...
━━━━━━━━━
⏳ This takes 20-30 seconds...
```

**Available States:**
- `analyzing` - Progress indicator during processing  
- `plan_ready` - Action options after meal plan delivery
- `greeting` - Basic navigation for new users
- `error` - Recovery options when issues occur
- `default` - General help for unrecognized input

**Implementation:** `format_sms_with_help(message, state)` in server.py:111-178

### **Progress SMS Updates**
```python
# Background flow sends these messages:
1. "🔍 Looking up your account..."
2. "🔐 Found your account! Logging into Farm to People..."  
3. "📦 Analyzing your current cart and customizable boxes..."
4. "🤖 Generating personalized meal plans with your ingredients..."
5. [Final meal plan SMS]
```

---

## 📅 **MEAL CALENDAR SYSTEM (NEW - Aug 31, 2025)**

### **Revolutionary Feature: Drag & Drop Meal Planning**
Transform cart contents into interactive weekly meal calendar with smart ingredient allocation.

### **Key Innovations:**
- **Smart Ingredient Tracking** - System prevents over-allocation of ingredients
- **Drag & Drop Interface** - Move meals between days with real-time conflict detection  
- **Context-Aware Regeneration** - AI considers remaining ingredients when recreating meals
- **Cross-Device Sync** - Seamless planning across phone and desktop

### **Architecture:**
```
Cart Data → Ingredient Pool → Weekly Calendar → Meal Assignments
     ↓            ↓               ↓              ↓
   JSON        Database       React UI     Supabase Storage
```

### **Database Schema (4 New Tables):**
- `weekly_meal_plans` - Main meal plan containers
- `meal_assignments` - Individual meals per day (Mon-Fri)
- `ingredient_pools` - Track ingredient allocation/availability  
- `meal_plan_sessions` - Cross-device sync sessions

### **User Flow Example:**
1. **Generate Plan** - AI creates 5-day meal plan from cart
2. **Review Calendar** - See Monday-Friday with assigned meals
3. **Drag to Modify** - Move Tuesday's chicken to Thursday
4. **Auto-Validation** - System checks ingredient availability
5. **Smart Regeneration** - Click refresh on Tuesday for new meal
6. **Conflict Resolution** - Suggest alternatives if ingredients insufficient

### **Storage Architecture (Redis-Ready):**
```python
# Abstract storage layer for easy migration
storage = SupabaseMealStorage()  # Current
# storage = RedisMealStorage()   # Future (>100 users)

# Key operations:
await storage.create_meal_plan(user_phone, week_of, cart_data)
await storage.assign_meal(plan_id, "monday", meal_data, ingredients)
await storage.get_ingredient_pool(plan_id)  # Real-time availability
```

### **Status:** 
- ✅ **Backend Complete** - Database schema, storage layer, conflict detection
- 🚧 **API Endpoints** - In development (meal CRUD, regeneration)
- 📅 **Frontend** - Starting soon (drag & drop calendar component)

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
      "name": "Organic Hass Avocados",
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

---

## 📊 CURRENT IMPLEMENTATION STATUS

### ✅ **COMPLETED FEATURES (as of 8/31)**
- **✅ Web App Foundation** - Complete 7-step onboarding with smart user detection
- **✅ Settings System** - Full CRUD operations for all user preferences
- **✅ Dashboard Integration** - Live cart data with meal suggestions and refresh functionality
- **✅ Cart Scraping** - Comprehensive capture including delivery date extraction
- **✅ User Management** - Phone-first flow with existing user skip logic
- **✅ Database Schema** - Supabase user/preference storage with encrypted credentials
- **✅ Live Cart → Dashboard** - Real FTP data integration with phone format handling
- **✅ Navigation System** - Clean tab structure (Cart/Meals/Settings) with proper routing
- **✅ GPT-5 Implementation** - Production-ready meal plan generation
- **✅ Deployment** - Live on Railway with environment variables configured
- **✅ Meal Calendar System** - Interactive weekly planning with drag & drop functionality
- **✅ Ingredient Pool Tracking** - Real-time allocation with visual progress bars
- **✅ Meal Variety Engine** - Different proteins/cooking methods each day
- **✅ Preference Integration** - User goals shape meal generation (high-protein, quick dinners)
- **✅ Cross-device Foundation** - Session management API for multi-device sync
- **✅ Cart Analysis Fixes** - Proper cart detection, delivery date display, box categorization
- **✅ Date Navigation Fixes** - Stable week navigation without erratic date jumping

### ✅ **COMPLETED THIS WEEK (8/31 - MEAL CALENDAR & DEBUG FIXES)**
- **✅ Saturday PM:** Complete meal planning database schema with ingredient allocation
- **✅ Saturday PM:** Meal planning API with CRUD operations and conflict detection
- **✅ Saturday PM:** User preference integration in meal generation algorithms
- **✅ Saturday PM:** Meal variety system (different proteins/cooking methods per day)
- **✅ Saturday PM:** Interactive meal calendar interface with drag & drop
- **✅ Saturday PM:** Ingredient pool tracking with real-time progress visualization
- **✅ Saturday PM:** Mobile-responsive calendar design with touch-friendly interactions
- **✅ Saturday PM:** Complete documentation of meal calendar system
- **✅ Saturday LATE:** Critical cart analysis debugging - fixed phone format lookup
- **✅ Saturday LATE:** Fixed Python indentation errors preventing server startup
- **✅ Saturday LATE:** Fixed "Please analyze your cart first" error with proper cart detection
- **✅ Saturday LATE:** Added delivery date display in green text at top-right
- **✅ Saturday LATE:** Fixed meal calendar week navigation with proper date handling
- **✅ Saturday LATE:** Fixed customizable box categorization using `customizable` flag

### ✅ **PREVIOUS WEEK (8/26-8/28)**
- **✅ Monday:** Settings page with 5 preference categories and modal editing
- **✅ Tuesday:** Dashboard navigation refactor (Home→Cart, Cart→Meals)
- **✅ Wednesday:** Live scraper integration with database credential lookup
- **✅ Wednesday:** Delivery date extraction from cart pages
- **✅ Wednesday:** Meal refresh functionality with 3x daily limit
- **✅ Thursday:** Onboarding flow refactor - phone number first with user detection
- **✅ Thursday:** Production deployment with full end-to-end testing

### 📝 **FUTURE FEATURES**
- **Confirmation Flow** - User approval before recipe generation
- **Cart Total Calculation** - Pricing transparency
- **Weekly Feedback Loop** - Recipe rating system
- **Seasonal Intelligence** - Produce availability awareness
- **Preference Evolution** - Learning from user behavior

---

## 🚨 CRITICAL GAPS & HANDOFF ISSUES

### ~~**Gap 1: Preferences → Meal Planning** ✅ RESOLVED~~
~~**Issue**: Collected preferences not utilized in GPT prompts~~  
~~**Impact**: Missing personalization opportunity despite data collection~~  
**Status**: ✅ **FIXED** - User preferences now integrated into meal generation

### ~~**Gap 2: Live Cart → Real Analysis** ✅ RESOLVED~~
~~**Issue**: Scraper works but test data still used~~  
~~**Impact**: Recommendations don't reflect actual purchased ingredients~~  
**Status**: ✅ **FIXED** - System now properly uses stored cart data with phone format lookup

### **Gap 3: Goals → Ranking Logic**
**Issue**: Goal weights defined but not implemented  
**Impact**: "Quick dinners" goal doesn't prioritize fast recipes  
**Solution**: Implement ranking adjustments based on goals

### **NEW: Cart Data Structure Mismatch**
**Issue**: Customizable boxes sometimes stored in `non_customizable_boxes` array  
**Impact**: Frontend logic fails to detect customizable features  
**Status**: ✅ **FIXED** - Now uses `customizable` flag regardless of storage array

---

## 💻 KEY CODE COMPONENTS

### **Core Files (Modularized Sept 4, 2025)**
```
server/
├── server.py                # FastAPI main app (1647 lines, down from 2000+) ✅
├── templates/
│   ├── dashboard.html       # LEGACY: 2954 lines monolith (backup)
│   └── dashboard_refactored.html # NEW: Clean HTML only (750 lines) ✅
├── static/js/modules/       # NEW: Modular JavaScript architecture
│   ├── shared.js           # Global state, utilities, event bus (140 lines) ✅
│   ├── cart-manager.js     # Cart analysis & display (450 lines) ✅
│   ├── meal-planner.js     # Meal calendar & ingredients (650 lines) ✅
│   └── settings.js         # User preferences (430 lines) ✅
└── services/               # NEW: Backend services (Sept 3)
    ├── phone_service.py     # Phone normalization ✅
    ├── sms_handler.py       # SMS routing ✅
    ├── account_service.py   # User account lookup ✅
    ├── scraper_service.py   # Cart scraping orchestration ✅
    ├── meal_generator.py    # Meal plan generation ✅
    ├── cart_service.py      # Cart analysis with caching ✅
    ├── cache_service.py     # Redis integration (1hr TTL) ✅
    ├── encryption_service.py # Fernet encryption (replacing base64) ✅
    ├── data_isolation_service.py # User data isolation ✅
    └── meal_flow_service.py # Complete flow orchestration ✅

generators/                  # PDF/HTML generation
├── pdf_minimal.py           # Penny-style PDF generator ✅
└── templates/
    └── meal_plan_minimal.html # Clean design, no emojis ✅

scrapers/
├── comprehensive_scraper.py  # PRIMARY: Full cart extraction ✅
└── auth_helper.py           # Authentication handling ✅
```

### **Architecture Improvements (Sept 3-4, 2025)**
1. **Services Architecture**: Extracted 11 services from monolithic server.py
2. **Phone Normalization**: Centralized E.164 format prevents cross-user data contamination
3. **Redis Caching**: 1-hour TTL with force refresh option
4. **Fernet Encryption**: Replaced insecure base64 password storage
5. **Dashboard Modularization**: Split 2954-line file into clean modules
6. **Real Ingredient Tracking**: Replaced mock percentages with actual allocation
7. **Event-Driven Communication**: Modules communicate via event bus
8. **Proper State Management**: Global AppState object for cross-module data

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

---

## 🚨 CRITICAL ENVIRONMENT VARIABLES

```bash
# Required in .env file
EMAIL=your@email.com              # Farm to People login (or FTP_EMAIL)
PASSWORD=yourpassword             # Farm to People password (or FTP_PWD)
VONAGE_API_KEY=xxx               # SMS service
VONAGE_API_SECRET=xxx            
VONAGE_PHONE_NUMBER=18334391183  # System phone number
YOUR_PHONE_NUMBER=+1234567890    # Test recipient
OPENAI_API_KEY=xxx               # GPT-4 access
SUPABASE_URL=xxx                 # Database URL
SUPABASE_KEY=xxx                 # Database key
```

---

## 📈 KEY METRICS & TARGETS

### **Web App Performance**
- Onboarding Completion: >85% target (7-step flow)
- Existing User Recognition: >95% accuracy
- Cart Scraping Speed: <30 seconds with real credentials
- Dashboard Load Time: <3 seconds
- Settings Update Success: >99%

### **Technical Performance**
- Scraper Success Rate: >95% (✅ tested with real data)
- Database Operations: >99% uptime (Supabase)
- Railway Deployment: >99.5% availability
- AI Response Quality: GPT-5 production ready

### **Protein Requirements (NEW)**
- Women: 30g minimum per meal
- Men: 35-40g minimum per meal
- All meals must show protein content

---

## 🎯 NEXT SPRINT GOALS (Priority Order)

### **✅ Sprint 1: Web App Foundation (COMPLETED 8/28)**
1. ✅ Complete 7-step onboarding with user detection
2. ✅ Build settings system with full CRUD operations  
3. ✅ Connect live cart data to dashboard
4. ✅ Deploy to production on Railway

### **🚧 Sprint 2: Meal Planning Integration (Week of 9/2)**
1. Connect user preferences to GPT-5 meal generation
2. Generate recipe PDFs with full cooking instructions
3. Add cart total calculations with pricing transparency
4. Implement confirmation flow before recipe generation

### **📋 Sprint 3: User Experience Polish (Week of 9/9)**
1. Add meal calendar visualization for weekly planning
2. Build weekly feedback collection and rating system
3. Implement error recovery and retry mechanisms
4. Add analytics tracking for user behavior insights

### **🔮 Sprint 4: Advanced Features (Week of 9/16)**
1. SMS integration for notifications and updates
2. Seasonal intelligence for produce availability
3. Learning system that evolves with user preferences
4. Advanced personalization based on cooking history

---

## 🎯 MODULAR DASHBOARD SYSTEM (NEW - Sept 4, 2025)

### **Why We Refactored**
The original dashboard.html had grown to 2954 lines - unmaintainable and prone to bugs. The new modular system:
- **Separates concerns**: Each feature in its own file
- **Enables real ingredient tracking**: No more mock percentages
- **Improves maintainability**: Update features independently
- **Adds proper state management**: Cross-module communication via event bus

### **Module Communication**
```javascript
// Example: Cart module notifies Meal module
eventBus.emit('cart-analyzed', cartData);

// Meal module listens and responds
eventBus.on('cart-analyzed', (cartData) => {
    this.initializeMealPlan(cartData);
});
```

### **Key API Endpoints Used by Modules**
- `POST /api/analyze-cart` - Cart analysis with force refresh
- `GET /api/user-settings` - Load user preferences
- `POST /api/update-preferences` - Save preference changes
- `POST /api/generate-weekly-meals` - Generate meal plan from ingredients
- `POST /api/regenerate-meal` - Replace single meal
- `POST /api/generate-recipe` - Create full recipe PDF

### **Deployment Steps**
1. **Test locally first**: `python server/server.py`
2. **Replace dashboard**: `mv dashboard.html dashboard_backup.html && mv dashboard_refactored.html dashboard.html`
3. **Verify static files**: Check `/static/js/modules/` accessible
4. **Push to production**: Git commit and Railway auto-deploys

## 🆘 TROUBLESHOOTING

### 🔴 **CRITICAL: Phone Number Format Issues - HAPPENS FREQUENTLY!**
**If cart shows old data or "user not found" - CHECK THIS FIRST:**
```bash
# THE PROBLEM: Phone stored as 4254955323 but queried as +14254955323
# SYMPTOMS: Old cart data, failed analysis, "user not found"

# QUICK DIAGNOSTIC:
source venv/bin/activate
python -c "
import sys; sys.path.insert(0, 'server')
import supabase_client as db
phone = '4254955323'  # <-- YOUR PHONE NUMBER
user = db.get_user_by_phone(phone)
cart = db.get_latest_cart_data(phone)
print(f'✅ User found: {bool(user)}')
print(f'✅ Cart found: {bool(cart)}')
if cart: 
    data = cart.get('cart_data', {})
    if data.get('customizable_boxes'):
        print('Cart items:', [i['name'][:20] for i in data['customizable_boxes'][0]['selected_items'][:3]])
"

# PERMANENT FIX: See docs/PHONE_NUMBER_CRITICAL.md
# QUICK DEBUG: See DEBUGGING_PHONE_ISSUES.md
```

### **Common Issues**
```bash
# Virtual environment not activated
command not found: python
# Fix: source venv/bin/activate

# Server not restarting
Changes not reflected
# Fix: ps aux | grep server.py && kill [PID]

# Python indentation errors preventing startup
IndentationError: expected an indented block
# Fix: Check server.py for consistent indentation (spaces vs tabs)

# Cart analysis shows "Please analyze your cart first"
mealPlanData not set despite cart being analyzed
# Fix: Ensure showCartAnalysis() sets mealPlanData = { cart_data: cartData }

# Phone number format mismatch
Cart data not found despite being stored in Supabase
# Fix: System now tries multiple formats: phone, +phone, +1phone, 1phone

# Scraper authentication fails
Zipcode modal appears
# Fix: Check EMAIL/PASSWORD in .env

# Date navigation jumping erratically
Meal calendar showing wrong weeks or skipping by months
# Fix: Avoid date mutation - create new Date objects instead of modifying existing ones

# Customizable boxes not detected
Box has customizable=true but appears as non-customizable
# Fix: Check customizable flag, not which array it's stored in
```

---

## 📞 SUPPORT & RESOURCES

- **GitHub Issues:** Report bugs at project repository
- **Documentation:** See `/docs` folder for detailed guides
- **Test Data:** Sample JSONs in `/farm_box_data`
- **Logs:** Check terminal output and `server.log`
- **Debug Protocol:** ALWAYS check DEBUGGING_PROTOCOL.md first

---

## 🚀 DEPLOYMENT CHECKLIST

- [ ] All tests passing
- [ ] Environment variables configured
- [ ] Database migrations complete
- [ ] Vonage webhook configured
- [ ] SSL certificates ready
- [ ] Monitoring enabled (Sentry/DataDog)
- [ ] Error tracking setup
- [ ] Documentation updated
- [ ] Conversation state management tested
- [ ] Rate limiting configured

---

**Last Updated:** August 31, 2025  
**Version:** 3.1.0  
**Status:** Core System Complete - Cart analysis, meal calendar, debugging fixes deployed  
**Recent Fixes:** Phone format lookup, cart detection, delivery date display, date navigation stability  
**Next Sprint:** Week of September 2 - Advanced meal planning features

*This guide provides the essential information for developing and maintaining the Farm to People AI Assistant. For detailed implementation specifics, refer to the documentation index above.*