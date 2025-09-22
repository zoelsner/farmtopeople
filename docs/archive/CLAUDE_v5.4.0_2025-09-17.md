# 🤖 CLAUDE.md - Farm to People AI Assistant Development Guide

## 🎯 PROJECT OVERVIEW

**Farm to People AI Assistant** transforms weekly produce boxes into personalized meal plans through intelligent SMS conversations. The system learns user preferences, analyzes cart contents, and delivers actionable cooking guidance.

**Current Status:** Cart Scraper Fixed - Stale data issue resolved, performance restored
**Last Updated:** September 16, 2025
**Version:** 5.5.0 (Scraper Stale Data Fix + Performance Restoration)
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

# 5. Test dashboard variants (experimental)
open http://localhost:8000/dashboard-v3.html
```

### **Critical Development Rules**
- ✅ ALWAYS activate venv before running Python code
- ✅ Use GPT-5 (model="gpt-5") - it works in production!
- ✅ Test comprehensive_scraper.py before making changes
- ✅ Restart server after code modifications
- ✅ Best PDF design: `generators/templates/meal_plan_minimal.html` (Penny-style)
- ✅ **Protein in titles:** "38g protein" must be prominent under each meal name
- ✅ NEVER use GPT-3.5 - use GPT-5 or gpt-4o-mini only

### **🚨 CRITICAL: Smart Meal Generation & Frontend Debugging (Sept 16, 2025)**
**Key learnings for meal categorization and UI updates:**
- ⚠️ **Multiple updateMealSuggestions functions** - dashboard.html has TWO functions (lines 2713 & 3089). Line 3089 is the one actually used!
- ⚠️ **Time parsing bug** - "10-12 min" was parsed as 1012 minutes. Fixed with range handling: `time_part.split('-')[0]`
- ⚠️ **Backend categorization logic** - Based on cooking time (<20 min) AND ingredients (yogurt, cups, fruit) for snacks
- ✅ **Complete implementation details** - See docs/MEAL_LOCKING_SYSTEM_PLAN.md for full Phase 1 documentation

### **🚨 CRITICAL: Cart Scraper Debugging Lessons (Sept 16, 2024)**
**BEFORE adding complexity to fix stale data, check these first:**
- ⚠️ **Variable scope conflicts** - Watch for `os`, `email`, `datetime` shadowing
- ⚠️ **Modal timing** - Farm to People loads content dynamically (needs 3s wait)
- ⚠️ **Don't assume external caching** - Test with diagnostics first
- ⚠️ **Simplicity first** - Remove complexity before adding more
- ⚠️ **Performance baseline** - Current: 40s, Target: 25s (with smart optimizations)
- 📖 **Full lessons:** See `docs/SCRAPER_DEBUGGING_LESSONS_2024_09.md`

---

## 📚 DOCUMENTATION INDEX

### **Business & Product Docs**
- [`docs/complete_business_flow.md`](docs/complete_business_flow.md) - End-to-end customer journey with confirmation flow
- [`docs/updated_business_flow.md`](docs/updated_business_flow.md) - Latest requirements (high-protein, meal calendar)
- [`docs/system_gap_analysis.md`](docs/system_gap_analysis.md) - Current gaps and improvement roadmap
- [`docs/ONBOARDING_SYSTEM.md`](docs/ONBOARDING_SYSTEM.md) - Preference collection implementation

### **Technical Documentation**
- [`docs/dashboard-v3-status.md`](docs/dashboard-v3-status.md) - **NEW:** Dashboard v3 modularization status
- [`docs/dashboard-refactoring-plan.md`](docs/dashboard-refactoring-plan.md) - **NEW:** Complete refactoring architecture
- [`DEPLOYMENT_INSTRUCTIONS.md`](DEPLOYMENT_INSTRUCTIONS.md) - **NEW:** Dashboard v3 deployment guide
- [`docs/MEAL_CALENDAR_IMPLEMENTATION_PLAN.md`](docs/MEAL_CALENDAR_IMPLEMENTATION_PLAN.md) - Complete meal planning system design
- [`docs/CODEBASE_AUDIT_REPORT_AUG31.md`](docs/CODEBASE_AUDIT_REPORT_AUG31.md) - Comprehensive architecture audit
- [`database/meal_planning_schema.sql`](database/meal_planning_schema.sql) - Database schema for meal planning
- [`docs/refactoring_opportunities.md`](docs/refactoring_opportunities.md) - Architecture improvements & conversation state management
- [`docs/conversational_ai_architecture.md`](docs/conversational_ai_architecture.md) - AI system design patterns
- [`docs/SCRAPER_DEBUGGING_LESSONS_2024_09.md`](docs/SCRAPER_DEBUGGING_LESSONS_2024_09.md) - **NEW:** Sept 2024 stale data debugging lessons
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

### 🔄 **UNIFIED MEAL DATA FLOW (New - Sept 15, 2025)**

The system now maintains one source of truth for meal data across both Cart and Meals tabs:

```
Cart Tab Analysis → GPT-5 API → localStorage cache → Meals Tab Sync
     ↓                              ↓                      ↓
