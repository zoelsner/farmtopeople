# 📖 Meal Planning Logic Documentation

## Overview

The meal planning system intelligently allocates ingredients from your Farm to People cart across a 5-day meal plan (Monday-Friday). It uses realistic portion sizes and smart name cleaning to create an intuitive cooking experience.

**Last Updated:** September 4, 2025  
**Version:** 1.0.0

## Core Modules

### 1. ingredient-allocator.js
**Purpose:** Smart allocation of ingredients to meals based on realistic portions

**Key Features:**
- Whole portion allocation for small quantities
- Spreading abundant items across multiple meals
- Smart ingredient matching with fuzzy name detection

### 2. ingredient-cleaner.js
**Purpose:** Clean verbose product names for better display

**Key Features:**
- Removes marketing terms (boneless, skinless, organic, grass-fed)
- Keeps meaningful terms (bone-in, rainbow, bunched)
- Proper capitalization and formatting

### 3. meal-planner.js
**Purpose:** Orchestrates meal generation and calendar display

**Key Features:**
- Generates meals based on actual cart contents
- Drag-and-drop meal reorganization
- Real-time ingredient pool tracking

## Allocation Logic

### Portion Size Rules

#### Proteins (Main Rule: Use whole portions when small)
```javascript
// Chicken Example (0.7 lbs available)
if (remaining <= 1.0 lbs) {
    USE ALL for one meal  // Don't split small amounts
}

// Multiple chicken breasts (4 pieces)
if (total <= 2 pieces) {
    USE ALL for one meal  // 1-2 pieces = one meal
} else {
    USE 1-2 pieces per meal  // Spread across days
}
```

#### Vegetables (Main Rule: Spread when abundant)
```javascript
// Many carrots (12 pieces)
if (total >= 6 pieces) {
    USE 1-2 per meal  // Spread across week
}

// Few tomatoes (2 pieces)
if (total <= 2 pieces) {
    USE ALL in one meal  // Don't split small amounts
}
```

#### Supporting Ingredients
- Each meal gets 2-4 total ingredients
- Prioritize items with low usage (< 50% allocated)
- Add vegetables that complement the protein

### Real Example Walkthrough

**Your Cart:**
- Boneless, Skinless Chicken Breast: 0.7 lbs
- Organic Heirloom Tomatoes: 2 pieces
- Organic Bunched Rainbow Carrots: 12 pieces
- Pasture Raised Eggs: 6 pieces

**Meal Generation:**

**Monday:** 
- Name: "Pan-Seared Chicken with Tomatoes"
- Allocates: ALL chicken (0.7 lbs), BOTH tomatoes
- Why: Small portions used completely

**Tuesday:**
- Name: "Scrambled Eggs with Rainbow Carrots"
- Allocates: 3 eggs, 2 carrots
- Why: Eggs split in half, carrots spread out

**Wednesday-Friday:**
- Continue with remaining eggs and carrots
- Vegetables spread across days

## Name Cleaning Logic

### Before & After Examples

```javascript
// Input from Farm to People
"Boneless, Skinless Organic Free-Range Chicken Breast"

// After cleaning for meal name
"Chicken"  // Super clean for meal titles

// After cleaning for ingredient pool
"Chicken Breast"  // Keep some detail for clarity
```

### Terms Removed
- Marketing: organic, grass-fed, free-range, pasture-raised
- Processing: boneless, skinless (except bone-in)
- Certifications: certified, non-GMO, sustainable
- Descriptors: fresh, premium, locally-sourced

### Terms Kept
- Preparation: ground, chopped, diced, sliced
- Varieties: rainbow (carrots), cherry (tomatoes), baby
- Colors: red, yellow, green
- Meaningful types: bone-in, steelhead, New York (strip)

## Meal Name Generation

### Pattern
```
[Cooking Method] + [Clean Protein] + "with" + [Vegetables]
```

### Cooking Methods Rotation
- Chicken: Pan-Seared, Grilled, Roasted, Herb-Crusted, Baked
- Beef: Grilled, Pan-Seared, Braised
- Fish: Pan-Seared, Baked, Grilled
- Eggs: Scrambled, Poached, Frittata

### Examples
```javascript
// Complex input
protein: "Boneless, Skinless Organic Chicken Breast"
vegetables: ["Organic Heirloom Tomatoes", "Rainbow Carrots"]

// Clean output
"Pan-Seared Chicken with Tomatoes and Carrots"

// With 3+ vegetables
"Roasted Chicken with Seasonal Vegetables"
```

