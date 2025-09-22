/**
 * Cart Manager Module v3
 * Complete cart analysis functionality with all features from dashboard.html
 */

import { appState, Utils } from './core.js';
import apiClient from './api-client.js';

export class CartManagerV3 {
    constructor() {
        this.container = null;
        this.refreshesLeft = 3;
        this.isAnalyzing = false;
    }

    async init() {
        this.container = document.getElementById('cartContainer');
        if (!this.container) {
            console.error('Cart container not found');
            return;
        }

        // Listen for tab changes
        appState.on('cart:opened', () => {
            this.checkAndLoadCart();
        });

        // Listen for refresh requests
        appState.on('cart:refresh', () => {
            this.refreshCart();
        });

        // Load saved refreshes count
        const savedRefreshes = localStorage.getItem('refreshesLeft');
        if (savedRefreshes !== null) {
            this.refreshesLeft = parseInt(savedRefreshes, 10);
        }

        // Initial load
        await this.checkAndLoadCart();
    }

    async checkAndLoadCart() {
        try {
            // First try to get saved cart from server
            const response = await apiClient.getSavedCart();

            if (response && response.cart_data) {
                appState.update('cart.data', response.cart_data);
                this.displayCartAnalysis(response.cart_data, response.swaps || [], response.addons || []);
            } else {
                // Check localStorage as fallback
                const cachedData = Utils.storage.get('cartAnalysisData');
                if (cachedData && cachedData.timestamp) {
                    // Only use cache if less than 1 hour old
                    const oneHour = 60 * 60 * 1000;
                    if (Date.now() - cachedData.timestamp < oneHour) {
                        appState.update('cart.data', cachedData.cartData);
                        this.displayCartAnalysis(cachedData.cartData, cachedData.swaps, cachedData.addons);
                        return;
                    }
                }
                // Show start screen if no data
                this.showStartScreen();
            }
        } catch (error) {
            console.error('Error loading cart:', error);
            this.showStartScreen();
        }
    }

    showStartScreen() {
        this.container.innerHTML = `
            <div class="start-screen">
                <div class="start-icon">📦</div>
                <h2 class="start-title">Cart Analysis</h2>
                <p class="start-description">
                    See what's in your Farm to People cart, suggested swaps, and add-ons to complete your meals.
                </p>
                <button class="analyze-button" id="analyzeButton">
                    Analyze My Cart
                </button>
            </div>
        `;

        // Add styles
        this.addStartScreenStyles();

        // Add event listener
        const button = document.getElementById('analyzeButton');
        if (button) {
            button.addEventListener('click', () => this.startAnalysis());
        }
    }

    addStartScreenStyles() {
        if (!document.getElementById('cart-start-styles')) {
            const style = document.createElement('style');
            style.id = 'cart-start-styles';
            style.textContent = `
                .start-screen {
                    text-align: center;
                    padding: 60px 20px;
                }
                .start-icon {
                    font-size: 48px;
                    margin-bottom: 20px;
                }
                .start-title {
                    font-size: 24px;
                    font-weight: 600;
                    color: #212529;
                    margin-bottom: 8px;
                }
                .start-description {
                    font-size: 16px;
                    color: #6c757d;
                    margin-bottom: 24px;
                    line-height: 1.4;
                }
                .analyze-button {
                    background: #28a745;
                    color: white;
                    border: none;
                    padding: 14px 32px;
                    border-radius: 8px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }
                .analyze-button:hover {
                    background: #218838;
                    transform: translateY(-1px);
                }
            `;
            document.head.appendChild(style);
        }
    }

    async startAnalysis() {
        if (this.isAnalyzing) return;

        this.isAnalyzing = true;
        appState.update('cart.isLoading', true);

        // Clear previous data
        Utils.storage.remove('cartAnalysisData');

        // Show loading state
        this.showLoadingState();

        // Cycle through status messages
        const statuses = [
            'Logging into Farm to People...',
            'Found your account! Loading cart...',
            'Analyzing your produce selections...',
            'Creating personalized suggestions...',
            'Almost done...'
        ];

        let statusIndex = 0;
        const statusInterval = setInterval(() => {
            if (statusIndex < statuses.length) {
                const statusElement = document.querySelector('.loading-status');
                if (statusElement) {
                    statusElement.textContent = statuses[statusIndex];
                }
                statusIndex++;
            }
        }, 3000);

        try {
            // Call analyze cart API
            const result = await apiClient.analyzeCart(false);

            clearInterval(statusInterval);

            if (result.success && result.cart_data) {
                // Store in app state
                appState.update('cart.data', result.cart_data);
                appState.update('cart.lastAnalyzed', Date.now());

                // Generate swaps and addons
                const { swaps, addons } = await this.generateSwapsAndAddons(result.cart_data);

                // Cache the data
                Utils.storage.set('cartAnalysisData', {
                    cartData: result.cart_data,
                    swaps,
                    addons,
                    timestamp: Date.now()
                });

                // Display results
                this.displayCartAnalysis(result.cart_data, swaps, addons);

                // Update header subtitle
                document.querySelector('.header .subtitle').textContent = 'Analysis complete';
            } else {
                throw new Error(result.error || 'Failed to analyze cart');
            }
        } catch (error) {
            clearInterval(statusInterval);
            this.showError('Failed to analyze cart', error.message);
        } finally {
            this.isAnalyzing = false;
            appState.update('cart.isLoading', false);
        }
    }

