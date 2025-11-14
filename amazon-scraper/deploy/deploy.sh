#!/bin/bash
# Deploy Amazon scraper to DigitalOcean droplet
# Run this from your LOCAL Ubuntu machine

set -e  # Exit on error

# Configuration
DROPLET_IP="146.190.240.167"
DROPLET_USER="root"
PROJECT_DIR="~/themall"
LOCAL_DIR="/home/ren/Desktop/themall"

echo "🚀 Deploying Amazon Scraper to DigitalOcean..."
echo "📍 Target: $DROPLET_USER@$DROPLET_IP"
echo ""

# Check if we can connect
echo "🔍 Testing SSH connection..."
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes $DROPLET_USER@$DROPLET_IP exit 2>/dev/null; then
    echo "❌ Cannot connect via SSH key"
    echo "💡 You'll need to enter password for each command"
    echo ""
fi

# Sync code to droplet
echo "📦 Syncing code to droplet..."
rsync -avz --progress \
    --exclude='venv/' \
    --exclude='data/' \
    --exclude='logs/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.git/' \
    --exclude='DROPLET_ACCESS.md' \
    "$LOCAL_DIR/" \
    "$DROPLET_USER@$DROPLET_IP:$PROJECT_DIR/"

echo ""
echo "✅ Code synced successfully!"
echo ""

# Install/update dependencies on droplet
echo "📚 Installing Python dependencies on droplet..."
ssh $DROPLET_USER@$DROPLET_IP << 'ENDSSH'
    cd ~/themall/amazon-scraper

    # Activate virtual environment
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi

    source venv/bin/activate

    # Upgrade pip
    pip install --upgrade pip

    # Install requirements
    if [ -f "requirements.txt" ]; then
        echo "Installing requirements..."
        pip install -r requirements.txt
    else
        echo "⚠️  No requirements.txt found!"
    fi

    # Install Playwright browsers if not exists
    if ! playwright --version &> /dev/null; then
        echo "Installing Playwright browsers..."
        playwright install chromium
    fi

    echo "✅ Dependencies installed!"
ENDSSH

echo ""
echo "✅ Dependencies updated successfully!"
echo ""

# Setup cron jobs
echo "⏰ Setting up cron jobs..."
if [ -f "$LOCAL_DIR/deploy/crontab" ]; then
    scp "$LOCAL_DIR/deploy/crontab" "$DROPLET_USER@$DROPLET_IP:/tmp/scraper_cron"
    ssh $DROPLET_USER@$DROPLET_IP "crontab /tmp/scraper_cron && rm /tmp/scraper_cron"
    echo "✅ Cron jobs configured!"
else
    echo "⚠️  No crontab file found, skipping cron setup"
fi

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "📋 Next steps:"
echo "  1. Test scraper: ssh $DROPLET_USER@$DROPLET_IP 'cd ~/themall/amazon-scraper && source venv/bin/activate && python scripts/test_scraper.py'"
echo "  2. View cron jobs: ssh $DROPLET_USER@$DROPLET_IP 'crontab -l'"
echo "  3. Check logs: ssh $DROPLET_USER@$DROPLET_IP 'tail -f ~/themall/amazon-scraper/logs/scraper.log'"
echo ""
echo "🔗 SSH: ssh $DROPLET_USER@$DROPLET_IP"
echo ""
