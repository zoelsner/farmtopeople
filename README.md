Farm to People Meal Planner (Personal Project)

This repository contains a personal project that automates scraping Farm to People cart contents and uses AI to generate meal plans and suggested add‑ons. It also exposes a small FastAPI service for future SMS and mobile integrations.

## SMS Opt‑In Policy

This service sends SMS messages only in direct response to a user’s request. There is no marketing or promotional messaging.

- Opt‑in method: Users opt in by initiating a conversation (e.g., texting "hello", "plan", or "new") to the project’s phone number, or by giving explicit verbal consent to the project owner to be contacted.
- Message frequency: On‑demand/transactional. Messages are sent only when a user interacts (for example, requesting a plan or continuing a conversation). No recurring campaigns.
- Opt‑out instructions: Text "STOP" to stop receiving messages at any time. You may text "START" to re‑enable messages.
- Help instructions: Text "HELP" for assistance.
- Carrier disclaimer: Message and data rates may apply.
- Privacy: Phone numbers and message content are used solely to power the requested conversation (meal planning and customer support style responses). Data is not sold or shared with third parties.
- Age: This service is intended for adults.

If you have questions about this policy, reply "HELP" in the SMS thread.

You can link directly to this section in the Twilio form by using the repository URL with the anchor `#sms-opt-in-policy` (example: `https://github.com/<your-username>/farmtopeople#sms-opt-in-policy`).