Meal suggestions        Cache: cachedMealSuggestions    Featured meal display
"Try Different"    →    updateMealSuggestions()    →    populateSimpleMealCard()
     ↓                              ↓                      ↓
Both tabs update simultaneously with same meal data
```

**Key Functions:**
- `syncMealsFromCart()` - Pulls GPT meals from localStorage to Meals tab
- `populateSimpleMealCard(meal)` - Displays actual meal data (name, time, protein)
- `regenerateSimpleMeal()` - Uses same `/api/refresh-meals` as Cart tab
- `updateMealSuggestions(meals)` - Updates both tabs when new meals generated

**Data Sources (Priority Order):**
1. `localStorage.cachedMealSuggestions` - Fresh GPT-generated meals
2. Cart tab DOM extraction - Fallback from `mealSuggestionsContainer`
3. Empty state - If no meal data available

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

### **Dashboard Navigation (PWA Fixed with iframe approach!)**
- **Cart Tab:** Live cart analysis with delivery date
- **Meals Tab:** Weekly meal calendar with drag-and-drop (Monday-Friday)
- **Settings Tab:** iframe modal (loads settings.html in modal - NO page refresh!) ✅ PWA navigation fixed

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

### ✅ **LATEST FIXES (Sept 15, 2025 - Cart Scraper Debugging)**
- **✅ Fixed Cart Analysis Hanging**: Resolved datetime scope bug in comprehensive_scraper.py line 875
- **✅ Fixed UI State Management**: Cart section now properly hides during loading
- **✅ Added Comprehensive Logging**: Server and scraper now log detailed progress with timestamps
- **✅ Added Timeout Protection**: 120-second timeout prevents indefinite hanging with fallback to cached data
- **✅ Improved Error Handling**: Better error messages and graceful fallbacks

### ❌ **KNOWN ISSUES (Remaining)**
- **Cart Lock Calculation Bug**: Shows wrong day (Sun instead of Wed) and disappears on refresh
- **Delivery Date Format**: Shows full string instead of clean "Thu • 4:00PM" format
- **Performance Issue**: Scraping takes ~50 seconds (increased timeouts for reliability)
- **Redis Warning**: "No module named 'server.services'" in scraper (non-critical)

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

### ✅ **COMPLETED THIS WEEK (Sept 15 - GPT-5 Integration & Loading Experience)**
- **✅ Sunday:** Unify meal data between Cart and Meals tabs for consistent experience
- **✅ Sunday:** Replace ingredient listing with actual GPT-generated meal display in Meals tab
- **✅ Sunday:** Create syncMealsFromCart() function for seamless data synchronization
- **✅ Sunday:** Connect Meals tab regeneration to existing /api/refresh-meals endpoint
- **✅ Sunday:** Add automatic sync when switching between tabs
- **✅ Sunday:** Implement clean UI design with subtle colors and improved typography
- **✅ Sunday:** Ensure zero risk to Cart tab functionality (safe implementation)
- **✅ Sunday:** Create one source of truth for meal data across application
- **✅ Sunday:** Implement GPT-5 Redis meal caching for persistence across page refreshes
- **✅ Sunday:** Fix duplicate progress timer issues during cart refresh operations
- **✅ Sunday:** Repair "New Suggestions" button functionality with Redis integration
- **✅ Sunday:** Enhance loading experience with progress bar, timer, and cancel button
- **✅ Sunday:** Optimize spinner animations for smooth performance across browsers

### ✅ **PREVIOUS WEEK (Sept 14 - Dashboard PWA Navigation Fix)**
- **✅ Friday:** Fix PWA navigation issue - Settings now uses iframe modal approach
- **✅ Friday:** Resolve JavaScript conflicts causing blank Settings modal
- **✅ Friday:** Implement iframe-based Settings loading with production UI
- **✅ Friday:** Add iframe detection to hide duplicate navigation
- **✅ Friday:** Create stable PWA experience without page refreshes
- **✅ Friday:** Update comprehensive documentation

### ✅ **PREVIOUS WEEK (8/31 - MEAL CALENDAR & DEBUG FIXES)**
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

### 📝 **PRIORITY FEATURES TO BUILD**

#### 🔴 **High Priority (Next Sprint)**
1. **Complete meals-v3.js Module**
   - Implement drag & drop meal calendar
   - Ingredient pool tracking with visual progress bars
   - Meal regeneration with constraints
   - Conflict detection when moving meals
   - PDF recipe generation integration

2. **Confirmation Flow**
   - User approval modal before recipe generation
   - Preview of what will be created
   - Option to adjust preferences first

3. **Cart Total Calculation**
   - Show total cost in cart analysis
   - Individual item pricing
   - Box pricing breakdown

#### 🟡 **Medium Priority**
4. **Weekly Feedback Loop**
   - Star rating for each meal
   - Quick feedback options (too spicy, perfect, needs more time)
   - Learn from ratings to improve future suggestions

5. **Recipe PDF Generation**
   - Full cooking instructions
   - Shopping list for additional ingredients
   - Nutritional information
   - Print-friendly format

6. **SMS Integration Enhancement**
   - Weekly meal plan delivery via SMS
   - Quick recipe lookup by texting meal name
   - Cooking timer reminders

#### 🟢 **Nice to Have**
7. **Seasonal Intelligence**
   - Know what's in season locally
   - Suggest recipes based on seasonal availability
   - Weather-based meal suggestions

8. **Preference Evolution**
   - Machine learning from user choices
   - Automatically adjust spice levels, cooking times
   - Family member preference profiles

9. **Social Features**
   - Share recipes with friends
   - Community recipe ratings
   - Chef tips and tricks

10. **Advanced Analytics**
    - Nutritional tracking over time
    - Cost per meal analysis
    - Waste reduction metrics

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

### ~~**Gap 3: PWA Navigation Breaking** ✅ RESOLVED~~
~~**Issue**: Settings tab caused page refresh, breaking PWA experience~~
~~**Impact**: Users lost context when switching tabs~~
**Status**: ✅ **FIXED** - Settings now uses iframe modal approach

### **Gap 4: Goals → Ranking Logic** 🚧 PENDING
**Issue**: Goal weights defined but not implemented
**Impact**: "Quick dinners" goal doesn't prioritize fast recipes
**Solution**: Implement ranking adjustments in meal generation API

### ~~**Gap 5: Cart Data Structure Mismatch** ✅ RESOLVED~~
~~**Issue**: Customizable boxes sometimes stored in wrong array~~
~~**Impact**: Frontend logic failed to detect customizable features~~
**Status**: ✅ **FIXED** - Now uses `customizable` flag regardless of storage array

---

## 💻 KEY CODE COMPONENTS

### **Core Files (Unified Meal Data + Clean UI - Sept 15, 2025)**
```
server/
├── server.py                # FastAPI main app with iframe Settings route ✅
├── templates/
│   ├── dashboard.html       # PRIMARY: Main dashboard (3652 lines) with iframe Settings ✅
│   ├── settings.html        # Settings page loaded in iframe (566 lines) ✅
│   ├── dashboard-v3.html    # EXPERIMENTAL: Modular attempt (unused)
│   └── dashboard-modular*.html # EXPERIMENTAL: Various attempts (unused)
├── static/js/modules/       # Various JavaScript modules (mixed usage)
│   ├── Various .js files   # Some used, some experimental
├── static/css/
│   ├── dashboard-base.css      # Core styles (existing) ✅
│   ├── dashboard-components.css # Reusable UI (new) ✅
│   └── dashboard-modules.css    # Module-specific (new) ✅
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

