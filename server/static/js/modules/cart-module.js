// Cart Analysis Module
// Handles all cart-related functionality including analysis, display, and refresh

export class CartModule {
    constructor() {
        this.cartData = null;
        this.refreshCount = parseInt(localStorage.getItem('refreshCount') || '0');
        this.lastRefreshDate = localStorage.getItem('lastRefreshDate');
        this.isAnalyzing = false;
    }

    async analyzeCart(forceRefresh = false) {
        if (this.isAnalyzing) return;
        
        const analyzeBtn = document.getElementById('analyzeBtn');
        const cartAnalysis = document.getElementById('cartAnalysis');
        const loadingState = document.getElementById('loadingState');
        const errorState = document.getElementById('errorState');
        const cartSummary = document.getElementById('cartSummary');
        const mealSuggestions = document.getElementById('mealSuggestions');
        
        this.isAnalyzing = true;
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = '<span class="loading-spinner"></span> Analyzing...';
        
        cartAnalysis.style.display = 'none';
        errorState.style.display = 'none';
        loadingState.style.display = 'block';
        
        const phone = localStorage.getItem('userPhone');
        if (!phone) {
            this.showError('No phone number found. Please complete onboarding first.');
            return;
        }
        
        try {
            const response = await fetch('/api/analyze-cart', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    phone_number: phone,
                    force_refresh: forceRefresh
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Failed to analyze cart');
            }
            
            const data = await response.json();
            
            if (data.success) {
                this.cartData = data.cart_data;
                window.mealPlanData = { cart_data: this.cartData };
                
                this.showCartAnalysis(this.cartData);
                this.generateMealSuggestions(this.cartData);
                
                if (data.delivery_date) {
                    this.updateDeliveryDate(data.delivery_date);
                }
                
                loadingState.style.display = 'none';
                cartAnalysis.style.display = 'block';
                
                if (forceRefresh) {
                    this.updateRefreshCount();
                }
                
                analyzeBtn.innerHTML = 'Refresh Analysis';
                
                document.getElementById('headerSubtitle').textContent = 'Your cart has been analyzed';
                
                if (window.navigationManager) {
                    window.navigationManager.enableMealsTab();
                }
            } else {
                throw new Error(data.message || 'Analysis failed');
            }
        } catch (error) {
            console.error('Cart analysis error:', error);
            this.showError(error.message);
        } finally {
            this.isAnalyzing = false;
            analyzeBtn.disabled = false;
            if (!this.cartData) {
                analyzeBtn.innerHTML = 'Analyze Cart';
            }
        }
    }

    showCartAnalysis(cartData) {
        const cartSummary = document.getElementById('cartSummary');
        let html = '<div class="cart-analysis-content">';
        
        // Individual items
        if (cartData.individual_items && cartData.individual_items.length > 0) {
            html += '<div class="cart-section">';
            html += '<h3 class="cart-section-title">Individual Items</h3>';
            html += '<div class="items-grid">';
            cartData.individual_items.forEach(item => {
                html += `
                    <div class="cart-item">
                        <div class="item-name">${item.name}</div>
                        <div class="item-details">
                            <span class="item-quantity">${item.quantity} ${item.unit}</span>
                            ${item.price ? `<span class="item-price">${item.price}</span>` : ''}
                        </div>
                    </div>
                `;
            });
            html += '</div></div>';
        }
        
        // Customizable boxes
        if (cartData.customizable_boxes && cartData.customizable_boxes.length > 0) {
            cartData.customizable_boxes.forEach(box => {
                html += '<div class="cart-section">';
                html += `<h3 class="cart-section-title">${box.box_name}</h3>`;
                if (box.customizable) {
                    html += '<span class="customizable-badge">Customizable</span>';
                }
                html += '<div class="items-grid">';
                box.selected_items.forEach(item => {
                    html += `
                        <div class="cart-item">
                            <div class="item-name">${item.name}</div>
                            <div class="item-details">
                                <span class="item-quantity">${item.quantity} ${item.unit}</span>
                            </div>
                        </div>
                    `;
                });
                html += '</div>';
                
                if (box.available_alternatives && box.available_alternatives.length > 0) {
                    html += '<div class="alternatives-section">';
                    html += '<h4>Available Alternatives</h4>';
                    html += '<div class="alternatives-list">';
                    box.available_alternatives.forEach(alt => {
                        html += `<span class="alternative-item">${alt.name}</span>`;
                    });
                    html += '</div></div>';
                }
                html += '</div>';
            });
        }
        
        // Non-customizable boxes
        if (cartData.non_customizable_boxes && cartData.non_customizable_boxes.length > 0) {
            cartData.non_customizable_boxes.forEach(box => {
                html += '<div class="cart-section">';
                html += `<h3 class="cart-section-title">${box.box_name}</h3>`;
                html += '<div class="items-grid">';
                box.selected_items.forEach(item => {
                    html += `
                        <div class="cart-item">
                            <div class="item-name">${item.name}</div>
                            <div class="item-details">
                                <span class="item-quantity">${item.quantity} ${item.unit}</span>
                            </div>
                        </div>
                    `;
                });
                html += '</div></div>';
            });
        }
        
        html += '</div>';
        cartSummary.innerHTML = html;
    }

