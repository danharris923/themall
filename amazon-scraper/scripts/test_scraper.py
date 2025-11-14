#!/usr/bin/env python3
"""
Quick test script for Amazon scraper
Run this locally to verify scraper works before deploying

Usage:
    python scripts/test_scraper.py                    # Test with visible browser
    python scripts/test_scraper.py --headless         # Test in headless mode
    python scripts/test_scraper.py --category audio   # Test specific category
"""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scraper import AmazonScraper
import yaml


def main():
    """Test scraper with a single category"""

    # Parse args
    headless = '--headless' in sys.argv
    test_category = 'audio_equipment'  # Default

    if '--category' in sys.argv:
        idx = sys.argv.index('--category')
        if idx + 1 < len(sys.argv):
            test_category = sys.argv[idx + 1]

    print(f"\n{'='*60}")
    print(f"🧪 Testing Amazon Scraper")
    print(f"{'='*60}")
    print(f"Category: {test_category}")
    print(f"Headless: {headless}")
    print(f"{'='*60}\n")

    # Load categories
    with open('config/categories.yaml') as f:
        categories = yaml.safe_load(f)

    if test_category not in categories:
        print(f"❌ Category '{test_category}' not found!")
        print(f"Available: {', '.join(categories.keys())}")
        sys.exit(1)

    # Get first category URL for testing
    test_url = categories[test_category]['categories'][0]['url']
    test_name = categories[test_category]['categories'][0]['name']

    print(f"📍 Testing: {test_name}")
    print(f"🔗 URL: {test_url}\n")

    # Create scraper
    scraper = AmazonScraper(
        config_path='config/scraper.yaml',
        headless=headless
    )

    # Scrape just 1 page for testing
    print(f"🚀 Starting test scrape (1 page only)...\n")
    products = scraper.scrape_category(test_url, max_pages=1)

    # Display results
    print(f"\n{'='*60}")
    print(f"📊 Test Results")
    print(f"{'='*60}")
    print(f"Total products scraped: {len(products)}")

    if products:
        print(f"\n🎯 Sample product:")
        sample = products[0]
        print(json.dumps(sample, indent=2))

        # Save to file
        output_file = Path('data/test_results.json')
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w') as f:
            json.dump(products, f, indent=2)
        print(f"\n💾 Full results saved to: {output_file}")

        # Show price distribution
        print(f"\n💰 Price distribution:")
        prices = [p['price_current'] for p in products if p.get('price_current')]
        if prices:
            print(f"  Min: ${min(prices):.2f}")
            print(f"  Max: ${max(prices):.2f}")
            print(f"  Avg: ${sum(prices) / len(prices):.2f}")

        # Show discount distribution
        discounts = [p['discount_percent'] for p in products if p.get('discount_percent', 0) > 0]
        if discounts:
            print(f"\n🎁 Discounts found: {len(discounts)}")
            print(f"  Min: {min(discounts)}%")
            print(f"  Max: {max(discounts)}%")
            print(f"  Avg: {sum(discounts) / len(discounts):.0f}%")

    else:
        print("❌ No products scraped!")
        print("Possible issues:")
        print("  - Amazon changed their HTML structure (update selectors)")
        print("  - CAPTCHA blocked us (try again later)")
        print("  - Network issues")
        print("  - Category URL invalid")

    print(f"\n{'='*60}")
    print("✅ Test complete!")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    main()
