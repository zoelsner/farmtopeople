/**
 * Meal Type Selector Module
 * Interactive meal planning based on user preferences and cart capacity
 */

import { EventBus } from './shared.js';
import { ingredientAllocator } from './ingredient-allocator.js';

export class MealTypeSelector {
    constructor() {
        this.container = null;
        this.preferences = {};
        this.cartCapacity = {};
        this.selectedMeals = {
            dinner: 0,
            lunch: 0,
            breakfast: 0,
            snacks: 0
        };
        this.ingredientPool = {};
    }
    
    /**
     * Initialize the selector in the given container
     */
    init(containerId, preferences, ingredientPool) {
        this.container = document.getElementById(containerId);
        this.preferences = preferences;
        this.ingredientPool = ingredientPool;
        
        // Analyze cart capacity first
        this.analyzeCartCapacity();
        
        // Render the selector UI
        this.render();
        
        // Set up event listeners
        this.attachEventListeners();
    }
    
    /**
     * Analyze what the cart can support
     */
    analyzeCartCapacity() {
        // Calculate total protein servings available
        const proteins = Object.entries(this.ingredientPool)
            .filter(([name, info]) => {
                const category = ingredientAllocator.categorizeIngredient(name);
                return category === 'protein';
            });
        
        let totalProteinServings = 0;
        proteins.forEach(([name, info]) => {
            const unit = (info.unit || '').toLowerCase();
            if (unit === 'lbs' || unit === 'lb') {
                // Approximately 4 servings per pound
                totalProteinServings += info.total * 4;
            } else if (unit === 'pieces' || unit === 'piece') {
                // Depends on the item
                if (name.toLowerCase().includes('egg')) {
                    totalProteinServings += info.total / 2; // 2 eggs per serving
                } else {
                    totalProteinServings += info.total; // 1 piece per serving
                }
            }
        });
        
        // Calculate vegetable abundance
        const vegetables = Object.entries(this.ingredientPool)
            .filter(([name, info]) => {
                const category = ingredientAllocator.categorizeIngredient(name);
                return category === 'vegetable';
            });
        
        const hasAbundantVeggies = vegetables.length > 5;
        
        // Determine capacity based on preferences
        const mealPreferences = this.preferences.meal_timing || ['dinner'];
        
        // Smart capacity calculation
        this.cartCapacity = {
            dinner: Math.min(5, Math.floor(totalProteinServings * 0.6)), // Most proteins go to dinner
            lunch: mealPreferences.includes('lunch') ? Math.min(3, Math.floor(totalProteinServings * 0.3)) : 0,
            breakfast: mealPreferences.includes('breakfast') ? Math.min(3, Math.floor(totalProteinServings * 0.2)) : 0,
            snacks: hasAbundantVeggies ? 5 : 3 // Snacks don't need protein
        };
        
        // Adjust based on what user said they cook for
        mealPreferences.forEach(pref => {
            if (pref === 'dinner' && !this.cartCapacity.dinner) {
                this.cartCapacity.dinner = Math.min(3, totalProteinServings);
            }
            if (pref === 'lunch' && !this.cartCapacity.lunch) {
                this.cartCapacity.lunch = Math.min(2, Math.floor(totalProteinServings * 0.3));
            }
        });
        
        console.log('Cart capacity analysis:', this.cartCapacity);
        console.log('Total protein servings:', totalProteinServings);
    }
    
    /**
     * Render the selector UI
     */
    render() {
        if (!this.container) return;
        
        const mealPreferences = this.preferences.meal_timing || ['dinner'];
        
        // Build HTML
        let html = `
            <div class="meal-type-selector">
                <div class="selector-header">
                    <h3>Plan Your Week</h3>
                    <p class="selector-subtitle">Based on your cart, here's what we can make:</p>
                </div>
                
                <div class="meal-type-grid">`;
        
        // Only show meal types from user preferences
        mealPreferences.forEach(mealType => {
            const capacity = this.cartCapacity[mealType] || 0;
            const icon = this.getMealIcon(mealType);
            
            // Suggest default amounts
            let suggested = 0;
            if (mealType === 'dinner') {
                suggested = Math.min(3, capacity); // Suggest 3 dinners
            } else if (mealType === 'lunch') {
                suggested = Math.min(2, capacity); // Suggest 2 lunches
            } else if (mealType === 'breakfast') {
                suggested = Math.min(2, capacity); // Suggest 2 breakfasts
            } else if (mealType === 'snacks') {
                suggested = Math.min(2, capacity); // Suggest 2 snacks
            }
            
            this.selectedMeals[mealType] = suggested; // Set initial selection
            
            html += `
                <div class="meal-type-card" data-meal-type="${mealType}">
                    <div class="meal-type-header">
                        <span class="meal-icon">${icon}</span>
                        <span class="meal-type-name">${this.capitalize(mealType)}</span>
                    </div>
                    <div class="meal-capacity">
                        <span class="capacity-label">Max: ${capacity}</span>
                        ${suggested > 0 ? `<span class="suggested">(Suggested: ${suggested})</span>` : ''}
                    </div>
                    <div class="meal-selector">
                        <button class="selector-btn minus" data-meal-type="${mealType}" data-action="minus">-</button>
                        <input type="number" 
                               class="meal-count" 
                               id="${mealType}-count"
                               data-meal-type="${mealType}"
                               value="${suggested}" 
                               min="0" 
                               max="${capacity}"
                               readonly>
                        <button class="selector-btn plus" data-meal-type="${mealType}" data-action="plus">+</button>
                    </div>
                </div>`;
        });
        
        html += `
                </div>
                
                <div class="ingredient-summary">
                    <h4>Ingredient Usage Preview</h4>
                    <div class="usage-bars" id="usage-preview">
                        <!-- Will be updated dynamically -->
                    </div>
                </div>
                
                <div class="selector-actions">
                    <button class="btn btn-secondary" id="reset-selections">Reset</button>
                    <button class="btn btn-primary" id="generate-meal-plan">
                        Generate Meal Plan
                    </button>
                </div>
            </div>`;
        
        this.container.innerHTML = html;
        
        // Update usage preview
        this.updateUsagePreview();
        
        // Add styles
        this.injectStyles();
    }
    
