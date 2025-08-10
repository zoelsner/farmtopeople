import os
from fastapi import FastAPI, Form, Request
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

@app.get("/healthz", status_code=200)
def health_check():
    """Health check endpoint to confirm the server is running."""
    return {"status": "ok"}

@app.post("/sms")
async def sms_reply(From: str = Form(...), Body: str = Form(...)):
    """
    Handles incoming SMS messages from Twilio.
    This is the main entry point for user interaction.
    """
    user_phone_number = From
    user_message = Body.lower().strip()
    
    print(f"Received message from {user_phone_number}: '{user_message}'")
    
    # Initialize the response object
    resp = MessagingResponse()
    
    # --- Main App Logic Router ---
    # Here, we'll connect the server to our existing scripts
    # For now, we'll just have a simple reply.
    
    if "hello" in user_message:
        reply = "Hi there! I'm your Farm to People meal planning assistant. How can I help?"
    elif "plan" in user_message:
        # TODO: Trigger the meal planner logic
        reply = "I'm ready to help you plan! First, I'll check your latest cart contents..."
    elif "new" in user_message:
        # TODO: Trigger the friend flow for new users
        reply = "Welcome! Let's get you set up. What's your cooking style?"
    else:
        reply = "Sorry, I didn't understand that. You can say 'plan' to get meal ideas or 'new' if you're a new user."
        
    # Add the reply to the TwiML response
    resp.message(reply)
    
    # Return the response as XML
    # Use the `str()` function on the response object to get the TwiML XML
    return str(resp)

if __name__ == "__main__":
    import uvicorn
    # To run this server locally, use the command:
    # uvicorn server:app --reload
    print("Starting server... To test, run 'uvicorn server:app --reload' in your terminal.")
    # This part is for local development and won't be used in production
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
