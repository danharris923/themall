#!/bin/bash
# Run all configured sites sequentially
# Useful for cron jobs: 0 2 * * * /root/themall/run_all_sites.sh >> /var/log/scraper-all.log 2>&1

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}======================================${NC}"
echo -e "${CYAN}Multi-Site Scraper - Running All Sites${NC}"
echo -e "${CYAN}Started: $(date)${NC}"
echo -e "${CYAN}======================================${NC}"
echo ""

# Get list of all site configs
SITES_DIR="$SCRIPT_DIR/sites"
SITE_COUNT=0
SUCCESS_COUNT=0
FAIL_COUNT=0

if [ ! -d "$SITES_DIR" ]; then
    echo "Error: Sites directory not found: $SITES_DIR"
    exit 1
fi

# Run each site
for config_file in "$SITES_DIR"/*.yaml; do
    if [ -f "$config_file" ]; then
        SITE_NAME=$(basename "$config_file" .yaml)
        SITE_COUNT=$((SITE_COUNT + 1))

        echo -e "${CYAN}[$SITE_COUNT] Running site: $SITE_NAME${NC}"
        echo -e "${CYAN}$(date)${NC}"
        echo ""

        if ./run_scraper.sh "$SITE_NAME"; then
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
            echo -e "${GREEN}✅ $SITE_NAME completed successfully${NC}"
        else
            FAIL_COUNT=$((FAIL_COUNT + 1))
            echo -e "\033[0;31m❌ $SITE_NAME failed\033[0m"
        fi

        echo ""
        echo -e "${CYAN}--------------------------------------${NC}"
        echo ""
    fi
done

# Summary
echo -e "${CYAN}======================================${NC}"
echo -e "${CYAN}All Sites Completed${NC}"
echo -e "${CYAN}Finished: $(date)${NC}"
echo -e "${CYAN}======================================${NC}"
echo -e "Total Sites: $SITE_COUNT"
echo -e "${GREEN}Successful: $SUCCESS_COUNT${NC}"
if [ $FAIL_COUNT -gt 0 ]; then
    echo -e "\033[0;31mFailed: $FAIL_COUNT\033[0m"
else
    echo -e "Failed: $FAIL_COUNT"
fi
echo ""
