# Farm to People–Focused Market Scan
## Inventory-Aware Meal Planning and Box Ecosystem

## 1) Executive Brief

### Thesis 1: Inventory-aware meal planning is the wedge
Most recipe apps and meal kits are shoppable but not truly inventory-aware for local farm boxes. A planner that ingests a weekly Farm to People box manifest, plans meals around it, and adapts to availability fills a clear gap. Start with Farm to People in NYC to prove product market fit where freshness, seasonality, and limited inventory matter.

### Thesis 2: Personalization and OOS resilience are under-served
Diet rules, ingredient dislikes, staples, and proactive plan B recipes for likely out-of-stocks are fragmented or missing in incumbents. Building a hard rules engine plus soft dislikes and automatic swap-aware plans creates differentiated utility and trust.

### Thesis 3: Gamified, no-typing UX drives retention
A mobile-first, big-tile, tap-only flow for choosing 3 dinners, with optional 3 to 10 minute level-up tiles and a cook-mode stepper, can turn weekly planning into a 5 minute habit. Streaks, badges, weekly digest reminders, and “auto-add staples” can compound engagement and retention.

---

## 2) Competitor Matrix

| Company / Product | Category (A-F) | Inventory-aware? | CSA/box-aware? | OOS handling | Dietary engine | Gamified UX | Platform focus | Pricing B2C / Tooling B2B | Geography | Notable strengths | Gaps vs concept |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BuzzFeed Tasty | A | Partial via retailer integrations | No | Retailer-level subs or refunds | Basic tags | High visual, not game | App + web | Free, affiliate | US | Video-first shoppable recipes | No CSA context, no deep personalization |
| Samsung Food (Whisk) | A | Yes, maps to retailer SKUs | No | User sets replacements, retailer subs | Strong prefs and filters | Moderate | App + web + appliances | Free, affiliate/API | Global | Universal recipe saver, multi-retailer | Not farm or box-aware |
| Cooklist | A/E | Yes, pantry and real-time store stock | No | Shows in-stock alternatives | Strong, learns brands and allergies | Low | App | Free, affiliate | US | Pantry-to-recipes with price match | Not CSA-timed or box-ingest |
| SideChef | A | Partial via retailer carts | No | Retailer subs or refunds | Good filters, curated plans | Interactive cook mode | App + web | Freemium + affiliate | US | Step-by-step guided cooking | Not box or inventory adaptive |
| RecipeTin (app/site) | A | No | No | N/A | Minimal | Low | App + web | One-time app fee | Global | High trust recipes | No planning or shopping |
| HelloFresh | B | Backend only | They are the box | Menu sell-outs, rare kit swaps | Basic plan-level | Low | App + web | Per-serving subscription | US/EU/AU | Convenience, variety | Closed ecosystem, packaging load |
| Blue Apron | B | Backend only | They are the box | Occasional subs/credits | Basic | Low | App + web | Per-serving subscription | US | Culinary quality, wine add-ons | Retention issues, no pantry use |
| Home Chef | B | Backend only | They are the box | Customize It protein swaps | Basic taste profile | Low | App + web + Kroger retail | Per-serving subscription | US | Protein swap flexibility | Closed loop, not local-first |
| Sunbasket | B | Backend only | They are the box | Sub similar organic items | Strong diet plans | Low | App + web | Premium per-serving | US | Organic focus, diets | Pricey, no CSA integration |
| Factor | B | Backend only, prepared | They are the box | Rare menu sell-outs | Diet categories | None | App + web | Per-meal subscription | US | No-cook convenience | No cooking or planning utility |
| Territory Foods | B | Backend only, prepared | They are the box | Chef-level subs, credits | Strong diet filters | None | Web | Per-meal subscription | US metros | Local chefs, health focus | Not for cooking or CSA use |
| Hungryroot | C | Yes, grocer plus recipes | Own weekly box, not external CSA | Auto-sub similar items, user can edit | Extensive dislikes and tastes | Moderate | App + web | Weekly food box, no app fee | US | Personalized cart + recipes | Closed catalog, not local farm |
| Instacart Recipes | C | Yes, store in-stock mapping | No | Shopper subs per user prefs | Light | Low | App + web | Free to browse, commerce fees | US/CA | Inspiration to cart in minutes | Not weekly planning or CSA-aware |
| Amazon/Whole Foods recipes | C | Yes within Fresh inventory | No | Auto or user-set subs | Light | Low | Amazon app, Alexa | Free, commerce margin | US/UK | Massive assortment and speed | Not local-first, shallow planning |
| Farm to People | D/F | Yes operationally, curated list | Yes, customizable weekly box | User swaps pre-cutoff, ops subs | Box-type level | Low | Web | Box price, small delivery fee | NYC area | Local, fresh, curated, flexible | No integrated planner or app |
| Harvie (ended 2024) | D | Yes for farm inventory | Yes, customizable CSA | Pre-lock swaps window | Preference ratings | Low | Web | B2B % fees | North America | Pioneered customizable CSA | Costly for farms, no planner |
| Local Line | D | Yes for farm shops | Yes for subscriptions | Inventory caps, manual comms | N/A consumer-level | Low | Web | B2B SaaS | North America | Strong farm e-commerce plumbing | No consumer planner or app |
| Barn2Door | D | Yes for farm shops | Yes for subscriptions | Manual ops comms | N/A consumer-level | Low | Web | B2B SaaS | US | Reliable farm DTC tooling | No consumer-side planning |
| CSAware | D | Yes for CSAs | Yes for CSAs | Swap limits, manual subs | Low | Low | Web | B2B 2% of sales | US | Battle-tested CSA ops | Dated UX, no planner |
| Farmigo (legacy) | D | Yes for buying clubs | Yes for CSAs | Prevent oversell, manual subs | Low | Low | Web | B2B SaaS | US | Early CSA e-commerce | Closed consumer product, no planner |
| Misfits Market | F | Yes warehouse stock | Own weekly box, not CSA | Refunds, no auto-sub by default | Light filters | Low | App + web | Per-item, order minimum | US | Budget, surplus sustainability | Not planning-first, quality variance |
| Local Roots NYC | F | Traditional CSA inventory | Yes seasonal shares | Farm subs, limited swaps | Share-type level | Low | Web + in-person pickup | Prepaid seasonal | NYC | Community, culture, local | Low convenience, limited customization |
| FreshDirect | F | Yes warehouse stock | No | Per-item subs or omit | Medium filters | Low | App + web | Per-item, delivery fees or pass | NYC metro | One-stop, quality, selection | Not inspiration-first, no CSA import |

