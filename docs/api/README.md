### API and Module Documentation

This directory documents all public HTTP APIs, functions, and components in the project. It includes endpoint specs, module overviews, and practical examples.

- HTTP Endpoints: see `http_endpoints.md`
- Server Modules: see `server_modules.md`
- Generators: see `generators.md`
- Scrapers: see `scrapers.md`

Quick start:

- Start the API server:
  - Using uvicorn: `uvicorn server.server:app --reload --host 0.0.0.0 --port 8000`
- Run a scraper (example):
  - `python scrapers/comprehensive_scraper.py`
- Generate a PDF meal plan (example):
  - `python -c "from generators.pdf_meal_planner import generate_pdf_meal_plan; print(generate_pdf_meal_plan())"`