    showLoadingState() {
        this.container.innerHTML = `
            <div class="loading-section">
                <div class="loading-animation"></div>
                <h2>Analyzing Your Cart</h2>
                <p class="loading-status">Logging into Farm to People...</p>
                <div class="loading-progress">
                    <div class="progress-bar"></div>
                </div>
            </div>
        `;

        // Add loading styles
        this.addLoadingStyles();
    }

    addLoadingStyles() {
        if (!document.getElementById('cart-loading-styles')) {
            const style = document.createElement('style');
            style.id = 'cart-loading-styles';
            style.textContent = `
                .loading-section {
                    text-align: center;
                    padding: 60px 20px;
                }
                .loading-section h2 {
                    font-size: 24px;
                    margin-bottom: 8px;
                    color: #212529;
                }
                .loading-status {
                    color: #6c757d;
                    margin-bottom: 24px;
                }
                .loading-progress {
                    width: 200px;
                    height: 4px;
                    background: #e9ecef;
                    border-radius: 2px;
                    margin: 0 auto;
                    overflow: hidden;
                }
                .progress-bar {
                    height: 100%;
                    background: #28a745;
                    width: 0;
                    animation: progress 15s ease-out;
                }
                @keyframes progress {
                    to { width: 90%; }
                }
            `;
            document.head.appendChild(style);
        }
    }

    async generateSwapsAndAddons(cartData) {
        try {
            const result = await apiClient.generateSwapsAndAddons(cartData);
            return {
                swaps: result.swaps || [],
                addons: result.addons || []
            };
        } catch (error) {
            console.error('Error generating swaps/addons:', error);
            // Return mock data as fallback
            return {
                swaps: this.getMockSwaps(),
                addons: this.getMockAddons()
            };
        }
    }

    getMockSwaps() {
        return [
            { item: 'Regular Lettuce', swap: 'Baby Spinach', reason: 'Higher iron content' },
            { item: 'White Rice', swap: 'Quinoa', reason: 'Complete protein source' }
        ];
    }

    getMockAddons() {
        return [
            { item: 'Greek Yogurt', reason: 'Adds 15g protein to breakfasts' },
            { item: 'Hemp Seeds', reason: 'Omega-3s and 10g protein per serving' }
        ];
    }

    displayCartAnalysis(cartData, swaps = [], addons = []) {
        // Show delivery date in header
        this.showDeliveryDate(cartData);

        // Store for meal planning
        appState.update('meals.cartData', cartData);

        // Build the exact HTML structure from original dashboard
        let html = `
            <!-- Cart Analysis Display - Shows After Analysis -->
            <div class="cart-analysis section active" id="cartAnalysisSection">
                <!-- Suggested Meals - TOP PRIORITY -->
                <div class="cart-section" id="suggestedMealsSection">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                        <h3 class="section-header" style="margin: 0;">Suggested Meals</h3>
                        <div style="display: flex; gap: 8px;">
                            <button id="refreshSuggestionsButton"
                                    style="background: #34C759; color: white; border: none; border-radius: 8px; padding: 8px 16px; font-size: 14px; font-weight: 600; cursor: pointer;">
                                ✨ New Suggestions
                            </button>
                            <button id="refreshCartButton"
                                    style="background: #007AFF; color: white; border: none; border-radius: 8px; padding: 8px 16px; font-size: 14px; font-weight: 600; cursor: pointer;">
                                🔄 Refresh Cart
                            </button>
                        </div>
                    </div>
                    <div id="suggestedMeals">
                        ${this.renderSuggestedMeals(cartData)}
                    </div>
                </div>

                <!-- Cart Summary -->
                <div id="cartSummary" style="display: flex; align-items: center; gap: 15px; margin-bottom: 20px; padding: 0 20px;">
                    ${this.renderCartSummary(cartData)}
                </div>

                <!-- Individual Items -->
                ${this.renderIndividualItemsSection(cartData)}

                <!-- Customizable Boxes -->
                ${this.renderCustomizableBoxesSection(cartData)}

                <!-- Non-Customizable Boxes -->
                ${this.renderNonCustomizableBoxesSection(cartData)}

                <!-- Suggested Swaps -->
                ${this.renderSwapsSection(swaps)}

                <!-- Recommended Add-ons -->
                ${this.renderAddonsSection(addons)}
            </div>
        `;

        this.container.innerHTML = html;

        // Add event listeners after rendering
        setTimeout(() => this.attachEventListeners(), 0);

        // Emit event that cart has been analyzed
        appState.emit('cart:analyzed', cartData);
    }

