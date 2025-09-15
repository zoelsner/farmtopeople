/**
 * API Client Module - Centralized API communication
 * Handles all server requests with consistent error handling
 */

import { appState, Utils } from './core.js';

export class APIClient {
    constructor() {
        this.baseURL = window.location.origin;
        this.defaultHeaders = {
            'Content-Type': 'application/json'
        };
    }

    // Generic request method with error handling
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            ...options,
            headers: {
                ...this.defaultHeaders,
                ...options.headers
            }
        };

        try {
            const response = await fetch(url, config);

            // Handle non-JSON responses
            const contentType = response.headers.get('content-type');
            let data;

            if (contentType && contentType.includes('application/json')) {
                data = await response.json();
            } else {
                data = await response.text();
            }

            if (!response.ok) {
                throw new Error(data.error || `HTTP ${response.status}`);
            }

            return data;
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    }

    // Cart APIs
    async analyzeCart(forceRefresh = false) {
        const phone = appState.get('user.phone') || localStorage.getItem('userPhone');

        return this.request('/api/analyze-cart', {
            method: 'POST',
            body: JSON.stringify({
                phone,
                force_refresh: forceRefresh
            })
        });
    }

    async getSavedCart() {
        return this.request('/api/get-saved-cart');
    }

    async generateSwapsAndAddons(cartData) {
        const phone = appState.get('user.phone') || localStorage.getItem('userPhone');

        return this.request('/api/generate-swaps-addons', {
            method: 'POST',
            body: JSON.stringify({
                phone,
                cart_data: cartData
            })
        });
    }

    // Meal APIs
    async generateWeeklyMeals(cartData, preferences = {}) {
        const phone = appState.get('user.phone') || localStorage.getItem('userPhone');

        return this.request('/api/generate-weekly-meals', {
            method: 'POST',
            body: JSON.stringify({
                phone,
                cart_data: cartData,
                preferences
            })
        });
    }

    async createMealPlan(weekOf, cartData) {
        const phone = appState.get('user.phone') || localStorage.getItem('userPhone');

        return this.request('/api/meal-plans/create', {
            method: 'POST',
            body: JSON.stringify({
                user_phone: phone,
                week_of: weekOf,
                cart_data: cartData
            })
        });
    }

    async getMealPlan(weekOf) {
        const phone = appState.get('user.phone') || localStorage.getItem('userPhone');

        return this.request(`/api/meal-plans/${phone}/${weekOf}`);
    }

    async regenerateMeal(planId, dayOfWeek, constraints = {}) {
        return this.request(`/api/meal-plans/${planId}/regenerate-meal`, {
            method: 'POST',
            body: JSON.stringify({
                day_of_week: dayOfWeek,
                constraints
            })
        });
    }

    async swapMeals(planId, sourceMealId, targetMealId, sourceDay, targetDay) {
        return this.request(`/api/meal-plans/${planId}/swap-meals`, {
            method: 'POST',
            body: JSON.stringify({
                source_meal_id: sourceMealId,
                target_meal_id: targetMealId,
                source_day: sourceDay,
                target_day: targetDay
            })
        });
    }

    async generateRecipe(mealData) {
        const phone = appState.get('user.phone') || localStorage.getItem('userPhone');

        return this.request('/api/generate-recipe', {
            method: 'POST',
            body: JSON.stringify({
                phone,
                meal: mealData
            })
        });
    }

    // Settings APIs
    async getUserSettings(phone = null) {
        const userPhone = phone || appState.get('user.phone') || localStorage.getItem('userPhone');
        return this.request(`/api/settings/${userPhone}`);
    }

    async updateUserSettings(category, value) {
        const phone = appState.get('user.phone') || localStorage.getItem('userPhone');

        return this.request('/api/update-preferences', {
            method: 'POST',
            body: JSON.stringify({
                phone,
                [category]: value
            })
        });
    }

    async getSettingsOptions() {
        return this.request('/api/settings/options');
    }

    // User APIs
    async checkExistingUser(phone) {
        const formattedPhone = Utils.formatPhone(phone);

        return this.request('/api/check-existing-user', {
            method: 'POST',
            body: JSON.stringify({
                phone: formattedPhone
            })
        });
    }

    async saveUserData(userData) {
        return this.request('/save-user-data', {
            method: 'POST',
            body: JSON.stringify(userData)
        });
    }

    // Session APIs
    async createSession(phone) {
        return this.request('/api/sessions/create', {
            method: 'POST',
            body: JSON.stringify({ phone })
        });
    }

    async getSession(sessionId) {
        return this.request(`/api/sessions/${sessionId}`);
    }

    async updateSession(sessionId, data) {
        return this.request(`/api/sessions/${sessionId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    // Utility methods
    async healthCheck() {
        return this.request('/api/health');
    }

    // Cache management
    clearCache() {
        // Clear localStorage items related to API responses
        const cacheKeys = [
            'cartAnalysisData',
            'cachedMealSuggestions',
            'userSettings',
            'settingsOptions'
        ];

        cacheKeys.forEach(key => {
            localStorage.removeItem(key);
        });
    }
}

// Create singleton instance
export const apiClient = new APIClient();

export default apiClient;