### **Architecture Improvements (Sept 14, 2025 - PWA Navigation Fixed)**
1. **PWA Navigation Fixed**: Settings uses iframe modal, no page refreshes!
2. **iframe-based Settings**: Loads production settings.html in modal overlay
3. **Duplicate Navigation Hidden**: Automatically detects iframe context and hides navigation
4. **JavaScript Conflict Resolution**: Fixed duplicate function conflicts causing blank modals
5. **Services Architecture**: Extracted 11 services from monolithic server.py
6. **Phone Normalization**: Centralized E.164 format prevents cross-user data contamination
7. **Redis Caching**: 1-hour TTL with force refresh option
8. **Fernet Encryption**: Replaced insecure base64 password storage
9. **Real Ingredient Tracking**: Replaced mock percentages with actual allocation
10. **Production UI Quality**: Maintains beautiful card-based settings UI in iframe

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

## 🎯 DASHBOARD PWA NAVIGATION SYSTEM (FIXED - Sept 14, 2025)

### **The iframe Settings Modal Solution**
The dashboard.html had critical PWA issues where Settings caused page refreshes. Our solution:
- **PWA Navigation Fixed**: Settings loads in iframe modal, no page refresh!
- **Preserves Production UI**: Uses existing beautiful settings.html interface
- **Automatic Navigation Hiding**: Detects iframe context and hides duplicate navigation
- **Maintains User Context**: Users never lose their place in the dashboard
- **Simple Implementation**: Minimal code changes, maximum compatibility

