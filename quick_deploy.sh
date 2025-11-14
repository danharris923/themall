#!/bin/bash
# Quick deploy to Digital Ocean

set -e

echo "🚀 Quick Deploy to Digital Ocean"
echo "================================="
echo ""

# Upload latest code to DO
echo "📤 Uploading code to DO..."
rsync -avz --progress \
  --exclude 'node_modules' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude '.git' \
  --exclude 'wordpress-docker' \
  --exclude 'themall/data/*.db' \
  proxy_config.json \
  search_scraper.py \
  search_terms.txt \
  amazon_credentials.json \
  themall/ \
  root@146.190.240.167:/root/themall/

echo ""
echo "✅ Code uploaded!"
echo ""
echo "To test the scraper on DO, run:"
echo "  ssh root@146.190.240.167 \"/root/auto_deploy.sh\""
echo ""
echo "To view logs:"
echo "  ssh root@146.190.240.167 \"tail -f /var/log/themall-deploy.log\""
echo ""
