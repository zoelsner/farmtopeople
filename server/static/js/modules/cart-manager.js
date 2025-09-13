/**
 * Cart Manager Module
 * Handles cart analysis, scraping, and display
 */

import { eventBus, apiCall, saveToStorage, getFromStorage, getPhoneNumber } from './shared.js';

class CartManager {
    constructor() {
        this.currentCartData = null;
        this.isAnalyzing = false;
        this.refreshCount = parseInt(localStorage.getItem('mealRefreshCount') || '0');
        this.lastRefreshDate = localStorage.getItem('lastRefreshDate');
    }

    /**
     * Start cart analysis process
     */
    async startAnalysis(forceRefresh = false) {
        if (this.isAnalyzing) return;
        
        const phone = getPhoneNumber();
        if (!phone) {
            this.showError('Phone number not found. Please complete onboarding first.');
            return;
        }

        this.isAnalyzing = true;
        window.AppState.currentState = 'loading';
        this.showLoadingState();

        try {
            const response = await apiCall('/api/analyze-cart', {
                method: 'POST',
                body: JSON.stringify({ 
                    phone_number: phone,
                    force_refresh: forceRefresh 
                })
            });

            if (response.success && response.cart_data) {
                this.currentCartData = response.cart_data;
                window.AppState.mealPlanData = { cart_data: response.cart_data };
                
                // Save to storage
                saveToStorage('cartAnalysisData', {
                    cartData: response.cart_data,
                    timestamp: Date.now()
                });
                saveToStorage('cartAnalysisState', 'complete');
                
                // Show results
                this.showCartAnalysis(response.cart_data);
                
                // Generate meal suggestions
                if (!forceRefresh || this.canRefreshMeals()) {
                    await this.generateMealSuggestions(response.cart_data);
                }
                
                // Notify other modules
                eventBus.emit('cart-analyzed', response.cart_data);
            } else {
                throw new Error(response.message || 'Failed to analyze cart');
            }
        } catch (error) {
            console.error('Cart analysis error:', error);
            this.showError('Failed to analyze cart. Please try again.');
        } finally {
            this.isAnalyzing = false;
        }
    }

    /**
     * Load saved cart data from storage
     */
    async loadSavedCartData() {
        const savedData = getFromStorage('cartAnalysisData');
        const savedState = localStorage.getItem('cartAnalysisState');
        
        if (savedData && savedData.cartData && savedState === 'complete') {
            const hourAgo = Date.now() - (60 * 60 * 1000);
            
            if (savedData.timestamp > hourAgo) {
                this.currentCartData = savedData.cartData;
                window.AppState.mealPlanData = { cart_data: savedData.cartData };
                this.showCartAnalysis(savedData.cartData);
                
                // Load cached meals if available
                const cachedMeals = getFromStorage('cachedMealSuggestions');
                if (cachedMeals) {
                    this.updateMealSuggestions(cachedMeals);
                }
                
                return true;
            }
        }
        return false;
    }

    /**
     * Display cart analysis results
     */
    showCartAnalysis(cartData) {
        window.AppState.currentState = 'complete';
        
        // Update UI
        document.getElementById('loadingSection').classList.remove('active');
        document.getElementById('cartAnalysisSection').classList.add('active');
        document.getElementById('headerSubtitle').textContent = 'Cart analysis complete';
        
        // Show delivery date
        this.showDeliveryDate(cartData);
        
        // Calculate category counts
        const counts = this.calculateCategoryCounts(cartData);
        this.displayCategoryCounts(counts);
        
        // Display items
        this.displayCartItems(cartData);
        
        // Display boxes
        this.displayCartBoxes(cartData);
    }

    /**
     * Calculate category counts from cart data
     */
    calculateCategoryCounts(cartData) {
        const counts = { protein: 0, produce: 0, fruit: 0 };
        
        // Count individual items
        if (cartData.individual_items) {
            cartData.individual_items.forEach(item => {
                const category = this.getItemCategory(item.name);
                if (counts.hasOwnProperty(category)) {
                    counts[category] += item.quantity || 1;
                }
            });
        }
        
        // Count box items
        ['customizable_boxes', 'non_customizable_boxes'].forEach(boxType => {
            if (cartData[boxType]) {
                cartData[boxType].forEach(box => {
                    if (box.selected_items) {
                        box.selected_items.forEach(item => {
                            const category = this.getItemCategory(item.name);
                            if (counts.hasOwnProperty(category)) {
                                counts[category] += item.quantity || 1;
                            }
                        });
                    }
                });
            }
        });
        
        return counts;
    }

    /**
     * Determine item category based on name
     */
    getItemCategory(itemName) {
        const name = itemName.toLowerCase();
        
        // Proteins
        if (name.includes('chicken') || name.includes('beef') || name.includes('pork') ||
            name.includes('fish') || name.includes('salmon') || name.includes('turkey') ||
            name.includes('egg') || name.includes('tofu') || name.includes('shrimp')) {
            return 'protein';
        }
        
        // Fruits
        if (name.includes('apple') || name.includes('banana') || name.includes('berry') ||
            name.includes('orange') || name.includes('grape') || name.includes('melon') ||
            name.includes('peach') || name.includes('pear') || name.includes('fruit')) {
            return 'fruit';
        }
        
        // Default to produce
        return 'produce';
    }

    /**
     * Display category counts
     */
    displayCategoryCounts(counts) {
        Object.entries(counts).forEach(([category, count]) => {
            const element = document.getElementById(`${category}Count`);
            if (element) {
                element.textContent = count;
            }
        });
    }

