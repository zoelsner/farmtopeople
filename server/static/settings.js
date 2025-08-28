/**
 * Settings Page JavaScript - Farm to People
 * 
 * Handles the 5-category settings interface:
 * 1. Household Size - Single selection from 4 options
 * 2. Meal Preferences - Multi-selection from breakfast/lunch/dinner/snacks
 * 3. Cooking Style - Multi-selection from 6 cooking methods  
 * 4. Dietary Restrictions - Multi-selection from 8 restrictions
 * 5. Health Goals - Multi-selection from 6 goals (max 2)
 * 
 * Features:
 * - Loads user preferences from phone number (from URL params or localStorage)
 * - Shows current selections in preview text on category cards
 * - Modal-based editing that reuses onboarding UI patterns
 * - Individual category updates without affecting other preferences
 * - Real-time preview updates after successful saves
 */

class SettingsManager {
    constructor() {
        this.userPhone = null;
        this.userPreferences = {};
        this.availableOptions = {};
        this.currentCategory = null;
        
        // Initialize the settings page
        this.init();
    }
    
    async init() {
        try {
            // Get user phone number (from URL params, localStorage, or prompt)
            await this.getUserPhone();
            
            // Load available options for all categories
            await this.loadAvailableOptions();
            
            // Load user's current preferences
            await this.loadUserPreferences();
            
            // Setup event listeners for category cards and modals
            this.setupEventListeners();
            
            // Update preview text for all categories
            this.updateAllPreviews();
            
        } catch (error) {
            console.error('Failed to initialize settings:', error);
            this.showMessage('Failed to load settings. Please try refreshing the page.', 'error');
        }
    }
    
    async getUserPhone() {
        // Try to get phone number from URL parameters first
        const urlParams = new URLSearchParams(window.location.search);
        let phone = urlParams.get('phone');
        
        // If not in URL, try localStorage (from previous sessions)
        if (!phone) {
            phone = localStorage.getItem('userPhone');
        }
        
        // If still no phone, prompt user to enter it
        if (!phone) {
            phone = prompt('Enter your phone number to access settings:');
            if (!phone) {
                throw new Error('Phone number required to access settings');
            }
            // Store for future use
            localStorage.setItem('userPhone', phone);
        }
        
        this.userPhone = phone;
    }
    
    async loadAvailableOptions() {
        try {
            const response = await fetch('/api/settings/options');
            const result = await response.json();
            
            if (result.success) {
                this.availableOptions = result.options;
            } else {
                throw new Error(result.error || 'Failed to load options');
            }
        } catch (error) {
            console.error('Failed to load options:', error);
            throw error;
        }
    }
    
    async loadUserPreferences() {
        try {
            // Remove any non-numeric characters for the API call
            const cleanPhone = this.userPhone.replace(/[^\d]/g, '');
            
            const response = await fetch(`/api/settings/${cleanPhone}`);
            const result = await response.json();
            
            if (result.success) {
                this.userPreferences = result.preferences;
            } else {
                throw new Error(result.error || 'Failed to load preferences');
            }
        } catch (error) {
            console.error('Failed to load preferences:', error);
            throw error;
        }
    }
    
    setupEventListeners() {
        // Category card click handlers
        document.querySelectorAll('.category-card').forEach(card => {
            card.addEventListener('click', (e) => {
                const category = card.dataset.category;
                this.openCategoryModal(category);
            });
        });
        
        // Modal close handlers
        document.getElementById('modalClose').addEventListener('click', () => {
            this.closeModal();
        });
        
        document.getElementById('modalCancel').addEventListener('click', () => {
            this.closeModal();
        });
        
        // Modal save handler
        document.getElementById('modalSave').addEventListener('click', () => {
            this.saveCategoryChanges();
        });
        
        // Close modal when clicking outside
        document.getElementById('modalOverlay').addEventListener('click', (e) => {
            if (e.target.id === 'modalOverlay') {
                this.closeModal();
            }
        });
    }
    
    updateAllPreviews() {
        this.updatePreview('household', this.userPreferences.household_size);
        this.updatePreview('meals', this.userPreferences.meal_timing);
        this.updatePreview('cooking', {
            methods: this.userPreferences.cooking_methods,
            time: this.userPreferences.time_preferences
        });
        this.updatePreview('dietary', this.userPreferences.dietary_restrictions);
        this.updatePreview('goals', this.userPreferences.goals);
    }
    
