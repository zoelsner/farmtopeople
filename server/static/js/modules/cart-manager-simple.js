/**
 * Cart Manager Module
 * Handles cart analysis and display
 */

export class CartManager {
    constructor() {
        this.cartData = null;
        this.mealSuggestions = null;
        this.phone = localStorage.getItem('userPhone') || '4254955323';
    }

    async loadSavedCart() {
        try {
            const response = await fetch('/api/get-saved-cart');
            const data = await response.json();
            
            if (data.success && data.cart_data) {
                this.cartData = data.cart_data;
                this.displaySavedCart();
            } else {
                this.displayStartScreen();
            }
        } catch (error) {
            console.error('Error loading saved cart:', error);
            this.displayStartScreen();
        }
    }

    displayStartScreen() {
        const container = document.getElementById('cartContainer');
        if (!container) return;
        
        container.innerHTML = `
            <div style="text-align: center; padding: 60px 20px;">
                <div style="font-size: 48px; margin-bottom: 20px;">📦</div>
                <h2 style="font-size: 24px; margin-bottom: 8px;">Cart Analysis</h2>
                <p style="color: #6c757d; margin-bottom: 24px;">
                    See what's in your Farm to People cart, suggested swaps, and add-ons.
                </p>
                <button onclick="window.cartManager.startAnalysis()" class="btn-primary" style="background: #28a745;">
                    Analyze My Cart
                </button>
            </div>
        `;
    }

    displaySavedCart() {
        const container = document.getElementById('cartContainer');
        if (!container) return;
        
        // Show delivery date
        const deliveryEl = document.getElementById('deliveryDate');
        const deliveryTextEl = document.getElementById('deliveryDateText');
        if (deliveryEl && deliveryTextEl && this.cartData.delivery_date) {
            deliveryTextEl.textContent = this.formatDeliveryDate(this.cartData.delivery_date);
            deliveryEl.style.display = 'block';
        }
        
        // Build cart display
        container.innerHTML = `
            <div style="padding: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                    <h3 style="margin: 0;">Suggested Meals</h3>
                    <div style="display: flex; gap: 10px;">
                        <button onclick="window.cartManager.refreshMeals()" class="btn-secondary">
                            ✨ New Suggestions
                        </button>
                        <button onclick="window.cartManager.startAnalysis()" class="btn-primary">
                            🔄 Refresh Cart
                        </button>
                    </div>
                </div>
                <div id="mealSuggestions">
                    ${this.mealSuggestions ? this.renderMeals() : '<p>Loading meal suggestions...</p>'}
                </div>
                
                <h3 style="margin-top: 30px;">Cart Contents</h3>
                <div id="cartItems">
                    ${this.renderCartItems()}
                </div>
            </div>
        `;
        
        // Load meal suggestions if not already loaded
        if (!this.mealSuggestions) {
            this.loadMealSuggestions();
        }
    }

    renderCartItems() {
        if (!this.cartData) return '';
        
        let html = '';
        
        // Individual items
        if (this.cartData.individual_items && this.cartData.individual_items.length > 0) {
            html += '<h4>Individual Items</h4><div style="margin-bottom: 20px;">';
            this.cartData.individual_items.forEach(item => {
                html += `
                    <div style="padding: 12px; background: white; border-radius: 8px; margin-bottom: 8px; border: 1px solid #e9ecef;">
                        <div style="display: flex; justify-content: space-between;">
                            <span>${item.name}</span>
                            <span style="color: #28a745; font-weight: 600;">${item.price}</span>
                        </div>
                        ${item.quantity ? `<div style="color: #6c757d; font-size: 14px;">${item.quantity} ${item.unit || ''}</div>` : ''}
                    </div>
                `;
            });
            html += '</div>';
        }
        
        // Customizable boxes
        if (this.cartData.customizable_boxes && this.cartData.customizable_boxes.length > 0) {
            html += '<h4>Customizable Boxes</h4><div>';
            this.cartData.customizable_boxes.forEach(box => {
                html += `
                    <div style="padding: 16px; background: white; border-radius: 8px; margin-bottom: 12px; border: 1px solid #e9ecef;">
                        <div style="font-weight: 600; margin-bottom: 8px;">${box.box_name}</div>
                        <div style="color: #6c757d; font-size: 14px;">
                            ${box.selected_count} items selected
                            ${box.alternatives_count ? ` • ${box.alternatives_count} alternatives available` : ''}
                        </div>
                    </div>
                `;
            });
            html += '</div>';
        }
        
        return html;
    }

