# CompIQ Deployment Guide (Free Tier)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USERS                                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        ▼                                       ▼
┌───────────────────┐                 ┌───────────────────┐
│  Firebase Hosting │                 │   Render.com      │
│  (Static SPA)     │◄────API────────►│   (Flask API)     │
│                   │                 │                   │
│  FREE: 10GB/mo    │                 │  FREE: 750hrs/mo  │
└───────────────────┘                 └───────────────────┘
        │                                       │
        │                                       ▼
        │                             ┌───────────────────┐
        │                             │   SQLite DB       │
        │                             │   (Persistent)    │
        │                             └───────────────────┘
        │
        └────► compiq-457.web.app (your URL)
```

## Free Tier Limits

| Service | Free Tier | Notes |
|---------|-----------|-------|
| **Firebase Hosting** | 10GB storage, 360MB/day bandwidth | Plenty for POC |
| **Render.com** | 750 hours/month, sleeps after 15min | Auto-wakes on request |
| **SQLite** | No limit | Persists on Render disk |

---

## Step 1: Deploy Backend to Render.com

### 1.1 Push to GitHub

```bash
cd /Users/abhay.manikanti/Documents/devops/competitor-monitor

# Initialize git (if not already)
git init
git add .
git commit -m "Initial commit - CompIQ Competitor Intelligence"

# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/compiq.git
git push -u origin main
```

### 1.2 Deploy on Render

1. Go to [https://dashboard.render.com](https://dashboard.render.com)
2. Sign up with GitHub
3. Click **"New +"** → **"Web Service"**
4. Connect your `compiq` repository
5. Configure:
   - **Name:** `compiq-api`
   - **Region:** Oregon (US West)
   - **Branch:** `main`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn run:app --bind 0.0.0.0:$PORT --workers 2`
   - **Plan:** **Free**

6. Add Environment Variables:
   ```
   FLASK_ENV=production
   SECRET_KEY=<generate-a-random-key>
   AZURE_OPENAI_KEY=<your-azure-openai-key>
   AZURE_OPENAI_ENDPOINT=https://oai-fort-common-dev-eastus2.openai.azure.com/
   AZURE_OPENAI_DEPLOYMENT=gpt-5-chat
   CORS_ORIGINS=https://compiq-457.web.app
   ```

7. Click **"Create Web Service"**

8. Wait for deployment (3-5 minutes)

9. **Copy your Render URL** (e.g., `https://compiq-api.onrender.com`)

---

## Step 2: Configure Frontend with Backend URL

### 2.1 Update API URL

Edit `frontend/js/app.js` and update the API_BASE_URL:

```javascript
const API_BASE_URL = window.location.hostname === 'localhost' 
    ? '' 
    : 'https://compiq-api.onrender.com'; // ← Your Render URL
```

### 2.2 Build Frontend

```bash
cd frontend
npm install
npm run build
```

---

## Step 3: Deploy Frontend to Firebase

### 3.1 Firebase Setup

```bash
# Login to Firebase (if not already)
firebase login

# Initialize (if needed)
cd /Users/abhay.manikanti/Documents/devops/competitor-monitor
firebase use compiq-457
```

### 3.2 Deploy

```bash
firebase deploy --only hosting
```

### 3.3 Your App is Live!

Visit: **https://compiq-457.web.app**

---

## Quick Deploy Script

Create and run this for one-command deployment:

```bash
#!/bin/bash
# quick-deploy.sh

echo "🔧 Building frontend..."
cd frontend
npm install
npm run build
cd ..

echo "🚀 Deploying to Firebase..."
firebase deploy --only hosting

echo "✅ Deployed to https://compiq-457.web.app"
```

---

## Alternative Backend Options

If Render.com doesn't work for you:

### Option A: Railway.app

1. Go to [railway.app](https://railway.app)
2. Sign up with GitHub
3. New Project → Deploy from GitHub
4. Select your repo
5. Railway auto-detects Python and deploys
6. Add environment variables in Settings
7. **Free:** 500 hours/month, $5 credit

### Option B: Fly.io

1. Install: `brew install flyctl`
2. Login: `fly auth login`
3. Launch: `fly launch`
4. Deploy: `fly deploy`
5. **Free:** 3 shared-cpu-1x VMs

### Option C: PythonAnywhere

1. Go to [pythonanywhere.com](https://www.pythonanywhere.com)
2. Free account
3. Upload code via Git
4. Configure WSGI
5. **Free:** Always-on, limited CPU

---

## Azure Migration (Later)

When you get Azure approval, migrate easily:

### Azure App Service

```bash
# Install Azure CLI
az login
az group create --name compiq-rg --location eastus2
az appservice plan create --name compiq-plan --resource-group compiq-rg --sku B1 --is-linux
az webapp create --name compiq-app --resource-group compiq-rg --plan compiq-plan --runtime "PYTHON:3.12"
az webapp up --name compiq-app --resource-group compiq-rg
```

### Azure Static Web Apps (Frontend)

```bash
az staticwebapp create \
    --name compiq-frontend \
    --resource-group compiq-rg \
    --source https://github.com/YOUR_USERNAME/compiq \
    --branch main \
    --app-location "/frontend" \
    --output-location "dist"
```

---

## Troubleshooting

### Backend not responding

1. Check Render.com dashboard for logs
2. Ensure environment variables are set
3. Free tier sleeps after 15min - first request takes ~30s to wake

### CORS errors

1. Verify `CORS_ORIGINS` env var on Render matches your Firebase URL
2. Check browser console for specific error

### Database issues

1. SQLite file persists on Render's disk
2. For production, consider upgrading to PostgreSQL (Render offers free tier)

### Frontend not loading

1. Ensure `npm run build` completed successfully
2. Check Firebase deployment logs
3. Verify `firebase.json` points to correct `frontend/dist` folder

---

## Cost Summary

| Service | Monthly Cost | Notes |
|---------|-------------|-------|
| Firebase Hosting | **$0** | Free tier |
| Render.com | **$0** | Free tier (sleeps after 15min) |
| **Total** | **$0** | Perfect for POC |

---

## Next Steps

1. ✅ Deploy backend to Render.com
2. ✅ Update frontend API URL
3. ✅ Deploy frontend to Firebase
4. 🎯 Demo to stakeholders
5. 🎯 Get Azure approval
6. 🎯 Migrate to Azure (when ready)