    updatePreview(category, value) {
        const previewElement = document.getElementById(`${category}Preview`);
        if (!previewElement) return;
        
        // Remove loading state
        previewElement.classList.remove('loading');
        
        let previewText = '';
        
        switch (category) {
            case 'household':
                previewText = value ? `${value} people` : 'Not set';
                break;
                
            case 'meals':
                if (value && value.length > 0) {
                    const mealLabels = value.map(mealId => {
                        const meal = this.availableOptions.meal_timings.find(m => m.id === mealId);
                        return meal ? meal.label : mealId;
                    });
                    previewText = mealLabels.join(', ');
                } else {
                    previewText = 'No meals selected';
                }
                break;
                
            case 'cooking':
                const methods = value?.methods || [];
                const timePrefs = value?.time || [];
                const allCooking = [...methods, ...timePrefs];
                
                if (allCooking.length > 0) {
                    previewText = `${allCooking.length} cooking preferences`;
                } else {
                    previewText = 'No cooking style set';
                }
                break;
                
            case 'dietary':
                if (value && value.length > 0) {
                    const restrictionLabels = value.map(restrictionId => {
                        const restriction = this.availableOptions.dietary_restrictions.find(r => r.id === restrictionId);
                        return restriction ? restriction.label.replace(' (', ' (').split(' (')[0] : restrictionId;
                    });
                    previewText = restrictionLabels.join(', ');
                } else {
                    previewText = 'No restrictions';
                }
                break;
                
            case 'goals':
                if (value && value.length > 0) {
                    const goalLabels = value.map(goalId => {
                        const goal = this.availableOptions.goals.find(g => g.id === goalId);
                        return goal ? goal.label.split(' (')[0] : goalId;
                    });
                    previewText = goalLabels.join(', ');
                } else {
                    previewText = 'No goals set';
                }
                break;
        }
        
        previewElement.textContent = previewText;
    }
    
    openCategoryModal(category) {
        this.currentCategory = category;
        
        // Set modal title and subtitle
        const titles = {
            household: { title: 'Household Size', subtitle: 'How many people are in your household?' },
            meals: { title: 'Meal Preferences', subtitle: 'Which meals do you want help with?' },
            cooking: { title: 'Cooking Style', subtitle: 'What cooking methods do you prefer?' },
            dietary: { title: 'Dietary Restrictions', subtitle: 'Any foods to avoid or dietary needs?' },
            goals: { title: 'Health Goals', subtitle: 'What are your meal planning goals? (Pick up to 2)' }
        };
        
        const categoryInfo = titles[category];
        document.getElementById('modalTitle').textContent = categoryInfo.title;
        document.getElementById('modalSubtitle').textContent = categoryInfo.subtitle;
        
        // Generate modal content based on category
        this.generateModalContent(category);
        
        // Show the modal
        document.getElementById('modalOverlay').classList.add('show');
    }
    
    generateModalContent(category) {
        const modalBody = document.getElementById('modalBody');
        modalBody.innerHTML = '';
        
        switch (category) {
            case 'household':
                this.generateHouseholdContent(modalBody);
                break;
            case 'meals':
                this.generateMealsContent(modalBody);
                break;
            case 'cooking':
                this.generateCookingContent(modalBody);
                break;
            case 'dietary':
                this.generateDietaryContent(modalBody);
                break;
            case 'goals':
                this.generateGoalsContent(modalBody);
                break;
        }
    }
    
    generateHouseholdContent(container) {
        const currentSize = this.userPreferences.household_size || '1-2';
        
        const sizeOptionsHtml = `
            <div class="size-options">
                ${this.availableOptions.household_sizes.map(size => `
                    <div class="size-option ${size === currentSize ? 'selected' : ''}" data-size="${size}">
                        <span class="size-number">${size}</span>
                        <span>people</span>
                    </div>
                `).join('')}
            </div>
        `;
        
        container.innerHTML = sizeOptionsHtml;
        
        // Add click handlers for size options
        container.querySelectorAll('.size-option').forEach(option => {
            option.addEventListener('click', () => {
                container.querySelectorAll('.size-option').forEach(o => o.classList.remove('selected'));
                option.classList.add('selected');
            });
        });
    }
    
    generateMealsContent(container) {
        const currentMeals = this.userPreferences.meal_timing || [];
        
        const mealsHtml = `
            <div class="modal-options">
                ${this.availableOptions.meal_timings.map(meal => `
                    <div class="option-item ${currentMeals.includes(meal.id) ? 'selected' : ''}" data-meal="${meal.id}">
                        <span class="option-text">${meal.icon} ${meal.label}</span>
                        <span class="option-check">✓</span>
                    </div>
                `).join('')}
            </div>
        `;
        
        container.innerHTML = mealsHtml;
        
        // Add click handlers for meal options
        container.querySelectorAll('.option-item').forEach(option => {
            option.addEventListener('click', () => {
                option.classList.toggle('selected');
            });
        });
    }
    
    generateCookingContent(container) {
        const currentMethods = this.userPreferences.cooking_methods || [];
        
        const cookingHtml = `
            <div class="modal-options">
                ${this.availableOptions.cooking_methods.map(method => `
                    <div class="option-item ${currentMethods.includes(method.id) ? 'selected' : ''}" data-method="${method.id}">
                        <span class="option-text">${method.label}</span>
                        <span class="option-check">✓</span>
                    </div>
                `).join('')}
            </div>
        `;
        
        container.innerHTML = cookingHtml;
        
        // Add click handlers for cooking method options
        container.querySelectorAll('.option-item').forEach(option => {
            option.addEventListener('click', () => {
                option.classList.toggle('selected');
            });
        });
    }
    
