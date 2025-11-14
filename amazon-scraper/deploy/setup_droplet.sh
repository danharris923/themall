#!/bin/bash
# Setup script for DigitalOcean droplet
# Run this ONCE on new droplet to install all dependencies
#
# Usage:
#   scp deploy/setup_droplet.sh root@146.190.240.167:~
#   ssh root@146.190.240.167
#   bash setup_droplet.sh

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  DigitalOcean Droplet Setup for Amazon Scraper            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Update system
echo "📦 Updating system packages..."
apt update
apt upgrade -y

echo ""
echo "✅ System updated!"
echo ""

# Install Python 3 and pip
echo "🐍 Installing Python 3..."
apt install -y python3 python3-pip python3-venv

python3 --version
pip3 --version

echo ""
echo "✅ Python installed!"
echo ""

# Install Playwright system dependencies
# These are required for Chromium to run in headless mode
echo "🎭 Installing Playwright system dependencies..."
apt install -y \
    libnss3 \
    libnspr4 \
    libdbus-1-3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    libxshmfence1 \
    fonts-liberation \
    libappindicator3-1

echo ""
echo "✅ Playwright dependencies installed!"
echo ""

# Install useful tools
echo "🔧 Installing utility tools..."
apt install -y \
    git \
    curl \
    wget \
    htop \
    nano \
    rsync \
    tree

echo ""
echo "✅ Tools installed!"
echo ""

# Create project directory
echo "📁 Creating project directory..."
mkdir -p ~/themall/amazon-scraper/{scraper,config,scripts,data/cookies,logs,deploy}
cd ~/themall/amazon-scraper

echo ""
echo "✅ Directory structure created!"
echo ""

# Create virtual environment
echo "🌐 Creating Python virtual environment..."
python3 -m venv venv

# Activate and upgrade pip
source venv/bin/activate
pip install --upgrade pip

echo ""
echo "✅ Virtual environment created!"
echo ""

# Create a simple requirements file for initial setup
# The real requirements.txt will be synced via deploy.sh
cat > /tmp/initial_requirements.txt << 'EOF'
playwright==1.48.0
pyyaml==6.0.2
colorama==0.4.6
EOF

echo "📚 Installing initial Python packages..."
pip install -r /tmp/initial_requirements.txt

echo ""
echo "✅ Python packages installed!"
echo ""

# Install Playwright browsers
echo "🎭 Installing Playwright Chromium browser..."
playwright install chromium
playwright install-deps

echo ""
echo "✅ Playwright browser installed!"
echo ""

# Setup swap file (important for 1GB droplet)
if [ ! -f /swapfile ]; then
    echo "💾 Creating 2GB swap file..."
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "✅ Swap file created!"
else
    echo "✅ Swap file already exists"
fi

echo ""
swapon --show
echo ""

# Setup UFW firewall (allow SSH only)
echo "🔒 Configuring firewall..."
ufw --force enable
ufw allow 22/tcp
ufw status

echo ""
echo "✅ Firewall configured!"
echo ""

# Create helper script for activating venv
cat > ~/themall/amazon-scraper/activate.sh << 'EOF'
#!/bin/bash
# Quick script to activate venv and cd to project
cd ~/themall/amazon-scraper
source venv/bin/activate
echo "✅ Virtual environment activated!"
echo "📁 Current directory: $(pwd)"
echo ""
echo "Available commands:"
echo "  python scripts/test_scraper.py           # Test scraper"
echo "  python scripts/scrape_deals.py --site X  # Run scraper"
echo "  tail -f logs/scraper.log                 # View logs"
echo "  crontab -l                                # View cron jobs"
echo ""
EOF
chmod +x ~/themall/amazon-scraper/activate.sh

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ✅ DROPLET SETUP COMPLETE!                               ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📋 Next steps:"
echo "  1. From your LOCAL machine, run: bash deploy/deploy.sh"
echo "  2. This will sync your code to the droplet"
echo "  3. Then test: ssh root@146.190.240.167"
echo "  4. Run: source ~/themall/amazon-scraper/activate.sh"
echo "  5. Test: python scripts/test_scraper.py --headless"
echo ""
echo "🔗 Quick SSH: ssh root@146.190.240.167"
echo "📊 View resources: htop"
echo "📝 View logs: tail -f ~/themall/amazon-scraper/logs/scraper.log"
echo ""
