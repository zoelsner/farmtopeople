# 🚨 MANDATORY DEBUGGING PROTOCOL

## ⚠️ READ THIS FIRST BEFORE TOUCHING ANY SCRAPER CODE

### 🎯 **STEP 1: TEST WORKING SCRIPTS FIRST**
Before changing ANY scraper code, ALWAYS run these tests:

```bash
# Test the working customize scraper
cd scrapers
python customize_scraper.py
```

**Expected output:**
- ✅ "Clicking CUSTOMIZE..." messages
- ✅ Browser visibly clicking into boxes
- ✅ "🔄 Available:" alternative items listed
- ✅ Complete counts (e.g., "7 selected, 8 alternatives")

### 🚨 **IF YOU DON'T SEE THIS OUTPUT, STOP!**
Something is broken. Fix the working script before proceeding.

---

## 📋 **STEP 2: VERIFY DATA COMPLETENESS**

```bash
# Check latest JSON output
ls -lt ../farm_box_data/customize_results_*.json | head -1
```

**Must contain:**
- `"selected_items"` array with items
- `"available_items"` array with alternatives  
- Non-empty alternatives (not `[]`)

---

## 🛠️ **STEP 3: IDENTIFY WHAT'S ACTUALLY BROKEN**

### Common Issues:
1. **Authentication** - Run auth tests first
   - **Environment Variables**: Check BOTH `EMAIL`/`PASSWORD` and `FTP_EMAIL`/`FTP_PWD`
   - **Fresh Sessions**: Clear browser_data or use incognito for login testing
   - **Login Flow**: Email → LOG IN → Password → LOG IN (two-step process)
   - **Zipcode Modal**: Only appears when clicking cart while NOT logged in
2. **Cart access** - Verify cart opens
3. **Customize clicking** - Watch browser behavior
4. **Data extraction** - Check JSON completeness

### Working Scripts to Test:
- `customize_scraper.py` - Full customize functionality
- `simple_scraper.py` - Basic cart scraping  
- `weekly_health_check.py` - System health

---

## 🚫 **NEVER:**
- Change working code without testing first
- Assume integration will work
- Keep "fixing" without reverting to working state
- Ignore missing terminal output messages

---

## ✅ **ALWAYS:**
- Test existing working scripts FIRST
- Watch browser behavior
- Verify terminal output messages
- Check JSON data completeness
- Use working code as foundation

---

*This protocol exists because working scripts were broken by not following it.*