    generateDietaryContent(container) {
        const currentRestrictions = this.userPreferences.dietary_restrictions || [];
        
        const dietaryHtml = `
            <div class="modal-options">
                ${this.availableOptions.dietary_restrictions.map(restriction => `
                    <div class="option-item ${currentRestrictions.includes(restriction.id) ? 'selected' : ''}" data-restriction="${restriction.id}">
                        <span class="option-text">${restriction.label}</span>
                        <span class="option-check">✓</span>
                    </div>
                `).join('')}
            </div>
        `;
        
        container.innerHTML = dietaryHtml;
        
        // Add click handlers for dietary options
        container.querySelectorAll('.option-item').forEach(option => {
            option.addEventListener('click', () => {
                option.classList.toggle('selected');
            });
        });
    }
    
    generateGoalsContent(container) {
        const currentGoals = this.userPreferences.goals || [];
        
        const goalsHtml = `
            <div class="modal-options">
                ${this.availableOptions.goals.map(goal => `
                    <div class="option-item ${currentGoals.includes(goal.id) ? 'selected' : ''}" data-goal="${goal.id}">
                        <span class="option-text">${goal.icon} ${goal.label}</span>
                        <span class="option-check">✓</span>
                    </div>
                `).join('')}
            </div>
        `;
        
        container.innerHTML = goalsHtml;
        
        // Add click handlers for goal options (with 2-selection limit)
        container.querySelectorAll('.option-item').forEach(option => {
            option.addEventListener('click', () => {
                const isSelected = option.classList.contains('selected');
                const currentSelected = container.querySelectorAll('.option-item.selected');
                
                if (isSelected) {
                    // Deselecting - always allowed
                    option.classList.remove('selected');
                } else if (currentSelected.length < 2) {
                    // Selecting - only if less than 2 already selected
                    option.classList.add('selected');
                } else {
                    // Already have 2 selected - show message
                    this.showMessage('You can select up to 2 goals. Deselect one to choose a different goal.', 'error');
                }
            });
        });
    }
    
    closeModal() {
        document.getElementById('modalOverlay').classList.remove('show');
        this.currentCategory = null;
    }
    
    async saveCategoryChanges() {
        if (!this.currentCategory) return;
        
        try {
            // Collect the current selections from the modal
            let value = this.collectModalSelections(this.currentCategory);
            
            // Send update to backend
            const cleanPhone = this.userPhone.replace(/[^\d]/g, '');
            
            const response = await fetch(`/api/settings/${cleanPhone}/update`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    category: this.currentCategory,
                    value: value
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Update local preferences
                this.updateLocalPreferences(this.currentCategory, value);
                
                // Update the preview for this category
                this.updatePreview(this.currentCategory, value);
                
                // Show success message
                this.showMessage('Settings updated successfully!', 'success');
                
                // Close the modal
                this.closeModal();
                
            } else {
                throw new Error(result.error || 'Failed to update preferences');
            }
            
        } catch (error) {
            console.error('Failed to save changes:', error);
            this.showMessage('Failed to save changes. Please try again.', 'error');
        }
    }
    
    collectModalSelections(category) {
        const modalBody = document.getElementById('modalBody');
        
        switch (category) {
            case 'household':
                const selectedSize = modalBody.querySelector('.size-option.selected');
                return selectedSize ? selectedSize.dataset.size : '1-2';
                
            case 'meals':
                const selectedMeals = modalBody.querySelectorAll('.option-item.selected');
                return Array.from(selectedMeals).map(item => item.dataset.meal);
                
            case 'cooking':
                const selectedMethods = modalBody.querySelectorAll('.option-item.selected');
                return {
                    methods: Array.from(selectedMethods).map(item => item.dataset.method),
                    time: [] // Time preferences would be handled separately if needed
                };
                
            case 'dietary':
                const selectedRestrictions = modalBody.querySelectorAll('.option-item.selected');
                return Array.from(selectedRestrictions).map(item => item.dataset.restriction);
                
            case 'goals':
                const selectedGoals = modalBody.querySelectorAll('.option-item.selected');
                return Array.from(selectedGoals).map(item => item.dataset.goal);
                
            default:
                return null;
        }
    }
    
    updateLocalPreferences(category, value) {
        switch (category) {
            case 'household':
                this.userPreferences.household_size = value;
                break;
            case 'meals':
                this.userPreferences.meal_timing = value;
                break;
            case 'cooking':
                this.userPreferences.cooking_methods = value.methods;
                this.userPreferences.time_preferences = value.time;
                break;
            case 'dietary':
                this.userPreferences.dietary_restrictions = value;
                break;
            case 'goals':
                this.userPreferences.goals = value;
                break;
        }
    }
    
    showMessage(text, type = 'success') {
        const container = document.getElementById('messageContainer');
        
        // Remove any existing messages
        container.innerHTML = '';
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        messageDiv.textContent = text;
        
        container.appendChild(messageDiv);
        
        // Auto-hide success messages after 3 seconds
        if (type === 'success') {
            setTimeout(() => {
                messageDiv.remove();
            }, 3000);
        }
    }
}

// Initialize settings when page loads
document.addEventListener('DOMContentLoaded', () => {
    new SettingsManager();
});