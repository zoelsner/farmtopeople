/**
 * Navigation Manager Module
 * Handles bottom navigation and tab switching
 */

export class NavigationManager {
    constructor() {
        this.currentTab = 'box';
        this.tabs = ['box', 'plan', 'settings'];
    }

    init() {
        // Initialize navigation
        this.setupEventListeners();
        this.switchToTab('box');
    }

    setupEventListeners() {
        // Add click handlers to nav tabs
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const tabName = tab.dataset.tab;
                if (tabName) {
                    this.switchToTab(tabName);
                }
            });
        });
    }

    switchToTab(tabName) {
        // Update nav tabs
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.classList.remove('active');
        });
        const activeTab = document.querySelector(`[data-tab="${tabName}"]`);
        if (activeTab) activeTab.classList.add('active');
        
        // Update content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        const activeContent = document.getElementById(`${tabName}Tab`);
        if (activeContent) activeContent.classList.add('active');
        
        // Update header
        this.updateHeader(tabName);
        
        // Trigger tab-specific initialization
        this.initializeTab(tabName);
        
        this.currentTab = tabName;
    }

    updateHeader(tabName) {
        const headerTitle = document.querySelector('.header h1');
        const headerSubtitle = document.getElementById('headerSubtitle');
        
        if (!headerTitle || !headerSubtitle) return;
        
        const headers = {
            'box': {
                title: 'Cart Analysis',
                subtitle: 'Ready to analyze your cart'
            },
            'plan': {
                title: 'Meal Planning',
                subtitle: 'Plan your weekly meals'
            },
            'settings': {
                title: 'Settings',
                subtitle: 'Update your preferences'
            }
        };
        
        const header = headers[tabName];
        if (header) {
            headerTitle.textContent = header.title;
            headerSubtitle.textContent = header.subtitle;
        }
    }

    initializeTab(tabName) {
        // Dispatch custom event for tab initialization
        window.dispatchEvent(new CustomEvent('tab-switched', { detail: { tab: tabName } }));
        
        // Tab-specific initialization
        switch(tabName) {
            case 'box':
                // Cart tab is initialized on demand when analyzing
                break;
            case 'plan':
                // Initialize meal calendar if data exists
                if (window.mealPlanData && window.mealPlanData.cart_data) {
                    if (typeof window.initMealCalendar === 'function') {
                        window.initMealCalendar();
                    }
                }
                break;
            case 'settings':
                // Load settings if manager exists
                if (window.settingsManager && !window.settingsManager.currentUserSettings.household_size) {
                    window.settingsManager.loadUserSettings();
                }
                break;
        }
    }

    getCurrentTab() {
        return this.currentTab;
    }
}

// Export the class
export { NavigationManager };