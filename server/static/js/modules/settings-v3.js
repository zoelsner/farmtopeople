/**
 * Settings Manager Module v3
 * PWA-friendly settings management WITHOUT page refreshes
 * CRITICAL: All modal interactions stay within the SPA
 */

import { appState, Utils } from './core.js';
import apiClient from './api-client.js';

export class SettingsManagerV3 {
    constructor() {
        this.container = null;
        this.currentSettings = {};
        this.settingsOptions = {};
        this.currentEditCategory = null;
        this.modal = null;
        this.initialized = false;
    }

    async init() {
        this.container = document.getElementById('settingsContainer');
        if (!this.container) {
            console.error('Settings container not found');
            return;
        }

        // Create modal if it doesn't exist
        this.createModal();

        // Listen for settings tab events
        appState.on('settings:opened', async () => {
            // CRITICAL: Do NOT reload page, just load settings data
            await this.loadSettings();
        });

        // Listen for preference updates from other modules
        appState.on('preferences:updated', (data) => {
            this.currentSettings = { ...this.currentSettings, ...data };
            this.displaySettings();
        });

        this.initialized = true;
    }

    createModal() {
        // Check if modal already exists
        if (document.getElementById('settingsModalV3')) {
            this.modal = document.getElementById('settingsModalV3');
            return;
        }

        // Create modal HTML
        const modalHTML = `
            <div id="settingsModalV3" class="settings-modal">
                <div class="modal-overlay" id="modalOverlay"></div>
                <div class="modal-container">
                    <div class="modal-header">
                        <h2 id="modalTitle">Edit Preference</h2>
                        <button class="modal-close-btn" id="modalCloseBtn">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="18" y1="6" x2="6" y2="18"></line>
                                <line x1="6" y1="6" x2="18" y2="18"></line>
                            </svg>
                        </button>
                    </div>
                    <div id="modalBody" class="modal-body"></div>
                    <div class="modal-footer">
                        <button class="btn-secondary" id="modalCancelBtn">Cancel</button>
                        <button class="btn-primary" id="modalSaveBtn">Save Changes</button>
                    </div>
                </div>
            </div>
        `;

        // Add to modals container or body
        const modalsContainer = document.getElementById('modalsContainer') || document.body;
        modalsContainer.insertAdjacentHTML('beforeend', modalHTML);

        this.modal = document.getElementById('settingsModalV3');

        // Add styles
        this.addModalStyles();

        // Setup modal event listeners
        this.setupModalListeners();
    }