---

## 3) NYC Customer Choice Snapshot

- FreshDirect: broadest choice and delivery slots. DIY planning. Competes on convenience and selection.
- Misfits Market: discounted organic groceries with order minimum. Good for budget. Variable quality. DIY planning.
- OurHarvest: local online farmers market. A la carte. Limited delivery days. DIY planning.
- Local Roots NYC: community CSA with pickups. Lower convenience. Limited customization. Seasonal commitment.
- Traditional NYC CSAs: many neighborhood groups. Lowest cost, least flexibility. No planner.
- Meal kits: HelloFresh, Blue Apron, Home Chef, Sunbasket. High convenience, no pantry or CSA integration.
- Hungryroot: weekly hybrid grocer plus recipes. Personalization strong. Closed catalog. Not local-first.
- Other NYC services: Green Top Farms, GoOrganicNYC, OurHarvest, MaxDelivery, Whole Foods via Amazon. Each trades off between speed, price, and curation.

---

## 4) Pricing, Monetization, Retention

- B2C price reality: pure meal planning apps cluster at free to 5 dollars per month. Paid-only planning struggles without commerce attachment.
- Primary monetization path: affiliate or rev share on add-ons and larger baskets for Farm to People, plus increased order frequency and lower churn.
- Subscription option: optional Pro tier at about 4.99 per month only once value is proven. Keep core planner free for F2P users.
- Retention loops: Thursday digest with proposed 3 dinners, saved profiles that learn, auto-add staples, streaks and badges, tap-to-add 10 minute level-ups, cook-mode stepper.
- B2B: white-label planner for CSAs and food hubs. Compete with CSAware and Local Line on UX rather than plumbing. Pricing about 50 to 150 dollars per month or small performance rev share.

---

## 5) Fast Tests and Risks

- Concierge MVP: manually send 3 tailored recipes for next week’s Farm to People box to 5 users. Track add-on sales and skips.
- Landing page and waitlist: validate demand and willingness to pay. Consider a small 5 dollar pre-order to gauge commitment.
- Partner pilot: one-week plan by a local chef for the current box. Measure open and usage rates.
- Risks: incumbents could bolt on partial features. Mitigation is focus on farm data integration, playful UX, and local relationships.
- Success metric: higher AOV, fewer skipped weeks, lower churn for Farm to People users who use the planner.

---

## Buckets and Definitions

- A: Recipe publishers and shoppable recipes
- B: Meal kits and prepared meals
- C: Grocery plus AI planners
- D: CSA and farm commerce platforms
- E: Use-what-you-have and pantry apps
- F: NYC-local boxes and markets

