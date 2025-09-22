/**
 * Ingredient Allocator Module
 * Smart ingredient matching and allocation for meal planning
 */

export class IngredientAllocator {
    constructor() {
        // Serving size estimates (in base units)
        this.servingSizes = {
            // Proteins (per serving)
            'chicken': 0.25,  // lbs
            'beef': 0.25,      // lbs
            'fish': 0.2,       // lbs
            'eggs': 2,         // pieces
            'tofu': 0.25,      // lbs
            
            // Vegetables (per serving)
            'tomatoes': 1,     // piece
            'carrots': 2,      // pieces
            'onions': 0.5,     // piece
            'garlic': 2,       // cloves
            'lettuce': 2,      // cups
            
            // Fruits (per serving)
            'apples': 0.5,     // piece
            'avocados': 0.5,   // piece
            'lemons': 0.25,    // piece
            'peaches': 1,      // piece
        };
        
        // Ingredient name mappings for fuzzy matching
        this.nameMappings = {
            'chicken breast': ['boneless skinless chicken', 'chicken breast', 'chicken thighs'],
            'beef': ['ground beef', 'steak', 'beef', 'stewing beef'],
            'tomatoes': ['heirloom tomatoes', 'cherry tomatoes', 'roma tomatoes', 'tomatoes'],
            'carrots': ['rainbow carrots', 'bunched carrots', 'baby carrots', 'carrots'],
            'eggs': ['pasture raised eggs', 'eggs', 'organic eggs'],
        };
    }
    
    /**
     * Allocate ingredients for a meal with realistic portions
     * @param {Object} meal - Meal object with name and servings
     * @param {Object} ingredientPool - Available ingredients
     * @returns {Array} Allocated ingredients with amounts
     */
    allocateForMeal(meal, ingredientPool) {
        const allocated = [];
        const mealLower = meal.name.toLowerCase();
        
        // Smart allocation based on meal name
        const mealIngredients = this.detectIngredientsInMeal(mealLower);
        
        for (const mealIng of mealIngredients) {
            const poolItem = this.findInPool(mealIng, ingredientPool);
            
            if (poolItem && poolItem.remaining > 0) {
                const amount = this.calculateRealisticAmount(mealIng, poolItem);
                
                if (amount > 0) {
                    // Allocate the ingredient
                    poolItem.allocated = (poolItem.allocated || 0) + amount;
                    poolItem.remaining = Math.max(0, poolItem.total - poolItem.allocated);
                    
                    allocated.push({
                        name: poolItem.name,
                        amount: amount,
                        unit: poolItem.unit
                    });
                }
            }
        }
        
        // Add some supporting vegetables if available
        this.addSupportingIngredients(allocated, ingredientPool, mealIngredients);
        
        return allocated;
    }
    
    /**
     * Calculate realistic amount based on ingredient type and quantity
     */
    calculateRealisticAmount(mealIngredient, poolItem) {
        const remaining = poolItem.remaining;
        const total = poolItem.total;
        const unit = (poolItem.unit || '').toLowerCase();
        
        // For proteins - use whole portions when small
        if (mealIngredient.category === 'protein') {
            if (unit === 'lbs' || unit === 'lb') {
                // If less than 1 lb remaining, use it all
                if (remaining <= 1.0) {
                    return remaining;
                }
                // Otherwise use 0.5-0.75 lbs for a meal
                return Math.min(0.75, remaining);
            } else if (unit === 'piece' || unit === 'pieces') {
                // For items like chicken breasts
                if (total <= 2) {
                    // If only 1-2 pieces total, use all for one meal
                    return remaining;
                }
                // Otherwise use 1-2 pieces
                return Math.min(2, remaining);
            }
        }
        
        // For vegetables - spread if abundant
        if (mealIngredient.category === 'vegetable') {
            if (unit === 'piece' || unit === 'pieces') {
                if (total >= 6) {
                    // If we have many, use 1-2 per meal
                    return Math.min(2, remaining);
                } else if (total <= 2) {
                    // If only 1-2 total, use all
                    return remaining;
                } else {
                    // Medium amount, use 1
                    return Math.min(1, remaining);
                }
            } else if (unit === 'lbs' || unit === 'lb') {
                if (remaining <= 0.5) {
                    // Small amount, use it all
                    return remaining;
                }
                // Use portion of larger amount
                return Math.min(0.3, remaining);
            }
        }
        
        // For fruits - similar to vegetables
        if (mealIngredient.category === 'fruit') {
            if (unit === 'piece' || unit === 'pieces') {
                if (total >= 6) {
                    return Math.min(1, remaining);
                } else {
                    return Math.min(2, remaining);
                }
            }
        }
        
        // Default: use 1 unit or all if less
        return Math.min(1, remaining);
    }
    
