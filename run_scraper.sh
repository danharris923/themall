#!/bin/bash
# Multi-Site Scraper Runner
# Usage: ./run_scraper.sh <site_name>
# Example: ./run_scraper.sh audiogear

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to show usage
show_usage() {
    echo -e "${CYAN}Multi-Site Amazon Scraper${NC}"
    echo ""
    echo "Usage:"
    echo "  $0 <site_name>      Run scraper for a specific site"
    echo "  $0 --list          List all available sites"
    echo "  $0 --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 audiogear       Scrape audio gear deals"
    echo "  $0 camping         Scrape camping gear deals"
    echo "  $0 photography     Scrape photography equipment deals"
    echo ""
}

# Parse arguments
if [ $# -eq 0 ]; then
    show_usage
    exit 1
fi

case "$1" in
    --help|-h)
        show_usage
        exit 0
        ;;
    --list|-l)
        python3 search_scraper.py --list-sites
        exit 0
        ;;
    *)
        SITE_NAME="$1"
        ;;
esac

# Check if site config exists
if [ ! -f "sites/${SITE_NAME}.yaml" ]; then
    echo -e "${RED}Error: Site config not found: sites/${SITE_NAME}.yaml${NC}"
    echo ""
    echo -e "${YELLOW}Available sites:${NC}"
    python3 search_scraper.py --list-sites
    exit 1
fi

# Check if venv exists
if [ -d "venv" ]; then
    echo -e "${GREEN}Activating virtual environment...${NC}"
    source venv/bin/activate
fi

# Run the scraper
echo -e "${CYAN}Starting scraper for site: ${SITE_NAME}${NC}"
echo -e "${CYAN}$(date)${NC}"
echo ""

python3 search_scraper.py --site "$SITE_NAME"

echo ""
echo -e "${GREEN}✅ Scraping completed!${NC}"
echo -e "${CYAN}$(date)${NC}"
