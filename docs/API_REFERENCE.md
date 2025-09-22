# 📚 API Reference Documentation

**Date:** September 4, 2025  
**Scope:** Complete API endpoint documentation  
**Base URL:** https://farmtopeople-production.up.railway.app  
**Version:** 1.0.0

---

## 🎯 API Overview

The Farm to People AI Assistant API provides endpoints for meal planning, cart analysis, user management, and SMS integration. All endpoints return JSON responses and use standard HTTP status codes.

### **Authentication**
Most endpoints require phone number-based authentication. Some endpoints require API key authentication for external integrations.

### **Rate Limiting**
- **SMS Endpoints:** 10 requests per minute per phone number
- **API Endpoints:** 100 requests per hour per API key
- **Web Endpoints:** 1000 requests per hour per IP

### **Error Handling**
All errors return JSON responses with the following structure:
```json
{
  "error": "Error message",
  "code": "ERROR_CODE",
  "details": "Additional error details"
}
```

---

## 📱 SMS Endpoints

### **POST /sms/incoming**
Handles incoming SMS messages from Vonage webhook.

**Request:**
```json
{
  "api-key": "webhook-key",
  "messageId": "uuid",
  "text": "user message",
  "to": "18334391183",
  "type": "text",
  "msisdn": "user-phone-number",
  "keyword": "MESSAGE_KEYWORD",
  "message-timestamp": "2025-09-04 12:00:00"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "SMS processed successfully"
}
```

**Status Codes:**
- `200` - Success
- `400` - Invalid request
- `500` - Server error

---

## 🛒 Cart Analysis Endpoints

### **GET /api/get-saved-cart**
Retrieves saved cart data for a user.

**Query Parameters:**
- `phone` (required): User's phone number in E.164 format

**Response:**
```json
{
  "status": "success",
  "cart_data": {
    "individual_items": [
      {
        "name": "Organic Avocados",
        "quantity": 5,
        "unit": "1 piece",
        "price": "$8.00",
        "type": "individual"
      }
    ],
    "customizable_boxes": [
      {
        "box_name": "The Cook's Box - Paleo",
        "selected_items": [...],
        "available_alternatives": [...],
        "selected_count": 9,
        "alternatives_count": 10
      }
    ],
    "non_customizable_boxes": [...]
  },
  "last_updated": "2025-09-04T12:00:00Z"
}
```

**Status Codes:**
- `200` - Success
- `404` - Cart not found
- `400` - Invalid phone number

### **POST /api/analyze-cart**
Triggers cart scraping and analysis.

**Request:**
```json
{
  "phone": "+12125551234",
  "force_refresh": false
}
```

**Response:**
```json
{
  "status": "success",
  "analysis": {
    "overview": "Cart analysis summary...",
    "swaps": [
      {
        "priority": 1,
        "box_name": "The Cook's Box - Paleo",
        "swap_out": "Black Sea Bass",
        "swap_in": "White Ground Turkey",
        "reasoning": "More versatile protein for multiple meals"
      }
    ],
    "meals": [
      {
        "title": "Pan-Seared Salmon with Roasted Vegetables",
        "servings": 2,
        "time": "25 min",
        "protein": "38g",
        "ingredients": ["Wild Salmon", "Brussels Sprouts", "Sweet Potatoes"],
        "status": "complete"
      }
    ],
    "additions": {
      "proteins": ["White Ground Turkey - $9.99"],
      "fresh_items": ["Garlic - $2.99", "2 Lemons - $1.99"],
      "pantry_staples": ["Olive Oil", "Salt", "Black Pepper"]
    }
  },
  "processing_time": "15.2s"
}
```

**Status Codes:**
- `200` - Success
- `400` - Invalid request
- `500` - Analysis failed

### **POST /api/refresh-meals**
Generates new meal suggestions based on cart data.

**Request:**
```json
{
  "phone": "+12125551234",
  "preferences": {
    "household_size": 2,
    "dietary_restrictions": ["vegetarian"],
    "health_goals": ["high-protein"],
    "cooking_style": ["quick-meals"],
    "cuisine_preferences": ["mediterranean"]
  }
}
```

**Response:**
```json
{
  "status": "success",
  "meals": [
    {
      "title": "Mediterranean Chickpea Bowl",
      "servings": 2,
      "time": "20 min",
      "protein": "28g",
      "ingredients": ["Chickpeas", "Cherry Tomatoes", "Cucumber", "Feta"],
      "difficulty": "easy",
      "cuisine": "mediterranean"
    }
  ],
  "total_servings": 10,
  "estimated_cost": "$45.00"
}
```

**Status Codes:**
- `200` - Success
- `400` - Invalid request
- `404` - User not found

---

## 👤 User Management Endpoints

