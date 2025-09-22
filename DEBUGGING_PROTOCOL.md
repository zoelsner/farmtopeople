# 🔧 Debugging Protocol - Farm to People Cart Scraper

## 🚨 Emergency Checklist

When cart scraper is failing or showing stale data, **work through this checklist in order**:

### 1. ✅ **Basic Functionality Check**
```bash
source venv/bin/activate
cd scrapers
python comprehensive_scraper.py
```

**Look for:**
- ❌ `cannot access local variable 'X'` - Variable scope issues
- ❌ `ImportError` - Module path problems
- ❌ Process hangs for >2 minutes - Performance regression

### 2. ✅ **Variable Scope Conflicts**
**Common symptoms:**
- `cannot access local variable 'os'`
- `cannot access local variable 'email'`
- `cannot access local variable 'datetime'`

**Fix:** Check for local imports shadowing global variables:
```python
# ❌ BAD - Creates scope conflicts
def function():
    import os  # Shadows global os import

# ✅ GOOD - Use alias or move to top
def function():
    import os as os_module
```

### 3. ✅ **Stale Modal Data Check**
**Symptoms:** Scraper returns old item selections (e.g., peaches instead of nectarines)

**Diagnostic steps:**
1. **Manual verification:** Open Farm to People customize modal in browser
2. **Check what items are actually selected** (have quantity selectors vs "Add" buttons)
3. **Add diagnostic logging** to see what scraper detects:

```python
# Add after modal opens:
nectarine_count = await modal.locator("article[aria-label*='Nectarine']").count()
peach_count = await modal.locator("article[aria-label*='Peach']").count()
print(f"📊 Modal check - Nectarines: {nectarine_count}, Peaches: {peach_count}")
```

### 4. ✅ **Wait Time Issues**
**Modal content loads dynamically** - if you see wrong items, try increasing wait time:

```python
# Current working solution:
await page.wait_for_timeout(3000)  # 3 seconds minimum
```

**Future optimization:**
```python
# Smart wait for content to load:
await page.wait_for_function("""() => {
    const articles = document.querySelectorAll('article[aria-label]');
    return articles.length >= 15;
}""", timeout=10000)
```

## 🔍 Common Issues & Solutions

### **Issue: "Email undefined" errors**
**Cause:** Session caching trying to use email variable before it's defined
**Solution:** Move credential extraction to very beginning of function

### **Issue: Modal shows old selections**
**Cause:** Not waiting long enough for dynamic content to load
**Solution:** Add 3+ second wait after modal opens

### **Issue: Performance regression (>60s)**
**Cause:** Usually added complexity (page refreshes, modal reopening)
**Solution:** Remove unnecessary complexity, stick to simple approach

### **Issue: Import errors**
**Cause:** Local imports in functions, path issues
**Solution:** Move imports to top of file or use proper sys.path handling

## ⚠️ What NOT To Do

### ❌ **Don't assume external caching issues**
- Farm to People's modal updates correctly
- Test manually in browser first
- Our scraper timing is usually the issue

### ❌ **Don't add page refreshes**
- Reloads potentially stale server data
- Adds 3-5 seconds with no benefit
- Can make problem worse

### ❌ **Don't add modal close/reopen logic**
- Same cached data returned
- Adds 5-8 seconds
- Increases complexity and failure points

### ❌ **Don't add session caching when debugging**
- Introduces scope conflicts
- Makes debugging harder
- Fix core issue first

## 📊 Performance Baselines

| Scenario | Expected Time | Red Flag |
|----------|---------------|----------|
| **Fresh login + scrape** | 35-45 seconds | >60 seconds |
| **With session cache** | 25-35 seconds | >50 seconds |
| **Individual items only** | 15-25 seconds | >40 seconds |

## 🔧 Diagnostic Tools

### **Add modal content inspection:**
```python
# After modal opens:
modal = page.locator("aside[aria-label*='Customize']").first
articles = await modal.locator("article[aria-label]").all()
print(f"🔍 Found {len(articles)} items in modal")

for i, article in enumerate(articles[:3]):
    name = await article.get_attribute("aria-label")
    print(f"  Item {i+1}: {name}")
```

### **Add performance timing:**
```python
import time
start_time = time.time()

# ... scraping logic ...

print(f"⏱️ Total time: {time.time() - start_time:.1f}s")
```

### **Add step-by-step logging:**
```python
print("🔐 Starting login...")
# login code
print("🛒 Opening cart...")
# cart code
print("📦 Processing customizable boxes...")
# modal code
```

## 🚀 Quick Recovery Steps

If scraper is completely broken:

1. **Revert to working commit:**
```bash
git log --oneline | grep "working\|fix"  # Find last working commit
git checkout [commit-hash] -- scrapers/comprehensive_scraper.py
```

2. **Remove recent complexity:**
   - Comment out session caching
   - Remove page refresh logic
   - Remove modal close/reopen logic
   - Keep only essential wait times

3. **Test with minimal example:**
```bash
# Test with environment variables only:
EMAIL=your@email.com PASSWORD=yourpassword python comprehensive_scraper.py
```

## 📖 Reference Documents

- [`docs/SCRAPER_DEBUGGING_LESSONS_2024_09.md`](docs/SCRAPER_DEBUGGING_LESSONS_2024_09.md) - Detailed lessons from Sept 2024 debugging session
- [`DEBUGGING_PHONE_ISSUES.md`](DEBUGGING_PHONE_ISSUES.md) - Phone number format issues
- [`CLAUDE.md`](CLAUDE.md) - Current development guidelines

---

**Remember:** Simple solutions often work better than complex ones. Always diagnose before optimizing.