import json
import os
import openai
from typing import Dict, List, Any
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv()
DATABASE_FILE = "../data/user_database.json"
AVAILABLE_BOXES = [
    {
        "name": "Seasonal Produce Box - Small",
        "description": "A curated selection of the best seasonal vegetables and fruits. Great for 1-2 people.",
        "tags": ["seasonal", "curated", "discovery", "vegetarian"]
    },
    {
        "name": "Butcher's Choice",
        "description": "High-quality, pasture-raised meats.",
        "tags": ["meat-lovers", "protein-heavy", "grilling"]
    },
    {
        "name": "The Cook's Box - Omnivore",
        "description": "A balanced box with protein, dairy, and produce.",
        "tags": ["omnivore", "balanced", "weeknight-meals"]
    }
]

# --- Database Functions ---
def load_user_data(user_id: str) -> Dict[str, Any]:
    try:
        with open(DATABASE_FILE, 'r') as f:
            db = json.load(f)
            for user in db:
                if user.get("user_id") == user_id:
                    return user
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    return None

# --- Core AI and Intake Functions ---
def run_intake_prompt() -> Dict[str, Any]:
    print("\n--- Let's Get to Know You ---")
    style = input("1. What's your cooking style? (e.g., quick & easy, experimental): ").strip()
    protein = input("2. Any favorite proteins? (e.g., chicken, fish, vegetarian): ").strip()
    dislikes = input("3. Any ingredients you really dislike?: ").strip()
    goal = input("4. What's your main goal? (e.g., eat healthier, learn to cook): ").strip()
    protein_goal = input("5. Any specific daily protein goals? (e.g., '150g' or 'no'): ").strip()
    return {"style": style, "protein": protein, "dislikes": dislikes, "goal": goal, "protein_goal": protein_goal}

def get_box_recommendation(preferences: Dict[str, Any]) -> Dict[str, Any]:
    print("\n--- Generating Your Personalized Recommendation... ---")
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    if not client.api_key: return {}
    
    system_prompt = (
        "You are a friendly, strategic guide for Farm to People. Your goal is to recommend the 'Seasonal Produce Box - Small' "
        "as the ideal starting point. Use the user's preferences to craft a persuasive reason why this box, "
        "plus some protein they can add themselves, is the perfect way to achieve their goals. ALWAYS suggest 'Organic Lemons' as an add-on."
        "\nRespond in this JSON format: "
        '{"primary_box": "Seasonal Produce Box - Small", "addons": ["Organic Lemons"], "reasoning": "Your personalized reasoning here."}'
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Here are my preferences: {json.dumps(preferences)}"}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Error calling OpenAI: {e}")
        return {}

def run_chat_agent(user_data: Dict[str, Any], recommendation: Dict[str, Any]):
    print("\n--- Your Personal Assistant is Ready ---")
    print("Ask me anything about your recommendation! Type 'done' to exit.")
    
    chat_history = []
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    while True:
        user_input = input("\nYour question: ").strip()
        if user_input.lower() == 'done': break
        
        system_prompt = (
            f"You are a helpful assistant for {user_data.get('name', 'a new customer')}. "
            f"They were just recommended: {json.dumps(recommendation)}. "
            f"Their preferences: {json.dumps(user_data.get('preferences', {}))}. "
            "Answer their questions concisely and helpfully. If they want to remove lemons, agree cheerfully."
        )
        
        messages = [{"role": "system", "content": system_prompt}, *chat_history, {"role": "user", "content": user_input}]
        
        try:
            response = client.chat.completions.create(model="gpt-5-mini", messages=messages)
            ai_response = response.choices[0].message.content
            print(f"Assistant: {ai_response}")
            chat_history.extend([{"role": "user", "content": user_input}, {"role": "assistant", "content": ai_response}])
        except Exception as e:
            print(f"Error during chat: {e}")

# --- Main Application ---
def main():
    user_id = "friend_1"
    user_data = load_user_data(user_id)
    
    if not user_data:
        print("Welcome, new friend! Let's get you set up.")
        preferences = run_intake_prompt()
        user_data = {"user_id": "new_friend", "name": "New Friend", "preferences": preferences}
    else:
        print(f"--- Welcome back, {user_data.get('name', 'friend')}! ---")

    recommendation = get_box_recommendation(user_data['preferences'])
    
    if recommendation:
        print("\n--- Here Is Your Personalized Recommendation ---")
        print(f"The best starting point for you is the '{recommendation.get('primary_box', 'N/A')}'.")
        if recommendation.get('addons'):
            print(f"I also suggest adding: {', '.join(recommendation['addons'])}.")
        print(f"\nHere's why: {recommendation.get('reasoning', 'It is a great choice!')}")
        
        run_chat_agent(user_data, recommendation)
    else:
        print("Sorry, I couldn't generate a recommendation right now.")

if __name__ == "__main__":
    main()
