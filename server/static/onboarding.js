/**
 * Farm to People Onboarding Flow
 * Research-backed preference collection with optimized conversion
 * 
 * FLOW STRUCTURE:
 * Step 1: Household size + meal timing (consolidated for faster completion)
 * Step 2: Meal preferences - Pick 3 of 8 concrete dishes (high-signal)
 * Step 3: Cooking styles - Pick 2+ of 8 methods (optional)
 * Step 4: Dietary restrictions - Multiple selection allowed
 * Step 5: Goals - Pick up to 2 outcome preferences
 * 
 * KEY FEATURES:
 * - <2 minute completion time
 * - Progressive disclosure (70/30 familiar/adventurous ratio)
 * - 20-30 preference signals from 6 selections
 * - Mobile-optimized 2x3 grid layouts
 * - Clear selection states with visual feedback
 * - Skip options on optional steps to reduce friction
 * - Immediate validation and progress indicators
 * 
 * DATA COLLECTION:
 * - Reveals: Direct preferences from meal choices (e.g., chicken, roast)
 * - Signals: Indirect preferences from cooking styles (e.g., time_fast)
 * - Goals: Outcome preferences for ML ranking (e.g., quick-dinners)
 */

/**
 * FARM_BOX_MEALS - Core preference discovery data structure
 * Each meal/style contains specific signals for personalization
 */