    /**
     * Display individual cart items
     */
    displayCartItems(cartData) {
        const container = document.getElementById('individualItemsList');
        if (!container) return;
        
        if (cartData.individual_items && cartData.individual_items.length > 0) {
            const itemsHTML = cartData.individual_items.map(item => {
                const category = this.getItemCategory(item.name);
                const color = this.getCategoryColor(category);
                
                return `
                    <div class="cart-item">
                        <span class="item-dot" style="background-color: ${color}"></span>
                        <span class="item-name">${item.name}</span>
                        <span class="item-quantity">${item.quantity || 1} ${item.unit || ''}</span>
                    </div>
                `;
            }).join('');
            
            container.innerHTML = itemsHTML;
            document.getElementById('individualItemsSection').style.display = 'block';
        } else {
            document.getElementById('individualItemsSection').style.display = 'none';
        }
    }

    /**
     * Display cart boxes
     */
    displayCartBoxes(cartData) {
        const container = document.getElementById('boxesList');
        if (!container) return;
        
        const allBoxes = [
            ...(cartData.customizable_boxes || []),
            ...(cartData.non_customizable_boxes || [])
        ];
        
        if (allBoxes.length > 0) {
            const boxesHTML = allBoxes.map(box => {
                const isCustomizable = box.customizable !== false;
                const itemsList = (box.selected_items || []).map(item => {
                    const category = this.getItemCategory(item.name);
                    const color = this.getCategoryColor(category);
                    
                    return `
                        <div class="box-item">
                            <span class="item-dot" style="background-color: ${color}"></span>
                            <span>${item.name}</span>
                        </div>
                    `;
                }).join('');
                
                return `
                    <div class="box-container">
                        <div class="box-header">
                            <span class="box-name">${box.box_name || 'Unnamed Box'}</span>
                            ${isCustomizable ? '<span class="customizable-badge">Customizable</span>' : ''}
                        </div>
                        <div class="box-items">${itemsList}</div>
                    </div>
                `;
            }).join('');
            
            container.innerHTML = boxesHTML;
            document.getElementById('boxesSection').style.display = 'block';
        } else {
            document.getElementById('boxesSection').style.display = 'none';
        }
    }

    /**
     * Get color for category
     */
    getCategoryColor(category) {
        const colors = {
            protein: '#FF6B6B',
            produce: '#51CF66',
            fruit: '#FFD93D'
        };
        return colors[category] || colors.produce;
    }

    /**
     * Show delivery date if available
     */
    showDeliveryDate(cartData) {
        const deliveryElement = document.getElementById('deliveryDate');
        if (!deliveryElement) return;
        
        if (cartData.delivery_date) {
            const date = new Date(cartData.delivery_date);
            const formatted = date.toLocaleDateString('en-US', { 
                weekday: 'short', 
                month: 'short', 
                day: 'numeric' 
            });
            deliveryElement.innerHTML = `🚚 Delivery: <span style="color: #51CF66; font-weight: bold;">${formatted}</span>`;
            deliveryElement.style.display = 'block';
        } else {
            deliveryElement.style.display = 'none';
        }
    }

    /**
     * Generate meal suggestions from cart
     */
    async generateMealSuggestions(cartData) {
        try {
            const phone = getPhoneNumber();
            const response = await apiCall('/api/generate-meals', {
                method: 'POST',
                body: JSON.stringify({
                    phone_number: phone,
                    cart_data: cartData
                })
            });
            
            if (response.meals) {
                this.updateMealSuggestions(response.meals);
                
                // Cache meals
                saveToStorage('cachedMealSuggestions', response.meals);
                saveToStorage('cachedMealSuggestionsTimestamp', Date.now());
                
                // Update refresh count
                this.refreshCount++;
                localStorage.setItem('mealRefreshCount', this.refreshCount.toString());
                localStorage.setItem('lastRefreshDate', new Date().toDateString());
            }
        } catch (error) {
            console.error('Failed to generate meals:', error);
        }
    }

    /**
     * Update meal suggestions display
     */
    updateMealSuggestions(meals) {
        const container = document.getElementById('suggestedMeals');
        if (!container || !meals) return;
        
        const mealsHTML = meals.map(meal => `
            <div class="meal-suggestion">
                <div class="meal-header">
                    <h4>${meal.name}</h4>
                    <span class="protein-badge">${meal.protein || '30g'} protein</span>
                </div>
                <p class="meal-description">${meal.description || ''}</p>
                <div class="meal-meta">
                    <span>⏱️ ${meal.cook_time || '30 min'}</span>
                    <span>👥 ${meal.servings || '2'} servings</span>
                    <span>🍽️ ${meal.difficulty || 'Easy'}</span>
                </div>
            </div>
        `).join('');
        
        container.innerHTML = mealsHTML;
    }

    /**
     * Check if meals can be refreshed (3x per day limit)
     */
    canRefreshMeals() {
        const today = new Date().toDateString();
        
        if (this.lastRefreshDate !== today) {
            this.refreshCount = 0;
            localStorage.setItem('mealRefreshCount', '0');
            localStorage.setItem('lastRefreshDate', today);
            return true;
        }
        
        return this.refreshCount < 3;
    }

    /**
     * Show loading state
     */
    showLoadingState() {
        document.getElementById('startSection').classList.remove('active');
        document.getElementById('cartAnalysisSection').classList.remove('active');
        document.getElementById('loadingSection').classList.add('active');
        document.getElementById('headerSubtitle').textContent = 'Analyzing your cart...';
    }

    /**
     * Show error state
     */
    showError(message) {
        window.AppState.currentState = 'error';
        alert(message); // Replace with better error UI
    }
}

// Initialize and export
const cartManager = new CartManager();

// Export for use in dashboard
window.CartManager = cartManager;

export default cartManager;