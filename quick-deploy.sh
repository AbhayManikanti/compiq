#!/bin/bash
# Quick deployment script for CompIQ

set -e

RENDER_URL="${RENDER_URL:-https://YOUR-RENDER-APP.onrender.com}"
PROJECT_DIR="/Users/abhay.manikanti/Documents/devops/competitor-monitor"

echo "╔════════════════════════════════════════════╗"
echo "║      CompIQ Deployment Script              ║"
echo "╚════════════════════════════════════════════╝"

cd "$PROJECT_DIR"

# Check if Render URL is set
if [[ "$RENDER_URL" == *"YOUR-RENDER-APP"* ]]; then
    echo ""
    echo "⚠️  Please set your Render.com backend URL first!"
    echo ""
    echo "1. Deploy backend to Render.com"
    echo "2. Get your URL (e.g., https://compiq-api.onrender.com)"
    echo "3. Run: RENDER_URL=https://your-app.onrender.com ./quick-deploy.sh"
    echo ""
    exit 1
fi

# Update frontend with backend URL
echo "📝 Updating API URL in frontend..."
sed -i '' "s|https://YOUR-RENDER-APP.onrender.com|$RENDER_URL|g" frontend/js/app.js
echo "   Backend URL: $RENDER_URL"

# Build frontend
echo ""
echo "🔧 Building frontend..."
cd frontend
if [ ! -d "node_modules" ]; then
    npm install
fi
npm run build
cd ..

# Deploy to Firebase
echo ""
echo "🚀 Deploying to Firebase Hosting..."
firebase deploy --only hosting

echo ""
echo "╔════════════════════════════════════════════╗"
echo "║      ✅ Deployment Complete!               ║"
echo "╚════════════════════════════════════════════╝"
echo ""
echo "🌐 Frontend: https://compiq-457.web.app"
echo "🔧 Backend:  $RENDER_URL"
echo ""
