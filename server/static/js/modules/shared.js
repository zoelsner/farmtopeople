/**
 * Shared Utilities Module
 * Common functions used across all dashboard modules
 */

// Global state management
window.AppState = {
    currentState: 'initial',
    mealPlanData: null,
    userSettings: null,
    phoneNumber: null
};

// Phone number utilities
export function getPhoneNumber() {
    // Check URL params first
    const urlParams = new URLSearchParams(window.location.search);
    let phone = urlParams.get('phone');
    
    if (!phone) {
        // Try localStorage
        phone = localStorage.getItem('userPhone');
    }
    
    if (!phone) {
        // Try to get from logged-in user
        const userData = JSON.parse(localStorage.getItem('userData') || '{}');
        phone = userData.phone_number;
    }
    
    // Cache it
    if (phone) {
        window.AppState.phoneNumber = phone;
    }
    
    return phone;
}

// Format phone for display
export function formatPhoneNumber(phone) {
    const cleaned = ('' + phone).replace(/\D/g, '');
    const match = cleaned.match(/^1?(\d{3})(\d{3})(\d{4})$/);
    if (match) {
        return '(' + match[1] + ') ' + match[2] + '-' + match[3];
    }
    return phone;
}

// API utilities
export async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(endpoint, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`API call failed: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Local storage utilities
export function saveToStorage(key, data) {
    try {
        localStorage.setItem(key, JSON.stringify(data));
        return true;
    } catch (e) {
        console.error('Failed to save to localStorage:', e);
        return false;
    }
}

export function getFromStorage(key, defaultValue = null) {
    try {
        const data = localStorage.getItem(key);
        return data ? JSON.parse(data) : defaultValue;
    } catch (e) {
        console.error('Failed to read from localStorage:', e);
        return defaultValue;
    }
}

// Date utilities
export function getMonday(date) {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1);
    return new Date(d.setDate(diff));
}

export function formatDate(date, format = 'short') {
    if (format === 'short') {
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } else if (format === 'full') {
        return date.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
    }
    return date.toLocaleDateString();
}

// Debounce utility for performance
export function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Event emitter for cross-module communication
class EventBus {
    constructor() {
        this.events = {};
    }
    
    on(event, callback) {
        if (!this.events[event]) {
            this.events[event] = [];
        }
        this.events[event].push(callback);
    }
    
    off(event, callback) {
        if (this.events[event]) {
            this.events[event] = this.events[event].filter(cb => cb !== callback);
        }
    }
    
    emit(event, data) {
        if (this.events[event]) {
            this.events[event].forEach(callback => callback(data));
        }
    }
}

export const eventBus = new EventBus();

// Export for use in other modules
window.DashboardUtils = {
    getPhoneNumber,
    formatPhoneNumber,
    apiCall,
    saveToStorage,
    getFromStorage,
    getMonday,
    formatDate,
    debounce,
    eventBus
};