/**
 * Meal Generator API Module
 * Generates dynamic meal plans using existing backend meal generation
 * Adds ingredient allocation for weekly planning
 */

import { apiCall, getPhoneNumber } from './shared.js';
import { ingredientCleaner } from './ingredient-cleaner.js';
import { ingredientAllocator } from './ingredient-allocator.js';

class MealGeneratorAPI {
    constructor() {
        this.isGenerating = false;
        this.lastGenerated = null;
        this.cacheTimeout = 30 * 60 * 1000; // 30 minutes cache
    }
    
    /**
     * Generate fresh meal plan using existing backend meal generation
     * This leverages /api/refresh-meals which already handles preferences
     */
    async generateMealPlan(ingredientPool, preferences = {}) {
        if (this.isGenerating) return null;
        
        // Check cache first
        if (this.lastGenerated && 
            Date.now() - this.lastGenerated.timestamp < this.cacheTimeout) {
            console.log('Using cached meal plan');
            return this.lastGenerated.meals;
        }
        
        this.isGenerating = true;
        
        try {
            const phone = getPhoneNumber();
            
            // First, get the cart data from AppState
            const cartData = window.AppState.mealPlanData?.cart_data;
            if (!cartData) {
                console.error('No cart data available');
                return this.generateFallbackMeals(ingredientPool);
            }
            
            // Call existing refresh-meals endpoint to get meal suggestions
            const response = await apiCall('/api/refresh-meals', {
                method: 'POST',
                body: JSON.stringify({
                    cart_data: cartData,
                    phone: phone
                })
            });
            
            if (response.success && response.meals) {
                // Transform the 4 meal suggestions into a 5-day weekly plan
                const weeklyMeals = this.createWeeklyPlan(
                    response.meals,
                    ingredientPool,
                    preferences
                );
                
                // Cache the result
                this.lastGenerated = {
                    meals: weeklyMeals,
                    timestamp: Date.now()
                };
                
                return weeklyMeals;
            }
            
            // Fallback to template generation if API fails
            return this.generateFallbackMeals(ingredientPool);
            
        } catch (error) {
            console.error('Failed to generate meals via API:', error);
            return this.generateFallbackMeals(ingredientPool);
        } finally {
            this.isGenerating = false;
        }
    }
    
    /**
     * Create a 5-day weekly plan from meal suggestions
     * Uses holistic planning to optimize ingredient allocation across the week
     */
    createWeeklyPlan(mealSuggestions, ingredientPool, preferences) {
        const days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'];
        const weeklyMeals = [];
        
        // Reset allocation tracking
        Object.values(ingredientPool).forEach(ing => {
            ing.allocated = 0;
            ing.remaining = ing.total;
        });
        
        // Use the first 4 suggestions and add one more variation
        const mealsToUse = [...mealSuggestions];
        
        // If we have less than 5 meals, duplicate and vary the last one
        while (mealsToUse.length < 5) {
            const lastMeal = mealsToUse[mealsToUse.length - 1];
            // Create a variation by changing cooking method
            const variation = { ...lastMeal };
            variation.name = this.varyMealName(variation.name);
            mealsToUse.push(variation);
        }
        
        // Allocate ingredients for each day
        days.forEach((day, index) => {
            const baseMeal = mealsToUse[index] || mealsToUse[0];
            
            // Create meal object with clean name
            const meal = {
                day: day,
                name: ingredientCleaner.cleanMealName(baseMeal.name),
                protein: baseMeal.protein_per_serving ? `${baseMeal.protein_per_serving}g` : '25g',
                cook_time: baseMeal.time || '30 min',
                servings: baseMeal.servings || 2,
                ingredients_used: []
            };
            
            // Allocate ingredients based on meal name and available pool
            const allocated = ingredientAllocator.allocateForMeal(
                { name: meal.name, servings: meal.servings },
                ingredientPool
            );
            
            meal.ingredients_used = allocated.map(ing => ({
                name: ingredientCleaner.cleanForIngredientPool(ing.name),
                amount: ing.amount,
                unit: ing.unit
            }));
            
            weeklyMeals.push(meal);
        });
        
        return weeklyMeals;
    }
    
    /**
     * Vary a meal name by changing cooking method
     */
    varyMealName(originalName) {
        const variations = {
            'Pan-Seared': ['Grilled', 'Roasted', 'Baked'],
            'Grilled': ['Pan-Seared', 'Roasted', 'Herb-Crusted'],
            'Roasted': ['Pan-Seared', 'Grilled', 'Braised'],
            'Baked': ['Pan-Seared', 'Roasted', 'Grilled']
        };
        
        // Find current method and replace
        for (const [method, alternatives] of Object.entries(variations)) {
            if (originalName.includes(method)) {
                const newMethod = alternatives[Math.floor(Math.random() * alternatives.length)];
                return originalName.replace(method, newMethod);
            }
        }
        
        // If no method found, add one
        const methods = ['Pan-Seared', 'Grilled', 'Roasted'];
        const randomMethod = methods[Math.floor(Math.random() * methods.length)];
        return `${randomMethod} ${originalName}`;
    }
    