### **Implementation Details**
```javascript
// iframe-based openSettingsModal function in dashboard.html (lines 2445-2563)
function openSettingsModal() {
    console.log('🔧 openSettingsModal called - using iframe approach');
    const iframe = document.createElement('iframe');
    const phone = localStorage.getItem('userPhone') || getPhoneNumber();
    iframe.src = `/settings?phone=${phone}&iframe=true`;
    // ... create modal overlay and insert iframe
}

// iframe detection in settings.html (lines 547-564)
const isInIframe = window.self !== window.top;
const iframeParam = urlParams.get('iframe') === 'true';
if (isInIframe || iframeParam) {
    // Hide bottom navigation when loaded in iframe
    const bottomTabs = document.querySelector('.bottom-tabs');
    if (bottomTabs) bottomTabs.style.display = 'none';
}
```

### **Key Benefits of iframe Approach**
- **Zero Page Refreshes**: Maintains PWA experience
- **Production UI Quality**: Full settings.html functionality
- **Easy Maintenance**: Settings page remains independent
- **Cross-Device Compatible**: Works on mobile and desktop
- **Backwards Compatible**: Original settings route still works

## ⚠️ IMPORTANT: Features to Preserve

When making changes, ensure these working features are NOT broken:

### **Critical Functionality**
1. **Phone-first onboarding** - Existing users skip to step 7
2. **Cart scraping** - comprehensive_scraper.py captures all box types
3. **Delivery date display** - Green text in top-right corner
4. **Refresh limit** - 3x per day for cart analysis
5. **Phone format handling** - Try multiple formats when querying
6. **Customizable box detection** - Check `customizable` flag, not array location
7. **PWA navigation** - NO page refreshes when switching tabs (dashboard v3)
8. **Settings modals** - Edit preferences without navigation
9. **Cart lock time** - 11:59 AM ET day before delivery

### **Data Persistence**
- User preferences saved to Supabase
- Cart data cached for 1 hour
- Settings persist across sessions
- Phone number drives all lookups

### **User Experience**
- Smooth tab transitions
- Loading states for all async operations
- Error messages are user-friendly
- Mobile-responsive design
- PWA installable

## 🆘 TROUBLESHOOTING

### 🔴 **NEW: Cart Analysis Issues (Sept 15, 2025)**

**Cart Stuck on "Analyzing Your Cart" Screen:**
```bash
# SYMPTOMS: Loading spinner stuck, console shows cart data loaded but UI doesn't update
# CAUSE: UI state management bug - multiple sections active simultaneously
# STATUS: ✅ FIXED - Cart section now properly hides during loading

# Check console for these logs:
"🔄 startAnalysis() - State transition to loading"
"Active sections after showCartAnalysis: {start: false, loading: false, cart: true}"

# If you see cart: true during loading, this indicates the old bug
```