const FARM_BOX_MEALS = {
    // Screen 1: Concrete dinner meals (pick 3 of 8)
    // Each meal has 5-6 'reveals' indicating specific preferences
    screen1: [
        {
            id: 'lemon-herb-roast-chicken',
            name: 'Lemon Herb Roast Chicken',
            image: 'https://images.pexels.com/photos/16510619/pexels-photo-16510619.jpeg?auto=compress&cs=tinysrgb&w=640&h=640&fit=crop&crop=center&q=80', // Top view roasted chicken in pan with fresh vegetables
            reveals: ['chicken', 'roast', 'comfort', 'family', '30_45m', 'dinner']
        },
        {
            id: '15-minute-chicken-stir-fry',
            name: '15-Minute Chicken Stir-Fry',
            image: 'https://images.pexels.com/photos/15735597/pexels-photo-15735597.jpeg?auto=compress&cs=tinysrgb&w=640&h=640&fit=crop', // Chicken stir fry in pan with vegetables
            reveals: ['chicken', 'quick', 'stir_fry', 'asian', 'veg_forward', 'weeknight']
        },
        {
            id: 'grilled-salmon-greens',
            name: 'Grilled Salmon with Greens',
            image: 'https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=640&h=640&fit=crop', // Grilled salmon with asparagus
            reveals: ['seafood', 'healthy', 'grill_pan', 'quick', 'low_carb']
        },
        {
            id: 'mediterranean-chickpea-bowl',
            name: 'Mediterranean Chickpea Bowl',
            image: 'https://images.pexels.com/photos/8286751/pexels-photo-8286751.jpeg?auto=compress&cs=tinysrgb&w=640&h=640&fit=crop', // Mediterranean bowl with chickpeas and vegetables
            reveals: ['vegetarian', 'mediterranean', 'grain_bowl', 'fresh', 'fiber']
        },
        {
            id: 'turkey-meatballs-farro',
            name: 'Turkey Meatballs with Farro',
            image: 'https://images.pexels.com/photos/5863621/pexels-photo-5863621.jpeg?auto=compress&cs=tinysrgb&w=640&h=640&fit=crop&crop=center&q=80', // Turkey meatballs with white rice and grain
            reveals: ['turkey', 'balanced', 'meal_prep_friendly', 'oven', 'high_protein']
        },
        {
            id: 'beef-tacos-skillet',
            name: 'Beef Tacos (Skillet)',
            image: 'https://images.unsplash.com/photo-1599974579688-8dbdd335c77f?w=640&h=640&fit=crop', // Fresh beef tacos plated
            reveals: ['beef', 'tex_mex', 'handhelds', 'skillet', 'weeknight']
        },
        {
            id: 'veggie-pesto-pasta',
            name: 'Veggie Pesto Pasta',
            image: 'https://images.pexels.com/photos/1435896/pexels-photo-1435896.jpeg?auto=compress&cs=tinysrgb&w=640&h=640&fit=crop', // Flat pasta with green pesto sauce and cherry tomatoes
            reveals: ['vegetarian', 'pasta', 'comfort', 'italian', '20_30m']
        },
        {
            id: 'seasonal-vegetable-soup',
            name: 'Seasonal Vegetable Soup',
            image: 'https://images.unsplash.com/photo-1547592166-23ac45744acd?w=640&h=640&fit=crop', // Colorful vegetable soup in bowl
            reveals: ['veg_forward', 'soup_stew', 'batch_cook', 'freezer_friendly']
        }
    ],
    
    // Screen 2: Cooking style preferences (pick 2+ of 8, optional)
    // Each style has 1-3 'signals' about cooking methods
    screen2: [
        {
            id: '15-20-minute-meals',
            name: '15–20 Minute Meals',
            image: 'https://images.pexels.com/photos/3872385/pexels-photo-3872385.jpeg?auto=compress&cs=tinysrgb&w=640&h=640&fit=crop', // Quick flatbread with sliced tomatoes
            signals: ['time_fast']
        },
        {
            id: 'one-pan-sheet-pan',
            name: 'One-Pan or Sheet-Pan',
            image: 'https://images.pexels.com/photos/17910326/pexels-photo-17910326.jpeg?auto=compress&cs=tinysrgb&w=640&h=640&fit=crop', // One-pan dish with rice and vegetables
            signals: ['one_pan', 'easy_cleanup', 'oven']
        },
        {
            id: 'meal-prep-week',
            name: 'Meal Prep for the Week',
            image: 'https://images.pexels.com/photos/30635719/pexels-photo-30635719.jpeg?auto=compress&cs=tinysrgb&w=640&h=640&fit=crop', // Stack of healthy meal prep containers
            signals: ['batch_cook', 'portions_4plus']
        },
        {
            id: 'stir-fry-skillet',
            name: 'Stir-Fry or Skillet',
            image: 'https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=640&h=640&fit=crop', // Wok stir fry toss vegetables with visible wok
            signals: ['stovetop_fast', 'asian_lean']
        },
        {
            id: 'salads-grain-bowls',
            name: 'Salads and Grain Bowls',
            image: 'https://images.pexels.com/photos/1213710/pexels-photo-1213710.jpeg?auto=compress&cs=tinysrgb&w=640&h=640&fit=crop', // Vegetable salad bowl
            signals: ['bowls', 'fresh']
        },
        {
            id: 'soups-stews',
            name: 'Soups and Stews',
            image: 'https://images.pexels.com/photos/1703272/pexels-photo-1703272.jpeg?auto=compress&cs=tinysrgb&w=640&h=640&fit=crop', // Bowl of soup with spoons
            signals: ['cozy', 'make_ahead', 'freezer']
        },
        {
            id: 'tacos-wraps',
            name: 'Tacos and Wraps',
            image: 'https://images.pexels.com/photos/14077456/pexels-photo-14077456.jpeg?auto=compress&cs=tinysrgb&w=640&h=640&fit=crop', // Wrap on wood tray
            signals: ['handhelds', 'family_friendly']
        },
        {
            id: 'grill-roast',
            name: 'Grill or Roast',
            image: 'https://images.pexels.com/photos/2233729/pexels-photo-2233729.jpeg?auto=compress&cs=tinysrgb&w=640&h=640&fit=crop', // Grilled meats on skewers
            signals: ['dry_heat', 'dinner_focus']
        }
    ]
};

