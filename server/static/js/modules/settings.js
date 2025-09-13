/**
 * Settings Module
 * Handles user preferences and settings management
 */

import { eventBus, apiCall, saveToStorage, getFromStorage, getPhoneNumber, formatPhoneNumber } from './shared.js';

class SettingsManager {
    constructor() {
        this.userData = null;
        this.preferences = {};
        this.isLoading = false;
    }

    /**
     * Load user settings from database
     */
    async loadUserSettings() {
        const phone = getPhoneNumber();
        if (!phone) {
            this.displayFallbackSettings();
            return;
        }

        this.isLoading = true;
        
        try {
            const response = await apiCall(`/api/user-settings?phone=${encodeURIComponent(phone)}`);
            
            if (response.success && response.user_data) {
                this.userData = response.user_data;
                this.preferences = response.user_data.preferences || {};
                
                // Cache locally
                saveToStorage('userData', this.userData);
                
                this.displayUserSettings();
            } else {
                this.displayFallbackSettings();
            }
        } catch (error) {
            console.error('Failed to load settings:', error);
            this.displayFallbackSettings();
        } finally {
            this.isLoading = false;
        }
    }

    /**
     * Display user settings
     */
    displayUserSettings() {
        if (!this.userData) return;
        
        // Phone number
        const phoneElement = document.getElementById('userPhone');
        if (phoneElement) {
            phoneElement.textContent = formatPhoneNumber(this.userData.phone_number || '');
        }
        
        // Household size
        this.selectHouseholdSize(this.userData.household_size || 2);
        
        // Meal preferences
        this.displayPreferences('meal', this.preferences.meal_preferences || []);
        
        // Cooking style
        this.displayPreferences('cooking', this.preferences.cooking_style || []);
        
        // Dietary restrictions
        this.displayPreferences('dietary', this.preferences.dietary_restrictions || []);
        
        // Health goals
        this.displayPreferences('health', this.preferences.health_goals || []);
        
        // Account credentials
        if (this.userData.ftp_email) {
            const emailElement = document.getElementById('ftpEmail');
            if (emailElement) {
                emailElement.textContent = this.userData.ftp_email;
            }
        }
    }

    /**
     * Display fallback settings
     */
    displayFallbackSettings() {
        const phoneElement = document.getElementById('userPhone');
        if (phoneElement) {
            phoneElement.textContent = 'Not connected';
        }
        
        // Set defaults
        this.selectHouseholdSize(2);
    }

    /**
     * Select household size
     */
    selectHouseholdSize(size) {
        document.querySelectorAll('.household-option').forEach(option => {
            if (option.dataset.value == size) {
                option.classList.add('selected');
            } else {
                option.classList.remove('selected');
            }
        });
    }

    /**
     * Display preferences for a category
     */
    displayPreferences(category, selected = []) {
        const container = document.getElementById(`${category}Preferences`);
        if (!container) return;
        
        const badges = selected.map(pref => 
            `<span class="preference-badge">${pref}</span>`
        ).join(' ');
        
        container.innerHTML = badges || '<span class="empty-text">None selected</span>';
    }

    /**
     * Open preference modal
     */
    openPreferenceModal(category) {
        const modal = document.getElementById('preferenceModal');
        const title = document.getElementById('modalTitle');
        const content = document.getElementById('modalContent');
        
        if (!modal || !title || !content) return;
        
        // Set title
        const titles = {
            meal: 'Meal Preferences',
            cooking: 'Cooking Style',
            dietary: 'Dietary Restrictions',
            health: 'Health Goals'
        };
        title.textContent = titles[category] || 'Preferences';
        
        // Build options
        content.innerHTML = this.getPreferenceOptions(category);
        
        // Show modal
        modal.classList.add('active');
        modal.dataset.category = category;
        
        // Pre-select current options
        this.preselectOptions(category);
    }

    /**
     * Get preference options for category
     */
    getPreferenceOptions(category) {
        const options = {
            meal: [
                'Quick & Easy', 'Gourmet', 'Comfort Food', 'International',
                'Healthy', 'Kid-Friendly', 'Vegetarian-Forward', 'High-Protein'
            ],
            cooking: [
                'Grilling', 'Roasting', 'Stir-Fry', 'Slow Cooker',
                'Instant Pot', 'Air Fryer', 'One-Pot', 'No-Cook'
            ],
            dietary: [
                'Vegetarian', 'Vegan', 'Gluten-Free', 'Dairy-Free',
                'Nut-Free', 'Low-Carb', 'Keto', 'Paleo',
                'Kosher', 'Halal', 'No Pork', 'No Shellfish'
            ],
            health: [
                'Weight Loss', 'Muscle Building', 'Heart Health', 'Digestive Health',
                'Energy Boost', 'Anti-Inflammatory', 'Blood Sugar Control', 'Immune Support'
            ]
        };
        
        const categoryOptions = options[category] || [];
        
        return categoryOptions.map(option => `
            <label class="preference-option">
                <input type="checkbox" value="${option}" />
                <span>${option}</span>
            </label>
        `).join('');
    }