**Scraper Returns Old Cart Data:**
```bash
# SYMPTOMS: Fresh scrape returns Monday cart instead of Thursday cart
# CAUSE: DateTime scope bug causing scraper to crash and fall back to cached data
# STATUS: ✅ FIXED - Removed duplicate datetime import in comprehensive_scraper.py line 875

# Check server logs for:
"❌ Scraper failed with error: cannot access local variable 'datetime'"
"⚠️ Scraper returned no data or timed out"
"✅ Using previously stored cart data as fallback"
```

**Cart Lock Time Wrong/Missing:**
```bash
# SYMPTOMS: Shows "Sun 11:59AM" instead of "Wed 11:59AM" or disappears on refresh
# CAUSE: Date parsing logic in dashboard.html needs fixing
# STATUS: ❌ KNOWN ISSUE

# Cart should lock day before delivery:
# Thu delivery → Wed 11:59 AM lock time
# Current calculation is incorrect
```

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

### **Settings Modal Issues (Fixed Sept 14, 2025)**
```bash
# Settings tab shows blank modal
# CAUSE: Duplicate openSettingsModal functions with ID conflicts
# SYMPTOM: "Cannot set properties of null (setting 'textContent')" at line 3575
# Fix: Remove duplicate function, rename modal wrapper ID from 'settingsModalContent' to 'settingsModalWrapper'

# Settings modal shows duplicate bottom navigation
# CAUSE: iframe loads settings.html which has its own navigation
# SYMPTOM: Two sets of bottom tabs visible
# Fix: Add iframe detection script to settings.html that hides bottom navigation

# Settings tab causes page refresh (breaks PWA)
# CAUSE: Original Settings implementation navigated to new page
# SYMPTOM: User loses context, app refreshes
# Fix: Use iframe approach - load settings.html?iframe=true in modal overlay
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

### **For Dashboard PWA Navigation**
- [x] Test all tabs - NO page refreshes
- [x] Settings iframe modal opens/closes properly
- [x] Settings shows production UI without duplicate navigation
- [x] Cart analysis completes
- [x] Delivery date displays
- [x] Phone format handling works
- [x] Mobile PWA tested
- [x] Browser back/forward works

### **General Deployment**
- [x] Environment variables configured
- [x] Database schema complete
- [x] Vonage webhook configured (SMS: 18334391183)
- [x] Railway deployment working
- [x] SSL certificates active
- [ ] Monitoring enabled (Sentry/DataDog)
- [x] Error tracking via console logs
- [x] Documentation updated (CLAUDE.md current)
- [ ] Rate limiting configured
- [ ] Load testing completed

---

**Last Updated:** September 15, 2025
**Version:** 5.4.0 (Cart Scraper Fixes + Comprehensive Logging)
**Status:** Cart Analysis System Fully Debugged and Operational
**Recent Updates:**
- Fixed critical datetime scope bug preventing fresh cart scraping
- Resolved UI state management issues causing stuck loading screens
- Added comprehensive logging with timestamps throughout scraper workflow
- Implemented 120-second timeout protection with graceful fallbacks
- Cart scraping now successfully captures Thursday delivery dates
- GPT-5 integration with full reasoning_effort compatibility
- Redis meal caching for persistence across page refreshes
- Fixed duplicate progress timer issues and "New Suggestions" button
- Enhanced loading experience with progress bar, timer, and cancel functionality
- Optimized spinner animations for smooth cross-browser performance
- Removed localStorage dependencies in favor of Redis caching
**Known Issues & Next Steps:**
- Cart lock calculation wrong day (shows Sun instead of Wed) and disappears on refresh
- Delivery date formatting needs cleanup (full string vs clean "Thu • 4:00PM" format)
- Scraper performance optimization (currently takes ~50 seconds)
- Redis warning "No module named 'server.services'" in scraper (non-critical)
**Next Sprint:** Fix remaining UI polish issues, optimize scraper performance, premium add-ons refresh integration

*This guide provides the essential information for developing and maintaining the Farm to People AI Assistant. For detailed implementation specifics, refer to the documentation index above.*