/**
 * OnboardingFlow - Main controller for preference collection
 * Manages state, validation, navigation, and API submission
 */
class OnboardingFlow {
    constructor() {
        this.currentStep = 1;
        this.totalSteps = 7;
        this.existingUser = false;
        this.data = {
            householdSize: null,
            mealTiming: [],  // New field for breakfast/lunch/dinner/snacks
            selectedMeals: [],
            dietaryRestrictions: [],
            goals: [],
            ftpEmail: null,
            ftpPassword: null,
            phoneNumber: null  // Optional for SMS features
        };
        
        this.init();
    }

    /**
     * Initialize the onboarding flow
     * Sets up all event listeners and populates meal grids
     */
    init() {
        this.setupEventListeners();
        this.populateMealGrids();
        this.updateProgress();
        this.updateStepContent(); // Ensure correct step 1 content is shown
    }

    setupEventListeners() {
        // Household size selection
        document.querySelectorAll('.size-option').forEach(option => {
            option.addEventListener('click', (e) => this.selectHouseholdSize(e));
        });

        // Meal timing selection (new)
        document.querySelectorAll('.timing-option').forEach(option => {
            option.addEventListener('click', (e) => this.toggleMealTiming(e));
        });

        // Meal tile selections
        document.addEventListener('click', (e) => {
            if (e.target.closest('.meal-tile')) {
                this.toggleMealSelection(e.target.closest('.meal-tile'));
            }
        });

        // Dietary restrictions
        document.querySelectorAll('.restriction-option:not(.goal-option)').forEach(option => {
            option.addEventListener('click', (e) => this.toggleRestriction(e));
        });
        
        // Goals (Step 5)
        document.querySelectorAll('.goal-option').forEach(option => {
            option.addEventListener('click', (e) => this.toggleGoal(e));
        });

        // Navigation buttons
        this.setupNavigationButtons();

        // Skip links
        this.setupSkipLinks();
    }

    setupNavigationButtons() {
        // Step 1 - Phone number
        const step1Button = document.getElementById('step1Next');
        if (step1Button) {
            step1Button.addEventListener('click', () => {
                console.log('Step 1 button clicked - calling checkExistingUser');
                this.checkExistingUser();
            });
        } else {
            console.error('Step1Next button not found!');
        }
        
        // Step 2 - Household
        document.getElementById('step2Back').addEventListener('click', () => this.prevStep());
        document.getElementById('step2Next').addEventListener('click', () => this.nextStep());
        
        // Step 3 - Meals 1
        document.getElementById('step3Back').addEventListener('click', () => this.prevStep());
        document.getElementById('step3Next').addEventListener('click', () => this.nextStep());
        
        // Step 4 - Meals 2
        document.getElementById('step4Back').addEventListener('click', () => this.prevStep());
        document.getElementById('step4Next').addEventListener('click', () => this.nextStep());
        
        // Step 5 - Dietary
        document.getElementById('step5Back').addEventListener('click', () => this.prevStep());
        document.getElementById('step5Next')?.addEventListener('click', () => this.nextStep());
        
        // Step 6 - Goals
        document.getElementById('step6Back').addEventListener('click', () => this.prevStep());
        document.getElementById('step6Next')?.addEventListener('click', () => this.nextStep());
        
        // Step 7 - FTP Account
        document.getElementById('step7Back')?.addEventListener('click', () => this.prevStep());
        document.getElementById('completeOnboarding').addEventListener('click', () => this.completeOnboarding());
        
        // FTP account form validation
        document.getElementById('ftpEmail')?.addEventListener('input', () => this.validateStep7());
        document.getElementById('ftpPassword')?.addEventListener('input', () => this.validateStep7());
        document.getElementById('phoneNumber')?.addEventListener('input', () => this.validateStep7());
    }