    /**
     * Pre-select current options in modal
     */
    preselectOptions(category) {
        const selected = this.preferences[`${category}_preferences`] || 
                        this.preferences[`${category}_restrictions`] || 
                        this.preferences[`${category}_style`] || 
                        this.preferences[`${category}_goals`] || 
                        [];
        
        document.querySelectorAll('#modalContent input[type="checkbox"]').forEach(checkbox => {
            checkbox.checked = selected.includes(checkbox.value);
        });
    }

    /**
     * Save preference changes
     */
    async savePreferences() {
        const modal = document.getElementById('preferenceModal');
        const category = modal.dataset.category;
        
        if (!category) return;
        
        // Collect selected options
        const selected = [];
        document.querySelectorAll('#modalContent input[type="checkbox"]:checked').forEach(checkbox => {
            selected.push(checkbox.value);
        });
        
        // Update local preferences
        const prefKey = category === 'dietary' ? 'dietary_restrictions' :
                       category === 'health' ? 'health_goals' :
                       `${category}_preferences`;
        
        this.preferences[prefKey] = selected;
        
        // Update display
        this.displayPreferences(category, selected);
        
        // Save to database
        await this.updateUserPreferences();
        
        // Close modal
        this.closePreferenceModal();
        
        // Notify other modules
        eventBus.emit('preferences-updated', this.preferences);
    }

    /**
     * Update household size
     */
    async updateHouseholdSize(size) {
        this.selectHouseholdSize(size);
        
        if (!this.userData) {
            this.userData = {};
        }
        
        this.userData.household_size = size;
        
        // Save to database
        await this.updateUserPreferences();
    }

    /**
     * Update user preferences in database
     */
    async updateUserPreferences() {
        const phone = getPhoneNumber();
        if (!phone) return;
        
        try {
            const response = await apiCall('/api/update-preferences', {
                method: 'POST',
                body: JSON.stringify({
                    phone_number: phone,
                    household_size: this.userData?.household_size || 2,
                    preferences: this.preferences
                })
            });
            
            if (response.success) {
                // Update local cache
                saveToStorage('userData', {
                    ...this.userData,
                    preferences: this.preferences
                });
                
                console.log('Preferences updated successfully');
            }
        } catch (error) {
            console.error('Failed to update preferences:', error);
        }
    }

    /**
     * Update account credentials
     */
    async updateAccountCredentials() {
        const phone = getPhoneNumber();
        if (!phone) {
            alert('Please complete onboarding first');
            return;
        }
        
        // Create form for credentials
        const email = prompt('Enter your Farm to People email:');
        if (!email) return;
        
        const password = prompt('Enter your Farm to People password:');
        if (!password) return;
        
        try {
            const response = await apiCall('/api/update-credentials', {
                method: 'POST',
                body: JSON.stringify({
                    phone_number: phone,
                    ftp_email: email,
                    ftp_password: password
                })
            });
            
            if (response.success) {
                // Update display
                const emailElement = document.getElementById('ftpEmail');
                if (emailElement) {
                    emailElement.textContent = email;
                }
                
                alert('Credentials updated successfully');
                
                // Trigger cart re-analysis
                eventBus.emit('credentials-updated');
            } else {
                alert('Failed to update credentials');
            }
        } catch (error) {
            console.error('Failed to update credentials:', error);
            alert('Failed to update credentials');
        }
    }

    /**
     * Close preference modal
     */
    closePreferenceModal() {
        const modal = document.getElementById('preferenceModal');
        if (modal) {
            modal.classList.remove('active');
        }
    }

    /**
     * Export settings data
     */
    async exportSettings() {
        const data = {
            userData: this.userData,
            preferences: this.preferences,
            exportDate: new Date().toISOString()
        };
        
        const json = JSON.stringify(data, null, 2);
        const blob = new Blob([json], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = 'farmtopeople-settings.json';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Household size selection
        document.querySelectorAll('.household-option').forEach(option => {
            option.addEventListener('click', () => {
                this.updateHouseholdSize(parseInt(option.dataset.value));
            });
        });
        
        // Preference edit buttons
        document.querySelectorAll('.edit-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const category = btn.dataset.category;
                if (category) {
                    this.openPreferenceModal(category);
                }
            });
        });
        
        // Modal close button
        const closeBtn = document.querySelector('.modal-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this.closePreferenceModal();
            });
        }
        
        // Save preferences button
        const saveBtn = document.getElementById('savePreferences');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                this.savePreferences();
            });
        }
        
        // Update credentials button
        const updateCredsBtn = document.getElementById('updateCredentials');
        if (updateCredsBtn) {
            updateCredsBtn.addEventListener('click', () => {
                this.updateAccountCredentials();
            });
        }
    }
}

// Initialize and export
const settingsManager = new SettingsManager();

// Export for use in dashboard
window.SettingsManager = settingsManager;

export default settingsManager;