### **GET /api/settings/{phone}**
Retrieves user preferences and settings.

**Path Parameters:**
- `phone`: User's phone number in E.164 format

**Response:**
```json
{
  "status": "success",
  "user": {
    "phone": "+12125551234",
    "email": "user@example.com",
    "preferences": {
      "household_size": 2,
      "dietary_restrictions": ["vegetarian"],
      "health_goals": ["high-protein"],
      "cooking_style": ["quick-meals"],
      "cuisine_preferences": ["mediterranean"],
      "cooking_skill_level": "intermediate"
    },
    "created_at": "2025-09-01T10:00:00Z",
    "last_active": "2025-09-04T12:00:00Z"
    }
}
```

**Status Codes:**
- `200` - Success
- `404` - User not found

### **POST /api/settings/{phone}/update**
Updates user preferences.

**Request:**
```json
{
  "preferences": {
    "household_size": 3,
    "dietary_restrictions": ["vegetarian", "gluten-free"],
    "health_goals": ["high-protein", "low-carb"],
    "cooking_style": ["batch-cooking"],
    "cuisine_preferences": ["mediterranean", "asian"],
    "cooking_skill_level": "advanced"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Preferences updated successfully",
  "updated_preferences": {
    "household_size": 3,
    "dietary_restrictions": ["vegetarian", "gluten-free"],
    "health_goals": ["high-protein", "low-carb"],
    "cooking_style": ["batch-cooking"],
    "cuisine_preferences": ["mediterranean", "asian"],
    "cooking_skill_level": "advanced"
  }
}
```

**Status Codes:**
- `200` - Success
- `400` - Invalid preferences
- `404` - User not found

### **GET /api/settings/options**
Retrieves available preference options.

**Response:**
```json
{
  "status": "success",
  "options": {
    "dietary_restrictions": [
      "vegetarian",
      "vegan",
      "gluten-free",
      "dairy-free",
      "nut-free",
      "no-pork",
      "no-beef"
    ],
    "health_goals": [
      "high-protein",
      "low-carb",
      "balanced",
      "weight-loss",
      "muscle-gain",
      "quick-meals"
    ],
    "cooking_style": [
      "quick-meals",
      "batch-cooking",
      "meal-prep",
      "from-scratch",
      "minimal-cooking"
    ],
    "cuisine_preferences": [
      "mediterranean",
      "asian",
      "mexican",
      "italian",
      "american",
      "indian",
      "comfort-food"
    ],
    "cooking_skill_levels": [
      "beginner",
      "intermediate",
      "advanced"
    ]
  }
}
```

**Status Codes:**
- `200` - Success

---

## 🍽️ Meal Planning Endpoints

### **GET /meal-plan/{analysis_id}**
Retrieves a specific meal plan analysis.

**Path Parameters:**
- `analysis_id`: Unique identifier for the meal plan

**Response:**
```json
{
  "status": "success",
  "analysis_id": "abc123",
  "created_at": "2025-09-04T12:00:00Z",
  "phone": "+12125551234",
  "analysis": {
    "overview": "Your cart analysis...",
    "swaps": [...],
    "meals": [...],
    "additions": {...}
  }
}
```

**Status Codes:**
- `200` - Success
- `404` - Analysis not found

### **POST /api/generate-meals**
Generates meal suggestions based on cart and preferences.

**Request:**
```json
{
  "phone": "+12125551234",
  "cart_data": {
    "individual_items": [...],
    "customizable_boxes": [...]
  },
  "preferences": {
    "household_size": 2,
    "dietary_restrictions": ["vegetarian"],
    "health_goals": ["high-protein"]
  }
}
```

**Response:**
```json
{
  "status": "success",
  "meals": [
    {
      "title": "Vegetarian Protein Bowl",
      "servings": 2,
      "time": "25 min",
      "protein": "32g",
      "ingredients": ["Quinoa", "Chickpeas", "Spinach", "Avocado"],
      "instructions": [
        "Cook quinoa according to package directions",
        "Sauté chickpeas with spices",
        "Combine with fresh vegetables",
        "Top with avocado and dressing"
      ],
      "nutrition": {
        "calories": 450,
        "protein": 32,
        "carbs": 45,
        "fat": 18
      }
    }
  ],
  "total_servings": 8,
  "estimated_cost": "$35.00"
}
```

**Status Codes:**
- `200` - Success
- `400` - Invalid request
- `500` - Generation failed

---

## 📄 PDF Generation Endpoints

### **GET /pdfs/{filename}**
Serves generated PDF meal plans.

**Path Parameters:**
- `filename`: PDF filename (e.g., `meal_plan_20250904_120000.pdf`)

**Response:**
- Binary PDF content with appropriate headers