    setupSkipLinks() {
        document.getElementById('skipMeals1')?.addEventListener('click', () => this.nextStep());
        document.getElementById('skipMeals2')?.addEventListener('click', () => this.nextStep());
        document.getElementById('skipRestrictions')?.addEventListener('click', () => this.nextStep());
        document.getElementById('skipGoals')?.addEventListener('click', () => this.nextStep());
    }

    populateMealGrids() {
        // Populate first meal grid (core preferences)
        const grid1 = document.getElementById('mealGrid1');
        FARM_BOX_MEALS.screen1.forEach(meal => {
            const tile = this.createMealTile(meal);
            grid1.appendChild(tile);
        });

        // Populate second meal grid (cooking style refinement)
        const grid2 = document.getElementById('mealGrid2');
        FARM_BOX_MEALS.screen2.forEach(meal => {
            const tile = this.createMealTile(meal);
            grid2.appendChild(tile);
        });
    }

    createMealTile(meal) {
        const tile = document.createElement('div');
        tile.className = 'meal-tile';
        tile.dataset.mealId = meal.id;
        
        tile.innerHTML = `
            <div class="meal-image" style="background-image: url('${meal.image}')"></div>
            <div class="meal-name">${meal.name}</div>
        `;
        
        return tile;
    }

    selectHouseholdSize(event) {
        // Clear previous selection
        document.querySelectorAll('.size-option').forEach(opt => {
            opt.classList.remove('selected');
        });
        
        // Select new option
        event.currentTarget.classList.add('selected');
        this.data.householdSize = event.currentTarget.dataset.size;
        
        // Check if both questions are answered
        this.validateStep1();
    }
    
    toggleMealTiming(event) {
        const option = event.currentTarget;
        const meal = option.dataset.meal;
        
        if (option.classList.contains('selected')) {
            // Deselect
            option.classList.remove('selected');
            this.data.mealTiming = this.data.mealTiming.filter(m => m !== meal);
        } else {
            // Select
            option.classList.add('selected');
            this.data.mealTiming.push(meal);
        }
        
        // Check if both questions are answered
        this.validateStep1();
    }
    
    /**
     * Validate Step 1 requirements
     * Requires both household size AND at least one meal timing
     */
    validateStep1() {
        const isValid = this.data.householdSize && this.data.mealTiming.length > 0;
        document.getElementById('step1Next').disabled = !isValid;
    }

    toggleMealSelection(tile) {
        const mealId = tile.dataset.mealId;
        const isSelected = tile.classList.contains('selected');
        
        if (isSelected) {
            // Deselect
            tile.classList.remove('selected');
            this.data.selectedMeals = this.data.selectedMeals.filter(id => id !== mealId);
        } else {
            // Select
            tile.classList.add('selected');
            this.data.selectedMeals.push(mealId);
        }
        
        this.updateMealSelectionUI();
    }

    /**
     * Update meal selection UI with counters and validation
     * Step 2: Requires exactly 3 selections
     * Step 3: Optional, allows any number
     */
    updateMealSelectionUI() {
        const selectedCount = this.data.selectedMeals.length;
        
        // Update counter for step 2
        if (this.currentStep === 3) {
            const counter = document.getElementById('selectionCounter1');
            const nextBtn = document.getElementById('step2Next');
            
            if (selectedCount === 0) {
                counter.textContent = 'Pick at least 3 meals that sound delicious';
                nextBtn.disabled = true;
            } else if (selectedCount < 3) {
                counter.textContent = `${selectedCount} of 3 selected`;
                nextBtn.disabled = true;
            } else {
                counter.textContent = `${selectedCount} meals selected. Great choices!`;
                nextBtn.disabled = false;
            }
        }
        
        // Update counter for step 4 - cooking styles (optional)
        if (this.currentStep === 4) {
            const counter = document.getElementById('selectionCounter2');
            const nextBtn = document.getElementById('step4Next');
            const styleCount = document.querySelectorAll('#mealGrid2 .meal-tile.selected').length;
            
            // Step 3 is optional - always allow proceeding
            nextBtn.disabled = false;
            
            if (styleCount === 0) {
                counter.textContent = 'Select 2 or more cooking styles (optional)';
            } else if (styleCount === 1) {
                counter.textContent = `${styleCount} style selected. Add more if you'd like!`;
            } else {
                counter.textContent = `${styleCount} cooking styles selected. Great!`;
            }
        }
    }

