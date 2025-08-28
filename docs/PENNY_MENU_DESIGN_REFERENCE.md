# Penny Menu - Design Reference

**Source:** Penny Restaurant Menu (August 24, 2025)  
**File:** `docs/H1EP7sq4TKedoWMdkys8_Penny Food 8.24.25.pdf`  
**Purpose:** Design inspiration for Farm to People meal plan PDFs

## Key Design Elements from Penny Menu

### **Typography & Layout**
- **Clean, minimal typography** - No decorative elements
- **Right-aligned pricing** - Creates visual order and scanning ease
- **Subtle blue accent color** (#4169E1 equivalent)
- **High information density** - Maximum content in minimal space
- **Professional restaurant aesthetic**

### **Menu Item Format**
```
Dish Name + Key Ingredient          Price
Secondary ingredient details

Examples:
Kinmedai + Plum                     22
Mackerel + Long Hots                24  
Bonito + Marinated Beans            26
Swordfish + Jimmy Nardellos         39
Black Bass + Tomato                 45
```

### **Section Organization**
- **Clear sections** without heavy visual dividers
- **Logical grouping** (Raw bar, Small plates, Mains)
- **Price hierarchy** - ascending order within sections
- **Minimal whitespace** but still readable

### **What We Adapted for Farm to People:**

#### **Meal Title Format (Our Version):**
```
Salmon + Roasted Vegetables
20 min    38g protein    serves 2

Chicken Stir-Fry + Peppers
15 min    35g protein    serves 2
```

#### **Design Principles We Borrowed:**
1. **"+" format** for ingredient combinations
2. **Right-aligned metadata** (time/protein/servings vs price)
3. **Clean typography** without emojis or decorations
4. **High information density**
5. **Professional, sophisticated feel**
6. **Subtle color accents**

#### **Our Adaptations:**
- **Protein prominence** - Essential for our high-protein users
- **Time indicators** - Critical for busy professionals  
- **Serving information** - Household planning necessity
- **No pricing** - Focus on nutrition and practicality

## Design Success Factors

### **Why Penny's Design Works:**
1. **Sophisticated simplicity** - Respects diner intelligence
2. **Easy scanning** - Right-aligned numbers, consistent format
3. **Information hierarchy** - Main item bold, details secondary
4. **Professional credibility** - High-end restaurant aesthetic
5. **Space efficiency** - Fits many items on single page

### **Applied to Our Use Case:**
- **Respects user time** - Quick scanning for meal decisions
- **Nutritional focus** - Protein content prominently displayed
- **Practical information** - Cooking time and servings upfront
- **Premium feel** - Professional design builds trust
- **SMS-friendly** - Clean format works on mobile viewing

## Implementation Notes

**Current Template:** `generators/templates/meal_plan_minimal.html`

**Key CSS Properties:**
- Subtle blue links (#4169E1)
- Clean sans-serif typography  
- Right-aligned metadata columns
- Minimal padding and borders
- High contrast for readability

**Success Metrics:**
- User feedback: "Looks professional"
- Higher confirmation rates vs emoji-heavy versions
- Faster decision-making (clean scanning)

---

**Saved:** August 26, 2025  
**Status:** Active design reference for all PDF generation  
**Next Review:** When updating PDF templates

*This menu exemplifies the "less is more" philosophy that makes our meal plans feel premium and trustworthy.*