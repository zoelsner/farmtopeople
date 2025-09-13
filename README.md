# 🌱 Farm to People AI Assistant

Transform weekly produce boxes into personalized meal plans with intelligent cart analysis and meal planning.

**Version:** 5.0.0 (Modular Architecture)  
**Status:** Production Ready  
**Live:** https://farmtopeople-production.up.railway.app

## 🚀 Quick Start

### Prerequisites
- Python 3.8+ (Railway uses 3.8)
- Redis (optional, for caching)
- Supabase account
- Farm to People account

### Local Development

```bash
# 1. Clone repository
git clone https://github.com/yourusername/farmtopeople.git
cd farmtopeople

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set environment variables
cp .env.example .env
# Edit .env with your credentials

# 5. Run server
python server/server.py

# 6. Open browser
open http://localhost:8000/dashboard
```

## 📁 Project Structure

```
farmtopeople/
├── server/
│   ├── server.py                    # Main FastAPI application
│   ├── templates/
│   │   └── dashboard_refactored.html # Modular dashboard (750 lines)
│   ├── static/js/modules/           # JavaScript modules
│   │   ├── shared.js                # Global state & utilities
│   │   ├── cart-manager.js          # Cart analysis logic
│   │   ├── meal-planner.js          # Meal calendar & ingredients
│   │   └── settings.js              # User preferences
│   └── services/                    # Backend services
│       ├── phone_service.py         # Phone normalization
│       ├── cache_service.py         # Redis caching
│       ├── encryption_service.py    # Fernet encryption
│       └── ...                      # 8 more services
├── scrapers/                        # Farm to People scrapers
├── generators/                      # PDF generation
└── docs/                           # Documentation
```

## 🔑 Environment Variables

Create a `.env` file with:

```bash
# Farm to People Credentials
FTP_EMAIL=your@email.com
FTP_PASSWORD=yourpassword

# Vonage SMS (optional)
VONAGE_API_KEY=xxx
VONAGE_API_SECRET=xxx
VONAGE_PHONE_NUMBER=18334391183

# OpenAI
OPENAI_API_KEY=xxx

# Supabase
SUPABASE_URL=xxx
SUPABASE_KEY=xxx

# Redis (optional)
REDIS_URL=redis://localhost:6379

# Encryption
ENCRYPTION_KEY=xxx  # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## 🏗️ Architecture

### Frontend Modules
- **cart-manager.js**: Handles cart analysis and display
- **meal-planner.js**: Weekly calendar with drag-and-drop
- **settings.js**: User preferences management
- **shared.js**: Event bus and global state

### Backend Services
- **Phone normalization**: Prevents cross-user data contamination
- **Redis caching**: 1-hour TTL with force refresh
- **Fernet encryption**: Secure password storage
- **Data isolation**: User data protection

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture documentation.

## 🚢 Deployment

### Railway Deployment

1. **Connect GitHub repository**
   ```bash
   git remote add origin https://github.com/yourusername/farmtopeople.git
   git push -u origin main
   ```

2. **Configure Railway**
   - Add Redis service
   - Set environment variables
   - Python 3.8 runtime

3. **Auto-deploy on push**
   ```bash
   git add .
   git commit -m "Deploy updates"
   git push
   ```

### Migration from Monolithic Dashboard

```bash
# 1. Backup original
cp server/templates/dashboard.html server/templates/dashboard_backup.html

# 2. Switch to refactored version
mv server/templates/dashboard_refactored.html server/templates/dashboard.html

# 3. Test locally
python server/server.py

# 4. Deploy
git commit -am "Switch to modular dashboard"
git push
```

## 📊 Key Features

- **Cart Analysis**: Real-time Farm to People cart scraping
- **Meal Planning**: Weekly calendar with ingredient tracking
- **Drag & Drop**: Reorganize meals between days
- **Ingredient Pool**: Track allocation and availability
- **User Preferences**: Dietary restrictions and goals
- **PDF Generation**: Full recipes on demand
- **SMS Integration**: Text-based meal planning (optional)

## 🔒 Security

- **E.164 Phone Normalization**: Prevents data bleeding between users
- **Fernet Encryption**: Secure password storage (not base64!)
- **Data Isolation**: Complete user data separation
- **Redis Caching**: Reduces scraping load with 1hr TTL

## 📖 Documentation

- [CLAUDE.md](CLAUDE.md) - Development guide and best practices
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture
- [docs/ONBOARDING_SYSTEM.md](docs/ONBOARDING_SYSTEM.md) - User onboarding flow
- [DEBUGGING_PROTOCOL.md](DEBUGGING_PROTOCOL.md) - Troubleshooting guide

## 🧪 Testing

```bash
# Test scraper
cd scrapers
python comprehensive_scraper.py

# Test services
python tests/test_refactored_services.py

# Test meal planner
python server/meal_planner.py
```

## 🐛 Common Issues

### Module not found errors
```bash
# Ensure static files are served
ls -la server/static/js/modules/
```

### Redis connection failed
```bash
# System works without Redis (graceful degradation)
# Or install locally: brew install redis
```

### Python version mismatch
```bash
# Railway uses Python 3.8, avoid 3.9+ features
# Check: python --version
```

## 📈 Performance

- **Cart Analysis**: <30 seconds
- **Cache Hit Rate**: >70%
- **Dashboard Load**: <3 seconds
- **Module Sizes**: ~400 lines average (down from 2954)

## 🤝 Contributing

1. Read [CLAUDE.md](CLAUDE.md) for development guidelines
2. Follow the modular architecture pattern
3. Test locally before pushing
4. Document API changes

## 📝 License

Private project - All rights reserved

## 🆘 Support

- GitHub Issues: Report bugs
- Documentation: Check `/docs` folder
- Logs: `tail -f server.log`

---

**Current Focus:** Real ingredient tracking with proper allocation in meal calendar

**Recent Updates (Sept 4, 2025):**
- Dashboard modularized (2954 → 750 lines + modules)
- Real ingredient tracking replacing mock percentages
- Event-driven architecture for module communication
- Fernet encryption replacing base64

*Built with FastAPI, JavaScript modules, and Farm to People integration*