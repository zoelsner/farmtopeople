# Smart Add-Ons Architecture & Implementation Plan

## Core Philosophy
Add-ons are items that CANNOT be obtained through swaps - they fill critical gaps and enhance specific meals with fresh ingredients that typically aren't pantry staples.

## Add-On vs Swap Distinction
- **Swaps**: Optimize WITHIN Farm to People's available alternatives (e.g., kale → arugula)
- **Add-Ons**: Items NOT available as swap options that complete/enhance meals (fresh herbs, aromatics, missing proteins)

## Smart Add-On Generation Logic

### Priority 1: Protein Gap Detection
```python
# Check if cart has sufficient protein
proteins_in_cart = count_proteins(cart_data)
meals_planned = len(meals)
if proteins_in_cart < meals_planned:
    # Suggest protein add-ons based on user preferences
    # e.g., "Add 2 chicken breasts for complete protein coverage"
```

### Priority 2: Meal-Specific Aromatics
Based on generated meals, suggest specific fresh ingredients:
- **Asian dishes** → Fresh ginger, garlic, scallions, sesame oil
- **Italian dishes** → Fresh basil, oregano, parmesan
- **Mexican dishes** → Fresh cilantro, lime, jalapeños
- **Mediterranean** → Fresh dill, lemon, mint
- **General roasting** → Fresh rosemary, thyme

### Priority 3: Always Return Something
Even with a perfect cart, ALWAYS suggest 1-3 fresh items:
- Default to versatile herbs (parsley, cilantro)
- Fresh citrus (lemon, lime)
- Universal aromatics (garlic, shallots)

## Implementation Fix Plan

### Step 1: Fix Empty Add-ons Bug
**Problem**: Add-ons always returning empty array
**Solution**: Actually call the generate_meal_addons function after meals are generated

```python
# Current (BROKEN):
addons = []  # Never populated!

# Fixed:
if meals:
    addons = await generate_meal_addons(meals, cart_data, user_preferences)
else:
    addons = generate_fallback_addons()  # Always return something
```

### Step 2: Enhance Add-On Intelligence
```python
async def generate_meal_addons(meals, cart_data, preferences):
    addons = []

    # 1. Check protein coverage
    protein_gap = analyze_protein_gap(cart_data, meals)
    if protein_gap:
        addons.append({
            "item": f"{protein_gap} servings of {preferred_protein}",
            "price": calculate_protein_price(protein_gap),
            "reason": f"Complete protein for {protein_gap} meals",
            "category": "protein"
        })

    # 2. Analyze meal-specific needs
    for meal in meals:
        meal_name = meal.get('name', '').lower()

        # Pattern matching for cuisine types
        if 'stir-fry' in meal_name or 'asian' in meal_name:
            if not has_item(cart_data, 'ginger'):
                addons.append({
                    "item": "Fresh Ginger Root",
                    "price": "$3.50",
                    "reason": f"Essential for authentic {meal['name']}",
                    "category": "produce"
                })

        if 'italian' in meal_name or 'pasta' in meal_name:
            if not has_item(cart_data, 'basil'):
                addons.append({
                    "item": "Fresh Basil",
                    "price": "$3.00",
                    "reason": f"Fresh herbs for {meal['name']}",
                    "category": "produce"
                })

    # 3. Ensure we always return something
    if len(addons) == 0:
        addons = get_universal_aromatics()

    return addons[:3]  # Cap at 3 suggestions
```

### Step 3: Fallback Aromatics
```python
def get_universal_aromatics():
    return [
        {
            "item": "Fresh Italian Parsley",
            "price": "$2.50",
            "reason": "Versatile fresh herb for garnishing",
            "category": "produce"
        },
        {
            "item": "Fresh Lemons",
            "price": "$3.00",
            "reason": "Brightens any dish",
            "category": "produce"
        },
        {
            "item": "Fresh Garlic",
            "price": "$2.00",
            "reason": "Essential aromatic for most cuisines",
            "category": "produce"
        }
    ]
```

## Cancel Button Fix

### Problem
Cancel button only stops client-side timers, not server-side scraping

### Solution
```javascript
// Add AbortController to fetch
let currentController = null;

async function startAnalysis() {
    currentController = new AbortController();

    fetch('/api/analyze-cart', {
        signal: currentController.signal,
        // ... rest of config
    });
}

function cancelAnalysis() {
    if (currentController) {
        currentController.abort();
    }
    // Clear UI state
}
```

## Testing Checklist
- [ ] Add-ons ALWAYS return 2-3 items
- [ ] Protein gaps are detected and suggested
- [ ] Meal-specific aromatics are recommended
- [ ] Cancel button stops server operations
- [ ] Swaps appear consistently in UI

## Success Metrics
1. **Never empty add-ons** - Always suggest something valuable
2. **Meal-aware suggestions** - "Ginger for your stir-fry" not generic "herbs"
3. **Gap filling** - Detect missing proteins and suggest them
4. **Fresh focus** - Only items that expire, not pantry staples