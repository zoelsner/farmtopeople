# 🚀 Production Deployment & Operations Guide

**Date:** September 4, 2025  
**Scope:** Complete production deployment and operations documentation  
**Current State:** Railway deployment with manual processes

---

## 🎯 Current Deployment Assessment

### **Production Environment**
- **Platform:** Railway.app
- **URL:** https://farmtopeople-production.up.railway.app
- **Branch:** `feature/customer-automation`
- **Database:** Supabase (PostgreSQL)
- **SMS Service:** Vonage API
- **AI Service:** OpenAI GPT-5

### **Deployment Gaps**
- **No automated deployment pipeline**
- **Manual environment variable management**
- **No database migration procedures**
- **Limited monitoring and alerting**
- **No rollback procedures**
- **No staging environment**

---

## 🏗️ Production Architecture

### **Current Production Stack**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Railway.app   │────│   Supabase      │────│   Vonage SMS    │
│   (FastAPI)     │    │   (PostgreSQL)  │    │   (API)         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Playwright    │    │   OpenAI        │    │   File Storage  │
│   (Scraping)    │    │   (GPT-5)       │    │   (PDFs)        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### **Environment Variables**
```bash
# Core Application
DEBUG=false
LOG_LEVEL=INFO
SECRET_KEY=your-secret-key

# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key

# SMS Service
VONAGE_API_KEY=your-vonage-key
VONAGE_API_SECRET=your-vonage-secret
VONAGE_PHONE_NUMBER=18334391183

# AI Service
OPENAI_API_KEY=your-openai-key

# Farm to People (Test Account)
FTP_EMAIL=your-test-email@example.com
FTP_PASSWORD=your-test-password

# Optional Services
REDIS_URL=redis://localhost:6379  # Future caching
SENTRY_DSN=your-sentry-dsn        # Error tracking
```

---

## 🚀 Deployment Procedures

### **1. Railway Deployment**

#### **Initial Setup**
```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login to Railway
railway login

# 3. Link to existing project
railway link

# 4. Set environment variables
railway variables set OPENAI_API_KEY=your-key
railway variables set SUPABASE_URL=your-url
railway variables set SUPABASE_KEY=your-key
railway variables set VONAGE_API_KEY=your-key
railway variables set VONAGE_API_SECRET=your-secret
railway variables set VONAGE_PHONE_NUMBER=18334391183
railway variables set FTP_EMAIL=your-email
railway variables set FTP_PASSWORD=your-password

# 5. Deploy
railway up
```

#### **Automated Deployment**
```yaml
# .github/workflows/deploy.yml
name: Deploy to Railway

on:
  push:
    branches: [main, feature/customer-automation]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install Railway CLI
        run: npm install -g @railway/cli
      
      - name: Deploy to Railway
        run: railway up --detach
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

### **2. Database Management**

#### **Migration Procedures**
```bash
# 1. Create migration
python -m alembic revision --autogenerate -m "Add meal planning tables"

# 2. Review migration
cat alembic/versions/xxx_add_meal_planning_tables.py

# 3. Apply migration (staging)
railway run --service staging python -m alembic upgrade head

# 4. Apply migration (production)
railway run --service production python -m alembic upgrade head
```

#### **Database Backup**
```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump $SUPABASE_URL > backup_$DATE.sql
aws s3 cp backup_$DATE.sql s3://farmtopeople-backups/
```

### **3. Environment Management**

#### **Staging Environment**
```bash
# Create staging environment
railway environment create staging

# Set staging variables
railway variables set --environment staging DEBUG=true
railway variables set --environment staging LOG_LEVEL=DEBUG
railway variables set --environment staging MOCK_SMS=true

# Deploy to staging
railway up --environment staging
```

#### **Production Environment**
```bash
# Production-specific settings
railway variables set --environment production DEBUG=false
railway variables set --environment production LOG_LEVEL=INFO
railway variables set --environment production SENTRY_DSN=your-sentry-dsn
```

---

## 📊 Monitoring & Observability

### **1. Application Monitoring**

#### **Health Checks**
```python
# server/health.py
from fastapi import APIRouter
import psutil
import os

router = APIRouter()

