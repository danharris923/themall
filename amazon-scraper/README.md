# Amazon Canada Scraper - TheMall Project

Multi-site Amazon deal scraper with Playwright. Develops on Ubuntu 24 LTS, deploys to DigitalOcean.

## Quick Start (Local Development)

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium
playwright install-deps

# Test scraper (visible browser)
python scripts/test_scraper.py

# Test headless mode
python scripts/test_scraper.py --headless

# Scrape a specific site
python scripts/scrape_deals.py --site audio_equipment --headless
```

## Project Structure

```
themall/
├── scraper/                 # Scraper module
│   ├── __init__.py
│   └── amazon_scraper.py    # Main scraper with Playwright + stealth
│
├── config/
│   ├── scraper.yaml         # Scraper settings (delays, selectors, limits)
│   └── categories.yaml      # 10 niches × category URLs
│
├── scripts/
│   ├── test_scraper.py      # Quick test (1 page)
│   └── scrape_deals.py      # Main script (multi-page, saves JSON)
│
├── deploy/
│   ├── setup_droplet.sh     # One-time droplet setup
│   ├── deploy.sh            # Deploy code via rsync
│   └── crontab              # Daily scraping schedule
│
├── data/
│   ├── cookies/             # Session cookies (avoid CAPTCHAs)
│   └── scraped/             # JSON output files
│
├── logs/                    # Verbose logs
│
├── requirements.txt
├── DROPLET_ACCESS.md        # Droplet IP, login instructions
└── README.md
```

## Features

### Scraper (`scraper/amazon_scraper.py`)
- **Playwright-based**: Chromium browser with full JS rendering
- **Stealth mode**: Removes webdriver detection, mimics human behavior
- **Anti-bot measures**:
  - Random delays between pages
  - Mouse movements & scrolling
  - Cookie persistence
  - Canadian locale/timezone/geolocation
- **CAPTCHA detection**: Waits 30s if CAPTCHA detected
- **Retry logic**: Exponential backoff on timeouts
- **Detailed logging**: Colored output (local), plain text (cron)

### Extracted Data
Each product includes:
- `asin` - Amazon Standard ID
- `title`, `brand`, `image_url`
- `price_current`, `price_original`, `discount_percent`
- `rating`, `review_count`
- `product_url`, `scraped_at`

### Configuration

**`config/scraper.yaml`**:
- Delays (5-10s between pages)
- Limits (5 pages = ~100 products per category)
- CSS selectors (update if Amazon changes layout)
- Browser settings (viewport, locale, geolocation)

**`config/categories.yaml`**:
- 10 niches (audio, pets, home, electronics, etc.)
- 2-4 category URLs per niche
- URLs pre-sorted by discount (`&s=discount-desc`)

## DigitalOcean Deployment

### 1. Initial Setup (One-Time)

```bash
# SSH into droplet
ssh root@146.190.240.167

# Upload and run setup script
scp deploy/setup_droplet.sh root@146.190.240.167:~
ssh root@146.190.240.167 'bash setup_droplet.sh'
```

This installs:
- Python 3 + pip
- Playwright + Chromium + system dependencies
- 2GB swap file (important for 1GB RAM)
- UFW firewall (SSH only)
- Project directory structure

### 2. Deploy Code (Repeatable)

```bash
# From LOCAL machine
bash deploy/deploy.sh
```

This does:
- Syncs code via rsync
- Installs Python requirements
- Installs Playwright browsers
- Sets up cron jobs

### 3. Verify Deployment

```bash
# SSH into droplet
ssh root@146.190.240.167

# Activate environment
source ~/themall/amazon-scraper/activate.sh

# Test scraper
python scripts/test_scraper.py --headless

# Check cron jobs
crontab -l
```

### 4. Monitor

```bash
# View live logs
tail -f ~/themall/amazon-scraper/logs/scraper.log
tail -f ~/themall/amazon-scraper/logs/cron_audio.log

# Check system resources
htop

# View scraped data
ls -lh ~/themall/amazon-scraper/data/scraped/
cat ~/themall/amazon-scraper/data/scraped/audio_equipment_latest.json | head -50
```

## Cron Schedule

Runs daily starting at 1 AM EST, staggered by 15 minutes:

| Time    | Site                     |
|---------|--------------------------|
| 1:00 AM | Audio Equipment          |
| 1:15 AM | Pet Supplies             |
| 1:30 AM | Home & Kitchen           |
| 1:45 AM | Electronics              |
| 2:00 AM | Sports & Outdoors        |
| 2:15 AM | Toys & Games             |
| 2:30 AM | Beauty & Personal Care   |
| 2:45 AM | Automotive               |
| 3:00 AM | Tools & Home Improvement |
| 3:15 AM | Garden & Outdoor         |
| 4:00 AM | Cleanup old logs         |

## Troubleshooting

### CAPTCHA Detected
- Scraper waits 30s automatically
- If persistent, try changing IP (restart droplet)
- Consider residential proxy

### Out of Memory
- 2GB swap file should help
- Reduce `max_pages_per_category` in config
- Upgrade to 2GB droplet ($12/mo)

### Amazon Changed Layout
- Update CSS selectors in `config/scraper.yaml`
- Test locally first: `python scripts/test_scraper.py`

### Playwright Not Found
```bash
source venv/bin/activate
playwright install chromium
playwright install-deps
```

## Next Steps (Engine Module)

The scraper outputs raw JSON files to `data/scraped/`. Next phases:

1. **Deal Filtering** (`engine/deal_filter.py`):
   - Apply discount % threshold (20%+)
   - Filter by rating (4.0+)
   - Remove low-quality deals

2. **WordPress Integration** (`engine/wordpress_manager.py`):
   - WP-CLI SSH connection
   - Post deals as WooCommerce products
   - Update existing products

3. **Database** (`engine/database.py`):
   - Track posted deals
   - Avoid duplicates
   - Price history

## Development Tips

### Test Locally First
Always test changes locally before deploying:
```bash
# Visible browser (watch scraper work)
python scripts/test_scraper.py

# Headless (like production)
python scripts/test_scraper.py --headless
```

### Update Selectors
If Amazon changes HTML:
1. Run local test with visible browser
2. Inspect elements in Chrome DevTools
3. Update `config/scraper.yaml` selectors
4. Test again locally
5. Deploy via `bash deploy/deploy.sh`

### Add New Site
1. Add to `config/categories.yaml`
2. Test locally: `python scripts/test_scraper.py --category newsite`
3. Deploy: `bash deploy/deploy.sh`
4. Add cron job in `deploy/crontab`

## Security Notes

⚠️ **Important**:
- `DROPLET_ACCESS.md` contains sensitive info - delete after use
- Change droplet root password: `passwd`
- Setup SSH keys (disable password login)
- Keep API token secure
- Rotate credentials regularly

## Requirements

**Local**:
- Ubuntu 24.04 LTS (or compatible Linux)
- Python 3.10+
- 4GB+ RAM recommended

**Production**:
- DigitalOcean droplet (1GB+ RAM)
- Ubuntu 24.04 LTS
- $6/mo minimum ($12/mo recommended)

## License

Private project - not for redistribution.

## Contact

For issues or questions about TheMall project, contact project maintainer.
