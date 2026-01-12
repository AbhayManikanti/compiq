#!/bin/bash
# CompIQ - Azure Deployment Script
# This script deploys the full-stack Flask app to Azure App Service

set -e

# ============================================================
# CONFIGURATION - Update these values
# ============================================================
RESOURCE_GROUP="compiq-rg"
LOCATION="eastus2"                    # Same region as your OpenAI
APP_NAME="compiq-app"                 # Must be globally unique
APP_SERVICE_PLAN="compiq-plan"
SKU="B1"                              # B1 = ~$13/mo, F1 = Free (limited)

# ============================================================
# COLORS
# ============================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}"
echo "╔════════════════════════════════════════════════════════╗"
echo "║       CompIQ - Azure Deployment                        ║"
echo "╚════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ============================================================
# CHECK PREREQUISITES
# ============================================================
echo -e "${YELLOW}[1/6] Checking prerequisites...${NC}"

if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI not installed${NC}"
    echo "Install it: brew install azure-cli"
    exit 1
fi

# Check if logged in
if ! az account show &> /dev/null; then
    echo "Please login to Azure..."
    az login
fi

SUBSCRIPTION=$(az account show --query name -o tsv)
echo -e "${GREEN}✓ Logged in to: $SUBSCRIPTION${NC}"

# ============================================================
# CREATE RESOURCE GROUP
# ============================================================
echo -e "${YELLOW}[2/6] Creating resource group...${NC}"

if az group show --name $RESOURCE_GROUP &> /dev/null; then
    echo -e "${GREEN}✓ Resource group '$RESOURCE_GROUP' already exists${NC}"
else
    az group create --name $RESOURCE_GROUP --location $LOCATION
    echo -e "${GREEN}✓ Created resource group '$RESOURCE_GROUP'${NC}"
fi

# ============================================================
# CREATE APP SERVICE PLAN
# ============================================================
echo -e "${YELLOW}[3/6] Creating App Service Plan...${NC}"

if az appservice plan show --name $APP_SERVICE_PLAN --resource-group $RESOURCE_GROUP &> /dev/null; then
    echo -e "${GREEN}✓ App Service Plan already exists${NC}"
else
    az appservice plan create \
        --name $APP_SERVICE_PLAN \
        --resource-group $RESOURCE_GROUP \
        --sku $SKU \
        --is-linux
    echo -e "${GREEN}✓ Created App Service Plan (SKU: $SKU)${NC}"
fi

# ============================================================
# CREATE WEB APP
# ============================================================
echo -e "${YELLOW}[4/6] Creating Web App...${NC}"

if az webapp show --name $APP_NAME --resource-group $RESOURCE_GROUP &> /dev/null; then
    echo -e "${GREEN}✓ Web App '$APP_NAME' already exists${NC}"
else
    az webapp create \
        --name $APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --plan $APP_SERVICE_PLAN \
        --runtime "PYTHON:3.12"
    echo -e "${GREEN}✓ Created Web App '$APP_NAME'${NC}"
fi

# ============================================================
# CONFIGURE APP SETTINGS
# ============================================================
echo -e "${YELLOW}[5/6] Configuring app settings...${NC}"

# Read from .env file if it exists
if [ -f .env ]; then
    source .env
fi

az webapp config appsettings set \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --settings \
        FLASK_ENV=production \
        SCM_DO_BUILD_DURING_DEPLOYMENT=true \
        AZURE_OPENAI_KEY="${AZURE_OPENAI_KEY:-}" \
        AZURE_OPENAI_ENDPOINT="${AZURE_OPENAI_ENDPOINT:-https://oai-fort-common-dev-eastus2.openai.azure.com/}" \
        AZURE_OPENAI_DEPLOYMENT="${AZURE_OPENAI_DEPLOYMENT:-gpt-5-chat}" \
    --output none

# Configure startup command
az webapp config set \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --startup-file "gunicorn run:app --bind 0.0.0.0:8000 --workers 2 --timeout 120" \
    --output none

echo -e "${GREEN}✓ App settings configured${NC}"

# ============================================================
# DEPLOY CODE
# ============================================================
echo -e "${YELLOW}[6/6] Deploying code...${NC}"

# Create deployment package (exclude unnecessary files)
echo "Creating deployment package..."
zip -r deploy.zip . \
    -x "*.git*" \
    -x "*venv/*" \
    -x "*__pycache__/*" \
    -x "*.pyc" \
    -x "*node_modules/*" \
    -x "*.env" \
    -x "data/*.db" \
    -x "logs/*" \
    -x "*.zip" \
    -x "frontend/node_modules/*" \
    -x "frontend/dist/*"

# Deploy using zip deploy
az webapp deployment source config-zip \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --src deploy.zip

# Clean up
rm -f deploy.zip

echo -e "${GREEN}✓ Code deployed${NC}"

# ============================================================
# DONE
# ============================================================
APP_URL="https://${APP_NAME}.azurewebsites.net"

echo ""
echo -e "${GREEN}"
echo "╔════════════════════════════════════════════════════════╗"
echo "║       ✅ Deployment Complete!                          ║"
echo "╚════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo -e "🌐 Your app is live at: ${GREEN}$APP_URL${NC}"
echo ""
echo "Next steps:"
echo "  1. Set your Azure OpenAI key:"
echo "     az webapp config appsettings set --name $APP_NAME --resource-group $RESOURCE_GROUP --settings AZURE_OPENAI_KEY=your-key"
echo ""
echo "  2. View logs:"
echo "     az webapp log tail --name $APP_NAME --resource-group $RESOURCE_GROUP"
echo ""
echo "  3. Open in browser:"
echo "     open $APP_URL"
echo ""