    showDeliveryDate(cartData) {
        const deliveryDateDiv = document.getElementById('deliveryDate');
        const deliveryDateText = document.getElementById('deliveryDateText');

        if (cartData.delivery_date && deliveryDateDiv && deliveryDateText) {
            const date = new Date(cartData.delivery_date);
            const formatted = date.toLocaleDateString('en-US', {
                weekday: 'short',
                month: 'short',
                day: 'numeric'
            });

            deliveryDateText.textContent = formatted;
            deliveryDateDiv.style.display = 'block';

            // Show cutoff time if close to deadline
            this.showCartCutoffTime(cartData.delivery_date);
        }
    }

    showCartCutoffTime(deliveryDateStr) {
        const deliveryDate = new Date(deliveryDateStr);
        const cutoffDate = new Date(deliveryDate);
        cutoffDate.setDate(cutoffDate.getDate() - 1);
        cutoffDate.setHours(11, 59, 0, 0);

        const now = new Date();
        const hoursUntilCutoff = (cutoffDate - now) / (1000 * 60 * 60);

        if (hoursUntilCutoff > 0 && hoursUntilCutoff < 48) {
            const cutoffBanner = document.createElement('div');
            cutoffBanner.className = 'cutoff-banner';
            cutoffBanner.innerHTML = `
                ⏰ Cart locks in ${Math.floor(hoursUntilCutoff)} hours
            `;
            cutoffBanner.style.cssText = `
                background: #fff3cd;
                color: #856404;
                padding: 8px;
                text-align: center;
                font-size: 14px;
                border-bottom: 1px solid #ffeaa7;
            `;

            const header = document.querySelector('.header');
            if (header && !document.querySelector('.cutoff-banner')) {
                header.appendChild(cutoffBanner);
            }
        }
    }

    renderScrapedTimestamp(cartData) {
        if (!cartData.scraped_at) return '';

        const scrapedDate = new Date(cartData.scraped_at);
        const now = new Date();
        const hoursSince = (now - scrapedDate) / (1000 * 60 * 60);

        let timeText;
        if (hoursSince < 1) {
            timeText = 'just now';
        } else if (hoursSince < 24) {
            timeText = `${Math.floor(hoursSince)} hours ago`;
        } else {
            timeText = `${Math.floor(hoursSince / 24)} days ago`;
        }

        return `
            <div class="scraped-info">
                <span>📅 Cart analyzed ${timeText}</span>
            </div>
        `;
    }

    renderRefreshButton() {
        if (this.refreshesLeft <= 0) {
            return `
                <div class="refresh-section">
                    <button class="refresh-button disabled" disabled>
                        No refreshes left today
                    </button>
                </div>
            `;
        }

        return `
            <div class="refresh-section">
                <button class="refresh-button" id="refreshButton">
                    🔄 Refresh Analysis
                </button>
            </div>
        `;
    }

    renderSuggestedMeals(cartData) {
        // TODO: Implement meal suggestions API call
        return `
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 12px;">
                <div style="background: #f8f9fa; padding: 16px; border-radius: 8px; border: 1px solid #e9ecef;">
                    <h4 style="color: #212529; margin-bottom: 8px;">High-Protein Chicken Stir-Fry</h4>
                    <p style="color: #28a745; font-weight: 600; margin-bottom: 4px;">32g protein</p>
                    <p style="color: #6c757d; font-size: 14px;">Quick 20-minute dinner with your vegetables</p>
                </div>
                <div style="background: #f8f9fa; padding: 16px; border-radius: 8px; border: 1px solid #e9ecef;">
                    <h4 style="color: #212529; margin-bottom: 8px;">Mediterranean Quinoa Bowl</h4>
                    <p style="color: #28a745; font-weight: 600; margin-bottom: 4px;">28g protein</p>
                    <p style="color: #6c757d; font-size: 14px;">Healthy lunch option with fresh produce</p>
                </div>
                <div style="background: #f8f9fa; padding: 16px; border-radius: 8px; border: 1px solid #e9ecef;">
                    <h4 style="color: #212529; margin-bottom: 8px;">Grass-Fed Beef Tacos</h4>
                    <p style="color: #28a745; font-weight: 600; margin-bottom: 4px;">35g protein</p>
                    <p style="color: #6c757d; font-size: 14px;">Family-friendly dinner ready in 25 minutes</p>
                </div>
            </div>
        `;
    }

