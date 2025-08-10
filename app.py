import os
import glob
from datetime import datetime, timedelta

# Import the main functions from our other scripts
import meal_planner
import friend_flow

FARM_BOX_DATA_DIR = "farm_box_data"


def get_latest_cart_file_status(directory: str, minutes_threshold: int = 120) -> bool:
    """
    Checks if a recent 'cart_contents' file exists.
    Returns True if a file is found within the time threshold, False otherwise.
    """
    try:
        cart_files = glob.glob(os.path.join(directory, "cart_contents_*.json"))
        if not cart_files:
            return False
            
        latest_file = max(cart_files, key=os.path.getmtime)
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(latest_file))
        
        # Return True if the file is recent enough
        return (datetime.now() - file_mod_time) < timedelta(minutes=minutes_threshold)
        
    except Exception as e:
        print(f"Error checking for cart files: {e}")
        return False


def main():
    """
    (Section A: Router)
    Main entry point for the application.
    Checks for a recent cart and routes the user to the appropriate flow.
    """
    print("===== Welcome to the Farm to People AI Assistant =====")
    
    # The scraper (farmbox_optimizer.py) must be run separately for now
    # to generate the data files.
    
    has_recent_cart = get_latest_cart_file_status(FARM_BOX_DATA_DIR)
    
    if has_recent_cart:
        print("\n>>> Recent cart data found. Starting Meal Planner...")
        meal_planner.main()
    else:
        print("\n>>> No recent cart data found. Starting Friend Flow for new users...")
        friend_flow.main()
        
    print("\n===== Assistant session complete. =====")


if __name__ == "__main__":
    main()