    /**
     * Update ingredient usage preview
     */
    updateUsagePreview() {
        const previewContainer = document.getElementById('usage-preview');
        if (!previewContainer) return;
        
        // Calculate estimated usage
        const totalMeals = Object.values(this.selectedMeals).reduce((a, b) => a + b, 0);
        const estimatedProteinUsage = (totalMeals * 20) + '%'; // Rough estimate
        const estimatedVeggieUsage = (totalMeals * 15) + '%'; // Rough estimate
        
        let html = `
            <div class="usage-item">
                <span class="usage-label">Proteins</span>
                <div class="usage-bar">
                    <div class="usage-fill" style="width: ${Math.min(100, totalMeals * 20)}%"></div>
                </div>
                <span class="usage-percent">${Math.min(100, totalMeals * 20)}%</span>
            </div>
            <div class="usage-item">
                <span class="usage-label">Vegetables</span>
                <div class="usage-bar">
                    <div class="usage-fill" style="width: ${Math.min(100, totalMeals * 15)}%"></div>
                </div>
                <span class="usage-percent">${Math.min(100, totalMeals * 15)}%</span>
            </div>`;
        
        previewContainer.innerHTML = html;
    }
    
    /**
     * Attach event listeners
     */
    attachEventListeners() {
        // Plus/minus buttons
        document.querySelectorAll('.selector-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const mealType = e.target.dataset.mealType;
                const action = e.target.dataset.action;
                this.adjustMealCount(mealType, action);
            });
        });
        
        // Generate button
        const generateBtn = document.getElementById('generate-meal-plan');
        if (generateBtn) {
            generateBtn.addEventListener('click', () => {
                this.generateMealPlan();
            });
        }
        
        // Reset button
        const resetBtn = document.getElementById('reset-selections');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                this.resetSelections();
            });
        }
    }
    
    /**
     * Adjust meal count
     */
    adjustMealCount(mealType, action) {
        const input = document.getElementById(`${mealType}-count`);
        if (!input) return;
        
        let currentValue = parseInt(input.value) || 0;
        const max = parseInt(input.max) || 0;
        
        if (action === 'plus' && currentValue < max) {
            currentValue++;
        } else if (action === 'minus' && currentValue > 0) {
            currentValue--;
        }
        
        input.value = currentValue;
        this.selectedMeals[mealType] = currentValue;
        
        // Update preview
        this.updateUsagePreview();
    }
    
    /**
     * Reset selections to suggested
     */
    resetSelections() {
        const mealPreferences = this.preferences.meal_timing || ['dinner'];
        
        mealPreferences.forEach(mealType => {
            const capacity = this.cartCapacity[mealType] || 0;
            let suggested = 0;
            
            if (mealType === 'dinner') suggested = Math.min(3, capacity);
            else if (mealType === 'lunch') suggested = Math.min(2, capacity);
            else if (mealType === 'breakfast') suggested = Math.min(2, capacity);
            else if (mealType === 'snacks') suggested = Math.min(2, capacity);
            
            const input = document.getElementById(`${mealType}-count`);
            if (input) {
                input.value = suggested;
                this.selectedMeals[mealType] = suggested;
            }
        });
        
        this.updateUsagePreview();
    }
    
    /**
     * Generate meal plan based on selections
     */
    generateMealPlan() {
        console.log('Generating meal plan with selections:', this.selectedMeals);
        
        // Emit event for meal planner to handle
        EventBus.emit('generate-custom-meal-plan', {
            selections: this.selectedMeals,
            ingredientPool: this.ingredientPool,
            preferences: this.preferences
        });
        
        // Show loading state
        const generateBtn = document.getElementById('generate-meal-plan');
        if (generateBtn) {
            generateBtn.textContent = 'Generating...';
            generateBtn.disabled = true;
            
            setTimeout(() => {
                generateBtn.textContent = 'Generate Meal Plan';
                generateBtn.disabled = false;
            }, 3000);
        }
    }
    
    /**
     * Get meal icon
     */
    getMealIcon(mealType) {
        const icons = {
            breakfast: '🌅',
            lunch: '☀️',
            dinner: '🌙',
            snacks: '🥨'
        };
        return icons[mealType] || '🍽️';
    }
    
    /**
     * Capitalize string
     */
    capitalize(str) {
        return str.charAt(0).toUpperCase() + str.slice(1);
    }
    
    /**
     * Inject styles
     */
    injectStyles() {
        const styleId = 'meal-type-selector-styles';
        if (document.getElementById(styleId)) return;
        
        const styles = `
            <style id="${styleId}">
                .meal-type-selector {
                    background: white;
                    border-radius: 12px;
                    padding: 24px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }
                
                .selector-header {
                    margin-bottom: 24px;
                }
                
                .selector-header h3 {
                    margin: 0 0 8px 0;
                    font-size: 20px;
                    font-weight: 600;
                }
                
                .selector-subtitle {
                    color: #666;
                    margin: 0;
                }
                
                .meal-type-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 16px;
                    margin-bottom: 24px;
                }
                
                .meal-type-card {
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    padding: 16px;
                    background: #f9f9f9;
                }
                
                .meal-type-header {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    margin-bottom: 12px;
                }
                
                .meal-icon {
                    font-size: 24px;
                }
                
                .meal-type-name {
                    font-weight: 500;
                    font-size: 16px;
                }
                
                .meal-capacity {
                    margin-bottom: 12px;
                    font-size: 14px;
                    color: #666;
                }
                
                .capacity-label {
                    font-weight: 500;
                }
                
                .suggested {
                    margin-left: 8px;
                    color: #10b981;
                    font-size: 12px;
                }
                
                .meal-selector {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                }
                
                .selector-btn {
                    width: 32px;
                    height: 32px;
                    border-radius: 6px;
                    border: 1px solid #d0d0d0;
                    background: white;
                    cursor: pointer;
                    font-size: 18px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    transition: all 0.2s;
                }
                
                .selector-btn:hover {
                    background: #f0f0f0;
                    border-color: #10b981;
                }
                
                .meal-count {
                    width: 60px;
                    height: 32px;
                    text-align: center;
                    border: 1px solid #d0d0d0;
                    border-radius: 6px;
                    font-size: 16px;
                    font-weight: 500;
                }
                
                .ingredient-summary {
                    margin-bottom: 24px;
                    padding: 16px;
                    background: #f5f5f5;
                    border-radius: 8px;
                }
                
                .ingredient-summary h4 {
                    margin: 0 0 16px 0;
                    font-size: 14px;
                    color: #666;
                }
                
                .usage-item {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    margin-bottom: 8px;
                }
                
                .usage-label {
                    width: 80px;
                    font-size: 14px;
                    color: #666;
                }
                
                .usage-bar {
                    flex: 1;
                    height: 8px;
                    background: #e0e0e0;
                    border-radius: 4px;
                    overflow: hidden;
                }
                
                .usage-fill {
                    height: 100%;
                    background: linear-gradient(90deg, #10b981 0%, #059669 100%);
                    transition: width 0.3s ease;
                }
                
                .usage-percent {
                    width: 40px;
                    text-align: right;
                    font-size: 14px;
                    font-weight: 500;
                }
                
                .selector-actions {
                    display: flex;
                    gap: 12px;
                    justify-content: flex-end;
                }
                
                .btn {
                    padding: 10px 20px;
                    border-radius: 6px;
                    font-size: 14px;
                    font-weight: 500;
                    cursor: pointer;
                    transition: all 0.2s;
                    border: none;
                }
                
                .btn-primary {
                    background: #10b981;
                    color: white;
                }
                
                .btn-primary:hover {
                    background: #059669;
                }
                
                .btn-primary:disabled {
                    background: #9ca3af;
                    cursor: not-allowed;
                }
                
                .btn-secondary {
                    background: white;
                    color: #666;
                    border: 1px solid #d0d0d0;
                }
                
                .btn-secondary:hover {
                    background: #f0f0f0;
                }
            </style>`;
        
        document.head.insertAdjacentHTML('beforeend', styles);
    }
}

// Export singleton
export const mealTypeSelector = new MealTypeSelector();