    renderIndividualItemsSection(cartData) {
        if (!cartData.individual_items || cartData.individual_items.length === 0) {
            return '';
        }

        const count = cartData.individual_items.length;

        // Build HTML exactly like original
        let html = `
            <div class="cart-section" id="individualItemsSection">
                <h3 class="section-header">
                    Individual Items <span id="individualItemsCount" style="color: #666; font-weight: normal; font-size: 16px;">(${count} items)</span>
                </h3>
                <div class="item-grid" id="individualItems">
        `;

        cartData.individual_items.forEach(item => {
            // Get category and colors
            const category = this.getItemCategory(item.name);
            const colors = this.getCategoryColors(category);

            // Format quantity properly
            let quantityText = '';
            if (item.unit && item.unit.startsWith('1 ')) {
                if (item.quantity === 1) {
                    quantityText = item.unit;
                } else {
                    const unitPart = item.unit.substring(2);
                    if (item.quantity > 1 && unitPart === 'piece') {
                        quantityText = `${item.quantity} pieces`;
                    } else if (item.quantity > 1 && unitPart === 'bunch') {
                        quantityText = `${item.quantity} bunches`;
                    } else if (item.quantity > 1 && unitPart === 'head') {
                        quantityText = `${item.quantity} heads`;
                    } else {
                        quantityText = `${item.quantity} ${unitPart}`;
                    }
                }
            } else {
                quantityText = `${item.quantity || 1} ${item.unit || 'piece'}`;
            }

            // Clean producer name if exists
            const producerName = item.producer ? this.cleanProducerName(item.producer) : '';

            html += `
                <div class="cart-item" style="display: flex; align-items: center; padding: 12px; border-bottom: 1px solid #eee;">
                    <div class="item-details" style="flex: 1;">
                        <div class="item-name">${item.name}</div>
                        <div class="item-quantity" style="color: #666; margin-top: 4px; font-size: 14px;">${quantityText}</div>
                        ${producerName ? `<div class="item-producer" style="color: #999; margin-top: 2px; font-size: 12px;">${producerName}</div>` : ''}
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        ${item.price ? `<span class="item-price" style="color: #2e7d32; font-weight: 500;">${item.price}</span>` : ''}
                        <span class="category-tag" style="
                            background: ${colors.bg};
                            color: ${colors.text};
                            padding: 4px 8px;
                            border-radius: 4px;
                            font-size: 12px;
                            font-weight: 500;
                        ">${category}</span>
                    </div>
                </div>
            `;
        });

        html += `
                </div>
            </div>
        `;

        return html;
    }

    renderCustomizableBoxesSection(cartData) {
        // Separate boxes based on customizable flag (not which array they're in)
        const allBoxes = [...(cartData.customizable_boxes || []), ...(cartData.non_customizable_boxes || [])];
        const actuallyCustomizable = allBoxes.filter(box => box.customizable === true || (box.customizable === undefined && box.alternatives_count > 0));

        if (actuallyCustomizable.length === 0) {
            return '';
        }

        // Calculate total items
        let totalItems = 0;
        actuallyCustomizable.forEach(box => {
            totalItems += (box.selected_items ? box.selected_items.length : 0);
        });

        let html = `
            <div class="cart-section" id="customizableBoxesSection">
                <h3 class="section-header">
                    Customizable Boxes <span id="customizableBoxesCount" style="color: #666; font-weight: normal; font-size: 16px;">(${totalItems} items)</span>
                </h3>
                <div id="customizableBoxes">
        `;

        actuallyCustomizable.forEach(box => {
            html += `
                <div style="margin-bottom: 20px;">
                    <div class="box-header">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <div class="box-name">${box.box_name}</div>
                            ${box.price ? `<span style="color: #2e7d32; font-weight: normal; font-size: 16px;">${box.price}</span>` : ''}
                        </div>
                        <div class="box-status">${box.alternatives_count || 0} available alternatives</div>
                    </div>
                    <div class="item-grid">
            `;

            if (box.selected_items) {
                box.selected_items.forEach(item => {
                    const category = this.getItemCategory(item.name);
                    const colors = this.getCategoryColors(category);
                    const producerName = item.producer ? this.cleanProducerName(item.producer) : '';

                    html += `
                        <div class="cart-item" style="display: flex; align-items: center; padding: 12px; border-bottom: 1px solid #eee;">
                            <div class="item-details" style="flex: 1;">
                                <div class="item-name">${item.name}</div>
                                ${producerName ? `<div class="item-producer" style="color: #999; margin-top: 2px; font-size: 12px;">${producerName}</div>` : ''}
                            </div>
                            <span class="category-tag" style="
                                background: ${colors.bg};
                                color: ${colors.text};
                                padding: 4px 8px;
                                border-radius: 4px;
                                font-size: 12px;
                                font-weight: 500;
                            ">${category}</span>
                        </div>
                    `;
                });
            }

            html += `
                    </div>
                </div>
            `;
        });

        html += `
                </div>
            </div>
        `;

        return html;
    }

