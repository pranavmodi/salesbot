# 🚂 Railway Deployment Guide

## Quick Setup Steps

### 1. **Create Railway Account**
- Go to [railway.app](https://railway.app)
- Sign up with GitHub

### 2. **Deploy from GitHub**
```bash
# Push your code to GitHub first
git add .
git commit -m "feat: add Railway deployment configuration"
git push origin main
```

### 3. **Connect Repository**
- In Railway dashboard: **New Project** → **Deploy from GitHub repo**
- Select your `salesbot` repository
- Railway will auto-detect it's a Python app

### 4. **Add PostgreSQL Database**
- In your Railway project: **New Service** → **Database** → **PostgreSQL**
- Railway will auto-generate `DATABASE_URL`

### 5. **Configure Environment Variables**
Go to your web service → **Variables** tab and add:

```env
# Core Configuration
FLASK_ENV=production
SECRET_KEY=your-super-secret-key-here
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_MODEL=gpt-4o

# Report Publishing
NETLIFY_PUBLISH_URL=https://possibleminds.in/.netlify/functions/publish-report-persistent
NETLIFY_WEBHOOK_SECRET=your-webhook-secret

# Email Configuration (JSON format - escape quotes)
EMAIL_ACCOUNTS={"account1":{"email":"your@email.com","password":"app-password","smtp_server":"smtp.gmail.com","smtp_port":587,"imap_server":"imap.gmail.com","imap_port":993}}

# Optional Settings
CALENDAR_URL=https://calendly.com/your-calendar-link
AUTO_RESEARCH_ENABLED=true
BASE_URL=https://your-app.up.railway.app
```

### 6. **Deploy**
- Railway automatically deploys when you push to GitHub
- Database migrations run automatically via `Procfile`
- Your app will be available at `https://your-app.up.railway.app`

## 📋 Deployment Files Created

✅ **Procfile** - Defines web server and database migrations  
✅ **requirements.txt** - Updated with versions and gunicorn  
✅ **runtime.txt** - Specifies Python 3.11.9  
✅ **railway.json** - Railway-specific configuration  
✅ **.env.example** - Template for environment variables  

## 🔧 Production Optimizations Applied

- **Gunicorn** WSGI server with 2 workers
- **Connection pooling** configured for all database access
- **Background job** optimized (5min intervals, smaller batches)
- **Auto-migrations** on deployment
- **Health checks** configured

## 💰 Estimated Monthly Cost

- **Railway Hobby Plan**: $5/month
- **Includes**: Web app + PostgreSQL + 500 hours compute
- **Perfect for**: Your sales automation app

## 🚀 Post-Deployment

1. **Test the deployment**: Visit your Railway URL
2. **Upload contacts**: Use the import feature
3. **Configure email accounts**: Use the /config page
4. **Set up campaigns**: Create your first email campaign

## 🔍 Monitoring

- **Railway Dashboard**: Monitor logs, metrics, deployments
- **Database**: Check connection counts and performance
- **Logs**: View real-time application logs

## 🆘 Troubleshooting

**Database Connection Issues:**
- Check `DATABASE_URL` is auto-set by Railway
- Verify connection pooling is working

**Email Issues:**
- Verify `EMAIL_ACCOUNTS` JSON is properly escaped
- Check SMTP credentials

**Build Failures:**
- Check `requirements.txt` versions
- View build logs in Railway dashboard

Ready to deploy! 🎉