    /**
     * Add supporting ingredients that aren't in meal name
     */
    addSupportingIngredients(allocated, pool, mainIngredients) {
        // Don't add too many items
        if (allocated.length >= 4) return;
        
        // Find vegetables/sides that haven't been allocated much
        const candidates = Object.entries(pool)
            .filter(([name, info]) => {
                // Skip if already allocated to this meal
                if (allocated.find(a => a.name === name)) return false;
                
                // Skip if no remaining
                if (!info.remaining || info.remaining <= 0) return false;
                
                // Prefer items with lots remaining
                const percentUsed = (info.allocated || 0) / info.total * 100;
                return percentUsed < 50;
            })
            .sort((a, b) => {
                // Sort by amount remaining (prefer items with more)
                return b[1].remaining - a[1].remaining;
            });
        
        // Add 1-2 supporting ingredients
        const toAdd = Math.min(2, 4 - allocated.length);
        for (let i = 0; i < toAdd && i < candidates.length; i++) {
            const [name, info] = candidates[i];
            const unit = (info.unit || '').toLowerCase();
            
            let amount;
            if (unit === 'piece' || unit === 'pieces') {
                // Use 1-2 pieces for sides
                amount = Math.min(info.total >= 6 ? 1 : 2, info.remaining);
            } else {
                // Use small amount for sides
                amount = Math.min(0.2, info.remaining);
            }
            
            if (amount > 0) {
                info.allocated = (info.allocated || 0) + amount;
                info.remaining = Math.max(0, info.total - info.allocated);
                
                allocated.push({
                    name: name,
                    amount: amount,
                    unit: info.unit
                });
            }
        }
    }
    
    /**
     * Detect ingredients mentioned in meal name
     */
    detectIngredientsInMeal(mealName) {
        const ingredients = [];
        
        // Check for proteins
        if (mealName.includes('chicken')) {
            ingredients.push({ type: 'chicken', category: 'protein' });
        }
        if (mealName.includes('beef') || mealName.includes('steak')) {
            ingredients.push({ type: 'beef', category: 'protein' });
        }
        if (mealName.includes('egg')) {
            ingredients.push({ type: 'eggs', category: 'protein' });
        }
        if (mealName.includes('fish') || mealName.includes('salmon')) {
            ingredients.push({ type: 'fish', category: 'protein' });
        }
        
        // Check for vegetables (matching what's in the screenshot)
        if (mealName.includes('tomato')) {
            ingredients.push({ type: 'tomatoes', category: 'vegetable' });
        }
        if (mealName.includes('carrot')) {
            ingredients.push({ type: 'carrots', category: 'vegetable' });
        }
        if (mealName.includes('corn')) {
            ingredients.push({ type: 'corn', category: 'vegetable' });
        }
        if (mealName.includes('rainbow') && mealName.includes('carrot')) {
            ingredients.push({ type: 'rainbow carrots', category: 'vegetable' });
        }
        
        // Check for cooking styles
        if (mealName.includes('salad')) {
            ingredients.push({ type: 'lettuce', category: 'vegetable' });
        }
        if (mealName.includes('grilled') || mealName.includes('roasted')) {
            // These cooking methods often use vegetables as sides
        }
        if (mealName.includes('seared') || mealName.includes('pan')) {
            // Pan-seared usually implies the protein mentioned
        }
        
        return ingredients;
    }
    
    /**
     * Find matching ingredient in pool
     */
    findInPool(mealIngredient, pool) {
        const type = mealIngredient.type;
        
        // Direct name matching first
        for (const [name, data] of Object.entries(pool)) {
            const nameLower = name.toLowerCase();
            
            // Check direct match
            if (nameLower.includes(type)) {
                return { name, ...data };
            }
            
            // Check mapped names
            const mappings = this.nameMappings[type] || [];
            for (const mapping of mappings) {
                if (nameLower.includes(mapping)) {
                    return { name, ...data };
                }
            }
        }
        
        return null;
    }
    