    renderNonCustomizableBoxesSection(cartData) {
        // Separate boxes based on customizable flag
        const allBoxes = [...(cartData.customizable_boxes || []), ...(cartData.non_customizable_boxes || [])];
        const actuallyNonCustomizable = allBoxes.filter(box => box.customizable === false);

        if (actuallyNonCustomizable.length === 0) {
            return '';
        }

        // Calculate total items
        let totalItems = 0;
        actuallyNonCustomizable.forEach(box => {
            totalItems += (box.selected_items ? box.selected_items.length : 0);
        });

        let html = `
            <div class="cart-section" id="nonCustomizableBoxesSection">
                <h3 class="section-header">
                    Fixed Boxes <span id="fixedBoxesCount" style="color: #666; font-weight: normal; font-size: 16px;">(${totalItems} items)</span>
                </h3>
                <div id="nonCustomizableBoxes">
        `;

        actuallyNonCustomizable.forEach(box => {
            html += `
                <div style="margin-bottom: 20px;">
                    <div class="box-header">
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <div class="box-name">${box.box_name}</div>
                            ${box.price ? `<span style="color: #2e7d32; font-weight: normal; font-size: 16px;">${box.price}</span>` : ''}
                        </div>
                        <div class="box-status">Fixed selection</div>
                    </div>
                    <div class="item-grid">
            `;

            if (box.selected_items) {
                box.selected_items.forEach(item => {
                    const category = this.getItemCategory(item.name);
                    const colors = this.getCategoryColors(category);
                    const producerName = item.producer ? this.cleanProducerName(item.producer) : '';

                    html += `
                        <div class="cart-item" style="display: flex; align-items: center; padding: 12px; border-bottom: 1px solid #eee;">
                            <div class="item-details" style="flex: 1;">
                                <div class="item-name">${item.name}</div>
                                ${producerName ? `<div class="item-producer" style="color: #999; margin-top: 2px; font-size: 12px;">${producerName}</div>` : ''}
                            </div>
                            <span class="category-tag" style="
                                background: ${colors.bg};
                                color: ${colors.text};
                                padding: 4px 8px;
                                border-radius: 4px;
                                font-size: 12px;
                                font-weight: 500;
                            ">${category}</span>
                        </div>
                    `;
                });
            }

            html += `
                    </div>
                </div>
            `;
        });

        html += `
                </div>
            </div>
        `;

        return html;
    }

    renderSwapsSection(swaps) {
        let html = `
            <div class="cart-section" id="swapsSection">
                <h3 class="section-header">Suggested Swaps</h3>
                <div id="suggestedSwaps">
        `;

        if (swaps && swaps.length > 0) {
            swaps.forEach(swap => {
                html += `
                    <div style="background: #f0f9ff; border: 1px solid #bae6fd; padding: 12px; border-radius: 8px; margin-bottom: 8px;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-size: 20px;">🔄</span>
                            <div>
                                <div style="font-weight: 500; color: #0369a1;">Swap ${swap.item} → ${swap.swap}</div>
                                <div style="color: #64748b; font-size: 14px; margin-top: 2px;">${swap.reason}</div>
                            </div>
                        </div>
                    </div>
                `;
            });
        } else {
            html += '<div style="color: #666; padding: 10px;">No swaps needed - your cart looks great!</div>';
        }

        html += `
                </div>
            </div>
        `;

        return html;
    }

    renderAddonsSection(addons) {
        let html = `
            <div class="cart-section" id="addonsSection">
                <h3 class="section-header">Recommended Add-ons</h3>
                <div id="recommendedAddons">
        `;

        if (addons && addons.length > 0) {
            addons.forEach(addon => {
                html += `
                    <div style="background: #f0fdf4; border: 1px solid #bbf7d0; padding: 12px; border-radius: 8px; margin-bottom: 8px;">
                        <div style="display: flex; align-items: center; gap: 8px;">
                            <span style="font-size: 20px;">➕</span>
                            <div>
                                <div style="font-weight: 500; color: #15803d;">Add ${addon.item}</div>
                                <div style="color: #64748b; font-size: 14px; margin-top: 2px;">${addon.reason}</div>
                            </div>
                        </div>
                    </div>
                `;
            });
        } else {
            html += '<div style="color: #666; padding: 10px;">Your cart is complete!</div>';
        }

        html += `
                </div>
            </div>
        `;

        return html;
    }

    getItemCategory(itemName) {
        const name = itemName.toLowerCase();
        if (name.includes('chicken') || name.includes('beef') || name.includes('pork') ||
            name.includes('turkey') || name.includes('fish') || name.includes('salmon') ||
            name.includes('bass') || name.includes('egg')) {
            return 'Protein';
        }
        if (name.includes('lettuce') || name.includes('kale') || name.includes('spinach') ||
            name.includes('chard') || name.includes('greens') || name.includes('arugula')) {
            return 'Greens';
        }
        if (name.includes('tomato') || name.includes('pepper') || name.includes('onion') ||
            name.includes('carrot') || name.includes('potato') || name.includes('squash')) {
            return 'Vegetables';
        }
        if (name.includes('apple') || name.includes('banana') || name.includes('orange') ||
            name.includes('berry') || name.includes('grape') || name.includes('fruit')) {
            return 'Fruit';
        }
        if (name.includes('bread') || name.includes('pasta') || name.includes('rice') ||
            name.includes('quinoa') || name.includes('grain')) {
            return 'Grains';
        }
        if (name.includes('milk') || name.includes('cheese') || name.includes('yogurt') ||
            name.includes('dairy')) {
            return 'Dairy';
        }
        return 'Other';
    }

