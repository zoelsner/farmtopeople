# 🚂 Railway.app Deployment Guide

## Quick Start (5 minutes to deploy!)

### Step 1: Install Railway CLI
```bash
npm install -g @railway/cli
```

### Step 2: Login to Railway
```bash
railway login
```
This will open your browser - sign up/login with GitHub.

### Step 3: Create New Project
```bash
railway new
```
- Choose "Empty Project"
- Name it: `farmtopeople-ai`

### Step 4: Link to Your Repo
```bash
railway link
```
Select the project you just created.

### Step 5: Set Environment Variables
```bash
# Vonage SMS
railway variables set VONAGE_API_KEY=d0ca42a8
railway variables set VONAGE_API_SECRET=AVcfwnPfagVp0R2x
railway variables set VONAGE_PHONE_NUMBER=2019773745

# OpenAI
railway variables set OPENAI_API_KEY=your_openai_key_here

# Supabase  
railway variables set SUPABASE_URL=https://zybssxnapxqziolkozjy.supabase.co
railway variables set SUPABASE_KEY=your_supabase_key_here

# Optional - Farm to People fallback credentials
railway variables set EMAIL=zooelsner@gmail.com
railway variables set PASSWORD=Trinidad1440*
```

### Step 6: Deploy!
```bash
railway up
```

### Step 7: Get Your URL
```bash
railway domain
```
This will give you your public URL (e.g., `https://farmtopeople-ai-production.up.railway.app`)

### Step 8: Update Vonage Webhook
1. Go to Vonage Dashboard
2. Update webhook URL to: `https://your-railway-url.up.railway.app/webhook/inbound-sms`
3. Save settings

### Step 9: Test!
Text "plan" to your Vonage number and watch the magic happen! 🎉

## 📊 Railway Dashboard

After deployment, you can monitor:
- **Logs**: Real-time application logs
- **Metrics**: CPU, Memory, Network usage
- **Variables**: Environment variables
- **Deployments**: Deployment history

Access at: https://railway.app/dashboard

## 🔧 Advanced Configuration

### Custom Domain (Optional)
```bash
railway domain add yourdomain.com
```

### Scale Up for Production
1. Go to Railway Dashboard
2. Click your project
3. Go to "Settings" → "Resources"
4. Increase to:
   - **CPU**: 2 vCPU
   - **Memory**: 4GB
   - **Disk**: 10GB

### Background Jobs (Future Enhancement)
Add Redis addon:
```bash
railway add redis
```

## 🐛 Troubleshooting

### "Build Failed"
Check the build logs:
```bash
railway logs --build
```

Common fixes:
- Ensure `requirements.txt` is up to date
- Check Dockerfile syntax
- Verify all imports work

### "App Crashed"
Check runtime logs:
```bash
railway logs
```

Common issues:
- Missing environment variables
- Port binding (should use Railway's $PORT)
- Browser installation issues

### "SMS Not Working"
1. Check webhook URL is correct
2. Verify environment variables are set
3. Check logs for errors: `railway logs`

### "Browser Issues"
If Playwright fails:
1. Check if Chrome installed properly in logs
2. Try redeploying: `railway up --detach`
3. Check memory usage isn't maxed out

## 💰 Cost Monitoring

Railway pricing:
- **Hobby Plan**: $5/month + usage
- **Usage**: ~$0.10/hour for our app
- **Total**: Expect ~$15-25/month

Monitor usage at: https://railway.app/account/usage

## 🔄 Continuous Deployment

Railway auto-deploys from your GitHub branch!

To set up:
1. Connect GitHub repo in Railway dashboard
2. Choose branch: `feature/customer-automation`
3. Enable auto-deploy

Every `git push` will trigger a new deployment.

## 📝 Environment Variables Reference

```env
# Required for SMS
VONAGE_API_KEY=your_key
VONAGE_API_SECRET=your_secret  
VONAGE_PHONE_NUMBER=your_number

# Required for AI
OPENAI_API_KEY=your_openai_key

# Required for Database
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key

# Optional fallback
EMAIL=your_ftp_email
PASSWORD=your_ftp_password
```

## 🎯 Post-Deployment Checklist

- [ ] App deployed successfully
- [ ] Environment variables set
- [ ] Domain configured
- [ ] Vonage webhook updated
- [ ] Test SMS flow works
- [ ] Monitor logs for 24 hours
- [ ] Set up alerts/monitoring

## 🚨 Emergency Commands

### Rollback Deployment
```bash
railway rollback
```

### Check Service Status
```bash
railway status
```

### View Environment Variables
```bash
railway variables
```

### Restart Service
```bash
railway restart
```

## 📞 Support

- **Railway Docs**: https://docs.railway.app
- **Discord**: https://discord.gg/railway
- **Status**: https://status.railway.app

---

**You're all set!** Railway makes deployment incredibly simple compared to other platforms. The whole process should take under 10 minutes! 🚀