    /**
     * Calculate amount needed based on type and servings
     */
    calculateAmount(type, servings, poolItem) {
        const baseAmount = this.servingSizes[type] || 1;
        let amount = baseAmount * servings;
        
        // Adjust based on unit
        if (poolItem.unit === 'piece' || poolItem.unit === 'pieces') {
            amount = Math.ceil(amount);
        } else if (poolItem.unit === 'lbs' || poolItem.unit === 'Lbs') {
            amount = Math.round(amount * 10) / 10; // Round to 0.1
        }
        
        return amount;
    }
    
    /**
     * Calculate usage percentage for ingredient
     */
    calculateUsagePercentage(ingredient) {
        if (!ingredient.total || ingredient.total === 0) return 0;
        
        const allocated = ingredient.allocated || 0;
        const percentage = (allocated / ingredient.total) * 100;
        
        return Math.min(100, Math.round(percentage));
    }
    
    /**
     * Format remaining amount for display
     */
    formatRemaining(ingredient) {
        const remaining = ingredient.remaining || ingredient.total || 0;
        const unit = ingredient.unit || '';
        
        // Fix decimal formatting
        if (typeof remaining === 'number') {
            if (unit === 'pieces' || unit === 'piece') {
                return `${Math.floor(remaining)} ${unit}`;
            } else {
                return `${remaining.toFixed(1)} ${unit}`;
            }
        }
        
        return `${remaining} ${unit}`;
    }
    
    /**
     * Categorize ingredient by type
     */
    categorizeIngredient(name) {
        const nameLower = name.toLowerCase();
        
        // Proteins
        if (nameLower.includes('chicken') || nameLower.includes('beef') || 
            nameLower.includes('fish') || nameLower.includes('salmon') ||
            nameLower.includes('egg') || nameLower.includes('tofu') ||
            nameLower.includes('turkey') || nameLower.includes('pork') ||
            nameLower.includes('sausage') || nameLower.includes('bass')) {
            return 'protein';
        }
        
        // Fruits
        if (nameLower.includes('apple') || nameLower.includes('banana') ||
            nameLower.includes('berry') || nameLower.includes('peach') ||
            nameLower.includes('plum') || nameLower.includes('nectarine') ||
            nameLower.includes('orange') || nameLower.includes('grape')) {
            return 'fruit';
        }
        
        // Default to vegetable
        return 'vegetable';
    }
    
    /**
     * Check if there are conflicts when moving a meal
     */
    checkMoveConflicts(fromDay, toDay, mealPlan) {
        const conflicts = [];
        const meal = mealPlan.meals[fromDay];
        
        if (!meal || !meal.allocated_ingredients) return conflicts;
        
        // Check each allocated ingredient
        for (const ing of meal.allocated_ingredients) {
            const poolItem = mealPlan.ingredient_pool[ing.name];
            
            if (poolItem) {
                // Calculate what would happen if we move this meal
                const otherAllocations = this.calculateOtherAllocations(
                    ing.name, 
                    fromDay, 
                    mealPlan
                );
                
                if (otherAllocations + ing.amount > poolItem.total) {
                    conflicts.push({
                        ingredient: ing.name,
                        needed: ing.amount,
                        available: poolItem.total - otherAllocations,
                        message: `Not enough ${ing.name} for this move`
                    });
                }
            }
        }
        
        return conflicts;
    }
    
    /**
     * Calculate allocations from other meals
     */
    calculateOtherAllocations(ingredientName, excludeDay, mealPlan) {
        let total = 0;
        
        for (const [day, meal] of Object.entries(mealPlan.meals)) {
            if (day !== excludeDay && meal.allocated_ingredients) {
                const allocation = meal.allocated_ingredients.find(
                    ing => ing.name === ingredientName
                );
                if (allocation) {
                    total += allocation.amount;
                }
            }
        }
        
        return total;
    }
    
    /**
     * Rebalance allocations after changes
     */
    rebalancePool(mealPlan) {
        // Reset all allocations
        for (const ingredient of Object.values(mealPlan.ingredient_pool)) {
            ingredient.allocated = 0;
            ingredient.remaining = ingredient.total;
        }
        
        // Recalculate from all meals
        for (const meal of Object.values(mealPlan.meals)) {
            if (meal.allocated_ingredients) {
                for (const ing of meal.allocated_ingredients) {
                    const poolItem = mealPlan.ingredient_pool[ing.name];
                    if (poolItem) {
                        poolItem.allocated += ing.amount;
                        poolItem.remaining = poolItem.total - poolItem.allocated;
                    }
                }
            }
        }
        
        return mealPlan.ingredient_pool;
    }
}

// Export singleton instance
export const ingredientAllocator = new IngredientAllocator();