@router.get("/health")
async def health_check():
    """Comprehensive health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": os.getenv("APP_VERSION", "unknown"),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "memory_usage": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent,
        "services": {
            "database": await check_database_connection(),
            "sms": await check_sms_service(),
            "ai": await check_ai_service()
        }
    }

@router.get("/metrics")
async def metrics():
    """Application metrics"""
    return {
        "requests_total": get_request_count(),
        "sms_sent_total": get_sms_count(),
        "meals_generated_total": get_meal_count(),
        "active_users": get_active_user_count()
    }
```

#### **Error Tracking**
```python
# server/monitoring.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

# Initialize Sentry
sentry_sdk.init(
    dsn=os.getenv("SENTRY_DSN"),
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,
    environment=os.getenv("ENVIRONMENT", "development")
)

# Custom error tracking
def track_meal_generation_error(error, user_phone, cart_data):
    sentry_sdk.capture_exception(error, extra={
        "user_phone": user_phone,
        "cart_items_count": len(cart_data.get("items", [])),
        "error_context": "meal_generation"
    })
```

### **2. Performance Monitoring**

#### **Response Time Tracking**
```python
# server/middleware/monitoring.py
import time
from fastapi import Request

@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    # Log slow requests
    if process_time > 5.0:
        logger.warning(f"Slow request: {request.url} took {process_time:.2f}s")
    
    # Add timing header
    response.headers["X-Process-Time"] = str(process_time)
    
    return response
```

#### **Resource Monitoring**
```python
# server/monitoring/resource_monitor.py
import psutil
import asyncio

class ResourceMonitor:
    def __init__(self):
        self.memory_threshold = 80  # 80% memory usage
        self.cpu_threshold = 90     # 90% CPU usage
    
    async def check_resources(self):
        """Check system resources"""
        memory_percent = psutil.virtual_memory().percent
        cpu_percent = psutil.cpu_percent()
        
        if memory_percent > self.memory_threshold:
            await self.alert_high_memory(memory_percent)
        
        if cpu_percent > self.cpu_threshold:
            await self.alert_high_cpu(cpu_percent)
    
    async def alert_high_memory(self, usage):
        """Alert on high memory usage"""
        message = f"High memory usage: {usage}%"
        await send_alert("memory", message)
    
    async def alert_high_cpu(self, usage):
        """Alert on high CPU usage"""
        message = f"High CPU usage: {usage}%"
        await send_alert("cpu", message)
```

---

## 🔧 Operations Procedures

### **1. Deployment Checklist**

#### **Pre-Deployment**
- [ ] Run full test suite
- [ ] Check code coverage (80%+)
- [ ] Review database migrations
- [ ] Update environment variables
- [ ] Backup production database
- [ ] Notify team of deployment

#### **Deployment**
- [ ] Deploy to staging first
- [ ] Run smoke tests on staging
- [ ] Deploy to production
- [ ] Verify health checks
- [ ] Monitor error rates
- [ ] Test critical user flows

#### **Post-Deployment**
- [ ] Monitor for 30 minutes
- [ ] Check error logs
- [ ] Verify SMS functionality
- [ ] Test cart scraping
- [ ] Monitor performance metrics
- [ ] Document any issues

### **2. Rollback Procedures**

#### **Emergency Rollback**
```bash
# 1. Stop current deployment
railway service stop

# 2. Rollback to previous version
railway rollback

# 3. Verify rollback
railway logs --tail

# 4. Test critical functionality
curl https://farmtopeople-production.up.railway.app/health
```

#### **Database Rollback**
```bash
# 1. Restore from backup
psql $SUPABASE_URL < backup_20250904_120000.sql

# 2. Verify data integrity
python -c "from server.database import check_data_integrity; check_data_integrity()"

# 3. Test application
python -m pytest tests/integration/test_database/
```

### **3. Incident Response**

#### **Severity Levels**
- **P0 (Critical):** Service down, data loss, security breach
- **P1 (High):** Major functionality broken, performance degraded
- **P2 (Medium):** Minor functionality issues, non-critical bugs
- **P3 (Low):** Cosmetic issues, enhancement requests

#### **Response Procedures**
```bash
# P0 Incident Response
1. Acknowledge incident within 5 minutes
2. Create incident channel in Slack
3. Assess impact and scope
4. Implement immediate fix or rollback
5. Communicate status to users
6. Post-incident review within 24 hours

# P1 Incident Response
1. Acknowledge within 30 minutes
2. Assess impact
3. Implement fix or workaround
4. Monitor resolution
5. Post-incident review within 48 hours
```

---

## 📈 Performance Optimization

### **1. Caching Strategy**

#### **Redis Integration**
```python
# server/cache/redis_cache.py
import redis
import json
from typing import Optional

class RedisCache:
    def __init__(self):
        self.redis = redis.from_url(os.getenv("REDIS_URL"))
        self.default_ttl = 3600  # 1 hour
    
    async def get(self, key: str) -> Optional[dict]:
        """Get cached data"""
        data = self.redis.get(key)
        if data:
            return json.loads(data)
        return None
    
    async def set(self, key: str, data: dict, ttl: int = None) -> bool:
        """Set cached data"""
        ttl = ttl or self.default_ttl
        return self.redis.setex(key, ttl, json.dumps(data))
    
    async def delete(self, key: str) -> bool:
        """Delete cached data"""
        return self.redis.delete(key) > 0
```

#### **Cache Implementation**
```python
# server/services/cart_service.py
from server.cache.redis_cache import RedisCache

class CartService:
    def __init__(self):
        self.cache = RedisCache()
    
    async def get_cart_analysis(self, phone: str, force_refresh: bool = False):
        """Get cart analysis with caching"""
        cache_key = f"cart_analysis:{phone}"
        
        if not force_refresh:
            cached = await self.cache.get(cache_key)
            if cached:
                return cached
        
        # Generate fresh analysis
        analysis = await self._generate_cart_analysis(phone)
        
        # Cache for 1 hour
        await self.cache.set(cache_key, analysis, ttl=3600)
        
        return analysis
```

### **2. Database Optimization**

#### **Connection Pooling**
```python
# server/database/pool.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    SUPABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

#### **Query Optimization**
```python
# server/repositories/user_repository.py
from sqlalchemy.orm import selectinload

class UserRepository:
    async def get_user_with_preferences(self, phone: str):
        """Optimized user query with preferences"""
        query = (
            select(User)
            .options(selectinload(User.preferences))
            .where(User.phone == phone)
        )
        return await self.session.execute(query).scalar_one_or_none()
```

---

## 🔒 Security Considerations

### **1. Environment Security**

#### **Secrets Management**
```bash
# Use Railway's built-in secrets management
railway variables set --secret OPENAI_API_KEY=your-key
railway variables set --secret SUPABASE_SERVICE_KEY=your-key

# Never commit secrets to code
echo "*.env" >> .gitignore
echo "secrets/" >> .gitignore
```

#### **Access Control**
```python
# server/middleware/auth.py
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_api_key(token: str = Depends(security)):
    """Verify API key for protected endpoints"""
    if token.credentials != os.getenv("API_KEY"):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return token
```

### **2. Data Protection**

#### **Encryption at Rest**
```python
# server/encryption/data_encryption.py
from cryptography.fernet import Fernet

class DataEncryption:
    def __init__(self):
        self.key = os.getenv("ENCRYPTION_KEY")
        self.cipher = Fernet(self.key.encode())
    
    def encrypt(self, data: str) -> str:
        """Encrypt sensitive data"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()
