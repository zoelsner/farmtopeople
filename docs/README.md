# 📚 Documentation Index

**Project:** Farm to People AI Assistant  
**Updated:** August 26, 2025  
**Status:** Core complete, shipping this week

## Primary Documents

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
- **Main Server:** `server/server.py`

### Key Technical Decisions:
- **GPT-5** is in production (model="gpt-5")
- **No emojis** in PDFs - clean typography only
- **Direct data passing** - no intermediate files
- **HTML→PDF** better than ReportLab
- **Penny aesthetic** wins over decorated designs

### This Week's Milestones:
- ✅ Monday AM: Connected scraper to meal planner
- ✅ Monday PM: Added preferences to GPT prompts
- ✅ Tuesday AM: Created Penny-style minimal PDF
- ⏳ Tuesday PM: Add help text to SMS
- ⏳ Wednesday: Redis state management
- ⏳ Thursday: Instant acknowledgments & modifications
- ⏳ Friday: Production deployment

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