**Headers:**
```
Content-Type: application/pdf
Content-Disposition: inline; filename="meal_plan.pdf"
Cache-Control: public, max-age=3600
```

**Status Codes:**
- `200` - Success
- `404` - PDF not found
- `410` - PDF expired

---

## 🌐 Web Application Endpoints

### **GET /onboard**
Returns the onboarding page HTML.

**Response:**
- HTML page for user onboarding

**Status Codes:**
- `200` - Success

### **POST /api/onboarding**
Processes onboarding form submission.

**Request:**
```json
{
  "phone": "+12125551234",
  "email": "user@example.com",
  "preferences": {
    "household_size": 2,
    "dietary_restrictions": ["vegetarian"],
    "health_goals": ["high-protein"],
    "cooking_style": ["quick-meals"],
    "cuisine_preferences": ["mediterranean"]
  },
  "ftp_credentials": {
    "email": "user@example.com",
    "password": "encrypted-password"
  }
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Onboarding completed successfully",
  "user_id": "uuid",
  "next_steps": "Visit /dashboard to analyze your cart"
}
```

**Status Codes:**
- `200` - Success
- `400` - Invalid data
- `409` - User already exists

### **GET /dashboard**
Returns the main dashboard HTML.

**Response:**
- HTML page for the main dashboard

**Status Codes:**
- `200` - Success

---

## 🔐 Authentication Endpoints

### **GET /login**
Returns the login page HTML.

**Response:**
- HTML page for FTP credentials login

**Status Codes:**
- `200` - Success

### **POST /login**
Processes FTP credentials and scrapes initial cart.

**Request:**
```json
{
  "phone": "+12125551234",
  "email": "user@example.com",
  "password": "ftp-password"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Login successful",
  "cart_scraped": true,
  "items_found": 15,
  "redirect_url": "/dashboard"
}
```

**Status Codes:**
- `200` - Success
- `401` - Invalid credentials
- `500` - Scraping failed

---

## 🏥 Health & Monitoring Endpoints

### **GET /health**
Basic health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-09-04T12:00:00Z",
  "version": "1.0.0",
  "environment": "production"
}
```

**Status Codes:**
- `200` - Healthy
- `503` - Unhealthy

### **GET /healthz**
Alternative health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "services": {
    "database": "healthy",
    "sms": "healthy",
    "ai": "healthy"
  }
}
```

**Status Codes:**
- `200` - All services healthy
- `503` - One or more services unhealthy

### **GET /metrics**
Application metrics endpoint.

**Response:**
```json
{
  "requests_total": 15420,
  "sms_sent_total": 892,
  "meals_generated_total": 445,
  "active_users": 23,
  "average_response_time": "1.2s",
  "error_rate": "0.02%"
}
```

**Status Codes:**
- `200` - Success

---

## 🧪 Testing Endpoints

### **POST /test-full-flow**
Tests the complete SMS flow (development only).

**Request:**
```json
{
  "phone": "+12125551234",
  "test_message": "plan"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Test flow completed",
  "steps_completed": [
    "SMS received",
    "User lookup",
    "Cart scraping",
    "Meal generation",
    "PDF creation",
    "SMS response"
  ],
  "total_time": "45.2s"
}
```

**Status Codes:**
- `200` - Success
- `400` - Invalid test data

---

## 📊 Error Codes Reference

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `INVALID_PHONE` | Invalid phone number format | 400 |
| `USER_NOT_FOUND` | User not found in database | 404 |
| `CART_NOT_FOUND` | Cart data not found | 404 |
| `SCRAPING_FAILED` | Cart scraping failed | 500 |
| `MEAL_GENERATION_FAILED` | AI meal generation failed | 500 |
| `SMS_SEND_FAILED` | SMS sending failed | 500 |
| `PDF_GENERATION_FAILED` | PDF generation failed | 500 |
| `RATE_LIMIT_EXCEEDED` | Rate limit exceeded | 429 |
| `INVALID_CREDENTIALS` | Invalid FTP credentials | 401 |
| `ANALYSIS_NOT_FOUND` | Meal plan analysis not found | 404 |

---

## 🔄 Webhook Integration

### **Vonage SMS Webhook**
The system integrates with Vonage SMS service to receive incoming messages.

**Webhook URL:** `https://farmtopeople-production.up.railway.app/sms/incoming`

**Configuration:**
- **Method:** POST
- **Content-Type:** application/json
- **Authentication:** API key in request body

**Supported Keywords:**
- `hello` - Start conversation
- `plan` - Generate meal plan
- `confirm` - Confirm meal plan
- `help` - Get help information
- `stop` - Opt out of service

This comprehensive API reference provides all the information needed to integrate with and maintain the Farm to People AI Assistant API.