    setupModalListeners() {
        // Modal overlay click to close
        const overlay = document.getElementById('modalOverlay');
        if (overlay) {
            overlay.addEventListener('click', () => this.closeModal());
        }

        // Close button
        const closeBtn = document.getElementById('modalCloseBtn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeModal());
        }

        // Cancel button
        const cancelBtn = document.getElementById('modalCancelBtn');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.closeModal());
        }

        // Save button
        const saveBtn = document.getElementById('modalSaveBtn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveChanges());
        }
    }

    async loadSettings() {
        // Show loading state
        this.showLoadingState();

        try {
            // Load user settings
            const userSettings = await apiClient.getUserSettings();
            this.currentSettings = userSettings;

            // Load available options if not already loaded
            if (Object.keys(this.settingsOptions).length === 0) {
                this.settingsOptions = await apiClient.getSettingsOptions();
            }

            // Display settings
            this.displaySettings();

            // Store in app state
            appState.update('user.settings', userSettings);

        } catch (error) {
            console.error('Error loading settings:', error);
            this.showError('Failed to load settings');
        }
    }

    showLoadingState() {
        this.container.innerHTML = `
            <div class="settings-loading">
                <div class="loading-spinner"></div>
                <p>Loading your preferences...</p>
            </div>
        `;
    }

    displaySettings() {
        const categories = [
            {
                key: 'household_size',
                icon: '👥',
                title: 'Household Size',
                description: 'How many people are you cooking for?',
                getValue: () => this.currentSettings.household_size || '1-2 people'
            },
            {
                key: 'meal_timing',
                icon: '🍴',
                title: 'Meal Preferences',
                description: 'What types of meals do you prefer?',
                getValue: () => {
                    const timing = this.currentSettings.meal_timing;
                    if (Array.isArray(timing)) return timing.join(', ');
                    return timing || 'Dinner';
                }
            },
            {
                key: 'cooking_style',
                icon: '👨‍🍳',
                title: 'Cooking Style',
                description: 'Your preferred cooking methods',
                getValue: () => {
                    const style = this.currentSettings.cooking_style;
                    if (Array.isArray(style) && style.length > 0) {
                        return style.join(', ');
                    }
                    return 'Not set';
                }
            },
            {
                key: 'dietary_restrictions',
                icon: '🥗',
                title: 'Dietary Restrictions',
                description: 'Any dietary needs or allergies',
                getValue: () => {
                    const restrictions = this.currentSettings.dietary_restrictions;
                    if (Array.isArray(restrictions) && restrictions.length > 0) {
                        return restrictions.join(', ');
                    }
                    return 'None';
                }
            },
            {
                key: 'health_goals',
                icon: '💪',
                title: 'Health Goals',
                description: 'What you want to achieve',
                getValue: () => {
                    const goals = this.currentSettings.health_goals;
                    if (Array.isArray(goals) && goals.length > 0) {
                        return goals.join(', ');
                    }
                    return 'Not set';
                }
            }
        ];

        let html = `
            <div class="settings-content">
                <div class="settings-header">
                    <h2>Your Preferences</h2>
                    <p>Tap any category to update your preferences</p>
                </div>
                <div class="settings-categories">
        `;

        categories.forEach(category => {
            html += `
                <div class="setting-card" data-category="${category.key}">
                    <div class="setting-icon">${category.icon}</div>
                    <div class="setting-info">
                        <h3>${category.title}</h3>
                        <p class="setting-description">${category.description}</p>
                        <p class="setting-value">${category.getValue()}</p>
                    </div>
                    <div class="setting-arrow">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="9 18 15 12 9 6"></polyline>
                        </svg>
                    </div>
                </div>
            `;
        });

        html += `
                </div>
                <div class="settings-footer">
                    <div class="account-info">
                        <h3>Account</h3>
                        <p class="account-email">${localStorage.getItem('ftpEmail') || 'Not set'}</p>
                        <p class="account-phone">${this.formatPhone(localStorage.getItem('userPhone'))}</p>
                    </div>
                </div>
            </div>
        `;

        this.container.innerHTML = html;

        // Add styles
        this.addSettingsStyles();

        // Add click listeners to setting cards
        this.attachSettingCardListeners();
    }

    attachSettingCardListeners() {
        const cards = document.querySelectorAll('.setting-card');
        cards.forEach(card => {
            const category = card.dataset.category;
            if (category) {
                card.addEventListener('click', () => this.openEditModal(category));
            }
        });
    }

    openEditModal(category) {
        // CRITICAL: Prevent any default navigation
        event?.preventDefault();
        event?.stopPropagation();

        this.currentEditCategory = category;

        // Update modal title
        const titles = {
            'household_size': 'Household Size',
            'meal_timing': 'Meal Preferences',
            'cooking_style': 'Cooking Style',
            'dietary_restrictions': 'Dietary Restrictions',
            'health_goals': 'Health Goals'
        };

        document.getElementById('modalTitle').textContent = `Edit ${titles[category]}`;

        // Generate modal content based on category
        const modalBody = document.getElementById('modalBody');
        modalBody.innerHTML = this.generateModalContent(category);

        // Show modal with animation
        this.modal.style.display = 'flex';
        requestAnimationFrame(() => {
            this.modal.classList.add('active');
        });

        // Setup checkbox limit enforcement if needed
        this.setupCheckboxLimits();

        // Prevent body scroll
        document.body.style.overflow = 'hidden';
    }

    generateModalContent(category) {
        const options = this.settingsOptions[category] || [];
        const currentValue = this.currentSettings[category];

        let html = '';

        switch (category) {
            case 'household_size':
                html = this.generateRadioOptions(options, currentValue);
                break;

            case 'meal_timing':
                html = this.generateCheckboxOptions(
                    ['Breakfast', 'Lunch', 'Dinner', 'Snacks'],
                    Array.isArray(currentValue) ? currentValue : [currentValue || 'Dinner']
                );
                break;

            case 'cooking_style':
                html = this.generateCheckboxOptions(
                    options.length > 0 ? options : [
                        'Quick & Easy (under 30 min)',
                        'Comfort Food',
                        'International Cuisine',
                        'Healthy & Light',
                        'Gourmet',
                        'One-Pot Meals'
                    ],
                    Array.isArray(currentValue) ? currentValue : []
                );
                break;

            case 'dietary_restrictions':
                html = this.generateCheckboxOptions(
                    options.length > 0 ? options : [
                        'Vegetarian',
                        'Vegan',
                        'Gluten-Free',
                        'Dairy-Free',
                        'Nut-Free',
                        'Low Carb',
                        'Paleo',
                        'Keto'
                    ],
                    Array.isArray(currentValue) ? currentValue : []
                );
                break;

            case 'health_goals':
                html = this.generateCheckboxOptions(
                    options.length > 0 ? options : [
                        'High Protein (30g+ per meal)',
                        'Weight Loss',
                        'Muscle Building',
                        'More Vegetables',
                        'Balanced Nutrition',
                        'Energy Boost'
                    ],
                    Array.isArray(currentValue) ? currentValue : [],
                    2 // Max 2 goals
                );
                break;
        }

        return `<div class="modal-options">${html}</div>`;
    }

    generateRadioOptions(options, currentValue) {
        return options.map(option => `
            <label class="option-label radio-option">
                <input type="radio"
                       name="preference"
                       value="${option}"
                       ${currentValue === option ? 'checked' : ''}>
                <span class="option-text">${option}</span>
            </label>
        `).join('');
    }

    generateCheckboxOptions(options, currentValues, maxSelections = null) {
        const header = maxSelections ? `<p class="selection-hint">Select up to ${maxSelections}</p>` : '';

        return header + options.map(option => `
            <label class="option-label checkbox-option">
                <input type="checkbox"
                       name="preference"
                       value="${option}"
                       ${currentValues.includes(option) ? 'checked' : ''}
                       data-max="${maxSelections || ''}"
                       class="preference-checkbox">
                <span class="option-text">${option}</span>
            </label>
        `).join('');
    }

    setupCheckboxLimits() {
        const checkboxes = document.querySelectorAll('.preference-checkbox[data-max]');
        checkboxes.forEach(checkbox => {
            const max = parseInt(checkbox.dataset.max);
            if (max) {
                checkbox.addEventListener('change', () => {
                    const checked = document.querySelectorAll('.preference-checkbox:checked');
                    if (checked.length > max) {
                        // Uncheck the oldest
                        checked[0].checked = false;
                    }
                });
            }
        });
    }

    enforceMaxSelections(max) {
        const checkboxes = document.querySelectorAll('input[name="preference"]:checked');
        if (checkboxes.length > max) {
            // Uncheck the oldest selection
            checkboxes[0].checked = false;
        }
    }

    closeModal() {
        // CRITICAL: Just close modal, no navigation
        event?.preventDefault();
        event?.stopPropagation();

        this.modal.classList.remove('active');
        setTimeout(() => {
            this.modal.style.display = 'none';
        }, 300);

        // Restore body scroll
        document.body.style.overflow = '';

        this.currentEditCategory = null;
    }

    async saveChanges() {
        // CRITICAL: Save without navigation
        event?.preventDefault();
        event?.stopPropagation();

        if (!this.currentEditCategory) return;

        // Get selected values
        let value;
        const radioInput = document.querySelector('input[name="preference"]:checked');
        const checkboxInputs = document.querySelectorAll('input[name="preference"]:checked');

        if (radioInput) {
            value = radioInput.value;
        } else if (checkboxInputs.length > 0) {
            value = Array.from(checkboxInputs).map(input => input.value);
        } else {
            // No selection made
            this.closeModal();
            return;
        }

        // Show saving state
        const saveButton = event.target;
        const originalText = saveButton.textContent;
        saveButton.textContent = 'Saving...';
        saveButton.disabled = true;

        try {
            // Update via API
            await apiClient.updateUserSettings(this.currentEditCategory, value);

            // Update local state
            this.currentSettings[this.currentEditCategory] = value;

            // Update app state
            appState.update(`user.settings.${this.currentEditCategory}`, value);

            // Refresh display
            this.displaySettings();

            // Close modal
            this.closeModal();

            // Show success feedback
            this.showSuccessFeedback('Preferences updated!');

        } catch (error) {
            console.error('Error saving settings:', error);
            alert('Failed to save changes. Please try again.');
        } finally {
            saveButton.textContent = originalText;
            saveButton.disabled = false;
        }
    }

    showSuccessFeedback(message) {
        const feedback = document.createElement('div');
        feedback.className = 'success-feedback';
        feedback.textContent = message;
        feedback.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #28a745;
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            z-index: 3000;
            animation: slideDown 0.3s ease;
        `;

        document.body.appendChild(feedback);

        setTimeout(() => {
            feedback.style.animation = 'slideUp 0.3s ease';
            setTimeout(() => feedback.remove(), 300);
        }, 2000);
    }

    formatPhone(phone) {
        if (!phone) return 'Not set';
        const cleaned = phone.replace(/\D/g, '');
        if (cleaned.length === 10) {
            return `(${cleaned.slice(0, 3)}) ${cleaned.slice(3, 6)}-${cleaned.slice(6)}`;
        }
        return phone;
    }

    showError(message) {
        this.container.innerHTML = `
            <div class="settings-error">
                <div class="error-icon">⚠️</div>
                <h3>Unable to Load Settings</h3>
                <p>${message}</p>
                <button class="btn-primary" onclick="window.settingsManagerV3.loadSettings()">
                    Try Again
                </button>
            </div>
        `;
    }

    addSettingsStyles() {
        if (!document.getElementById('settings-styles-v3')) {
            const style = document.createElement('style');
            style.id = 'settings-styles-v3';
            style.textContent = `
                .settings-content {
                    padding: 20px 0;
                }

                .settings-header {
                    margin-bottom: 24px;
                }

                .settings-header h2 {
                    font-size: 24px;
                    margin-bottom: 8px;
                }

                .settings-header p {
                    color: #6c757d;
                    font-size: 14px;
                }

                .settings-categories {
                    display: grid;
                    gap: 12px;
                    margin-bottom: 32px;
                }

                .setting-card {
                    background: white;
                    border: 1px solid #e9ecef;
                    border-radius: 12px;
                    padding: 16px;
                    display: flex;
                    align-items: center;
                    gap: 16px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }

                .setting-card:hover {
                    border-color: #007AFF;
                    transform: translateY(-2px);
                    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
                }

                .setting-card:active {
                    transform: translateY(0);
                }

                .setting-icon {
                    font-size: 32px;
                    width: 48px;
                    text-align: center;
                }

                .setting-info {
                    flex: 1;
                }

                .setting-info h3 {
                    font-size: 16px;
                    margin-bottom: 4px;
                    color: #212529;
                }

                .setting-description {
                    font-size: 12px;
                    color: #999;
                    margin-bottom: 4px;
                }

                .setting-value {
                    font-size: 14px;
                    color: #007AFF;
                    font-weight: 500;
                }

                .setting-arrow {
                    color: #999;
                }

                .account-info {
                    background: #f8f9fa;
                    border-radius: 12px;
                    padding: 20px;
                    text-align: center;
                }

                .account-info h3 {
                    font-size: 16px;
                    margin-bottom: 12px;
                }

                .account-email,
                .account-phone {
                    font-size: 14px;
                    color: #6c757d;
                    margin-bottom: 4px;
                }

                .settings-loading {
                    text-align: center;
                    padding: 60px 20px;
                }

                .settings-error {
                    text-align: center;
                    padding: 60px 20px;
                }

                .settings-error .error-icon {
                    font-size: 48px;
                    margin-bottom: 16px;
                }

                .settings-error h3 {
                    font-size: 20px;
                    margin-bottom: 8px;
                }

                .settings-error p {
                    color: #6c757d;
                    margin-bottom: 20px;
                }
            `;
            document.head.appendChild(style);
        }
    }

    addModalStyles() {
        if (!document.getElementById('settings-modal-styles-v3')) {
            const style = document.createElement('style');
            style.id = 'settings-modal-styles-v3';
            style.textContent = `
                .settings-modal {
                    display: none;
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    z-index: 2000;
                    align-items: center;
                    justify-content: center;
                }

                .settings-modal.active .modal-overlay {
                    opacity: 1;
                }

                .settings-modal.active .modal-container {
                    transform: translateY(0);
                    opacity: 1;
                }

                .modal-overlay {
                    position: absolute;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0, 0, 0, 0.5);
                    opacity: 0;
                    transition: opacity 0.3s ease;
                }

                .modal-container {
                    position: relative;
                    background: white;
                    border-radius: 16px;
                    width: 90%;
                    max-width: 500px;
                    max-height: 80vh;
                    overflow: hidden;
                    display: flex;
                    flex-direction: column;
                    transform: translateY(20px);
                    opacity: 0;
                    transition: all 0.3s ease;
                }

                .modal-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 20px;
                    border-bottom: 1px solid #e9ecef;
                }

                .modal-header h2 {
                    font-size: 20px;
                    margin: 0;
                }

                .modal-close-btn {
                    background: none;
                    border: none;
                    cursor: pointer;
                    color: #999;
                    padding: 4px;
                    transition: color 0.2s ease;
                }

                .modal-close-btn:hover {
                    color: #333;
                }

                .modal-body {
                    padding: 20px;
                    overflow-y: auto;
                    flex: 1;
                }

                .modal-footer {
                    display: flex;
                    gap: 12px;
                    padding: 20px;
                    border-top: 1px solid #e9ecef;
                }

                .modal-footer button {
                    flex: 1;
                }

                .modal-options {
                    display: grid;
                    gap: 12px;
                }

                .selection-hint {
                    color: #6c757d;
                    font-size: 14px;
                    margin-bottom: 12px;
                }

                .option-label {
                    display: flex;
                    align-items: center;
                    padding: 12px;
                    background: #f8f9fa;
                    border: 2px solid #e9ecef;
                    border-radius: 8px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                }

                .option-label:hover {
                    background: white;
                    border-color: #007AFF;
                }

                .option-label input {
                    margin-right: 12px;
                    width: 20px;
                    height: 20px;
                    cursor: pointer;
                }

                .option-label input:checked + .option-text {
                    font-weight: 600;
                    color: #007AFF;
                }

                .option-text {
                    flex: 1;
                    font-size: 16px;
                }

                @keyframes slideDown {
                    from {
                        transform: translate(-50%, -100%);
                    }
                    to {
                        transform: translate(-50%, 0);
                    }
                }

                @keyframes slideUp {
                    from {
                        transform: translate(-50%, 0);
                    }
                    to {
                        transform: translate(-50%, -100%);
                    }
                }
            `;
            document.head.appendChild(style);
        }
    }
}

export default SettingsManagerV3;