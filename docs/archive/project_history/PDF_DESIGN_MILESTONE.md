# PDF Design Milestone - August 25, 2025

## ✅ Final Version for Tonight

**Best Version:** `server/templates/meal_plan_minimal.html`

This is the clean, Penny-inspired design that hits the right aesthetic:

### What Works:
- **No emojis** - pure typography approach
- **Subtle blue links** (#4169E1) like Penny menu
- **Compact, dense layout** - maximum info on one page  
- **"+" format** for meal names (Salmon + Roasted Vegetables)
- **Protein in title format** - "38g protein" directly under meal name ✅ CRITICAL
- **Minimal gray tags** (20 min, serves 2) - secondary info
- **Clean sections** with light dividers
- **Right-aligned quantities**
- **Professional restaurant menu vibe**

### ✅ CONFIRMED FORMAT (Aug 26, 2025):
**Meal Title Structure:**
```
Salmon + Roasted Vegetables
20 min    38g protein    serves 2

Chicken Stir-Fry + Peppers  
15 min    35g protein    serves 2

Vegetable Frittata
25 min    24g protein    serves 4
```
**Key:** Protein content MUST be prominently displayed in meal metadata for high-protein users

### File Locations:
```
server/templates/meal_plan_minimal.html  # ← BEST VERSION
server/templates/meal_plan.html          # Earlier emoji version
server/pdf_one_page.py                   # Compact PDF attempt
server/html_meal_plan_generator.py       # Data processing logic
```

### Data Structure We Want:
1. **Current Selections** - What's in their box/cart
2. **Suggested Meals** - Just names + key stats
3. **Recommended Swaps** - Based on preferences
4. **Premium Additions** - Upsell opportunities
5. **Storage notes** - Ultra condensed

### Next Steps (for tomorrow):
1. Connect this HTML template to real scraped data
2. Add preference-based swap logic (no pork, etc)
3. Convert HTML to PDF (via headless browser or weasyprint)
4. Test with actual Farm to People data
5. Add to SMS flow

### Key Insight:
Less is more. The Penny aesthetic (minimal, typographic, no decorations) is much more sophisticated than boxes and emojis. This version respects the user's intelligence and time.

### ✅ PENNY MENU REFERENCE SAVED:
**File:** `docs/H1EP7sq4TKedoWMdkys8_Penny Food 8.24.25.pdf`  
**Documentation:** `docs/PENNY_MENU_DESIGN_REFERENCE.md`  
**Date Preserved:** August 26, 2025

The actual Penny restaurant menu that inspired our design is now preserved for future reference and design consistency.

---

**Status:** Good stopping point for tonight. This minimal design is the right direction.