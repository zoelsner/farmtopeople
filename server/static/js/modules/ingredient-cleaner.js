/**
 * Ingredient Cleaner Module
 * Cleans up verbose product names for display
 */

export class IngredientCleaner {
    constructor() {
        // ONLY remove processing terms that don't affect cooking
        // Keep quality indicators that customers value
        this.removeTerms = [
            'boneless',
            'skinless',
            // Only removing marketing fluff, not quality indicators
            'premium',
            'fresh',  // Everything should be fresh
            'all natural',
            'all-natural',
            'farm fresh',
            'locally sourced',  // Vague term
            'responsibly sourced',
            'small batch',
            'artisanal',
            'handpicked',
            'hand-picked'
        ];
        
        // Keep these terms as they're meaningful
        // Quality indicators: organic, grass-fed, pasture-raised, wild-caught, heirloom
        // Preparation states: ground, chopped, diced, sliced
        // Varieties: rainbow, bunched, cherry, baby
        // Important descriptors: bone-in, whole, split
        this.keepTerms = [
            'organic',
            'grass-fed',
            'grass fed',
            'pasture-raised',
            'pasture raised',
            'wild-caught',
            'wild caught',
            'heirloom',
            'heritage',
            'bone-in',
            'bone in',
            'whole',
            'split',
            'ground',
            'chopped',
            'diced',
            'sliced',
            'baby',
            'cherry',
            'grape',
            'rainbow',  // rainbow carrots
            'bunched',  // bunched carrots
            'yellow',
            'red',
            'white',
            'green',
            'purple',
            'steelhead', // type of fish
            'new york'  // NY strip steak
        ];
    }
    
    /**
     * Clean ingredient name for display
     */
    cleanIngredientName(name) {
        if (!name) return '';
        
        let cleaned = name;
        
        // Remove parenthetical info like (2 pack) or (1 lb)
        cleaned = cleaned.replace(/\([^)]*\)/g, '');
        
        // Remove terms we don't want
        this.removeTerms.forEach(term => {
            const regex = new RegExp(`\\b${term}\\b`, 'gi');
            cleaned = cleaned.replace(regex, '');
        });
        
        // Clean up extra spaces and punctuation
        cleaned = cleaned
            .replace(/,\s*,/g, ',')     // Remove double commas
            .replace(/\s+/g, ' ')        // Multiple spaces to single
            .replace(/^\s*,\s*/, '')     // Leading comma
            .replace(/\s*,\s*$/, '')     // Trailing comma
            .replace(/\s+&\s+/g, ' & ')  // Clean up ampersands
            .trim();
        
        // Capitalize properly
        cleaned = this.properCapitalization(cleaned);
        
        return cleaned;
    }
    
    /**
     * Clean meal name (more aggressive cleaning)
     */
    cleanMealName(mealName) {
        if (!mealName) return '';
        
        let cleaned = mealName;
        
        // First do basic cleaning
        cleaned = this.cleanIngredientName(cleaned);
        
        // Additional cleaning for meal names
        cleaned = cleaned
            .replace(/\bwith\s+with\b/gi, 'with')  // Remove double "with"
            .replace(/\band\s+and\b/gi, 'and');    // Remove double "and"
        
        // Simplify common patterns
        cleaned = this.simplifyMealName(cleaned);
        
        return cleaned;
    }
    
    /**
     * Simplify common meal name patterns
     */
    simplifyMealName(name) {
        // Map of replacements
        const simplifications = {
            'Chicken Breast': 'Chicken',
            'Chicken Breasts': 'Chicken',
            'Beef Steak': 'Beef',
            'Fish Fillet': 'Fish',
            'Eggs': 'Eggs'  // Keep eggs as is
        };
        
        let simplified = name;
        
        Object.entries(simplifications).forEach(([long, short]) => {
            const regex = new RegExp(`\\b${long}\\b`, 'gi');
            simplified = simplified.replace(regex, short);
        });
        
        return simplified;
    }
    
    /**
     * Clean ingredient for display in ingredient pool
     */
    cleanForIngredientPool(name) {
        if (!name) return '';
        
        let cleaned = name;
        
        // For ingredient pool, only remove boneless/skinless
        // Keep all quality indicators for transparency
        ['boneless', 'skinless'].forEach(term => {
            const regex = new RegExp(`\\b${term}\\b`, 'gi');
            cleaned = cleaned.replace(regex, '');
        });
        
        // Clean up extra spaces and punctuation
        cleaned = cleaned
            .replace(/,\s*,/g, ',')     // Remove double commas
            .replace(/\s+/g, ' ')        // Multiple spaces to single
            .replace(/^[\s,]+/, '')      // Leading comma/spaces
            .replace(/[\s,]+$/, '')      // Trailing comma/spaces
            .trim();
        
        return this.properCapitalization(cleaned);
    }
    
    /**
     * Proper capitalization for names
     */
    properCapitalization(str) {
        if (!str) return '';
        
        // Words that should stay lowercase
        const lowercase = ['with', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'of', 'a', 'an', 'the'];
        
        return str
            .toLowerCase()
            .split(' ')
            .map((word, index) => {
                // Always capitalize first word
                if (index === 0) {
                    return word.charAt(0).toUpperCase() + word.slice(1);
                }
                // Keep certain words lowercase
                if (lowercase.includes(word)) {
                    return word;
                }
                // Capitalize others
                return word.charAt(0).toUpperCase() + word.slice(1);
            })
            .join(' ');
    }
    
    /**
     * Generate clean meal name from ingredients
     */
    generateCleanMealName(protein, vegetables = [], cookingMethod = 'Roasted') {
        const cleanProtein = this.cleanIngredientName(protein);
        const cleanVeggies = vegetables.map(v => this.cleanIngredientName(v));
        
        // Build meal name
        let mealName = `${cookingMethod} ${cleanProtein}`;
        
        if (cleanVeggies.length > 0) {
            if (cleanVeggies.length === 1) {
                mealName += ` with ${cleanVeggies[0]}`;
            } else if (cleanVeggies.length === 2) {
                mealName += ` with ${cleanVeggies.join(' and ')}`;
            } else {
                // For 3+ vegetables, use "Seasonal Vegetables"
                mealName += ` with Seasonal Vegetables`;
            }
        }
        
        return mealName;
    }
}

// Export singleton
export const ingredientCleaner = new IngredientCleaner();