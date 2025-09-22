/**
 * Navigation Module v2 - PWA-friendly tab navigation
 * Ensures smooth transitions without page refreshes
 */

import { appState } from './core.js';

export class Navigation {
    constructor() {
        this.tabs = ['box', 'plan', 'settings'];
        this.initialized = false;
    }

    init() {
        if (this.initialized) return;

        // Map old tab names to new ones for compatibility
        this.tabMapping = {
            'box': 'box',      // Cart tab
            'plan': 'plan',    // Meals tab
            'settings': 'settings'
        };

        // Set up tab click handlers
        this.setupTabHandlers();

        // Handle browser back/forward
        this.setupHistoryHandlers();

        // Set initial tab from URL or default
        const hash = window.location.hash.slice(1);
        const initialTab = this.tabMapping[hash] || 'box';
        this.switchTab(initialTab, false);

        this.initialized = true;
    }

    setupTabHandlers() {
        // Handle bottom navigation tabs
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();

                const tabName = tab.dataset.tab;
                if (tabName && this.tabs.includes(tabName)) {
                    this.switchTab(tabName);
                }
            });
        });

        // Prevent any default link behaviors that might cause refresh
        document.addEventListener('click', (e) => {
            const link = e.target.closest('a');
            if (link && link.href && link.href.includes('#')) {
                e.preventDefault();
                const tab = link.href.split('#')[1];
                if (this.tabs.includes(tab)) {
                    this.switchTab(tab);
                }
            }
        });
    }

    setupHistoryHandlers() {
        window.addEventListener('popstate', (e) => {
            if (e.state && e.state.tab) {
                this.switchTab(e.state.tab, false);
            }
        });
    }

    switchTab(tabName, updateHistory = true) {
        // Validate tab name
        if (!this.tabs.includes(tabName)) {
            console.warn(`Invalid tab: ${tabName}`);
            return;
        }

        // Get current tab before switching
        const previousTab = appState.get('ui.activeTab');

        // Don't do anything if we're already on this tab
        if (previousTab === tabName && this.initialized) {
            return;
        }

        // Update state
        appState.update('ui.activeTab', tabName);

        // Hide all tab contents
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });

        // Show selected tab content
        const targetContent = document.getElementById(`${tabName}Tab`);
        if (targetContent) {
            targetContent.classList.add('active');
        }

        // Update nav tab active states
        document.querySelectorAll('.nav-tab').forEach(tab => {
            if (tab.dataset.tab === tabName) {
                tab.classList.add('active');
            } else {
                tab.classList.remove('active');
            }
        });

        // Update header based on tab
        this.updateHeader(tabName);

        // Update browser history without causing refresh
        if (updateHistory) {
            const newUrl = `${window.location.pathname}#${tabName}`;
            history.pushState({ tab: tabName }, '', newUrl);
        }

        // Emit tab change event for other modules
        appState.emit('tab:changed', {
            from: previousTab,
            to: tabName
        });

        // Tab-specific initialization
        this.handleTabSpecificInit(tabName, previousTab);
    }

    updateHeader(tabName) {
        const header = document.querySelector('.header h1');
        const subtitle = document.querySelector('.header .subtitle');

        if (!header) return;

        const titles = {
            'cart': {
                title: 'Cart Analysis',
                subtitle: 'Your Farm to People selections'
            },
            'meals': {
                title: 'Weekly Meals',
                subtitle: 'Personalized meal planning'
            },
            'settings': {
                title: 'Settings',
                subtitle: 'Your preferences'
            }
        };

        const config = titles[tabName] || titles['cart'];

        // Smooth text transition
        header.style.opacity = '0.5';
        subtitle.style.opacity = '0.5';

        setTimeout(() => {
            header.textContent = config.title;

            // Preserve email if it exists in subtitle
            const userEmail = localStorage.getItem('ftpEmail');
            subtitle.textContent = userEmail || config.subtitle;

            header.style.opacity = '1';
            subtitle.style.opacity = '1';
        }, 150);
    }

    handleTabSpecificInit(tabName, previousTab) {
        // Load tab-specific data if needed
        switch (tabName) {
            case 'settings':
                // Settings should NOT cause a page refresh
                // Just emit event for settings module to handle
                appState.emit('settings:opened', { from: previousTab });
                break;

            case 'meals':
                // Initialize meal calendar if needed
                appState.emit('meals:opened', { from: previousTab });
                break;

            case 'cart':
                // Check if cart needs refresh
                appState.emit('cart:opened', { from: previousTab });
                break;
        }
    }

    // Navigate to a specific tab programmatically
    goToTab(tabName) {
        this.switchTab(tabName);
    }

    // Get current active tab
    getCurrentTab() {
        return appState.get('ui.activeTab');
    }

    // Check if a specific tab is active
    isTabActive(tabName) {
        return this.getCurrentTab() === tabName;
    }

    // Refresh current tab content (without page reload)
    refreshCurrentTab() {
        const currentTab = this.getCurrentTab();
        appState.emit(`${currentTab}:refresh`, {});
    }
}