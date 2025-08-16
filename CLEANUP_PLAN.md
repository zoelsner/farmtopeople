# Farm to People - File Cleanup Plan
*Generated: August 16, 2025*

## 🎯 Objective
Clean up deprecated files while maintaining 110% confidence in system stability.

## ✅ **PHASE 1: SAFE DELETIONS (Immediate)**
These files are confirmed deprecated with zero risk:

### **Deprecated Scrapers**
```bash
# These are all superseded by complete_cart_scraper.py
rm farmbox_optimizer.py
rm capture_customize.py
rm capture_html.py
rm full_scraper.py
rm cart_structure_analyzer.py
```

### **Old Archive Directory**
```bash
# Already archived versions - safe to remove
rm -rf archive/
```

### **Old Debug Files**
```bash
# Old debugging artifacts
rm cart_open.png
rm customize_page.png
rm debug_output.txt
rm -rf debug_screenshots/
```

### **Old Documentation**
```bash
# Superseded documentation
rm SOP_v1_archive.md
rm architecture_analysis.md
rm farm_to_people_market_scan.md
rm ftp_opus_analysis.md
```

### **Old Data Files**
```bash
# Outdated data files
rm farmtopeople_products.csv
```

## ⚠️ **PHASE 2: CAREFUL VERIFICATION (After Phase 1)**
Verify these are not referenced elsewhere before deleting:

### **Data Directory Cleanup**
```bash
# Clean up old test outputs (keep recent working files)
cd farm_box_data/
# Keep files from last 7 days, remove older test files
find . -name "box_contents_202508*" -mtime +7 -delete
find . -name "cart_contents_202508*" -mtime +7 -delete
# Keep all complete_cart_* and weekly_* files (these are production outputs)
```

## 🔄 **PHASE 3: DOCUMENTATION UPDATES**
Update documentation to reflect cleaned architecture:

### **Update SOP.md**
- ✅ Already updated to v3
- Remove any references to deleted files

### **Update FARM_TO_PEOPLE_SCRAPER_GUIDE.md**
- Update to prioritize `complete_cart_scraper.py`
- Remove references to deprecated scrapers
- Update file structure section

### **Update README.md**
- Ensure reflects current architecture
- Remove references to deleted files

## 📂 **FINAL CLEAN ARCHITECTURE**

After cleanup, the project structure will be:

```
farmtopeople/
├── 🏆 PRODUCTION SCRAPERS
│   ├── complete_cart_scraper.py      # PRIMARY
│   ├── simple_scraper.py             # FAST ALTERNATIVE
│   ├── weekly_summary_scraper.py     # CUSTOMER COMM
│   ├── customize_scraper.py          # ALTERNATIVES
│   └── better_capture.py             # DEBUGGING
├── 🌐 SERVER & AI
│   ├── server.py                     # FastAPI server
│   ├── meal_planner.py               # Recipe generation
│   ├── app.py                        # Orchestration
│   └── friend_flow.py                # User onboarding
├── 💾 DATA & CONFIG
│   ├── supabase_client.py            # Database
│   ├── user_database.json            # User data
│   ├── requirements.txt              # Dependencies
│   └── farm_box_data/                # Output directory
├── 📚 DOCUMENTATION
│   ├── SOP.md                        # Main documentation
│   ├── FARM_TO_PEOPLE_SCRAPER_GUIDE.md # Technical guide
│   ├── README.md                     # Project overview
│   ├── COMPREHENSIVE_FILE_AUDIT.md   # This audit
│   └── CLEANUP_PLAN.md              # This plan
└── 🔧 INFRASTRUCTURE
    ├── browser_data/                 # Persistent sessions
    ├── venv/                         # Python environment
    └── __pycache__/                  # Python cache
```

## 🔍 **FILES TO KEEP - VERIFICATION**

### **✅ Confirmed Essential**
- `complete_cart_scraper.py` - PRIMARY SCRAPER ⭐
- `simple_scraper.py` - Fast box scraper
- `better_capture.py` - Debug tool
- `weekly_summary_scraper.py` - Customer communication
- `customize_scraper.py` - Alternative exploration
- `server.py` - FastAPI server
- `meal_planner.py` - AI recipe generation
- `supabase_client.py` - Database connection
- `app.py` - Orchestration script
- `friend_flow.py` - User onboarding system

### **📄 Documentation**
- `SOP.md` - Main documentation (recently updated v3)
- `FARM_TO_PEOPLE_SCRAPER_GUIDE.md` - Technical reference
- `README.md` - Project overview

### **⚙️ Configuration**
- `requirements.txt` - Python dependencies
- `user_database.json` - User data
- `.env` - Environment variables (if exists)

## 🚀 **EXECUTION ORDER**

1. **First**: Execute Phase 1 deletions (zero risk)
2. **Second**: Verify no broken imports after Phase 1
3. **Third**: Execute Phase 2 with verification
4. **Fourth**: Update documentation
5. **Finally**: Test all scrapers still work

## ✅ **VERIFICATION CHECKLIST**

After cleanup, verify:
- [ ] `complete_cart_scraper.py` still works
- [ ] `simple_scraper.py` still works  
- [ ] `better_capture.py` still works
- [ ] No broken imports in any files
- [ ] Documentation reflects reality
- [ ] All file references are valid

This plan ensures 110% confidence in maintaining system stability while achieving a clean, maintainable codebase.