    toggleRestriction(event) {
        const option = event.currentTarget;
        const isSelected = option.classList.contains('selected');
        const restriction = option.dataset.restriction;
        
        if (isSelected) {
            option.classList.remove('selected');
            this.data.dietaryRestrictions = this.data.dietaryRestrictions.filter(r => r !== restriction);
        } else {
            option.classList.add('selected');
            // Handle "no restrictions" special case
            if (restriction === 'none') {
                // Clear all other restrictions
                document.querySelectorAll('.restriction-option[data-restriction]:not(.goal-option)').forEach(opt => {
                    if (opt.dataset.restriction !== 'none') {
                        opt.classList.remove('selected');
                    }
                });
                this.data.dietaryRestrictions = ['none'];
            } else {
                // Remove "no restrictions" if selecting specific restriction
                document.querySelector('.restriction-option[data-restriction="none"]')?.classList.remove('selected');
                this.data.dietaryRestrictions = this.data.dietaryRestrictions.filter(r => r !== 'none');
                this.data.dietaryRestrictions.push(restriction);
            }
        }
    }
    
    toggleGoal(event) {
        const option = event.currentTarget;
        const isSelected = option.classList.contains('selected');
        const goal = option.dataset.goal;
        
        if (isSelected) {
            // Deselect
            option.classList.remove('selected');
            this.data.goals = this.data.goals.filter(g => g !== goal);
        } else {
            // Check if we already have 2 selected
            const selectedGoals = document.querySelectorAll('.goal-option.selected');
            if (selectedGoals.length >= 2) {
                // Show hint that max is 2
                const hint = document.querySelector('#step5 .selection-hint');
                if (hint) {
                    hint.style.color = '#dc3545';
                    hint.textContent = 'Maximum 2 goals - deselect one first';
                    setTimeout(() => {
                        hint.style.color = '#6c757d';
                        hint.textContent = 'Select up to 2 goals that matter most to you';
                    }, 2000);
                }
                return;
            }
            
            // Select
            option.classList.add('selected');
            this.data.goals.push(goal);
        }
    }

    nextStep() {
        if (this.currentStep < this.totalSteps) {
            this.showStep(this.currentStep + 1);
        }
    }

    prevStep() {
        if (this.currentStep > 1) {
            this.showStep(this.currentStep - 1);
        }
    }

    showStep(stepNumber) {
        // Hide current step
        document.getElementById(`step${this.currentStep}`).classList.remove('active');
        
        // Show new step
        this.currentStep = stepNumber;
        document.getElementById(`step${this.currentStep}`).classList.add('active');
        
        // Update UI
        this.updateProgress();
        this.updateStepContent();
        
        // Reset meal selection UI if on meal steps
        if (this.currentStep === 3 || this.currentStep === 4) {
            this.updateMealSelectionUI();
        }
    }

    updateProgress() {
        const progressPercent = (this.currentStep / this.totalSteps) * 100;
        document.getElementById('progressBar').style.width = `${progressPercent}%`;
        document.getElementById('stepIndicator').textContent = `Step ${this.currentStep} of ${this.totalSteps}`;
    }

