### Generators

Module: `generators/pdf_meal_planner.py`

- `generate_pdf_meal_plan(output_filename: Optional[str] = None, generate_detailed_recipes: bool = True, user_skill_level: str = "intermediate") -> str`
  - Convenience wrapper to produce a PDF meal plan using `PDFMealPlanner`.
  - Args:
    - `output_filename`: override default filename
    - `generate_detailed_recipes`: include professional recipes
    - `user_skill_level`: beginner | intermediate | advanced
  - Returns: Path to the generated PDF.
  - Example:
    ```python
    from generators.pdf_meal_planner import generate_pdf_meal_plan
    pdf_path = generate_pdf_meal_plan(user_skill_level="beginner")
    print(pdf_path)
    ```

Module: `generators/html_meal_plan_generator.py`

- Provides HTML generation utilities for meal plan previews.
  - Run standalone for preview:
    ```bash
    python generators/html_meal_plan_generator.py
    ```

Module: `generators/pdf_one_page.py` and `generators/pdf_meal_planner_v2.py`

- Alternate PDF layouts and experiments. Use the primary `pdf_meal_planner.py` for production.

