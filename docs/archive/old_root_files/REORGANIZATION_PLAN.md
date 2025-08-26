# 🏗️ CODEBASE REORGANIZATION PLAN

## Current Issues:
1. **22 documentation files** spread across root and /docs
2. **Test files mixed with production code** in root directory
3. **PDF generators scattered** (7 different PDF-related .py files)
4. **HTML templates in multiple places**
5. **Archive folders have crucial documentation** buried deep
6. **Browser_data folders** (150+ subdirectories of Chrome cache - unnecessary!)

## PROPOSED NEW STRUCTURE:

```
farmtopeople/
├── README.md                    # Main entry point
├── CLAUDE.md                    # AI assistant guide (keep)
├── .env.example                 # Environment template
│
├── /server/                     # All backend code
│   ├── server.py               # Main FastAPI server
│   ├── meal_planner.py         # GPT integration
│   ├── onboarding.py           # Preference analysis
│   ├── supabase_client.py      # Database
│   ├── /models/                # Data models
│   └── /templates/             # HTML templates (all versions)
│
├── /scrapers/                   # Web scraping
│   ├── comprehensive_scraper.py # PRIMARY scraper
│   ├── auth_helper.py          # Authentication
│   └── README.md               # Scraper documentation
│
├── /generators/                 # NEW - All PDF/HTML generation
│   ├── pdf_minimal.py          # Penny-style PDF
│   ├── html_generator.py       # HTML meal plans
│   └── /templates/             # Design templates
│
├── /data/                       # Data storage
│   ├── /scraped/               # Raw scraper output
│   └── /samples/               # Test data
│
├── /tests/                      # NEW - All test files
│   ├── test_scraper.py
│   ├── test_meal_planner.py
│   └── test_pdf_generation.py
│
├── /docs/                       # CONSOLIDATED documentation
│   ├── README.md               # Documentation index
│   ├── ARCHITECTURE.md         # System design (consolidated)
│   ├── BUSINESS_FLOW.md        # User journey & requirements
│   ├── DEVELOPMENT.md          # Setup & deployment
│   └── /archive/               # Historical docs
│
└── /archive/                    # Old implementations
```

## FILES TO DELETE:
- `browser_data/` folders (150+ Chrome cache directories!)
- Duplicate test PDFs in root
- Old HTML files in root
- Redundant backup files (*_BACKUP.py)

## DOCUMENTATION CONSOLIDATION:

### 1. **ARCHITECTURE.md** (merge from):
- architecture_analysis.md
- conversational_ai_architecture.md  
- REDIS_STATE_MANAGEMENT.md
- refactoring_opportunities.md

### 2. **BUSINESS_FLOW.md** (merge from):
- updated_business_flow.md
- system_gap_analysis.md
- ONBOARDING_SYSTEM.md
- dietary_intake_flow.md

### 3. **DEVELOPMENT.md** (merge from):
- CLOUD_DEPLOYMENT_PLAN.md
- RAILWAY_DEPLOYMENT_GUIDE.md
- DEBUGGING_PROTOCOL.md
- SOP.md

### 4. **Keep CLAUDE.md** as is (it's good)

### 5. **Archive these** (important but not daily use):
- IMPLEMENTATION_PLAN_WEEK1.md
- PDF_DESIGN_MILESTONE.md
- All market analysis docs

## CRITICAL PATH UPDATES NEEDED:

### Files with path dependencies to update:
1. **server.py** - Update template paths
2. **scrapers/comprehensive_scraper.py** - Update output paths
3. **meal_planner.py** - Update data file paths
4. **All test files** - Update import paths

## INSIGHTS TO PRESERVE:

### From Today's Work:
- **Penny-style minimal design wins** (meal_plan_minimal.html)
- **Single-page PDF is better** than multi-page
- **No emojis, subtle typography** is more professional
- **Direct scraper→planner connection** (no file intermediary)
- **GPT-5 in production** (not GPT-4)

### Key Technical Decisions:
- **Playwright for scraping** (not Selenium)
- **Supabase for user data** (not local storage)
- **Vonage for SMS** (not Twilio)
- **HTML→PDF** better than ReportLab direct

### Critical Gaps Still Present:
1. Preferences collected but not fully utilized
2. Cart total calculations missing
3. Confirmation flow before recipe generation
4. State management for conversations
5. Recipe modification handlers

## EXECUTION ORDER:

1. **Create new directories** (/generators, /tests, /data/scraped, /data/samples)
2. **Move files to correct locations**
3. **Update all import paths**
4. **Consolidate documentation** 
5. **Delete unnecessary files**
6. **Update README with new structure**
7. **Test everything still works**

## FILES THAT STAY IN ROOT:
- README.md
- CLAUDE.md
- .env.example
- requirements.txt
- setup_supabase.py (database setup)
- .gitignore

## What Gets Archived:
- All *_BACKUP.py files
- Old scraper versions
- Test PDFs and HTMLs
- Experiment files (test_*.py moving to /tests)

This reorganization will reduce clutter by ~60% and make the codebase much more navigable.