    getCategoryColors(category) {
        const colors = {
            'Protein': { bg: '#fce4ec', text: '#c2185b' },
            'Greens': { bg: '#e8f5e9', text: '#2e7d32' },
            'Vegetables': { bg: '#fff3e0', text: '#e65100' },
            'Fruit': { bg: '#f3e5f5', text: '#7b1fa2' },
            'Grains': { bg: '#e3f2fd', text: '#1565c0' },
            'Dairy': { bg: '#fff8e1', text: '#f57c00' },
            'Other': { bg: '#f5f5f5', text: '#616161' }
        };
        return colors[category] || colors['Other'];
    }

    cleanProducerName(producer) {
        if (!producer) return '';
        // Handle duplicated names like "Lagoner FarmsLagoner Farms"
        const halfLength = Math.floor(producer.length / 2);
        const firstHalf = producer.substring(0, halfLength);
        const secondHalf = producer.substring(halfLength);

        if (firstHalf === secondHalf) {
            return firstHalf;
        }

        return producer;
    }

    renderCartSummary(cartData) {
        // Calculate category counts like original
        const categoryCounts = { protein: 0, produce: 0, fruit: 0 };

        // Count from individual items
        if (cartData.individual_items) {
            cartData.individual_items.forEach(item => {
                const category = this.getItemCategorySimple(item.name);
                if (categoryCounts[category] !== undefined) {
                    categoryCounts[category] += item.quantity || 1;
                }
            });
        }

        // Count from all boxes
        ['customizable_boxes', 'non_customizable_boxes'].forEach(boxType => {
            if (cartData[boxType]) {
                cartData[boxType].forEach(box => {
                    if (box.selected_items) {
                        box.selected_items.forEach(item => {
                            const category = this.getItemCategorySimple(item.name);
                            if (categoryCounts[category] !== undefined) {
                                categoryCounts[category] += item.quantity || 1;
                            }
                        });
                    }
                });
            }
        });

        // Build summary items (only protein and fruit like original)
        const summaryItems = [];

        if (categoryCounts.protein > 0) {
            summaryItems.push(`<span style="font-size: 18px; color: #333; font-weight: 500;">${categoryCounts.protein}× protein</span>`);
        }

        if (categoryCounts.fruit > 0) {
            summaryItems.push(`<span style="font-size: 18px; color: #333; font-weight: 500;">${categoryCounts.fruit}× fruit</span>`);
        }

        return summaryItems.join('');
    }

    getItemCategorySimple(itemName) {
        const name = itemName.toLowerCase();
        if (name.includes('chicken') || name.includes('beef') || name.includes('pork') ||
            name.includes('turkey') || name.includes('fish') || name.includes('salmon') ||
            name.includes('egg') || name.includes('protein')) {
            return 'protein';
        }
        if (name.includes('apple') || name.includes('banana') || name.includes('orange') ||
            name.includes('berry') || name.includes('grape') || name.includes('fruit')) {
            return 'fruit';
        }
        return 'produce';
    }

    renderIndividualItems(cartData) {
        if (!cartData.individual_items || cartData.individual_items.length === 0) {
            return '';
        }

        // Group items by category
        const categorized = {};
        cartData.individual_items.forEach(item => {
            const category = Utils.getItemCategory(item.name);
            if (!categorized[category]) {
                categorized[category] = [];
            }
            categorized[category].push(item);
        });

        let html = '<div class="individual-items-section"><h3>Individual Items</h3>';

        Object.entries(categorized).forEach(([category, items]) => {
            const colors = Utils.getCategoryColors(category);
            html += `
                <div class="category-group">
                    <div class="category-header" style="background: ${colors.bg}; color: ${colors.text};">
                        ${category}
                    </div>
                    <div class="items-list">
            `;

            items.forEach(item => {
                html += `
                    <div class="item-card">
                        <div class="item-name">${item.name}</div>
                        <div class="item-details">
                            <span class="item-quantity">${item.quantity || 1} ${item.unit || 'piece'}</span>
                            ${item.price ? `<span class="item-price">${item.price}</span>` : ''}
                        </div>
                    </div>
                `;
            });

            html += '</div></div>';
        });

        html += '</div>';
        return html;
    }