    generateMealSuggestions(cartData) {
        const mealSuggestions = document.getElementById('mealSuggestions');
        const proteins = [];
        const vegetables = [];
        const fruits = [];
        
        // Categorize ingredients
        const allItems = [
            ...(cartData.individual_items || []),
            ...(cartData.customizable_boxes || []).flatMap(box => box.selected_items || []),
            ...(cartData.non_customizable_boxes || []).flatMap(box => box.selected_items || [])
        ];
        
        allItems.forEach(item => {
            const name = item.name.toLowerCase();
            if (name.includes('chicken') || name.includes('beef') || name.includes('salmon') || 
                name.includes('pork') || name.includes('turkey') || name.includes('fish') ||
                name.includes('shrimp') || name.includes('egg')) {
                proteins.push(item);
            } else if (name.includes('apple') || name.includes('banana') || name.includes('berry') ||
                       name.includes('orange') || name.includes('peach') || name.includes('pear')) {
                fruits.push(item);
            } else {
                vegetables.push(item);
            }
        });
        
        // Generate meal suggestions
        let suggestionsHtml = '<div class="meal-suggestions-grid">';
        
        // Suggest 3-4 meals based on ingredients
        const mealIdeas = this.generateMealIdeas(proteins, vegetables);
        mealIdeas.forEach(meal => {
            suggestionsHtml += `
                <div class="meal-card">
                    <div class="meal-header">
                        <h4>${meal.name}</h4>
                        <span class="meal-time">${meal.cookTime}</span>
                    </div>
                    <div class="meal-protein">38g protein</div>
                    <div class="meal-ingredients">
                        <strong>Using from your cart:</strong>
                        <ul>
                            ${meal.ingredients.map(ing => `<li>${ing}</li>`).join('')}
                        </ul>
                    </div>
                    <button class="btn-secondary" onclick="window.cartModule.generateRecipe('${meal.name}')">
                        Get Recipe
                    </button>
                </div>
            `;
        });
        
        // Add swap suggestions
        if (cartData.customizable_boxes && cartData.customizable_boxes.some(box => box.customizable)) {
            suggestionsHtml += `
                <div class="swap-suggestions-card">
                    <h4>Smart Swaps for Better Meals</h4>
                    <div class="swap-list">
                        ${this.generateSwapSuggestions(cartData).map(swap => `
                            <div class="swap-item">
                                <span class="swap-out">${swap.out}</span>
                                <span class="swap-arrow">→</span>
                                <span class="swap-in">${swap.in}</span>
                                <span class="swap-reason">${swap.reason}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        
        suggestionsHtml += '</div>';
        mealSuggestions.innerHTML = suggestionsHtml;
    }

    generateMealIdeas(proteins, vegetables) {
        const meals = [];
        
        // Generate meals based on available proteins
        if (proteins.some(p => p.name.toLowerCase().includes('chicken'))) {
            meals.push({
                name: 'Herb-Roasted Chicken & Vegetables',
                cookTime: '35 min',
                ingredients: ['Chicken Breast', 'Seasonal Vegetables', 'Fresh Herbs']
            });
        }
        
        if (proteins.some(p => p.name.toLowerCase().includes('beef'))) {
            meals.push({
                name: 'Grass-Fed Beef Stir-Fry',
                cookTime: '20 min',
                ingredients: ['Ground Beef', 'Bell Peppers', 'Onions']
            });
        }
        
        if (proteins.some(p => p.name.toLowerCase().includes('salmon'))) {
            meals.push({
                name: 'Pan-Seared Salmon with Greens',
                cookTime: '15 min',
                ingredients: ['Fresh Salmon', 'Mixed Greens', 'Lemon']
            });
        }
        
        // Add a vegetarian option
        if (vegetables.length > 3) {
            meals.push({
                name: 'Roasted Vegetable Buddha Bowl',
                cookTime: '30 min',
                ingredients: ['Seasonal Vegetables', 'Quinoa', 'Tahini Dressing']
            });
        }
        
        return meals.slice(0, 4); // Return max 4 meals
    }

    generateSwapSuggestions(cartData) {
        const swaps = [];
        const customizableBox = cartData.customizable_boxes[0];
        
        if (!customizableBox || !customizableBox.available_alternatives) return swaps;
        
        // Suggest protein swaps
        const hasChicken = customizableBox.selected_items.some(i => i.name.toLowerCase().includes('chicken'));
        if (hasChicken) {
            const salmonAlt = customizableBox.available_alternatives.find(a => a.name.toLowerCase().includes('salmon'));
            if (salmonAlt) {
                swaps.push({
                    out: 'Chicken Breast',
                    in: 'Wild Salmon',
                    reason: 'Higher omega-3s'
                });
            }
        }
        
        // Suggest vegetable variety
        const hasBasicVeggies = customizableBox.selected_items.some(i => 
            i.name.toLowerCase().includes('carrot') || i.name.toLowerCase().includes('celery')
        );
        if (hasBasicVeggies) {
            swaps.push({
                out: 'Regular Carrots',
                in: 'Rainbow Carrots',
                reason: 'More antioxidants'
            });
        }
        
        return swaps.slice(0, 3); // Return max 3 swaps
    }

    async generateRecipe(mealName) {
        // Implementation for recipe generation
        console.log('Generating recipe for:', mealName);
        alert('Recipe generation coming soon!');
    }

    updateDeliveryDate(dateStr) {
        const deliveryDateDiv = document.getElementById('deliveryDate');
        const deliveryDateText = document.getElementById('deliveryDateText');
        
        if (deliveryDateDiv && deliveryDateText) {
            const date = new Date(dateStr);
            const options = { weekday: 'short', month: 'short', day: 'numeric' };
            deliveryDateText.textContent = date.toLocaleDateString('en-US', options);
            deliveryDateDiv.style.display = 'block';
        }
    }

    updateRefreshCount() {
        const today = new Date().toDateString();
        
        if (this.lastRefreshDate !== today) {
            this.refreshCount = 1;
            this.lastRefreshDate = today;
        } else {
            this.refreshCount++;
        }
        
        localStorage.setItem('refreshCount', this.refreshCount.toString());
        localStorage.setItem('lastRefreshDate', this.lastRefreshDate);
        
        const refreshInfo = document.getElementById('refreshInfo');
        if (refreshInfo) {
            refreshInfo.textContent = `Refreshes today: ${this.refreshCount}/3`;
            refreshInfo.style.display = 'block';
            
            if (this.refreshCount >= 3) {
                document.getElementById('analyzeBtn').disabled = true;
                document.getElementById('analyzeBtn').textContent = 'Daily limit reached';
            }
        }
    }

    showError(message) {
        const loadingState = document.getElementById('loadingState');
        const errorState = document.getElementById('errorState');
        const errorMessage = document.getElementById('errorMessage');
        const analyzeBtn = document.getElementById('analyzeBtn');
        
        loadingState.style.display = 'none';
        errorState.style.display = 'block';
        errorMessage.textContent = message;
        
        analyzeBtn.innerHTML = 'Retry Analysis';
        analyzeBtn.disabled = false;
    }

    loadSavedCart() {
        const savedCart = localStorage.getItem('cartAnalysisData');
        if (savedCart) {
            try {
                const data = JSON.parse(savedCart);
                this.cartData = data.cart_data;
                window.mealPlanData = { cart_data: this.cartData };
                
                this.showCartAnalysis(this.cartData);
                this.generateMealSuggestions(this.cartData);
                
                if (data.delivery_date) {
                    this.updateDeliveryDate(data.delivery_date);
                }
                
                document.getElementById('loadingState').style.display = 'none';
                document.getElementById('cartAnalysis').style.display = 'block';
                document.getElementById('analyzeBtn').innerHTML = 'Refresh Analysis';
                document.getElementById('headerSubtitle').textContent = 'Your cart has been analyzed';
                
                if (window.navigationManager) {
                    window.navigationManager.enableMealsTab();
                }
            } catch (error) {
                console.error('Error loading saved cart:', error);
            }
        }
    }
}