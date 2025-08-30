### Server Modules

This section documents key server modules and their public functions.

Module: `server/supabase_client.py`

- `get_client() -> Client`
  - Initializes and returns a Supabase client using `SUPABASE_URL` and `SUPABASE_KEY`.
  - Raises `RuntimeError` if required env vars are missing.

- `upsert_user_credentials(*, phone_number: Optional[str], ftp_email: str, ftp_password: str, preferences: Optional[Dict[str, Any]] = None) -> Dict[str, Any>`
  - Upserts a user row keyed by `ftp_email`, optionally storing `phone_number` and `preferences`.
  - Returns the stored row. Password is stored base64-encoded for now.
  - Example:
    ```python
    from server.supabase_client import upsert_user_credentials
    upsert_user_credentials(phone_number="+15551234567", ftp_email="user@example.com", ftp_password="secret", preferences={"goals":["quick-dinners"]})
    ```

- `get_user_by_phone(phone_number: str) -> Optional[Dict[str, Any]]`
- `get_user_by_email(ftp_email: str) -> Optional[Dict[str, Any]]`
  - Fetch a user record; includes decoded `ftp_password` in returned dict.

Module: `server/file_utils.py`

- `get_latest_cart_file(directory: str = FARM_BOX_DATA_DIR, user_id: str = None) -> Union[str, None]`
- `get_latest_box_file(directory: str = FARM_BOX_DATA_DIR, box_name_slug: str = "") -> Union[str, None]`
- `get_latest_comprehensive_file(directory: str = FARM_BOX_DATA_DIR, user_id: str = None) -> Union[str, Dict]`
  - Locate most recent JSON files locally; production paths are TODO via Supabase.

- `load_cart_data(file_path_or_data: Union[str, Dict]) -> Dict`
  - Accepts a filesystem path or dict; returns a dict of cart data.

- `save_analysis_result(analysis_data: Dict, user_id: str = None) -> str`
  - Persists the analysis and returns an ID used by `/meal-plan/{analysis_id}`.

- `get_analysis_by_id(analysis_id: str) -> Optional[Dict]`
  - Retrieve stored analysis for web rendering.

- `get_comprehensive_ingredients_and_data(comprehensive_data: dict) -> Tuple[List[str], dict]`
  - Extracts ingredients and structured data used by analyzers.

Module: `server/product_catalog.py`

- `get_product_catalog() -> Dict[str, Dict[str, str]]`
  - Loads and caches the product catalog; local CSV by default.

- `get_curated_items_list() -> List[str]`
  - Fallback curated list of common items.

- `fuzzy_match_product(suggestion: str, threshold: float = 0.6) -> Optional[Dict[str, str]]`
- `find_best_catalog_match(suggestion: str) -> Optional[Tuple[str, str, str]]`
  - Various matching helpers for mapping AI output to real products.

- `add_pricing_to_analysis(analysis_text: str) -> str`
  - Post-process analysis text by inserting real pricing and products.

- `get_product_by_name(product_name: str) -> Optional[Dict[str, str]]`
- `search_products_by_category(category: str) -> List[Dict[str, str]]`

Module: `server/cart_analyzer.py`

- `generate_cart_analysis_summary(user_id: str = None) -> str`
  - Orchestrates: load latest cart, build AI prompt, add pricing, save results, return SMS summary with link.
  - Example:
    ```python
    from server.cart_analyzer import generate_cart_analysis_summary
    sms = generate_cart_analysis_summary()
    print(sms)
    ```

- `create_sms_summary(full_analysis: str, analysis_id: str) -> str`
- `generate_meal_titles_only(full_analysis: str) -> str`

Module: `server/meal_planner.py`

- `generate_cart_analysis_summary(user_id: str = None) -> str`
  - Back-compat wrapper around `cart_analyzer.generate_cart_analysis_summary`.

- `get_master_product_list(catalog_file: str = None) -> List[str]`
- `get_all_ingredients_from_cart(cart_data: dict, data_dir: str) -> List[str]`

- `generate_meal_plan(ingredients: List[str], master_product_list: List[str], diet_hard: List[str] = None, dislikes: List[str] = None, time_mode: str = "standard", allow_surf_turf: bool = False) -> dict`
  - Legacy GPT-based planner; consider `cart_analyzer` for new flows.

- `validate_meal_plan(meal_plan: Dict[str, Any], available_ingredients: List[str], master_product_list: List[str]) -> List[str]`
- `run_repair_prompt(...) -> Dict[str, Any]`

Module: `server/onboarding.py`

- `analyze_meal_preferences(selected_meal_ids: List[str]) -> Dict[str, Any]`
  - Converts selected meal IDs into rich preference signals.

- `save_preferences(data: Dict[str, Any]) -> Dict[str, Any]` (async)
  - Saves preferences and optional FTP credentials; returns status and session info.
  - Example (simplified):
    ```python
    import anyio
    from server.onboarding import save_preferences
    payload = {"householdSize":2, "mealTiming":["dinner"], "selectedMeals":[], "dietaryRestrictions":[], "goals":["quick-dinners"], "ftpEmail":"user@example.com", "ftpPassword":"secret", "phoneNumber":"+15551234567"}
    anyio.run(lambda: save_preferences(payload))
    ```

Module: `server/recipe_generator.py`

- `enhance_meal_plan_with_recipes(meal_plan: Dict[str, Any], user_skill_level: str = "intermediate") -> Dict[str, Any]`
  - Adds professional recipe details to each meal in a plan.

