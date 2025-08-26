# 🌱 Farm to People AI Assistant

Transform weekly produce deliveries into personalized meal plans via SMS. Learn preferences, reduce waste, increase satisfaction.

## What It Does

1. **Texts customers** after cart closes: "Your meal plan is ready!"
2. **Analyzes their cart** using web scraping (Playwright)
3. **Generates 5 meals** with GPT-5 based on preferences
4. **Delivers recipes** as clean, single-page PDFs

## Quick Start

```bash
# Setup
git clone https://github.com/farmtopeople/ai-assistant.git
cd farmtopeople
git checkout feature/customer-automation
python -m venv venv
source venv/bin/activate  # ALWAYS DO THIS FIRST!
pip install -r requirements.txt
playwright install chromium

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run
python server/server.py
```

## Key Features

✅ **Smart Scraping** - Captures all cart types (individual items, boxes)  
✅ **Preference Learning** - 6-step onboarding collects dietary needs  
✅ **GPT-5 Powered** - Yes, GPT-5 works (model="gpt-5")  
✅ **SMS Simple** - No app needed, just text messaging  
✅ **Penny-Style PDFs** - Clean typography, no emojis  

## Architecture

```
SMS (Vonage) → Server (FastAPI) → Scraper (Playwright)
                    ↓
              GPT-5 Meal Plan
                    ↓
              HTML/PDF Output
```

## This Week's Schedule

- ✅ **Monday**: Connected scraper→planner, added preferences to GPT
- ✅ **Tuesday AM**: Created Penny-style PDF design
- ⏳ **Tuesday PM**: Add help text to SMS
- ⏳ **Wednesday**: Redis conversation state
- ⏳ **Thursday**: Instant acknowledgments & modifications
- ⏳ **Friday**: Production deployment

## Project Structure

```
/server         # Backend (FastAPI, meal planner)
/scrapers       # Web scraping (Playwright)
/generators     # PDF/HTML generation
/tests          # Test suite
/docs           # Documentation
    ├── ARCHITECTURE.md    # System design
    ├── BUSINESS_FLOW.md   # User journey
    └── DEVELOPMENT.md     # Setup guide
```

## Testing

```bash
# Test scraper
cd scrapers && python comprehensive_scraper.py

# Test full flow
curl -X POST http://localhost:8000/test-full-flow

# Run tests
pytest tests/
```

## Key Technical Decisions

- **Playwright > Selenium** - Better modal handling
- **GPT-5 > GPT-4** - Works in production!
- **Vonage > Twilio** - Simpler webhooks
- **HTML→PDF > ReportLab** - More control
- **No emojis** - Professional aesthetic

## Environment Variables

```bash
OPENAI_API_KEY=sk-...      # Must have GPT-5 access
SUPABASE_URL=...            # Database
SUPABASE_KEY=...
VONAGE_API_KEY=...          # SMS service
VONAGE_API_SECRET=...
VONAGE_PHONE_NUMBER=18334391183
FTP_EMAIL=...               # Test account
FTP_PASSWORD=...
```

## Documentation

- **[Architecture](docs/ARCHITECTURE.md)** - System design & technical details
- **[Business Flow](docs/BUSINESS_FLOW.md)** - User journey & requirements  
- **[Development](docs/DEVELOPMENT.md)** - Setup, deployment, debugging
- **[Claude Guide](CLAUDE.md)** - AI assistant instructions

## Support

- **Issues**: GitHub issues
- **Docs**: See `/docs` folder
- **AI Assistant**: Read CLAUDE.md

---

**Status**: Core complete, shipping Friday  
**Version**: 2.2.0  
**Branch**: `feature/customer-automation`  
**Updated**: August 26, 2025