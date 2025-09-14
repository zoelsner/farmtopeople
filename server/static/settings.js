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

        // Detect if we're in iframe mode
        this.isInIframe = window.self !== window.top || new URLSearchParams(window.location.search).has('iframe');
        console.log('🐛 [DEBUG] iframe mode detected:', this.isInIframe);

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
            
            // Setup event listeners for category cards and modals (defensive approach)
            try {
                this.setupEventListeners();
            } catch (error) {
                console.log('🐛 [DEBUG] Error setting up event listeners:', error);
            }
            
            // Update preview text for all categories
            this.updateAllPreviews();

            // Force update dish preferences if it's still showing loading
            console.log('🐛 [DEBUG] Force checking dish preferences preview');
            const dishPreview = document.getElementById('dishesPreview');
            if (dishPreview) {
                console.log('🐛 [DEBUG] Current dish preview text:', dishPreview.textContent);
                console.log('🐛 [DEBUG] Selected meal IDs:', this.userPreferences.selected_meal_ids);

                // Always try to update dish preferences
                this.updatePreview('dishes', this.userPreferences.selected_meal_ids);

                // If still showing loading after update, show a more helpful message
                setTimeout(() => {
                    if (dishPreview.textContent === 'Loading...' || dishPreview.classList.contains('loading')) {
                        dishPreview.classList.remove('loading');
                        dishPreview.textContent = 'Complete onboarding to select dish preferences';
                        console.log('🐛 [DEBUG] Set fallback text for dish preferences');
                    }
                }, 100);
            }
            
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
                console.log('🐛 [DEBUG] Full API response:', result);
                console.log('🐛 [DEBUG] User preferences loaded:', this.userPreferences);
                console.log('🐛 [DEBUG] selected_meal_ids:', this.userPreferences.selected_meal_ids);
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
                try {
                    const category = card.dataset.category;
                    console.log('🐛 [DEBUG] Category card clicked:', category);
                    this.openCategoryModal(category);
                } catch (error) {
                    console.error('🐛 [ERROR] Error in category card click handler:', error);
                    // Provide graceful fallback - prevent the error from breaking the whole page
                }
            });
        });
        
        // Modal close handlers (only if elements exist)
        const modalClose = document.getElementById('modalClose');
        const modalCancel = document.getElementById('modalCancel');
        const modalSave = document.getElementById('modalSave');
        const modalOverlay = document.getElementById('modalOverlay');

        if (modalClose) {
            modalClose.addEventListener('click', () => {
                try {
                    this.closeModal();
                } catch (error) {
                    console.error('🐛 [ERROR] Error in modal close handler:', error);
                }
            });
        }

        if (modalCancel) {
            modalCancel.addEventListener('click', () => {
                try {
                    this.closeModal();
                } catch (error) {
                    console.error('🐛 [ERROR] Error in modal cancel handler:', error);
                }
            });
        }

        if (modalSave) {
            modalSave.addEventListener('click', () => {
                try {
                    this.saveCategoryChanges();
                } catch (error) {
                    console.error('🐛 [ERROR] Error in modal save handler:', error);
                }
            });
        }

        if (modalOverlay) {
            // Close modal when clicking outside
            modalOverlay.addEventListener('click', (e) => {
                try {
                    if (e.target.id === 'modalOverlay') {
                        this.closeModal();
                    }
                } catch (error) {
                    console.error('🐛 [ERROR] Error in modal overlay click handler:', error);
                }
            });
        }

        console.log('🐛 [DEBUG] Modal elements found:', {
            modalClose: !!modalClose,
            modalCancel: !!modalCancel,
            modalSave: !!modalSave,
            modalOverlay: !!modalOverlay
        });
    }
    
    updateAllPreviews() {
        this.updatePreview('household', this.userPreferences.household_size);
        this.updatePreview('meals', this.userPreferences.meal_timing);
        console.log('🐛 [DEBUG] About to update dishes preview with:', this.userPreferences.selected_meal_ids);
        this.updatePreview('dishes', this.userPreferences.selected_meal_ids);
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

            case 'dishes':
                console.log('🐛 [DEBUG] updatePreview for dishes called with value:', value);
                console.log('🐛 [DEBUG] Value type:', typeof value, 'Array?', Array.isArray(value));

                if (value && Array.isArray(value) && value.length > 0) {
                    // Show names of selected dishes
                    const dishNames = value.map(mealId => {
                        // Convert meal IDs to readable names
                        return mealId.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                    }).slice(0, 2); // Show first 2
                    previewText = dishNames.join(', ');
                    if (value.length > 2) {
                        previewText += ` and ${value.length - 2} more`;
                    }
                    console.log('🐛 [DEBUG] Generated dish preview text:', previewText);
                } else {
                    previewText = 'No dishes selected from onboarding';
                    console.log('🐛 [DEBUG] No dishes - using fallback text:', previewText);
                }
                break;

            case 'cooking':
                const methods = value?.methods || [];
                const timePrefs = value?.time || [];

                if (methods.length > 0) {
                    const methodLabels = methods.map(methodId => {
                        const method = this.availableOptions.cooking_methods?.find(m => m.id === methodId);
                        return method ? method.label : methodId;
                    });
                    previewText = methodLabels.join(', ');
                } else {
                    previewText = 'No cooking methods selected';
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
        console.log('🐛 [DEBUG] openCategoryModal called with category:', category);
        this.currentCategory = category;

        // Set modal title and subtitle
        const titles = {
            household: { title: 'Household Size', subtitle: 'How many people are in your household?' },
            meals: { title: 'Meal Timing', subtitle: 'Which meals do you want help with?' },
            dishes: { title: 'Dish Preferences', subtitle: 'What meals sound delicious to you? (Pick at least 3)' },
            cooking: { title: 'Cooking Style', subtitle: 'What cooking methods do you prefer?' },
            dietary: { title: 'Dietary Restrictions', subtitle: 'Any foods to avoid or dietary needs?' },
            goals: { title: 'Health Goals', subtitle: 'What are your meal planning goals? (Pick up to 2)' }
        };

        const categoryInfo = titles[category];
        console.log('🐛 [DEBUG] categoryInfo:', categoryInfo);

        // Check if categoryInfo exists
        if (!categoryInfo) {
            console.log('🐛 [DEBUG] CategoryInfo not found for category:', category);
            return;
        }

        // Check if modal elements exist (they may not in iframe context)
        const modalTitle = document.getElementById('modalTitle');
        const modalSubtitle = document.getElementById('modalSubtitle');

        if (modalTitle && modalSubtitle && categoryInfo) {
            modalTitle.textContent = categoryInfo.title;
            modalSubtitle.textContent = categoryInfo.subtitle;
            console.log('🐛 [DEBUG] Modal title and subtitle set successfully');
        } else {
            console.log('🐛 [DEBUG] Modal elements not found');
            console.log('🐛 [DEBUG] modalTitle:', !!modalTitle, 'modalSubtitle:', !!modalSubtitle, 'categoryInfo:', !!categoryInfo);

            // Don't exit early - try to generate content anyway in case modal elements load later
            console.log('🐛 [DEBUG] Continuing with modal generation despite missing title elements');
        }
        
        // Generate modal content based on category
        try {
            this.generateModalContent(category);
        } catch (error) {
            console.log('🐛 [DEBUG] Error generating modal content:', error);
        }
        
        // Show the modal (check if it exists first)
        const modalOverlay = document.getElementById('modalOverlay');
        if (modalOverlay) {
            modalOverlay.classList.add('show');
            console.log('🐛 [DEBUG] Modal overlay shown successfully');
        } else {
            console.log('🐛 [DEBUG] modalOverlay not found - cannot show modal');
        }
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
            case 'dishes':
                this.generateDishesContent(modalBody);
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

    generateDishesContent(container) {
        const currentDishes = this.userPreferences.selected_meal_ids || [];

        // Simple meal options for now - we can enhance this later with images
        const dishes = [
            { id: 'lemon-herb-roast-chicken', name: 'Lemon Herb Roast Chicken' },
            { id: 'mediterranean-chickpea-bowl', name: 'Mediterranean Chickpea Bowl' },
            { id: 'turkey-meatballs-farro', name: 'Turkey Meatballs with Farro' },
            { id: '15-minute-chicken-stir-fry', name: '15-Minute Chicken Stir-Fry' },
            { id: 'grilled-salmon-greens', name: 'Grilled Salmon with Greens' },
            { id: 'beef-tacos-skillet', name: 'Beef Tacos Skillet' },
            { id: 'vegetarian-curry-bowl', name: 'Vegetarian Curry Bowl' },
            { id: 'pasta-with-seasonal-vegetables', name: 'Pasta with Seasonal Vegetables' }
        ];

        const dishesHtml = `
            <div class="modal-options">
                ${dishes.map(dish => `
                    <div class="option-item ${currentDishes.includes(dish.id) ? 'selected' : ''}" data-dish="${dish.id}">
                        <span class="option-text">${dish.name}</span>
                        <span class="option-check">✓</span>
                    </div>
                `).join('')}
            </div>
        `;

        container.innerHTML = dishesHtml;

        // Add click handlers for dish options
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

            case 'dishes':
                const selectedDishes = modalBody.querySelectorAll('.option-item.selected');
                return Array.from(selectedDishes).map(item => item.dataset.dish);

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
            case 'dishes':
                this.userPreferences.selected_meal_ids = value;
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