# Farm to People AI Assistant - Standard Operating Procedure (SOP v2)

_Last Updated: August 10, 2025_

## 1. Core Product Vision: "The Thursday Afternoon Magic"

The primary goal of this project is to transform the Farm to People weekly box experience. We will turn the moment of "what do I do with these ingredients?" into an exciting, engaging culinary journey that begins on Thursday afternoon, two days before the box even arrives. Our core strategy is **Reverse Meal Planning**: we start with the user's actual, confirmed box contents and build a personalized, beautiful, and actionable plan around them.

## 2. Technical Architecture & Project Structure

The application is being refactored into a professional, scalable structure to support our long-term vision of a multi-platform service (SMS, Web App, iOS App).

### Target Project Structure:
```
farm-to-people-assistant/
├── backend/
│   ├── server.py                 # FastAPI main server
│   ├── scraper/
│   │   ├── box_monitor.py        # Thursday afternoon scheduler
│   │   └── farmbox_optimizer.py  # Playwright scraper
│   ├── ai_engine/
│   │   └── meal_planner.py       # OpenAI recipe generation
│   ├── messaging/
│   │   └── sms_handler.py        # Twilio integration
│   └── database/
│       └── supabase_client.py    # User data & preferences
└── ... (other files)
```

## 3. The "Thursday Magic" User Flow

This is the primary operational flow of the application.

1.  **Thursday 2 PM (Box Lock):** The user's Farm to People box for the upcoming weekend delivery is locked and can no longer be customized.
2.  **Thursday 3 PM (Automated Scrape):** The `box_monitor.py` scheduler automatically triggers the `farmbox_optimizer.py` script for all active users. The scraper logs in, scrapes the final, confirmed contents of each user's box, and saves this data to our Supabase database.
3.  **Thursday 3:05 PM (The Teaser SMS):** Immediately after the scrape, the system sends the first SMS to the user via Twilio.
    *   **Example:** _"🌟 Zach, your Farm to People box is locked in! This week's stars include White Peaches and Organic Green Kale. How's your energy for the week? Reply: 1=Tired 😴, 2=Normal 😊, 3=Ambitious 🚀"_
4.  **Thursday 6 PM (The Plan Delivery):** Based on the user's energy level response, the system sends the main event: a link to a beautifully generated PDF meal plan.
    *   **Example:** _"🍽️ Your adventures await! Based on your 'Normal' energy, your personalized meal plan is ready. It includes a 35-min version of our Peach and Kale Salad. View your full visual guide here: [link-to-pdf]"_
5.  **Weekend (Engagement & Learning):** The system can send follow-up tips and gather feedback on the meals.

## 4. Current State vs. Next Steps

We have successfully built the foundational components for this vision. Now, we will execute a planned refactor to align our existing code with this new architecture.

### **Current State:**
*   We have a functional, monolithic scraper (`farmbox_optimizer.py`).
*   We have a powerful AI meal planner (`meal_planner.py`).
*   We have a prototype server (`server.py`) and Supabase connection (`supabase_client.py`).

### **Next Steps (The Refactor):**

1.  **Restructure the Project:** Create the new `backend/` sub-directory structure and move the existing `.py` files into their new, logical homes.
2.  **Create the Box Monitor:** Build the `box_monitor.py` script with a scheduler (like `schedule`) to trigger the scraper.
3.  **Refactor the Scraper for Automation:** Modify `farmbox_optimizer.py` to run "headless" and be importable as a module, so it can be called by the monitor.
4.  **Integrate the Full SMS Flow:** Upgrade `server.py` to handle the multi-step "Thursday Magic" conversation, including the energy level reply and sending the final plan.

This refactoring process will be our primary focus to transition from a successful prototype to the foundation of a real, scalable product.