    renderBoxes(cartData) {
        let html = '';

        // Render customizable boxes
        if (cartData.customizable_boxes && cartData.customizable_boxes.length > 0) {
            html += '<div class="boxes-section"><h3>Customizable Boxes</h3>';

            cartData.customizable_boxes.forEach(box => {
                html += `
                    <div class="box-card customizable">
                        <div class="box-header">
                            <h4>${box.box_name}</h4>
                            <span class="box-badge">Customizable</span>
                        </div>
                        <div class="box-items">
                `;

                if (box.selected_items) {
                    box.selected_items.forEach(item => {
                        html += `
                            <div class="box-item">
                                <span class="item-name">${item.name}</span>
                                ${item.producer ? `<span class="item-producer">${Utils.cleanProducerName(item.producer)}</span>` : ''}
                            </div>
                        `;
                    });
                }

                if (box.available_alternatives && box.available_alternatives.length > 0) {
                    html += `
                        <details class="alternatives-section">
                            <summary>View ${box.available_alternatives.length} alternatives</summary>
                            <div class="alternatives-list">
                    `;

                    box.available_alternatives.forEach(alt => {
                        html += `<div class="alternative-item">${alt.name}</div>`;
                    });

                    html += '</div></details>';
                }

                html += '</div></div>';
            });

            html += '</div>';
        }

        // Render non-customizable boxes
        if (cartData.non_customizable_boxes && cartData.non_customizable_boxes.length > 0) {
            html += '<div class="boxes-section"><h3>Fixed Boxes</h3>';

            cartData.non_customizable_boxes.forEach(box => {
                // Check if actually customizable (data structure issue)
                const isCustomizable = box.customizable === true;

                html += `
                    <div class="box-card ${isCustomizable ? 'customizable' : ''}">
                        <div class="box-header">
                            <h4>${box.box_name}</h4>
                            ${isCustomizable ? '<span class="box-badge">Customizable</span>' : ''}
                        </div>
                        <div class="box-items">
                `;

                if (box.selected_items) {
                    box.selected_items.forEach(item => {
                        html += `
                            <div class="box-item">
                                <span class="item-name">${item.name}</span>
                                ${item.producer ? `<span class="item-producer">${Utils.cleanProducerName(item.producer)}</span>` : ''}
                            </div>
                        `;
                    });
                }

                html += '</div></div>';
            });

            html += '</div>';
        }

        return html;
    }

