### HTTP Endpoints (FastAPI)

Base URL defaults to `http://localhost:8000` unless deployed.

Endpoints:

- GET `/health`
  - Purpose: Basic health check for Railway.
  - Response: `{ "status": "healthy", "service": "farmtopeople-sms" }`
  - Example:
    - `curl http://localhost:8000/health`

- GET `/healthz`
  - Purpose: Server liveness check.
  - Response: `{ "status": "ok" }`
  - Example:
    - `curl http://localhost:8000/healthz`

- GET or POST `/sms/incoming`
  - Purpose: Vonage webhook for incoming SMS messages.
  - Query (GET): `msisdn`, `text`
  - Body (POST): JSON or form with `msisdn`, `text`
  - Behavior: Parses method-specific payload, triggers SMS handling flow.
  - Example (GET):
    - `curl "http://localhost:8000/sms/incoming?msisdn=15551234567&text=plan"`
  - Example (POST JSON):
    - `curl -X POST http://localhost:8000/sms/incoming -H 'Content-Type: application/json' -d '{"msisdn":"15551234567","text":"plan"}'`

- GET `/login`
  - Purpose: Returns an HTML form for collecting Farm to People credentials.
  - Response: HTML (FastAPI `HTMLResponse`).
  - Example:
    - Open in browser: `http://localhost:8000/login`

- POST `/login`
  - Purpose: Save credentials to Supabase (upsert by email), optional phone.
  - Form fields: `phone` (optional), `email` (required), `password` (required)
  - Success: `Saved. You can now text 'plan' to get meal ideas.`
  - Example:
    - `curl -X POST http://localhost:8000/login -F email=user@example.com -F password=secret -F phone=+15551234567`

- GET `/pdfs/{filename}`
  - Purpose: Serve generated PDF meal plans.
  - Path params: `filename` (string)
  - Response: PDF file if exists; 404 otherwise.
  - Example:
    - `curl -I http://localhost:8000/pdfs/sample.pdf`

- GET `/meal-plan/{analysis_id}`
  - Purpose: Serve full cart analysis by ID as formatted HTML.
  - Path params: `analysis_id` (string)
  - Response: Rendered HTML or 404 if not found.
  - Example:
    - `curl http://localhost:8000/meal-plan/abc123`

- POST `/test-full-flow`
  - Purpose: Manually trigger the full pipeline for testing.
  - Env: Requires `YOUR_PHONE_NUMBER` in `.env`.
  - Response: `{ status, message }` and schedules background task.
  - Example:
    - `curl -X POST http://localhost:8000/test-full-flow`

- GET `/`
  - Purpose: Landing page with links to onboarding and SMS instructions.
  - Response: HTML (Jinja2 template `index.html`).

- GET `/sms`
  - Purpose: SMS opt-in instructions page for Vonage compliance.
  - Response: HTML (Jinja2 template `sms_optin.html`).

- GET `/dashboard`
  - Purpose: Main dashboard after onboarding.
  - Response: HTML (Jinja2 template `dashboard.html`).

- POST `/api/analyze-cart`
  - Purpose: Trigger cart analysis from the dashboard; returns quickly and can be polled for updates.
  - Body: JSON containing user/session context as implemented by frontend.
  - Response: `{ status|success, ... }` with progress semantics.
  - Example:
    - `curl -X POST http://localhost:8000/api/analyze-cart -H 'Content-Type: application/json' -d '{}'`

- POST `/api/refresh-meals`
  - Purpose: Generate new meal suggestions from the same cart data.
  - Body JSON: `cart_data` (required), `phone` (optional to load preferences)
  - Response: `{ success, meals, household_size }` or error with debug info.
  - Example:
    - `curl -X POST http://localhost:8000/api/refresh-meals -H 'Content-Type: application/json' -d '{"cart_data": {"individual_items": []}}'`

- GET `/onboard`
  - Purpose: Serve preference onboarding flow UI.
  - Query: `phone` (optional)
  - Response: HTML (Jinja2 template `onboarding.html`).

- POST `/api/onboarding`
  - Purpose: Save onboarding preferences; delegates to `server/onboarding.py`.
  - Body JSON: see module docs for fields; returns `{ status, message, session_id, account_type, preferences }`.
  - Example:
    - `curl -X POST http://localhost:8000/api/onboarding -H 'Content-Type: application/json' -d '{"householdSize":2,"mealTiming":["dinner"],"selectedMeals":[],"dietaryRestrictions":[],"goals":["quick-dinners"],"ftpEmail":"user@example.com","ftpPassword":"secret","phoneNumber":"+15551234567"}'`

- GET `/settings`
  - Purpose: Settings page for updating user preferences.
  - Response: HTML (Jinja2 template `settings.html`).

- GET `/api/settings/options`
  - Purpose: Returns available options for all settings categories.
  - Response: JSON lists aligned with onboarding option sets.

- GET `/api/settings/{phone}`
  - Purpose: Fetch user preferences by phone for settings display.
  - Path params: `phone` (string)

- POST `/api/settings/{phone}/update`
  - Purpose: Update specific preference categories for a user.
  - Path params: `phone` (string)
  - Body JSON: partial preference payload to update categories.

Notes:
- Many endpoints depend on environment variables (`OPENAI_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, etc.). Ensure `.env` is configured.
- Background tasks and SMS functionality may be disabled locally.