## Drag & Drop Logic

### Move Validation
```javascript
// When moving Tuesday's chicken to Thursday
1. Check Thursday's current allocation
2. Verify chicken not over-allocated
3. Update both days' ingredient pools
4. Recalculate percentages
```

### Conflict Detection
- Warns if moving would over-allocate ingredients
- Prevents impossible moves (not enough ingredients)
- Suggests alternatives when conflicts occur

## Ingredient Pool Display

### Usage Percentage Calculation
```javascript
usagePercent = (allocated / total) * 100

// Visual indicators
< 30% used  → Green (plenty left)
30-70% used → Yellow (moderate use)
> 70% used  → Red (mostly allocated)
```

### Display Format
```
Chicken Breast       [████████░░] 80% used
2.0 lbs left

Rainbow Carrots      [███░░░░░░░] 25% used  
9 pieces left
```

## Special Cases

### Empty Days
- Allow manual meal addition
- Suggest meals based on remaining ingredients
- "Add Meal" prompt shows available options

### Over-allocation Prevention
```javascript
if (requested > remaining) {
    // Use only what's available
    amount = remaining;
    // Show warning to user
}
```

### Minimum Portions
- Never allocate less than 0.1 lbs of proteins
- Round vegetables to whole pieces
- Keep meals practical (no 0.03 lbs portions)

## API Integration Points

### Meal Generation Endpoint
```javascript
POST /api/generate-weekly-meals
{
    phone_number: "+1234567890",
    ingredient_pool: { /* current pool */ },
    preferences: { /* dietary restrictions */ }
}
```

### Single Meal Regeneration
```javascript
POST /api/regenerate-meal
{
    day: "tuesday",
    available_ingredients: { /* remaining pool */ },
    existing_meals: ["Monday's meal", ...]  // For variety
}
```

## User Preferences Integration

### Dietary Restrictions
- Filter out restricted ingredients
- Adjust protein portions for health goals
- Prioritize preferred cooking methods

### Portion Adjustments
```javascript
// Household size affects portions
if (household_size >= 4) {
    servings = 4;  // Larger portions
    protein_amount *= 1.5;
}
```

## Performance Optimizations

### Caching Strategy
- Meal plans saved per week
- Ingredient pools stored in localStorage
- Regenerate only changed days

### Efficient Updates
```javascript
// Batch DOM updates
const fragment = document.createDocumentFragment();
// Add all meal cards to fragment
container.appendChild(fragment);  // Single reflow
```

## Future Enhancements

1. **Smart Pairing**: Learn which vegetables go with which proteins
2. **Recipe Integration**: Click meal for full recipe
3. **Leftover Tracking**: Mark meals as cooked, track remaining
4. **Shopping List**: Generate list for missing ingredients
5. **Meal Preferences**: Remember favorite combinations

## Testing Checklist

- [ ] 0.7 lbs chicken allocates to single meal
- [ ] 12 carrots spread across multiple days  
- [ ] Names properly cleaned (no "boneless, skinless")
- [ ] Drag & drop updates percentages correctly
- [ ] Conflicts prevented when over-allocating
- [ ] Ingredient pool shows accurate usage
- [ ] Meals match actual cart contents
- [ ] Supporting vegetables auto-added

---

## Quick Reference

### File Locations
```
/server/static/js/modules/
├── meal-planner.js         # Main orchestration
├── ingredient-allocator.js  # Portion logic
└── ingredient-cleaner.js    # Name cleaning
```

### Key Functions
```javascript
// Allocate ingredients
ingredientAllocator.allocateForMeal(meal, pool)

// Clean names
ingredientCleaner.cleanMealName(name)
ingredientCleaner.cleanForIngredientPool(name)

// Generate meals
mealPlanner.generateMealTemplates(proteins, vegetables)
```

### Debug Commands
```javascript
// Check current allocation
console.log(window.AppState.mealPlanData.ingredient_pool)

// Force regenerate
MealPlanner.instance.generateSampleMeals()

// Check specific day
console.log(MealPlanner.instance.mealPlan.meals.monday)
```

---

*This logic creates realistic meal plans that match how people actually cook - using whole portions for small amounts and spreading abundant items across the week.*