    /**
     * Prepare ingredients for API (kept for compatibility)
     */
    prepareIngredientsForAPI(ingredientPool) {
        const ingredients = [];
        
        Object.entries(ingredientPool).forEach(([name, info]) => {
            // Clean the name for better AI understanding
            const cleanName = ingredientCleaner.cleanForIngredientPool(name);
            
            ingredients.push({
                name: cleanName,
                original_name: name,
                quantity: info.total,
                unit: info.unit || 'piece',
                category: this.categorizeIngredient(name)
            });
        });
        
        return ingredients;
    }
    
    
    /**
     * Categorize ingredient
     */
    categorizeIngredient(name) {
        const nameLower = name.toLowerCase();
        
        // Proteins
        if (nameLower.includes('chicken') || nameLower.includes('beef') || 
            nameLower.includes('fish') || nameLower.includes('salmon') ||
            nameLower.includes('egg') || nameLower.includes('tofu')) {
            return 'protein';
        }
        
        // Fruits
        if (nameLower.includes('apple') || nameLower.includes('banana') ||
            nameLower.includes('berry') || nameLower.includes('peach') ||
            nameLower.includes('plum') || nameLower.includes('nectarine')) {
            return 'fruit';
        }
        
        // Default to vegetable
        return 'vegetable';
    }
    
    /**
     * Generate fallback meals if API fails
     */
    generateFallbackMeals(ingredientPool) {
        const meals = [];
        const days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'];
        
        // Simple fallback logic
        const proteins = Object.entries(ingredientPool)
            .filter(([name]) => this.categorizeIngredient(name) === 'protein')
            .slice(0, 5);
        
        days.forEach((day, index) => {
            let mealName = 'Seasonal Vegetables';
            let protein = '15g';
            
            if (proteins[index]) {
                const [name, info] = proteins[index];
                const cleanName = ingredientCleaner.cleanIngredientName(name);
                mealName = `Roasted ${cleanName} with Vegetables`;
                protein = '25g';
            }
            
            meals.push({
                day: day,
                name: mealName,
                protein: protein,
                cook_time: '30 min',
                servings: 2,
                ingredients_used: []
            });
        });
        
        return meals;
    }
    
    /**
     * Regenerate a single meal for a specific day
     */
    async regenerateMealForDay(day, ingredientPool, existingMeals, preferences = {}) {
        try {
            const phone = getPhoneNumber();
            
            // Get cart data
            const cartData = window.AppState.mealPlanData?.cart_data;
            if (!cartData) {
                console.error('No cart data available for regeneration');
                return null;
            }
            
            // Call refresh-meals to get new suggestions
            const response = await apiCall('/api/refresh-meals', {
                method: 'POST',
                body: JSON.stringify({
                    cart_data: cartData,
                    phone: phone
                })
            });
            
            if (response.success && response.meals && response.meals.length > 0) {
                // Pick a meal that's different from existing ones
                const existingNames = existingMeals.map(m => m.name.toLowerCase());
                
                // Find a meal that's not already used
                let selectedMeal = response.meals.find(meal => 
                    !existingNames.includes(meal.name.toLowerCase())
                );
                
                // If all are used, take the first one and vary it
                if (!selectedMeal) {
                    selectedMeal = response.meals[0];
                    selectedMeal.name = this.varyMealName(selectedMeal.name);
                }
                
                // Clean and format the meal
                const meal = {
                    name: ingredientCleaner.cleanMealName(selectedMeal.name),
                    protein: selectedMeal.protein_per_serving ? `${selectedMeal.protein_per_serving}g` : '25g',
                    cook_time: selectedMeal.time || '30 min',
                    servings: selectedMeal.servings || 2,
                    ingredients_used: []
                };
                
                // Allocate ingredients for this meal
                const allocated = ingredientAllocator.allocateForMeal(
                    { name: meal.name, servings: meal.servings },
                    ingredientPool
                );
                
                meal.ingredients_used = allocated.map(ing => ({
                    name: ingredientCleaner.cleanForIngredientPool(ing.name),
                    amount: ing.amount,
                    unit: ing.unit
                }));
                
                return meal;
            }
            
            // Fallback
            return this.generateFallbackMealForDay(day, ingredientPool);
            
        } catch (error) {
            console.error('Failed to regenerate meal:', error);
            return this.generateFallbackMealForDay(day, ingredientPool);
        }
    }
    
    /**
     * Generate fallback meal for a single day
     */
    generateFallbackMealForDay(day, ingredientPool) {
        // Find available protein
        const availableProtein = Object.entries(ingredientPool)
            .find(([name, info]) => {
                const category = this.categorizeIngredient(name);
                return category === 'protein' && info.remaining > 0;
            });
        
        let mealName = 'Seasonal Vegetable Medley';
        let protein = '10g';
        
        if (availableProtein) {
            const [name] = availableProtein;
            const cleanName = ingredientCleaner.cleanIngredientName(name);
            const methods = ['Pan-Seared', 'Grilled', 'Roasted', 'Baked'];
            const method = methods[Math.floor(Math.random() * methods.length)];
            mealName = `${method} ${cleanName} with Vegetables`;
            protein = '25g';
        }
        
        return {
            name: mealName,
            protein: protein,
            cook_time: '30 min',
            servings: 2,
            ingredients_used: []
        };
    }
    
    /**
     * Clear cache to force fresh generation
     */
    clearCache() {
        this.lastGenerated = null;
    }
}

// Export singleton
export const mealGeneratorAPI = new MealGeneratorAPI();