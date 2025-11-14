#!/usr/bin/env python3
"""
Main scraper script - runs daily via cron on DigitalOcean

Scrapes Amazon deals for a specific site niche and prepares data
for WordPress posting (via engine/wordpress_manager.py)

Usage:
    python scripts/scrape_deals.py --site audio_equipment
    python scripts/scrape_deals.py --site pet_supplies --headless
    python scripts/scrape_deals.py --site all                    # All sites
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper import AmazonScraper
import yaml


def setup_logging(site_name):
    """Setup log file for this scraping session"""
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / f"scrape_{site_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    # Redirect stdout to log file (in addition to console)
    class Logger:
        def __init__(self, filename):
            self.terminal = sys.stdout
            self.log = open(filename, 'w')

        def write(self, message):
            self.terminal.write(message)
            self.log.write(message)
            self.log.flush()

        def flush(self):
            self.terminal.flush()
            self.log.flush()

    sys.stdout = Logger(log_file)
    return log_file


def load_categories():
    """Load category configuration"""
    with open('config/categories.yaml') as f:
        return yaml.safe_load(f)


def scrape_site(site_key, categories_config, scraper):
    """
    Scrape all categories for a specific site

    Args:
        site_key: Site identifier (e.g., 'audio_equipment')
        categories_config: Full categories config dict
        scraper: AmazonScraper instance

    Returns:
        List of all products scraped
    """
    site_config = categories_config[site_key]
    site_name = site_config['name']

    print(f"\n{'='*70}")
    print(f"🎯 Scraping site: {site_name} ({site_key})")
    print(f"{'='*70}\n")

    all_products = []

    for category in site_config['categories']:
        cat_name = category['name']
        cat_url = category['url']

        print(f"\n{'─'*70}")
        print(f"📂 Category: {cat_name}")
        print(f"🔗 URL: {cat_url}")
        print(f"{'─'*70}\n")

        try:
            # Scrape this category
            products = scraper.scrape_category(cat_url)

            # Add category tag to each product
            for product in products:
                product['category'] = cat_name
                product['site'] = site_key

            all_products.extend(products)

            print(f"\n✓ Scraped {len(products)} products from {cat_name}\n")

        except Exception as e:
            print(f"\n❌ Error scraping {cat_name}: {e}\n")
            import traceback
            traceback.print_exc()
            continue

    print(f"\n{'='*70}")
    print(f"📊 Site scraping complete: {site_name}")
    print(f"Total products: {len(all_products)}")
    print(f"{'='*70}\n")

    return all_products


def save_results(site_key, products):
    """
    Save scraped products to JSON file

    Engine module will read this file to filter deals
    and post to WordPress

    Args:
        site_key: Site identifier
        products: List of product dicts
    """
    output_dir = Path('data/scraped')
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = output_dir / f"{site_key}_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(products, f, indent=2)

    print(f"💾 Results saved to: {output_file}")

    # Also save as "latest" for easy access
    latest_file = output_dir / f"{site_key}_latest.json"
    with open(latest_file, 'w') as f:
        json.dump(products, f, indent=2)

    print(f"💾 Latest results: {latest_file}")

    return output_file


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Scrape Amazon deals for a site')
    parser.add_argument('--site', required=True, help='Site key from categories.yaml (or "all")')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    args = parser.parse_args()

    # Setup logging
    log_file = setup_logging(args.site)
    print(f"📝 Logging to: {log_file}\n")

    # Load configuration
    categories_config = load_categories()

    # Determine which sites to scrape
    if args.site == 'all':
        site_keys = list(categories_config.keys())
        print(f"🌍 Scraping ALL sites: {', '.join(site_keys)}\n")
    else:
        if args.site not in categories_config:
            print(f"❌ Site '{args.site}' not found in config!")
            print(f"Available sites: {', '.join(categories_config.keys())}")
            sys.exit(1)
        site_keys = [args.site]

    # Create scraper instance
    print(f"🔧 Initializing scraper (headless={args.headless})...\n")
    scraper = AmazonScraper(
        config_path='config/scraper.yaml',
        headless=args.headless
    )

    # Scrape each site
    for site_key in site_keys:
        try:
            products = scrape_site(site_key, categories_config, scraper)

            if products:
                save_results(site_key, products)
            else:
                print(f"⚠️  No products scraped for {site_key}")

        except KeyboardInterrupt:
            print(f"\n⚠️  Scraping interrupted by user")
            break

        except Exception as e:
            print(f"\n❌ Error scraping site {site_key}: {e}")
            import traceback
            traceback.print_exc()
            continue

    print(f"\n{'='*70}")
    print("🎉 All scraping complete!")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    main()