    updateStepContent() {
        const titles = {
            1: 'Let\'s get started',
            2: 'Household & Meal Planning', 
            3: 'What meals excite you?',
            4: 'How do you like to cook?',
            5: 'Dietary preferences & needs',
            6: 'What are your goals?',
            7: 'Connect your Farm to People account'
        };
        
        const subtitles = {
            1: 'Enter your phone number to check for existing preferences or start fresh.',
            2: 'Tell us about your household size and which meals you need help with.',
            3: 'Pick at least 3 meals that sound delicious. We\'ll learn your preferences from these choices.',
            4: 'Select 2 or more cooking styles (optional). This helps us understand how you like to cook.',
            5: 'Select any dietary preferences or restrictions to help us personalize your meal plans.',
            6: 'Tell us what you\'re hoping to achieve with your farm box meals.',
            7: 'Enter your Farm to People login to analyze your cart and get personalized meal plans.'
        };
        
        document.getElementById('stepTitle').textContent = titles[this.currentStep];
        document.getElementById('stepSubtitle').textContent = subtitles[this.currentStep];
    }

    /**
     * Validate Step 6 - FTP Account credentials
     * Requires email and password to proceed
     */
    validateStep7() {
        const email = document.getElementById('ftpEmail')?.value;
        const password = document.getElementById('ftpPassword')?.value;
        const isValid = email && email.includes('@') && password && password.length >= 1;
        
        document.getElementById('completeOnboarding').disabled = !isValid;
        
        // Store values in data
        if (email) this.data.ftpEmail = email;
        if (password) this.data.ftpPassword = password;
        
        const phone = document.getElementById('phoneNumber')?.value;
        if (phone) this.data.phoneNumber = phone;
    }
    
    /**\n     * Check if user already exists in database with preferences\n     * If existing user found, skip preference collection steps\n     */\n    async checkExistingUser() {\n        console.log('checkExistingUser called!');\n        const phoneInput = document.getElementById('phoneNumberStep1');\n        console.log('Phone input element:', phoneInput);\n        const phone = phoneInput.value.replace(/[^\\d]/g, '');\n        console.log('Phone number:', phone);\n        \n        // Validate phone number format\n        if (!phone || phone.length < 10) {\n            alert('Please enter a valid phone number');\n            return;\n        }\n        \n        try {\n            // Look up user by phone number\n            const response = await fetch(`/api/settings/${phone}`);\n            if (response.ok) {\n                const userData = await response.json();\n                \n                // Check if user has existing preferences\n                if (userData.preferences && Object.keys(userData.preferences).length > 0) {\n                    // Existing user - skip to FTP credentials step\n                    console.log('Existing user found, skipping preference collection');\n                    this.existingUser = true;\n                    this.data.phoneNumber = phone;\n                    this.showWelcomeBack(userData);\n                    this.showStep(7); // Jump directly to FTP account setup\n                    return;\n                }\n            }\n            \n            // New user or no preferences - continue with full onboarding\n            console.log('New user or no preferences, starting full onboarding');\n            this.data.phoneNumber = phone;\n            this.nextStep(); // Go to step 2 (household)\n            \n        } catch (error) {\n            // API error or user not found - treat as new user\n            console.log('User lookup failed, treating as new user:', error);\n            this.data.phoneNumber = phone;\n            this.nextStep();\n        }\n    }\n    \n    /**\n     * Show welcome back message for returning users\n     * Temporarily updates UI to indicate user recognition\n     */\n    showWelcomeBack(userData) {\n        const subtitle = document.getElementById('stepSubtitle');\n        const originalText = subtitle.textContent;\n        \n        // Show welcome message in green\n        subtitle.textContent = `Welcome back! We found your preferences. Just verify your Farm to People account.`;\n        subtitle.style.color = '#28a745';\n        \n        // Reset to original after 3 seconds\n        setTimeout(() => {\n            subtitle.textContent = originalText;\n            subtitle.style.color = '#6c757d';\n        }, 3000);\n    }\n\n    /**\n     * Complete the onboarding process and save user data\n     */\n    async completeOnboarding() {
        // Validate and capture final form data
        this.validateStep7();
        
        // Show loading state
        const btn = document.getElementById('completeOnboarding');
        const originalText = btn.textContent;
        btn.textContent = 'Saving preferences...';
        btn.disabled = true;
        
        try {
            // Send data to backend with meal timing included
            const response = await fetch('/api/onboarding', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    householdSize: this.data.householdSize,
                    mealTiming: this.data.mealTiming,
                    selectedMeals: this.data.selectedMeals,
                    dietaryRestrictions: this.data.dietaryRestrictions,
                    goals: this.data.goals,
                    ftpEmail: this.data.ftpEmail,
                    ftpPassword: this.data.ftpPassword,
                    phoneNumber: this.data.phoneNumber
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                // Success! Show confirmation based on account type
                this.showCompletionMessage(result);
            } else {
                throw new Error('Failed to save preferences');
            }
        } catch (error) {
            console.error('Onboarding error:', error);
            alert('Sorry, there was an error saving your preferences. Please try again.');
            btn.textContent = originalText;
            btn.disabled = false;
        }
    }

