# Dashboard Refactoring Plan

## Current State Analysis
- **Main File**: dashboard.html (3,546 lines)
- **Functions**: 65 JavaScript functions
- **Major Features**:
  - Cart Analysis & Display
  - Meal Planning Calendar
  - Settings Management
  - User Authentication
  - API Communication
  - State Management

## Proposed Module Structure

### Core HTML Template (dashboard-v3.html) ~200 lines
```
- Basic HTML structure
- Tab containers
- Modal placeholders
- Module script imports
```

### JavaScript Modules

#### 1. Core Module (core.js) ~150 lines
```javascript
// Singleton state manager
export class AppState {
  - User data
  - Cart data
  - Meal plan data
  - Settings cache
  - Event bus for module communication
}

// Utility functions
export const Utils = {
  - formatPhone()
  - formatDate()
  - debounce()
  - localStorage helpers
}
```

#### 2. Navigation Module (navigation.js) ~100 lines
```javascript
export class Navigation {
  - Tab switching (no page refresh!)
  - URL management (history API)
  - Active state management
  - PWA-friendly routing
}
```

#### 3. Cart Module (cart.js) ~500 lines
```javascript
export class CartManager {
  - loadSavedCart()
  - startAnalysis()
  - showCartAnalysis()
  - generateSwapsAndAddons()
  - refreshCartData()
  - displayCartItems()
  - showDeliveryDate()
  - ingredient categorization
}
```

#### 4. Meals Module (meals.js) ~600 lines
```javascript
export class MealsManager {
  - Calendar initialization
  - Drag & drop handling
  - Meal generation API calls
  - Ingredient pool tracking
  - Weekly plan management
  - PDF generation
  - Meal regeneration
}
```

#### 5. Settings Module (settings.js) ~400 lines
```javascript
export class SettingsManager {
  - loadUserSettings()
  - displayCategories()
  - Modal management (no page nav!)
  - Preference updates
  - Account credentials
  - Form validation
  - Save handlers
}
```

#### 6. API Module (api.js) ~200 lines
```javascript
export class APIClient {
  - Centralized error handling
  - Auth management
  - Request interceptors
  - Response caching
  - All API endpoints
}
```

#### 7. UI Components Module (components.js) ~300 lines
```javascript
export const Components = {
  - Loading states
  - Error displays
  - Cards
  - Modals
  - Buttons
  - Progress bars
}
```

### CSS Files

#### 1. Base Styles (base.css) ~200 lines
- Reset & typography
- Colors & variables
- Layout utilities

#### 2. Component Styles (components.css) ~300 lines
- Cards
- Buttons
- Forms
- Modals

#### 3. Module Styles (modules.css) ~200 lines
- Cart-specific
- Meals-specific
- Settings-specific

## Key Improvements

### 1. PWA Navigation Fix
```javascript
// No more page refreshes!
class Navigation {
  switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
      tab.classList.remove('active');
    });

    // Show selected tab
    document.getElementById(`${tabName}Tab`).classList.add('active');

    // Update URL without refresh
    history.pushState({tab: tabName}, '', `#${tabName}`);

    // Emit event for other modules
    AppState.emit('tab-changed', tabName);
  }
}
```

### 2. Module Communication
```javascript
// Event-driven architecture
AppState.on('cart-analyzed', (data) => {
  MealsManager.enableMealGeneration(data);
  SettingsManager.updateRecommendations(data);
});

AppState.on('settings-updated', (settings) => {
  MealsManager.updatePreferences(settings);
  CartManager.recalculateRecommendations(settings);
});
```

### 3. State Management
```javascript
// Single source of truth
class AppState {
  static instance = null;

  constructor() {
    if (AppState.instance) return AppState.instance;

    this.state = {
      user: {},
      cart: {},
      meals: {},
      settings: {}
    };

    this.listeners = {};
    AppState.instance = this;
  }

  update(key, value) {
    this.state[key] = value;
    this.emit(`${key}-updated`, value);
  }
}
```

## Implementation Steps

### Phase 1: Core Infrastructure (2 hours)
1. Create dashboard-v3.html with basic structure
2. Implement Core module with AppState
3. Implement Navigation module with PWA-friendly routing
4. Set up module loader and initialization

### Phase 2: Feature Modules (4 hours)
1. Port Cart functionality to cart.js
2. Port Meals functionality to meals.js
3. Port Settings to settings.js (fix PWA issues!)
4. Create API client module

### Phase 3: Testing & Polish (2 hours)
1. Test all tab transitions (no refreshes!)
2. Verify all 65 functions work
3. Test on mobile PWA
4. Performance optimization

## Benefits

1. **Maintainability**: 7 modules @ ~400 lines each vs 1 file @ 3546 lines
2. **PWA Fixed**: No page refreshes, smooth navigation
3. **Testability**: Each module can be tested independently
4. **Reusability**: Modules can be used in other pages
5. **Performance**: Lazy loading, better caching
6. **Developer Experience**: Clear separation of concerns

## Migration Strategy

1. Keep dashboard.html as backup
2. Create dashboard-v3.html alongside
3. Test thoroughly in development
4. A/B test with select users
5. Full rollout when stable

## Success Metrics

- [ ] No page refreshes when switching tabs
- [ ] All 65 functions preserved
- [ ] Page load < 2 seconds
- [ ] Code coverage > 80%
- [ ] Zero console errors
- [ ] PWA score > 95