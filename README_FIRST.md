# 🚨 READ THIS FIRST - SCRAPER DEBUGGING

## ⚠️ BEFORE TOUCHING ANY SCRAPER CODE

### 🎯 **ALWAYS RUN THIS FIRST:**
```bash
cd scrapers
python verify_working_state.py
```

If this fails, **DO NOT** proceed with changes.

### 🔧 **Test the Working Scraper:**
```bash
python customize_scraper.py
```

**Must see:**
- "Clicking CUSTOMIZE..." messages
- Browser clicking into boxes
- "🔄 Available:" alternatives listed

### 📋 **Debugging Protocol:**
See `DEBUGGING_PROTOCOL.md` for complete checklist.

### 📚 **Lessons Learned:**
See `CRITICAL_SCRAPING_LESSONS_LEARNED.md` for what went wrong before.

---

## 🎯 **CURRENT WORKING SCRAPER:**
- **File:** `customize_scraper.py`
- **Status:** ✅ Production ready
- **Last verified:** August 16, 2025

**This scraper clicks into boxes and extracts alternatives correctly.**

---

*Test working scripts FIRST. Always.*
