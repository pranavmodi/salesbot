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

### 3. **Add PostgreSQL Database FIRST**
- In Railway dashboard: **New Project** → **Database** → **PostgreSQL**
- This creates the database service and generates `DATABASE_URL`

### 4. **Connect Repository**
- In your Railway project: **New Service** → **GitHub Repo**
- Select your `salesbot` repository
- Railway will auto-detect it's a Python app

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

✅ **Dockerfile** - Custom Docker build for reliable deployment  
✅ **Procfile** - Defines web server and database migrations  
✅ **requirements.txt** - Updated with versions and gunicorn  
✅ **runtime.txt** - Specifies Python 3.11.9  
✅ **railway.json** - Railway-specific configuration (Docker mode)  
✅ **.dockerignore** - Optimizes Docker build speed  
✅ **.env.example** - Template for environment variables  
✅ **start.sh** - Startup script with migration handling  

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

**Migration Error: "DATABASE_URL environment variable not set"**
- **Solution**: Add PostgreSQL database service BEFORE deploying
- **Steps**: New Service → Database → PostgreSQL
- **Important**: Database must exist before web service deployment

**Database Connection Issues:**
- Check `DATABASE_URL` is auto-set by Railway
- Verify connection pooling is working
- Restart the web service if needed

**Email Issues:**
- Verify `EMAIL_ACCOUNTS` JSON is properly escaped
- Check SMTP credentials
- Test with a single email account first

**Build Failures:**
- Check `requirements.txt` versions
- View build logs in Railway dashboard
- Ensure all dependencies are properly specified

Ready to deploy! 🎉