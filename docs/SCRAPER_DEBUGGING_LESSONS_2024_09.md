# 🔧 Cart Scraper Debugging Lessons - September 2024

## 📋 Executive Summary

**Date:** September 16, 2024
**Issue:** Cart scraper showing stale data (White Peaches instead of Yellow Nectarines after user swap)
**Duration:** ~3 hours debugging
**Outcome:** ✅ **RESOLVED** - Fresh data now correctly scraped
**Performance:** 30s → 2min+ (broken) → 40s (fixed) → Target: 25s (future)

## 🎯 The Problem

User swapped White Peaches → Yellow Nectarines in Farm to People UI, but our scraper continued showing:
- **Selected Items:** White Peaches ❌
- **Available Items:** Yellow Nectarines ❌

**Expected Result:** Yellow Nectarines selected, White Peaches available.

## 🔍 What We Initially Thought vs Reality

### ❌ **Initial Hypothesis (WRONG)**
"Farm to People has server-side caching issues. Their modal shows stale data."

**Why This Was Wrong:**
- User's screenshots showed Farm to People UI correctly displaying nectarines as selected
- We were assuming their problem without proper diagnosis
- Led us down wrong optimization paths

### ✅ **Actual Root Cause**
**Variable scope conflicts** in our scraper code causing crashes and fallbacks:
1. `os` variable shadowing in session caching imports
2. `email` variable undefined in certain execution paths
3. `datetime` local import conflicts with global import

## 🚫 What We Tried That FAILED

### 1. Page Refresh Before Modal (❌ HARMFUL)
```python
# FAILED ATTEMPT
await page.reload()
await page.wait_for_load_state("networkidle", timeout=10000)
```
**Why It Failed:** Reloaded potentially stale page state from server, added 3-5 seconds, didn't solve core issue.

### 2. Modal Close/Reopen Logic (❌ HARMFUL)
```python
# FAILED ATTEMPT
await page.keyboard.press("Escape")
await customize_btn.click()
fresh_box_data = await scrape_customize_modal(page)
```
**Why It Failed:** Still got same cached modal content, added 5-8 seconds, increased complexity.

### 3. Complex Session Caching (❌ INTRODUCED BUGS)
```python
# FAILED ATTEMPT
server_path = os.path.join(os.path.dirname(__file__), '../server')  # os undefined!
```
**Why It Failed:** Created scope conflicts, caused crashes, made debugging harder.

## ✅ What Actually WORKED

### 1. Fixed Scope Conflicts
```python
# WORKING SOLUTION
import os as os_module  # Avoid scope conflicts
server_path = os_module.path.join(...)

# Use top-level datetime import, not local
stored_parsed_date = datetime.fromisoformat(...)
```

### 2. Simple Wait for Modal Content
```python
# WORKING SOLUTION
print("⏰ Waiting 3 seconds for modal to fully load...")
await page.wait_for_timeout(3000)
```

### 3. Diagnostic Logging
```python
# WORKING SOLUTION
nectarine_count = await modal.locator("article[aria-label*='Nectarine']").count()
peach_count = await modal.locator("article[aria-label*='Peach']").count()
print(f"📊 Modal check - Nectarines: {nectarine_count}, Peaches: {peach_count}")
```

## 📊 Performance Timeline

| Phase | Duration | Status | Notes |
|-------|----------|--------|-------|
| **Original** | 30s | ✅ Working | Baseline performance |
| **After "Fixes"** | 2min+ | ❌ Broken | Crashes, stale data |
| **After Debug** | 40s | ✅ Working | Correct data, stable |
| **Future Target** | 25s | 🎯 Goal | With smart optimizations |

## 🧠 Key Lessons Learned

### 1. **Diagnosis Before Solutions**
- ❌ **Don't assume external issues** (Farm to People caching)
- ✅ **Add diagnostics first** to see what's actually happening
- ✅ **Test with real scenarios** (user's actual swaps)

### 2. **Scope Management in Python**
- ❌ **Avoid local imports** that shadow global variables
- ✅ **Use aliases** (`import os as os_module`) when necessary
- ✅ **Watch for variable shadowing** across function scopes

### 3. **Performance vs Correctness**
- ❌ **Don't optimize before fixing** core functionality
- ✅ **Get it working first**, then make it fast
- ✅ **Remove complexity** that doesn't solve the problem

### 4. **Farm to People Specific Quirks**
- Modal content loads **dynamically via JavaScript**
- Need **3+ second wait** for content to fully populate
- Session cookies can help but **aren't necessary** for correctness

## 🚀 Future Optimization Opportunities (25s Target)

### Smart Waits (5-8s savings)
```python
# Instead of fixed 3000ms wait:
await page.wait_for_function("""() => {
    const articles = document.querySelectorAll('article[aria-label]');
    return articles.length >= 15;  // Wait for full modal content
}""", timeout=10000)
```

### Session Persistence (5-8s savings)
```python
# Properly implemented session caching:
if valid_session_cookies_exist():
    skip_login()  # Save 5-8 seconds
```

### Parallel Box Processing (3-5s savings)
```python
# Process multiple boxes concurrently:
box_tasks = [process_box(btn) for btn in customize_btns]
all_box_data = await asyncio.gather(*box_tasks)
```

## ⚠️ Red Flags to Watch For

### Code Smells That Indicate Problems:
1. **Variable scope errors** - `cannot access local variable`
2. **Performance regression** - Scraping takes >60s
3. **Adding complexity without clear benefit**
4. **Assuming external service issues** without verification
5. **Local imports inside functions** that might shadow globals

### Debugging Checklist:
- [ ] Can the scraper run without crashing?
- [ ] Does the modal show correct items in browser?
- [ ] Are we waiting long enough for dynamic content?
- [ ] Do variable names have scope conflicts?
- [ ] Are imports at the correct scope level?

## 📈 Success Metrics

### ✅ **Current State (Fixed)**
- **Functionality:** Cart swaps correctly reflected
- **Performance:** ~40 seconds total
- **Reliability:** No crashes, consistent results
- **Data Accuracy:** Yellow Nectarines show as selected ✅

### 🎯 **Target State (Future)**
- **Functionality:** Same accuracy maintained
- **Performance:** ~25 seconds total
- **Reliability:** Same stability
- **Features:** + Session persistence, + Smart waits

## 💡 Recommendations for Future Development

1. **Always start with diagnostics** when debugging data issues
2. **Avoid premature optimization** - fix correctness first
3. **Be extremely careful with variable scoping** in Python
4. **Test with real user scenarios**, not just synthetic data
5. **Document performance baselines** before making changes
6. **Keep solutions simple** until complexity is truly needed
7. **Save working states** before attempting optimizations

## 🏆 What We Accomplished

- ✅ **Fixed stale data issue** - Nectarines now show correctly
- ✅ **Restored performance** - Back to reasonable 40s from 2min+
- ✅ **Improved reliability** - No more crashes from scope conflicts
- ✅ **Added diagnostic capabilities** - Can debug future issues faster
- ✅ **Simplified codebase** - Removed harmful complexity
- ✅ **Preserved working features** - All existing functionality intact

---

**Key Takeaway:** Sometimes the best solution is to **remove complexity, not add it**. The 3-second wait + scope fixes solved what hours of "optimizations" couldn't.