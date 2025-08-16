# Farm to People AI Assistant - Standard Operating Procedure (SOP)

_Last Updated: August 10, 2025_

## 1. Executive Summary

This document outlines the architecture, operational flows, and future roadmap for the Farm to People AI Assistant. The system's primary goal is to increase customer retention and order value for Farm to People by providing a hyper-personalized, AI-driven meal planning and onboarding experience via SMS.

## 2. Current State Architecture

The application is composed of several distinct Python scripts and a cloud database, orchestrated by a central web server.

### Core Components:
*   **`server.py` (FastAPI Web Server):** The main entry point for all external interactions. It listens for incoming SMS messages from Twilio via a webhook.
*   **`farmbox_optimizer.py` (The Scraper):** A Playwright-based script that can log into a user's Farm to People account, scrape their current cart and customizable box contents, and save the data to structured JSON files.
*   **`meal_planner.py` (The Meal Planner AI):** Uses the scraped data and a master product catalog (`farmtopeople_products.csv`) to generate a validated and repaired meal plan via multiple calls to the OpenAI API (`gpt-4o-mini`).
*   **`friend_flow.py` (The Onboarding AI):** Manages the conversational onboarding for new users, asking intake questions and providing a strategic, AI-driven box recommendation.
*   **`supabase_client.py` (Database Client):** A dedicated helper module that handles all communication with the Supabase cloud database, including fetching and storing user credentials.
*   **Supabase (PostgreSQL Database):** The cloud-based "source of truth" for all user data, including contact information, encrypted FTP credentials, and preferences.

### Main Operational Flow: The "Plan" Command

This is the flow for an existing user who wants a meal plan.

1.  **User Texts "plan"**: A user sends an SMS with the word "plan" to the designated Twilio number.
2.  **Twilio Webhook**: Twilio forwards the message content and the user's phone number to our `server.py`'s `/sms` endpoint.
3.  **Credential Fetch**: `server.py` calls `supabase_client.py` to fetch the user's FTP credentials from the Supabase `users` table, using the phone number as the key.
4.  **Scraper Execution**: The server triggers the `farmbox_optimizer.py` script as a background task, passing in the fetched credentials.
5.  **Data Acquisition**: The scraper logs into farmtopeople.com, scrapes the cart and box contents, and saves them to `farm_box_data/`.
6.  **Meal Plan Generation**: Upon successful completion of the scraper, the server triggers the `meal_planner.py` script.
7.  **AI Meal Plan**: `meal_planner.py` uses the scraped data, the master product list, and the user's preferences (future state) to generate, validate, and repair a meal plan with OpenAI.
8.  **SMS Reply**: The final, formatted meal plan is sent back to the user as a new SMS message via the Twilio API.

### Secondary Flow: The "New User" Onboarding

1.  **User Texts "new"**: A new user initiates contact.
2.  **Server Recognizes New User**: The server checks Supabase, finds no existing user, and triggers the `friend_flow.py` logic.
3.  **Secure Credential Link**: The server replies with the first intake question and a secure link to the `/login` web form to collect their FTP credentials.
4.  **Intake Conversation**: A multi-step conversational intake is managed by `friend_flow.py` (currently simulated in the terminal, future state via SMS).
5.  **AI Recommendation**: After intake, an AI-powered recommendation for a starting box is generated.
6.  **Q&A Session**: A conversational agent is activated to answer any follow-up questions the new user might have.

## 3. Future Roadmap: Next Steps

The following are the next three major development phases to move the application from a functional proof-of-concept to a live, multi-user cloud service.

### Step 1: Full Cloud Deployment & Live SMS
*   **Goal**: Get the application running 24/7 on a cloud server and make the SMS interaction fully live.
*   **Tasks**:
    1.  Deploy the `server.py` application to a hosting provider (e.g., Render, Railway).
    2.  Configure all environment variables (`OPENAI_API_KEY`, `SUPABASE_URL`, etc.) in the production environment.
    3.  Update the Twilio webhook to point to the new, permanent public URL of the deployed server (instead of the temporary `ngrok` URL).
    4.  Implement a background job queue (e.g., using FastAPI's `BackgroundTasks`) to handle long-running tasks like scraping without timing out Twilio's webhook.

### Step 2: Full Integration of `friend_flow.py` and Database
*   **Goal**: Move beyond the terminal simulation and make the "Friend Flow" a true, stateful SMS conversation, with all data saved to Supabase.
*   **Tasks**:
    1.  Create a `sessions` table or use the `preferences` column in the `users` table to track a new user's progress through the intake questions.
    2.  Modify `server.py` to handle a multi-step SMS conversation (e.g., "Question 1 -> User Answer -> Question 2 -> ...").
    3.  Save the final, collected preferences to the `users` table in Supabase.
    4.  Create the `meal_plans` and `recommendation_history` tables in Supabase and log every AI-generated plan and recommendation.

### Step 3: Develop a Simple Web App (PWA)
*   **Goal**: Create a mobile-friendly web interface as a faster, richer alternative to the pure SMS experience, proving product-market fit before committing to a native app.
*   **Tasks**:
    1.  Expand the FastAPI server with new API endpoints to serve data to a web front-end (e.g., `/api/get_meal_plan`, `/api/user_preferences`).
    2.  Build a simple front-end using a modern framework (like React or Vue) that communicates with our existing API.
    3.  Implement a simple login system on the web app that uses our `users` table.
    4.  Deploy the web app on a service like Vercel or Netlify.