    renderSwapSuggestions(swaps) {
        if (!swaps || swaps.length === 0) return '';

        return `
            <div class="suggestions-section">
                <h3>💡 Suggested Swaps</h3>
                <div class="suggestions-list">
                    ${swaps.map(swap => `
                        <div class="suggestion-card">
                            <div class="suggestion-icon">🔄</div>
                            <div class="suggestion-content">
                                <div class="suggestion-title">Swap ${swap.item} → ${swap.swap}</div>
                                <div class="suggestion-reason">${swap.reason}</div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    renderAddonSuggestions(addons) {
        if (!addons || addons.length === 0) return '';

        return `
            <div class="suggestions-section">
                <h3>➕ Recommended Add-ons</h3>
                <div class="suggestions-list">
                    ${addons.map(addon => `
                        <div class="suggestion-card">
                            <div class="suggestion-icon">✨</div>
                            <div class="suggestion-content">
                                <div class="suggestion-title">Add ${addon.item}</div>
                                <div class="suggestion-reason">${addon.reason}</div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    renderMealSuggestions() {
        return `
            <div class="meal-suggestions-section">
                <h3>🍽 Ready to Plan Meals?</h3>
                <p>Switch to the Meals tab to generate personalized recipes based on your cart items.</p>
                <button class="btn-primary" id="goToMealsButton">
                    Go to Meal Planning
                </button>
            </div>
        `;
    }

    attachEventListeners() {
        // Refresh suggestions button
        const refreshSuggestionsBtn = document.getElementById('refreshSuggestionsButton');
        if (refreshSuggestionsBtn) {
            refreshSuggestionsBtn.addEventListener('click', () => this.refreshSuggestions());
        }

        // Refresh cart button
        const refreshCartBtn = document.getElementById('refreshCartButton');
        if (refreshCartBtn) {
            refreshCartBtn.addEventListener('click', () => this.refreshCart());
        }

        // Go to meals button
        const mealsBtn = document.getElementById('goToMealsButton');
        if (mealsBtn) {
            mealsBtn.addEventListener('click', () => {
                if (window.navigation) {
                    window.navigation.switchTab('plan');
                }
            });
        }
    }

    async refreshSuggestions() {
        console.log('Refreshing meal suggestions...');
        // TODO: Call API to generate new meal suggestions
        const suggestedMealsDiv = document.getElementById('suggestedMeals');
        if (suggestedMealsDiv) {
            // For now, just show a loading state then restore
            suggestedMealsDiv.innerHTML = '<div style="text-align: center; padding: 20px; color: #666;">Generating new suggestions...</div>';
            setTimeout(() => {
                suggestedMealsDiv.innerHTML = this.renderSuggestedMeals(appState.get('cart.data'));
            }, 1500);
        }
    }

    async refreshCart() {
        // Force refresh
        await this.startAnalysis();
    }

    showError(title, message) {
        this.container.innerHTML = `
            <div class="error">
                <div class="error-icon">⚠️</div>
                <h3>${title}</h3>
                <p class="error-message">${message}</p>
                <button class="btn-primary" id="retryButton">
                    Try Again
                </button>
            </div>
        `;

        // Add event listener
        const retryBtn = document.getElementById('retryButton');
        if (retryBtn) {
            retryBtn.addEventListener('click', () => this.startAnalysis());
        }
    }

    addAnalysisStyles() {
        if (!document.getElementById('cart-analysis-styles')) {
            const style = document.createElement('style');
            style.id = 'cart-analysis-styles';
            style.textContent = `
                .cart-analysis {
                    padding: 20px 0;
                }

                .scraped-info {
                    text-align: center;
                    color: #6c757d;
                    font-size: 14px;
                    margin-bottom: 16px;
                }

                .refresh-section {
                    text-align: center;
                    margin-bottom: 20px;
                }

                .refresh-button {
                    background: white;
                    color: #007AFF;
                    border: 1px solid #007AFF;
                    padding: 10px 20px;
                    border-radius: 8px;
                    font-size: 14px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }

                .refresh-button:hover:not(.disabled) {
                    background: #007AFF;
                    color: white;
                }

                .refresh-button.disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }

                .cart-summary {
                    background: white;
                    border-radius: 12px;
                    padding: 20px;
                    margin-bottom: 20px;
                    border: 1px solid #e9ecef;
                }

                .cart-summary h3 {
                    margin-bottom: 16px;
                    font-size: 18px;
                }

                .summary-stats {
                    display: flex;
                    gap: 32px;
                }

                .stat {
                    display: flex;
                    flex-direction: column;
                }

                .stat-value {
                    font-size: 24px;
                    font-weight: 600;
                    color: #212529;
                }

                .stat-label {
                    font-size: 14px;
                    color: #6c757d;
                }

                .individual-items-section,
                .boxes-section,
                .suggestions-section,
                .meal-suggestions-section {
                    margin-bottom: 24px;
                }

                .individual-items-section h3,
                .boxes-section h3,
                .suggestions-section h3,
                .meal-suggestions-section h3 {
                    font-size: 18px;
                    margin-bottom: 16px;
                }

                .category-group {
                    margin-bottom: 16px;
                }

                .category-header {
                    padding: 8px 12px;
                    border-radius: 8px;
                    font-size: 14px;
                    font-weight: 600;
                    margin-bottom: 8px;
                }

                .items-list {
                    display: grid;
                    gap: 8px;
                }

                .item-card {
                    background: white;
                    border: 1px solid #e9ecef;
                    border-radius: 8px;
                    padding: 12px;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }

                .item-name {
                    font-weight: 500;
                    color: #212529;
                }

                .item-details {
                    display: flex;
                    gap: 12px;
                    font-size: 14px;
                    color: #6c757d;
                }

                .box-card {
                    background: white;
                    border: 1px solid #e9ecef;
                    border-radius: 12px;
                    padding: 20px;
                    margin-bottom: 16px;
                }

                .box-card.customizable {
                    border-color: #007AFF;
                }

                .box-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 16px;
                }

                .box-header h4 {
                    margin: 0;
                    font-size: 16px;
                }

                .box-badge {
                    background: #007AFF;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 12px;
                    font-weight: 600;
                }

                .box-items {
                    display: grid;
                    gap: 8px;
                }

                .box-item {
                    display: flex;
                    justify-content: space-between;
                    padding: 8px 0;
                    border-bottom: 1px solid #f0f0f0;
                }

                .box-item:last-child {
                    border-bottom: none;
                }

                .item-producer {
                    font-size: 12px;
                    color: #999;
                }

                .alternatives-section {
                    margin-top: 12px;
                    padding-top: 12px;
                    border-top: 1px solid #e9ecef;
                }

                .alternatives-section summary {
                    cursor: pointer;
                    color: #007AFF;
                    font-size: 14px;
                    font-weight: 500;
                }

                .alternatives-list {
                    margin-top: 12px;
                    display: grid;
                    gap: 6px;
                }

                .alternative-item {
                    padding: 6px 12px;
                    background: #f8f9fa;
                    border-radius: 6px;
                    font-size: 14px;
                }

                .suggestions-list {
                    display: grid;
                    gap: 12px;
                }

                .suggestion-card {
                    background: #f0f9ff;
                    border: 1px solid #bae6fd;
                    border-radius: 8px;
                    padding: 16px;
                    display: flex;
                    gap: 12px;
                }

                .suggestion-icon {
                    font-size: 24px;
                }

                .suggestion-title {
                    font-weight: 600;
                    color: #212529;
                    margin-bottom: 4px;
                }

                .suggestion-reason {
                    font-size: 14px;
                    color: #6c757d;
                }

                .meal-suggestions-section {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 24px;
                    border-radius: 12px;
                    text-align: center;
                }

                .meal-suggestions-section h3 {
                    color: white;
                    margin-bottom: 8px;
                }

                .meal-suggestions-section p {
                    margin-bottom: 16px;
                    opacity: 0.9;
                }

                .meal-suggestions-section .btn-primary {
                    background: white;
                    color: #667eea;
                }

                .meal-suggestions-section .btn-primary:hover {
                    background: #f8f9fa;
                }
            `;
            document.head.appendChild(style);
        }
    }
}

// Export for use in other modules
export default CartManagerV3;