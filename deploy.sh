#!/bin/bash
# Deployment script for Competitor Monitor to Firebase/Cloud Run
# Project: compiq-457

set -e

PROJECT_ID="compiq-457"
REGION="us-central1"
SERVICE_NAME="competitor-monitor"

echo "🚀 Deploying Competitor Monitor to Firebase + Cloud Run"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Check if logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -1 > /dev/null; then
    echo "❌ Not logged in to gcloud. Run: gcloud auth login"
    exit 1
fi

# Set project
echo "📌 Setting project..."
gcloud config set project $PROJECT_ID

# Check billing
BILLING_ENABLED=$(gcloud billing projects describe $PROJECT_ID --format="value(billingEnabled)")
if [ "$BILLING_ENABLED" != "True" ]; then
    echo "❌ Billing is not enabled on project $PROJECT_ID"
    echo "Please enable billing at: https://console.cloud.google.com/billing/linkedaccount?project=$PROJECT_ID"
    exit 1
fi

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com

# Generate a secret key if not exists
SECRET_KEY=$(openssl rand -hex 32)

# Set environment variables - you can add your Azure OpenAI keys here
echo "🔐 Note: Set your environment variables in Cloud Run console or via gcloud:"
echo "   AZURE_OPENAI_ENDPOINT=your-endpoint"
echo "   AZURE_OPENAI_API_KEY=your-key"
echo "   AZURE_OPENAI_DEPLOYMENT=your-deployment"

# Deploy to Cloud Run
echo "🐳 Building and deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --source . \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --set-env-vars="FLASK_ENV=production,SECRET_KEY=$SECRET_KEY" \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 3 \
    --timeout 300

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format="value(status.url)")
echo ""
echo "✅ Cloud Run deployment complete!"
echo "🌐 Service URL: $SERVICE_URL"

# Deploy Firebase Hosting (optional - for custom domain)
echo ""
echo "📦 Deploying Firebase Hosting..."
firebase deploy --only hosting

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "Your app is available at:"
echo "  Cloud Run: $SERVICE_URL"
echo "  Firebase Hosting: https://$PROJECT_ID.web.app"
echo ""
echo "To add environment variables (Azure OpenAI keys):"
echo "  gcloud run services update $SERVICE_NAME --region=$REGION \\"
echo "    --set-env-vars='AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/'"
echo "    --set-env-vars='AZURE_OPENAI_API_KEY=your-key'"
