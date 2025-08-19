# Farm to People AI - Cloud Deployment Plan

## 🚀 Executive Summary

Deploy the Farm to People SMS meal planning system to a production cloud environment that can:
- Handle multiple concurrent users
- Run browser automation reliably
- Scale for Thursday afternoon spikes
- Maintain 99.9% uptime for SMS responsiveness

## 📊 Architecture Overview

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│                 │     │              │     │                 │
│  Vonage SMS     │────▶│  Cloud       │────▶│    Supabase     │
│  Webhooks       │     │  Server      │     │    Database     │
│                 │     │              │     │                 │
└─────────────────┘     └──────────────┘     └─────────────────┘
                               │
                               ▼
                    ┌──────────────────┐
                    │                  │
                    │  Playwright      │
                    │  Browser Pool    │
                    │                  │
                    └──────────────────┘
```

## 🏆 Recommended Stack: Railway.app

### Why Railway?
1. **Playwright Support**: Native support for headless Chrome
2. **Background Jobs**: Built-in support for long-running tasks
3. **Easy Deployment**: Direct from GitHub
4. **Automatic HTTPS**: SSL certificates included
5. **Environment Variables**: Simple .env management
6. **Cost Effective**: ~$20/month for our needs

### Railway Deployment Steps:
```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login
railway login

# 3. Create new project
railway new

# 4. Link to GitHub repo
railway link

# 5. Deploy
railway up
```

## 🔧 Alternative Options Comparison

### 1. **Heroku** (Traditional Choice)
**Pros:**
- Mature platform
- Great buildpack support
- Easy scaling

**Cons:**
- Playwright requires custom buildpack
- More expensive ($25/month minimum)
- 30-second timeout for web requests

**Setup:**
```bash
heroku create farmtopeople-ai
heroku buildpacks:add --index 1 https://github.com/jontewks/puppeteer-heroku-buildpack
heroku buildpacks:add heroku/python
git push heroku main
```

### 2. **AWS EC2** (Maximum Control)
**Pros:**
- Full control over environment
- Can run full Chrome (not just headless)
- Best for complex browser automation

**Cons:**
- Requires DevOps knowledge
- Manual scaling
- ~$40/month for reliable instance

**Setup:**
```bash
# Use Ubuntu 22.04 AMI
# t3.medium instance (2 vCPU, 4GB RAM)
sudo apt update
sudo apt install python3-pip chromium-browser
pip install -r requirements.txt
# Configure systemd service
```

### 3. **Google Cloud Run** (Serverless)
**Pros:**
- Scales to zero
- Pay per request
- Automatic HTTPS

**Cons:**
- 60-minute timeout max
- Complex Playwright setup
- Cold starts affect performance

### 4. **DigitalOcean App Platform**
**Pros:**
- Simple deployment
- Good Python support
- Predictable pricing

**Cons:**
- Limited Playwright support
- Would need custom Docker image

## 📦 Required Cloud Configurations

### 1. **Dockerfile for Playwright**
```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.41.0-focal

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Install Playwright browsers
RUN playwright install chromium

# Run server
CMD ["uvicorn", "server.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. **Environment Variables**
```env
# Vonage
VONAGE_API_KEY=xxx
VONAGE_API_SECRET=xxx
VONAGE_PHONE_NUMBER=12019773745

# OpenAI
OPENAI_API_KEY=xxx

# Supabase
SUPABASE_URL=xxx
SUPABASE_KEY=xxx

# Server Config
PYTHON_ENV=production
PORT=8000
```

### 3. **Background Job Queue (Redis + Celery)**
```python
# celery_app.py
from celery import Celery
import os

celery_app = Celery(
    'farmtopeople',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379')
)

@celery_app.task
def process_meal_plan(phone_number):
    from scrapers.customize_scraper import main
    # Run scraper in background
    main()
```

## 🔒 Security Considerations

1. **API Keys**: Use environment variables, never commit
2. **Webhook Security**: Validate Vonage signatures
3. **Database**: Use Supabase Row Level Security
4. **Browser**: Run in sandboxed environment
5. **HTTPS**: Always use SSL certificates

## 📈 Scaling Strategy

### Phase 1: Single Server (Current)
- 1 server running FastAPI
- Sequential request processing
- Good for < 100 users

### Phase 2: Worker Pool (Thursday Scale)
- 1 web server + 3 worker servers
- Redis queue for jobs
- Can handle 500+ concurrent users

### Phase 3: Auto-scaling (Future)
- Kubernetes cluster
- Horizontal pod autoscaling
- Browser pool management

## 💰 Cost Analysis

### Railway.app (Recommended)
- **Server**: $20/month
- **Database**: Free (using Supabase)
- **Total**: ~$20/month

### AWS EC2
- **EC2 t3.medium**: $30/month
- **EBS Storage**: $8/month
- **Data Transfer**: $5/month
- **Total**: ~$43/month

### Heroku
- **Dyno**: $25/month
- **Postgres**: $9/month
- **Total**: ~$34/month

## 🚦 Deployment Checklist

### Pre-deployment:
- [ ] All tests passing locally
- [ ] Environment variables documented
- [ ] Backup of working code created
- [ ] Database migrations ready
- [ ] SSL certificate configured

### Deployment:
- [ ] Create cloud account
- [ ] Set up environment variables
- [ ] Deploy application
- [ ] Update Vonage webhook URL
- [ ] Test SMS flow end-to-end

### Post-deployment:
- [ ] Monitor logs for 24 hours
- [ ] Set up error alerting
- [ ] Configure backup strategy
- [ ] Document deployment process

## 🔄 CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
name: Deploy to Railway

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: railwayapp/deploy-action@v1
        with:
          token: ${{ secrets.RAILWAY_TOKEN }}
```

## 📱 Thursday Automation Setup

```python
# scheduler.py
import schedule
import time
from datetime import datetime

def thursday_scrape():
    """Run at 3 PM every Thursday"""
    users = get_all_users_from_supabase()
    for user in users:
        celery_app.send_task('process_meal_plan', args=[user['phone']])

# Schedule for 3 PM Thursday
schedule.every().thursday.at("15:00").do(thursday_scrape)

while True:
    schedule.run_pending()
    time.sleep(60)
```

## 🎯 Next Steps

1. **Immediate (Week 1)**:
   - Sign up for Railway.app
   - Create Dockerfile
   - Deploy current working version
   - Update Vonage webhooks

2. **Short-term (Week 2-3)**:
   - Add Redis for job queue
   - Implement Celery workers
   - Set up monitoring

3. **Long-term (Month 2+)**:
   - Add Thursday automation
   - Implement auto-scaling
   - Add PDF generation

## 🆘 Troubleshooting Cloud Issues

### "Browser not found"
```bash
# Add to Dockerfile
RUN apt-get update && apt-get install -y \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libgtk-3-0
```

### "Timeout errors"
- Increase server timeout: `--timeout 300`
- Use background jobs for scraping
- Implement proper health checks

### "Memory issues"
- Use `--single-process` for Playwright
- Limit concurrent browsers
- Implement browser recycling

## 📞 Support Resources

- **Railway**: https://railway.app/help
- **Playwright**: https://playwright.dev/python/docs/docker
- **FastAPI**: https://fastapi.tiangolo.com/deployment/
- **Supabase**: https://supabase.com/docs

---

**Ready to Deploy?** Start with Railway.app for the smoothest experience!

