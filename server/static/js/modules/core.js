/**
 * Core Module - State Management and Utilities
 * Provides centralized state management and utility functions
 */

// Singleton AppState for centralized state management
export class AppState {
    static instance = null;

    constructor() {
        if (AppState.instance) {
            return AppState.instance;
        }

        this.state = {
            user: {
                phone: localStorage.getItem('userPhone') || '',
                email: localStorage.getItem('ftpEmail') || '',
                settings: {}
            },
            cart: {
                data: null,
                lastAnalyzed: null,
                refreshesLeft: 3,
                isLoading: false
            },
            meals: {
                currentPlan: null,
                weekOf: null,
                draggedMeal: null,
                ingredientPool: {}
            },
            settings: {
                isLoading: false,
                currentCategory: null,
                options: {}
            },
            ui: {
                activeTab: 'cart',
                modalOpen: false
            }
        };

        this.listeners = {};
        AppState.instance = this;
    }

    // Get state value
    get(path) {
        const keys = path.split('.');
        let value = this.state;
        for (const key of keys) {
            value = value?.[key];
        }
        return value;
    }

    // Update state and emit events
    update(path, value) {
        const keys = path.split('.');
        const lastKey = keys.pop();
        let target = this.state;

        for (const key of keys) {
            if (!target[key]) target[key] = {};
            target = target[key];
        }

        const oldValue = target[lastKey];
        target[lastKey] = value;

        // Emit change event
        this.emit(`${path}:changed`, { oldValue, newValue: value });
        this.emit('state:changed', { path, oldValue, newValue: value });
    }

    // Event emitter functionality
    on(event, callback) {
        if (!this.listeners[event]) {
            this.listeners[event] = [];
        }
        this.listeners[event].push(callback);
    }

    off(event, callback) {
        if (!this.listeners[event]) return;
        this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    }

    emit(event, data) {
        if (!this.listeners[event]) return;
        this.listeners[event].forEach(callback => {
            try {
                callback(data);
            } catch (error) {
                console.error(`Error in event listener for ${event}:`, error);
            }
        });
    }

    // Clear user-specific data (for logout or user switch)
    clearUserData() {
        this.update('cart.data', null);
        this.update('cart.lastAnalyzed', null);
        this.update('meals.currentPlan', null);
        this.update('user.settings', {});
        localStorage.removeItem('cartAnalysisData');
        localStorage.removeItem('cachedMealSuggestions');
    }
}

// Utility functions
export const Utils = {
    // Format phone number to E.164 format
    formatPhone(phone) {
        if (!phone) return '';
        const cleaned = phone.replace(/\D/g, '');
        if (cleaned.length === 10) {
            return `+1${cleaned}`;
        }
        if (cleaned.length === 11 && cleaned[0] === '1') {
            return `+${cleaned}`;
        }
        return phone;
    },

    // Format date for display
    formatDate(date, format = 'short') {
        if (!date) return '';
        const d = new Date(date);

        if (format === 'short') {
            return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        }
        if (format === 'full') {
            return d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
        }
        return d.toLocaleDateString();
    },

    // Debounce function for performance
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Local storage helpers with JSON support
    storage: {
        get(key) {
            try {
                const item = localStorage.getItem(key);
                return item ? JSON.parse(item) : null;
            } catch {
                return localStorage.getItem(key);
            }
        },

        set(key, value) {
            try {
                localStorage.setItem(key, typeof value === 'string' ? value : JSON.stringify(value));
            } catch (error) {
                console.error('Error saving to localStorage:', error);
            }
        },

        remove(key) {
            localStorage.removeItem(key);
        },

        clear() {
            localStorage.clear();
        }
    },

    // Check if running as PWA
    isPWA() {
        return window.matchMedia('(display-mode: standalone)').matches ||
               window.navigator.standalone === true;
    },

    // Generate unique ID
    generateId() {
        return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    },

    // Deep clone object
    deepClone(obj) {
        return JSON.parse(JSON.stringify(obj));
    },

    // Clean producer name (remove duplicates)
    cleanProducerName(producer) {
        if (!producer) return 'Local Farm';
        const parts = producer.split(' - ');
        const uniqueParts = [...new Set(parts)];
        let cleaned = uniqueParts.join(' - ');
        cleaned = cleaned.replace(/^From /, '');
        return cleaned || 'Local Farm';
    },

    // Determine item category
    getItemCategory(itemName) {
        const name = itemName.toLowerCase();
        const categories = {
            'Fruits': ['apple', 'banana', 'orange', 'berry', 'grape', 'peach', 'pear', 'plum', 'melon', 'mango', 'pineapple', 'citrus', 'fruit'],
            'Vegetables': ['carrot', 'lettuce', 'tomato', 'cucumber', 'pepper', 'broccoli', 'spinach', 'kale', 'cabbage', 'onion', 'garlic', 'potato', 'squash', 'zucchini', 'vegetable', 'greens', 'salad'],
            'Proteins': ['chicken', 'beef', 'pork', 'turkey', 'fish', 'salmon', 'egg', 'tofu', 'beans', 'protein', 'meat'],
            'Dairy': ['milk', 'cheese', 'yogurt', 'butter', 'cream', 'dairy'],
            'Grains': ['bread', 'rice', 'pasta', 'quinoa', 'oat', 'cereal', 'grain', 'flour'],
            'Pantry': ['oil', 'vinegar', 'sauce', 'spice', 'seasoning', 'honey', 'sugar', 'salt']
        };

        for (const [category, keywords] of Object.entries(categories)) {
            if (keywords.some(keyword => name.includes(keyword))) {
                return category;
            }
        }
        return 'Other';
    },

    // Get category color scheme
    getCategoryColors(category) {
        const colors = {
            'Fruits': { bg: '#ffebe6', text: '#ff6b4a' },
            'Vegetables': { bg: '#e6f7e6', text: '#4caf50' },
            'Proteins': { bg: '#ffe6e6', text: '#ff4444' },
            'Dairy': { bg: '#f0f8ff', text: '#2196f3' },
            'Grains': { bg: '#fff3e0', text: '#ff9800' },
            'Pantry': { bg: '#f5f5f5', text: '#757575' },
            'Other': { bg: '#f9f9f9', text: '#666666' }
        };
        return colors[category] || colors['Other'];
    }
};

// Initialize singleton instance
export const appState = new AppState();

// Export for backward compatibility
export default {
    AppState,
    appState,
    Utils
};