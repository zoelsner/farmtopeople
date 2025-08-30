# 📚 Documentation Index

**Project:** Farm to People AI Assistant  
**Updated:** August 26, 2025 (Monday night)  
**Status:** Core complete, shipping Friday

## 📍 CURRENT DOCUMENTATION (Use These!)

### [📐 ARCHITECTURE.md](ARCHITECTURE.md)
System design, technical architecture, component relationships, data flow, and technology choices.

**Key Sections:**
- Core components (scraper, planner, SMS, database)
- Data flow diagrams
- Technical decisions (Playwright, GPT-5, Vonage, Supabase)
- Performance optimizations
- Security considerations

### [💼 BUSINESS_FLOW.md](BUSINESS_FLOW.md)
User journey, business logic, value propositions, and success metrics.

**Key Sections:**
- Complete user journey (onboarding → weekly planning → feedback)
- Preference intelligence system
- Customer segments
- Business rules
- Success metrics

### [🛠️ DEVELOPMENT.md](DEVELOPMENT.md)
Setup instructions, deployment guide, debugging tips, and common commands.

**Key Sections:**
- Local development setup
- GPT-5 configuration (IT WORKS!)
- Railway deployment
- Troubleshooting guide
- Performance optimization

## Quick Reference

### Most Important Files:
- **Primary Scraper:** `scrapers/comprehensive_scraper.py`
- **Meal Planner:** `server/meal_planner.py` (uses GPT-5)
- **Best PDF Design:** `generators/templates/meal_plan_minimal.html` (Penny-style)
- **Design Reference:** `docs/PENNY_MENU_DESIGN_REFERENCE.md` + actual menu PDF
- **Main Server:** `server/server.py`

### Key Technical Decisions:
- **GPT-5** is in production (model="gpt-5")
- **No emojis** in PDFs - clean typography only
- **Direct data passing** - no intermediate files
- **HTML→PDF** better than ReportLab
- **Penny aesthetic** wins over decorated designs
### API and Module Docs

- See the new API reference in `docs/api/`:
  - [HTTP Endpoints](api/http_endpoints.md)
  - [Server Modules](api/server_modules.md)
  - [Generators](api/generators.md)
  - [Scrapers](api/scrapers.md)

### This Week's Milestones:
- ✅ Monday AM: Connected scraper to meal planner
- ✅ Monday PM: Added preferences to GPT prompts
- ✅ Tuesday AM: Created Penny-style minimal PDF
- ⏳ Tuesday PM: Add help text to SMS
- ⏳ Wednesday: Redis state management
- ⏳ Thursday: Instant acknowledgments & modifications
- ⏳ Friday: Production deployment

## 📂 Archive Structure

```
docs/
├── README.md                    # This file
├── ARCHITECTURE.md              # Current system design ✅
├── BUSINESS_FLOW.md            # Current user journey ✅
├── DEVELOPMENT.md              # Current setup guide ✅
└── archive/
    ├── project_history/        # Planning & analysis docs
    │   └── README.md           # Explains timeline & context
    ├── august_2025_refactor/   # Scraper debugging history
    └── old_root_files/         # Cleaned from root directory
```

## ⚠️ Important Timeline Context

We're in **Week 3** of development:
- **Week 1** (Aug 18-19): Initial setup & research
- **Week 2** (Aug 21-24): Design & planning
- **Week 3** (Aug 25-30): Implementation week ← **WE ARE HERE**

The "IMPLEMENTATION_PLAN_WEEK1.md" in archives was created TODAY (Monday Aug 25) as our accelerated ship plan, not in Week 1!

## Key Insights Preserved

### From Development:
1. **Less is more** - Single-page PDFs beat multi-page
2. **GPT-5 works** - Despite documentation saying otherwise
3. **Typography > Graphics** - No emojis, clean design
4. **Direct > Files** - Pass data directly, skip file I/O
5. **Explicit > Magic** - Show users their cart contents

### From User Research:
1. **Speed matters** - 30-second total response time max
2. **SMS preferred** - No app downloads
3. **Protein focus** - 30g+ per meal is critical
4. **Swaps essential** - Flag preference conflicts

### From Technical Implementation:
1. **Playwright > Selenium** - Better modal handling
2. **Vonage > Twilio** - Simpler webhooks
3. **Supabase > Local DB** - Built-in features
4. **HTML templates > ReportLab** - More control

---

*For AI assistants: Start with ARCHITECTURE.md for technical understanding, BUSINESS_FLOW.md for product context, and DEVELOPMENT.md for implementation details.*