    showCompletionMessage(result = {}) {
        // Save credentials to localStorage for dashboard
        if (this.data.ftpEmail && this.data.ftpPassword) {
            localStorage.setItem('ftpEmail', this.data.ftpEmail);
            localStorage.setItem('ftpPassword', this.data.ftpPassword);
        }
        
        // Different messages based on account completeness
        const vonageNumber = '(833) 439-1183';  // Always show Vonage number for texting
        const isComplete = result.account_type === 'complete';
        
        const message = isComplete ? 
            `<p style="color: #6c757d; margin-bottom: 24px; line-height: 1.5;">
                Perfect! Your account is all set up. We can now analyze your Farm to People cart 
                and create personalized meal plans based on your preferences.
            </p>
            <p style="color: #28a745; margin-bottom: 32px; font-size: 16px; font-weight: 500;">
                ✅ Redirecting to your dashboard...
            </p>` :
            `<p style="color: #6c757d; margin-bottom: 24px; line-height: 1.5;">
                Your preferences have been saved. We'll use this information to create 
                personalized meal plans that match your tastes and dietary needs.
            </p>
            <p style="color: #6c757d; margin-bottom: 32px; font-size: 14px;">
                Text <strong>"PLAN"</strong> to <strong>(833) 439-1183</strong> anytime to get a 
                personalized meal plan based on your current Farm to People cart.
            </p>`;
        
        // Replace step content with success message
        document.querySelector('.content').innerHTML = `
            <div style="text-align: center; padding: 40px 20px;">
                <div style="font-size: 48px; margin-bottom: 16px;">🎉</div>
                <h2 style="color: #28a745; margin-bottom: 16px;">${isComplete ? 'Account Created!' : 'All set!'}</h2>
                ${message}
                <div style="background: #f8f9fa; border-radius: 12px; padding: 16px; font-size: 14px; color: #495057;">
                    💡 <strong>Tip:</strong> Your preferences will improve over time as we learn from your choices and feedback.
                </div>
            </div>
        `;
        
        // Update progress to 100%
        document.getElementById('progressBar').style.width = '100%';
        document.getElementById('stepIndicator').textContent = 'Complete!';
        
        // Redirect to dashboard after 2 seconds if complete
        if (isComplete) {
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 2000);
        }
    }
}

// Initialize onboarding when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new OnboardingFlow();
});

/**
 * Analytics tracking for conversion optimization
 * Track key metrics for A/B testing and improvement
 */
function trackOnboardingEvent(event, data = {}) {
    // This would integrate with your analytics platform
    console.log('Onboarding Event:', event, data);
    
    // Example events to track:
    // - step_started: {step: 2}
    // - step_completed: {step: 2, duration_seconds: 45}
    // - meal_selected: {meal_id: 'roasted-chicken-vegetables', step: 2}
    // - onboarding_abandoned: {last_step: 3, duration_seconds: 120}
    // - onboarding_completed: {total_duration_seconds: 180, meals_selected: 5}
}