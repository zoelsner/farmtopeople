/**
 * Meals Manager Module v3
 * Placeholder for meal planning functionality
 * TODO: Implement full meal calendar with drag & drop
 */

import { appState } from './core.js';
import apiClient from './api-client.js';

export class MealsManagerV3 {
    constructor() {
        this.container = null;
        this.currentWeek = null;
        this.mealPlan = null;
    }

    async init() {
        this.container = document.getElementById('mealsContainer');
        if (!this.container) {
            console.error('Meals container not found');
            return;
        }

        // Listen for meals tab events
        appState.on('meals:opened', () => {
            this.loadMealsView();
        });

        // Listen for cart data updates
        appState.on('cart.data:changed', (data) => {
            if (data.newValue) {
                this.enableMealGeneration();
            }
        });
    }

    loadMealsView() {
        // Check if we have cart data
        const cartData = appState.get('cart.data');

        if (!cartData) {
            this.showEmptyState();
        } else {
            this.showMealPlanning();
        }
    }

    showEmptyState() {
        this.container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🍽</div>
                <h2 class="empty-state-title">Plan Your Weekly Meals</h2>
                <p class="empty-state-text">
                    Analyze your cart first to generate personalized meal suggestions based on your ingredients.
                </p>
                <button class="btn-primary" id="goToCartButton">
                    Go to Cart Analysis
                </button>
            </div>
        `;

        // Add event listener for go to cart button
        const goToCartBtn = document.getElementById('goToCartButton');
        if (goToCartBtn) {
            goToCartBtn.addEventListener('click', () => {
                if (window.navigation) {
                    window.navigation.switchTab('box');
                }
            });
        }
    }

    showMealPlanning() {
        this.container.innerHTML = `
            <div class="meals-content">
                <div class="meals-header">
                    <h2>Weekly Meal Plan</h2>
                    <div class="week-navigation">
                        <button class="week-nav-btn" onclick="window.mealsManagerV3.previousWeek()">←</button>
                        <span class="week-display">This Week</span>
                        <button class="week-nav-btn" onclick="window.mealsManagerV3.nextWeek()">→</button>
                    </div>
                </div>

                <div class="ingredient-pool">
                    <h3>Available Ingredients</h3>
                    <p>Your cart items will be tracked here as you plan meals.</p>
                </div>

                <div class="meal-calendar">
                    ${this.generateCalendarHTML()}
                </div>

                <div class="meal-actions">
                    <button class="btn-primary" onclick="window.mealsManagerV3.generateMealPlan()">
                        Generate Meal Suggestions
                    </button>
                    <button class="btn-secondary" onclick="window.mealsManagerV3.clearPlan()">
                        Clear Plan
                    </button>
                </div>
            </div>
        `;

        // Make this available globally for onclick handlers
        window.mealsManagerV3 = this;
    }

    generateCalendarHTML() {
        const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'];
        let html = '';

        days.forEach(day => {
            html += `
                <div class="day-column">
                    <div class="day-header">
                        <div class="day-name">${day}</div>
                        <div class="day-date"></div>
                    </div>
                    <div class="meal-slot" data-day="${day.toLowerCase()}">
                        <div class="empty-slot-text">Drop meal here</div>
                        <button class="add-meal-btn">+ Add Meal</button>
                    </div>
                </div>
            `;
        });

        return html;
    }

    enableMealGeneration() {
        // Enable meal generation when cart data is available
        const button = document.querySelector('.meal-actions .btn-primary');
        if (button) {
            button.disabled = false;
            button.textContent = 'Generate Meal Suggestions';
        }
    }

    async generateMealPlan() {
        const cartData = appState.get('cart.data');
        if (!cartData) {
            alert('Please analyze your cart first');
            return;
        }

        // Show loading state
        const button = event.target;
        const originalText = button.textContent;
        button.textContent = 'Generating...';
        button.disabled = true;

        try {
            // Call API to generate meals
            const meals = await apiClient.generateWeeklyMeals(cartData);

            // Display generated meals
            this.displayMealPlan(meals);

            alert('Meal plan generated! (Full implementation coming soon)');
        } catch (error) {
            console.error('Error generating meal plan:', error);
            alert('Failed to generate meal plan. Please try again.');
        } finally {
            button.textContent = originalText;
            button.disabled = false;
        }
    }

    displayMealPlan(meals) {
        // TODO: Implement meal display with drag & drop
        console.log('Meal plan:', meals);
    }

    previousWeek() {
        // TODO: Implement week navigation
        console.log('Previous week');
    }

    nextWeek() {
        // TODO: Implement week navigation
        console.log('Next week');
    }

    clearPlan() {
        if (confirm('Clear all meals from this week?')) {
            // TODO: Implement clear functionality
            console.log('Clearing meal plan');
        }
    }
}

export default MealsManagerV3;