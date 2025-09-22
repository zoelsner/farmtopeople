/**
 * Settings Manager Module
 * Handles all settings-related functionality for the PWA
 */

export class SettingsManager {
    constructor() {
        this.currentUserSettings = {};
        this.settingsOptions = {};
        this.currentEditCategory = null;
        this.phone = localStorage.getItem('userPhone') || '4254955323';
    }

    async loadUserSettings() {
        const loadingEl = document.getElementById('settingsLoading');
        const categoriesEl = document.getElementById('settingsCategories');
        
        if (loadingEl) loadingEl.style.display = 'block';
        if (categoriesEl) categoriesEl.style.display = 'none';
        
        try {
            // Load user preferences
            const userResponse = await fetch(`/api/settings/${this.phone}`);
            const userData = await userResponse.json();
            this.currentUserSettings = userData;
            
            // Load available options
            const optionsResponse = await fetch('/api/settings/options');
            this.settingsOptions = await optionsResponse.json();
            
            // Display settings
            this.displaySettings();
            return true;
        } catch (error) {
            console.error('Error loading settings:', error);
            if (categoriesEl) {
                categoriesEl.innerHTML = '<p style="text-align: center; color: #dc3545;">Failed to load settings</p>';
            }
            return false;
        } finally {
            if (loadingEl) loadingEl.style.display = 'none';
            if (categoriesEl) categoriesEl.style.display = 'grid';
        }
    }

    displaySettings() {
        const categories = this.getCategories();
        const categoriesEl = document.getElementById('settingsCategories');
        if (!categoriesEl) return;
        
        const html = categories.map(cat => `
            <div class="category-card settings-category" data-category="${cat.key}" style="background: white; border-radius: 12px; padding: 20px; border: 1px solid #e9ecef; cursor: pointer; transition: all 0.2s ease;">
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <div style="display: flex; align-items: center; gap: 12px;">
                        ${this.getCategoryIcon(cat.key)}
                        <div>
                            <div style="font-size: 18px; font-weight: 600;">${cat.title}</div>
                            <div style="color: #6c757d; font-size: 14px;">${cat.getValue()}</div>
                        </div>
                    </div>
                    <span style="color: #adb5bd; font-size: 20px;">›</span>
                </div>
            </div>
        `).join('');
        
        categoriesEl.innerHTML = html;
        
        // Add click handlers
        document.querySelectorAll('.settings-category').forEach(el => {
            el.addEventListener('click', () => {
                this.openSettingsModal(el.dataset.category);
            });
        });
    }

    getCategories() {
        return [
            {
                key: 'household_size',
                title: 'Household Size',
                getValue: () => this.currentUserSettings.household_size || '1-2 people'
            },
            {
                key: 'meal_timing',
                title: 'Meal Preferences',
                getValue: () => {
                    const timing = this.currentUserSettings.meal_timing;
                    if (Array.isArray(timing)) return timing.join(', ');
                    return timing || 'Dinner';
                }
            },
            {
                key: 'cooking_methods',
                title: 'Cooking Style',
                getValue: () => {
                    const methods = this.currentUserSettings.cooking_methods || [];
                    return methods.length ? `${methods.length} preferences` : 'Not set';
                }
            },
            {
                key: 'dietary_restrictions',
                title: 'Dietary Restrictions',
                getValue: () => {
                    const restrictions = this.currentUserSettings.dietary_restrictions || [];
                    return restrictions.length ? restrictions.join(', ') : 'None';
                }
            },
            {
                key: 'goals',
                title: 'Health Goals',
                getValue: () => {
                    const goals = this.currentUserSettings.goals || [];
                    return goals.length ? goals.join(', ') : 'Not set';
                }
            }
        ];
    }

    getCategoryIcon(key) {
        // Using SVG icons instead of emojis
        const icons = {
            'household_size': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>',
            'meal_timing': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>',
            'cooking_methods': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2"></path><path d="M7 2v20"></path><path d="M21 15V2v0a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3Zm0 0v7"></path></svg>',
            'dietary_restrictions': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"></path><path d="M2 17l10 5 10-5"></path><path d="M2 12l10 5 10-5"></path></svg>',
            'goals': '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle></svg>'
        };
        return icons[key] || '';
    }

    openSettingsModal(category) {
        this.currentEditCategory = category;
        const modal = document.getElementById('settingsModal');
        const modalTitle = document.getElementById('modalTitle');
        const modalContent = document.getElementById('modalContent');
        
        if (!modal || !modalTitle || !modalContent) return;
        
        // Set title
        const titles = {
            'household_size': 'Household Size',
            'meal_timing': 'Meal Preferences',
            'cooking_methods': 'Cooking Style',
            'dietary_restrictions': 'Dietary Restrictions',
            'goals': 'Health Goals'
        };
        modalTitle.textContent = titles[category] || 'Edit Preference';
        
        // Build content
        const options = this.settingsOptions[category] || [];
        const currentValue = this.currentUserSettings[category];
        let content = '';
        
        if (category === 'household_size') {
            // Radio buttons for household size
            content = options.map(opt => `
                <label style="display: block; padding: 12px; margin: 8px 0; border: 1px solid #e9ecef; border-radius: 8px; cursor: pointer;">
                    <input type="radio" name="setting_value" value="${opt.value}" ${currentValue === opt.value ? 'checked' : ''}>
                    <span style="margin-left: 8px;">${opt.label}</span>
                </label>
            `).join('');
        } else {
            // Checkboxes for multi-select
            const currentValues = Array.isArray(currentValue) ? currentValue : [];
            content = options.map(opt => `
                <label style="display: block; padding: 12px; margin: 8px 0; border: 1px solid #e9ecef; border-radius: 8px; cursor: pointer;">
                    <input type="checkbox" name="setting_value" value="${opt.value}" ${currentValues.includes(opt.value) ? 'checked' : ''}>
                    <span style="margin-left: 8px;">${opt.label}</span>
                </label>
            `).join('');
        }
        
        modalContent.innerHTML = content;
        modal.style.display = 'block';
    }

    closeModal() {
        const modal = document.getElementById('settingsModal');
        if (modal) modal.style.display = 'none';
        this.currentEditCategory = null;
    }

    async saveChanges() {
        if (!this.currentEditCategory) return;
        
        let value;
        if (this.currentEditCategory === 'household_size') {
            // Get radio button value
            const selected = document.querySelector('input[name="setting_value"]:checked');
            value = selected ? selected.value : null;
        } else {
            // Get checkbox values
            const checked = document.querySelectorAll('input[name="setting_value"]:checked');
            value = Array.from(checked).map(cb => cb.value);
        }
        
        try {
            const response = await fetch(`/api/settings/${this.phone}/update`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    [this.currentEditCategory]: value
                })
            });
            
            if (response.ok) {
                // Update local data
                this.currentUserSettings[this.currentEditCategory] = value;
                // Refresh display
                this.displaySettings();
                // Close modal
                this.closeModal();
                return true;
            } else {
                console.error('Failed to save settings');
                return false;
            }
        } catch (error) {
            console.error('Error saving settings:', error);
            return false;
        }
    }
}

// Export the class
export { SettingsManager };