    renderMeals() {
        if (!this.mealSuggestions || this.mealSuggestions.length === 0) {
            return '<p>No meal suggestions available.</p>';
        }
        
        return this.mealSuggestions.map(meal => `
            <div style="padding: 16px; background: white; border-radius: 12px; margin-bottom: 12px; border: 1px solid #e9ecef;">
                <h4 style="margin-bottom: 8px;">${meal.name}</h4>
                <div style="color: #007AFF; font-weight: 600; margin-bottom: 8px;">
                    ${meal.protein || 0}g protein
                </div>
                <div style="color: #6c757d; font-size: 14px;">
                    ${meal.time || '30 min'} • ${meal.servings || 4} servings
                </div>
            </div>
        `).join('');
    }

    async startAnalysis() {
        const container = document.getElementById('cartContainer');
        if (!container) return;
        
        // Show loading state
        container.innerHTML = `
            <div style="text-align: center; padding: 60px 20px;">
                <div class="loading-animation"></div>
                <h3>Analyzing Your Cart</h3>
                <p style="color: #6c757d;">This may take 20-30 seconds...</p>
            </div>
        `;
        
        try {
            const response = await fetch('/api/analyze-cart', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ phone: this.phone })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.cartData = data.cart_data;
                this.mealSuggestions = data.meals;
                this.displaySavedCart();
            } else {
                container.innerHTML = `
                    <div style="text-align: center; padding: 60px 20px;">
                        <p style="color: #dc3545;">Failed to analyze cart: ${data.error || 'Unknown error'}</p>
                        <button onclick="window.cartManager.startAnalysis()" class="btn-primary" style="margin-top: 20px;">
                            Try Again
                        </button>
                    </div>
                `;
            }
        } catch (error) {
            console.error('Error analyzing cart:', error);
            container.innerHTML = `
                <div style="text-align: center; padding: 60px 20px;">
                    <p style="color: #dc3545;">Error analyzing cart</p>
                    <button onclick="window.cartManager.startAnalysis()" class="btn-primary" style="margin-top: 20px;">
                        Try Again
                    </button>
                </div>
            `;
        }
    }

    async refreshMeals() {
        const suggestionsEl = document.getElementById('mealSuggestions');
        if (!suggestionsEl) return;
        
        suggestionsEl.innerHTML = '<p>Generating new meal suggestions...</p>';
        
        try {
            const response = await fetch('/api/refresh-meals', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ phone: this.phone })
            });
            
            const data = await response.json();
            
            if (data.success && data.meals) {
                this.mealSuggestions = data.meals;
                suggestionsEl.innerHTML = this.renderMeals();
            } else {
                suggestionsEl.innerHTML = '<p style="color: #dc3545;">Failed to generate new suggestions</p>';
            }
        } catch (error) {
            console.error('Error refreshing meals:', error);
            suggestionsEl.innerHTML = '<p style="color: #dc3545;">Error generating suggestions</p>';
        }
    }

    async loadMealSuggestions() {
        try {
            const response = await fetch('/api/refresh-meals', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ phone: this.phone })
            });
            
            const data = await response.json();
            
            if (data.success && data.meals) {
                this.mealSuggestions = data.meals;
                const suggestionsEl = document.getElementById('mealSuggestions');
                if (suggestionsEl) {
                    suggestionsEl.innerHTML = this.renderMeals();
                }
            }
        } catch (error) {
            console.error('Error loading meal suggestions:', error);
        }
    }

    formatDeliveryDate(dateStr) {
        if (!dateStr) return '';
        // Extract the readable part if it's a complex date string
        const match = dateStr.match(/([A-Za-z]+,\s+[A-Za-z]+\s+\d+)/);
        return match ? match[1] : dateStr;
    }
}

// Export the class
export { CartManager };