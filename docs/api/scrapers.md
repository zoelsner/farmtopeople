### Scrapers

Common requirements:
- `.env` with `EMAIL` and `PASSWORD` (or `FTP_EMAIL` and `FTP_PWD`)
- Playwright installed and browsers set up: `playwright install` (once)

Module: `scrapers/auth_helper.py`

- `login_to_farm_to_people(page) -> bool`
  - Logs in using credentials from environment variables.

- `ensure_logged_in(page, fast_check=True) -> bool`
  - Verifies session, attempts re-login if needed.

Module: `scrapers/complete_cart_scraper.py`

- `generate_weekly_customer_summary(cart_data) -> str`
  - Produces a formatted weekly summary using cart items and boxes.

- CLI usage:
  ```bash
  python scrapers/complete_cart_scraper.py
  ```

Module: `scrapers/comprehensive_scraper.py`

- Headless Playwright workflow to collect comprehensive cart data including customizable boxes and alternatives.
- Outputs structured JSON used by analyzers.
- CLI usage:
  ```bash
  python scrapers/comprehensive_scraper.py
  ```

Module: `scrapers/weekly_summary_scraper.py` and `scrapers/weekly_health_check.py`

- Weekly utilities for generating summaries and health checks.

Notes:
- For multi-user or backup variants, see files suffixed with `_WORKING_BACKUP` or `MULTIUSER`.