```

#### **Input Validation**
```python
# server/validators/input_validators.py
from pydantic import BaseModel, validator
import re

class PhoneNumberValidator(BaseModel):
    phone: str
    
    @validator('phone')
    def validate_phone(cls, v):
        if not re.match(r'^\+1\d{10}$', v):
            raise ValueError('Invalid phone number format')
        return v
```

---

## 📋 Maintenance Procedures

### **1. Regular Maintenance**

#### **Daily Tasks**
- [ ] Check application health
- [ ] Review error logs
- [ ] Monitor performance metrics
- [ ] Verify SMS functionality
- [ ] Check database connections

#### **Weekly Tasks**
- [ ] Review security logs
- [ ] Update dependencies
- [ ] Backup database
- [ ] Performance analysis
- [ ] Capacity planning

#### **Monthly Tasks**
- [ ] Security audit
- [ ] Dependency updates
- [ ] Performance optimization
- [ ] Disaster recovery testing
- [ ] Documentation updates

### **2. Capacity Planning**

#### **Resource Monitoring**
```python
# server/monitoring/capacity_monitor.py
class CapacityMonitor:
    def __init__(self):
        self.metrics = {
            "requests_per_minute": 0,
            "active_users": 0,
            "memory_usage": 0,
            "cpu_usage": 0
        }
    
    async def track_usage(self):
        """Track resource usage trends"""
        # Collect metrics
        # Analyze trends
        # Alert on capacity issues
        pass
    
    async def predict_capacity_needs(self):
        """Predict future capacity needs"""
        # Analyze historical data
        # Predict growth trends
        # Recommend scaling actions
        pass
```

This comprehensive production guide provides everything needed to deploy, monitor, and maintain the Farm to People AI Assistant in production.

