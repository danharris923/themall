# Amazon Scraper - Complete Deployment Package

## ✅ What's Been Built

### 1. Core Scraper Module (`scraper/`)
- **`amazon_scraper.py`** (500+ lines) - Full-featured Playwright scraper
  - Stealth browser configuration (removes webdriver detection)
  - Human behavior simulation (mouse, scrolling, delays)
  - Cookie persistence across sessions
  - CAPTCHA detection and waiting
  - Retry logic with exponential backoff
  - Detailed colorized logging

### 2. Configuration Files (`config/`)
- **`scraper.yaml`** - All scraper settings
  - Delays (5-10s between pages)
  - Limits (5 pages, 100 products, 3 retries)
  - CSS selectors for Amazon.ca
  - Browser settings (viewport, locale, geolocation)

- **`categories.yaml`** - 10 site niches
  - Audio Equipment
  - Pet Supplies
  - Home & Kitchen
  - Electronics & Gadgets
  - Sports & Outdoors
  - Toys & Games
  - Beauty & Personal Care
  - Automotive
  - Tools & Home Improvement
  - Garden & Outdoor Living
  - Each with 2-4 pre-sorted category URLs

### 3. Scripts (`scripts/`)
- **`test_scraper.py`** - Quick test (1 page, visible/headless)
- **`scrape_deals.py`** - Production scraper (multi-page, saves JSON)
  - Supports `--site <name>` or `--site all`
  - Comprehensive logging
  - Saves timestamped + "latest" JSON files

### 4. Deployment (`deploy/`)
- **`setup_droplet.sh`** - One-time droplet setup
  - Installs Python, Playwright, system dependencies
  - Creates 2GB swap file
  - Sets up UFW firewall
  - Creates project structure

- **`deploy.sh`** - Repeatable code deployment
  - Syncs code via rsync
  - Installs Python requirements
  - Sets up cron jobs

- **`crontab`** - Daily scraping schedule
  - 10 sites × staggered by 15 minutes
  - Starts 1 AM EST, ends 3:15 AM
  - Automatic log cleanup (7 days)

### 5. Documentation
- **`README.md`** - Complete technical documentation
- **`QUICKSTART.md`** - Step-by-step deployment guide
- **`DROPLET_ACCESS.md`** - Droplet IP, credentials, API commands
- **`requirements.txt`** - All Python dependencies

## 📊 Your DigitalOcean Droplet

```
Name:       scraper
ID:         529749000
IP:         146.190.240.167
Region:     Toronto, Canada
OS:         Ubuntu 24.04 LTS
RAM:        1GB (+ 2GB swap)
CPU:        1 vCPU
Disk:       25GB SSD
Cost:       $6/month
Status:     ✅ ACTIVE
```

## 🚀 Quick Deployment Commands

### 1. Setup Droplet (One Time)
```bash
# Copy setup script
scp deploy/setup_droplet.sh root@146.190.240.167:~

# Run setup
ssh root@146.190.240.167 'bash setup_droplet.sh'
```

### 2. Deploy Code (Repeatable)
```bash
# From local machine
bash deploy/deploy.sh
```

### 3. Test on Droplet
```bash
# SSH in
ssh root@146.190.240.167

# Test scraper
source ~/themall/amazon-scraper/activate.sh
python scripts/test_scraper.py --headless
```

### 4. Monitor
```bash
# View logs
tail -f ~/themall/amazon-scraper/logs/scraper.log
tail -f ~/themall/amazon-scraper/logs/cron_audio.log

# Check cron
crontab -l

# Check system
htop
df -h
```

## 📁 Project Structure

```
themall/
├── scraper/
│   ├── __init__.py
│   └── amazon_scraper.py          # 500+ lines, fully documented
│
├── config/
│   ├── scraper.yaml               # Scraper settings
│   └── categories.yaml            # 10 niches × categories
│
├── scripts/
│   ├── test_scraper.py            # Quick test
│   └── scrape_deals.py            # Production scraper
│
├── deploy/
│   ├── setup_droplet.sh           # One-time setup
│   ├── deploy.sh                  # Deploy code
│   └── crontab                    # Cron schedule
│
├── data/
│   ├── cookies/                   # Session cookies
│   └── scraped/                   # JSON output
│
├── logs/                          # Verbose logs
│
├── requirements.txt               # Python deps
├── README.md                      # Full documentation
├── QUICKSTART.md                  # Deployment guide
└── DROPLET_ACCESS.md              # Droplet info
```

## 🎯 What Each Product Contains

```json
{
  "asin": "B08XYZ123",
  "title": "Sony WH-1000XM4 Headphones",
  "brand": "Sony",
  "image_url": "https://m.media-amazon.com/...",
  "price_current": 298.00,
  "price_original": 399.99,
  "discount_percent": 25,
  "rating": 4.7,
  "review_count": 15234,
  "product_url": "https://www.amazon.ca/dp/B08XYZ123",
  "category": "Headphones",
  "site": "audio_equipment",
  "scraped_at": "2025-11-12T14:30:00"
}
```

## ⏰ Cron Schedule

| Time    | Site                     | Log File               |
|---------|--------------------------|------------------------|
| 1:00 AM | Audio Equipment          | cron_audio.log         |
| 1:15 AM | Pet Supplies             | cron_pets.log          |
| 1:30 AM | Home & Kitchen           | cron_home.log          |
| 1:45 AM | Electronics              | cron_electronics.log   |
| 2:00 AM | Sports & Outdoors        | cron_sports.log        |
| 2:15 AM | Toys & Games             | cron_toys.log          |
| 2:30 AM | Beauty & Personal Care   | cron_beauty.log        |
| 2:45 AM | Automotive               | cron_auto.log          |
| 3:00 AM | Tools & Home Improvement | cron_tools.log         |
| 3:15 AM | Garden & Outdoor         | cron_garden.log        |
| 4:00 AM | Cleanup old logs (7d+)   | -                      |

## 🔧 Key Features

### Anti-Bot Measures
1. **Stealth browser** - Removes webdriver detection
2. **Human behavior** - Random mouse movements, scrolling
3. **Cookie persistence** - Maintains session across runs
4. **Random delays** - 5-10s between pages
5. **Canadian locale** - Toronto geolocation, en-CA
6. **CAPTCHA detection** - Auto-waits 30s

### Reliability
1. **Retry logic** - 3 attempts with exponential backoff
2. **Timeout handling** - 30s page load timeout
3. **Error logging** - Full stack traces
4. **Graceful degradation** - Skips failed products
5. **Connection pooling** - Reuses browser context

### Performance
1. **Headless mode** - No GUI overhead
2. **Efficient selectors** - Minimal DOM queries
3. **Swap file** - Prevents OOM on 1GB RAM
4. **Staggered crons** - Prevents resource conflicts
5. **Log rotation** - Auto-deletes old logs

## 📈 Expected Output

**Per Site Per Day**:
- 2-4 categories scraped
- 5 pages per category
- ~20 products per page
- **Total: 100-200 products per site**

**All Sites Per Day**:
- 10 sites
- **Total: 1,000-2,000 products**

**Storage**:
- ~2MB JSON per site per day
- ~20MB total per day
- ~600MB per month

## 🔐 Security Checklist

Before going live:

- [ ] Change droplet root password: `passwd`
- [ ] Setup SSH keys: `ssh-copy-id root@146.190.240.167`
- [ ] Revoke DigitalOcean API token
- [ ] Delete `DROPLET_ACCESS.md` (contains sensitive info)
- [ ] Setup fail2ban (optional)
- [ ] Enable automatic security updates
- [ ] Create non-root user for scraper (optional)
- [ ] Review UFW rules: `ufw status`

## 🐛 Troubleshooting Guide

### CAPTCHA Issues
```bash
# Wait 30s (automatic)
# If persistent, restart droplet (new IP)
curl -X POST -H 'Content-Type: application/json' \
    -H 'Authorization: Bearer TOKEN' \
    -d '{"type":"reboot"}' \
    "https://api.digitalocean.com/v2/droplets/529749000/actions"
```

### Out of Memory
```bash
# Check swap
free -h

# Add more swap if needed
sudo fallocate -l 4G /swapfile2
sudo chmod 600 /swapfile2
sudo mkswap /swapfile2
sudo swapon /swapfile2
```

### Amazon Changed Layout
```bash
# Test locally first
python scripts/test_scraper.py

# Update selectors in config/scraper.yaml
# Re-deploy
bash deploy/deploy.sh
```

### Scraper Not Running
```bash
# Check cron jobs
crontab -l

# Check cron logs
tail -100 ~/themall/amazon-scraper/logs/cron_audio.log

# Test manually
cd ~/themall
source venv/bin/activate
python scripts/scrape_deals.py --site audio_equipment --headless
```

## 📊 Monitoring Commands

```bash
# View all scraped data
ls -lh ~/themall/amazon-scraper/data/scraped/

# Count products in latest file
cat ~/themall/amazon-scraper/data/scraped/audio_equipment_latest.json | grep '"asin"' | wc -l

# View recent logs
tail -50 ~/themall/amazon-scraper/logs/scraper.log

# Check disk usage
du -sh ~/themall/amazon-scraper/

# Monitor in real-time
watch -n 5 'ls -lh ~/themall/amazon-scraper/data/scraped/'
```

## 🎯 Next Steps (Phase 2)

Once scraper is running smoothly:

### 1. Deal Filtering (`engine/deal_filter.py`)
- Apply discount threshold (20%+)
- Filter by rating (4.0+)
- Remove low review count (<10)
- Deduplicate across sites

### 2. WordPress Integration (`engine/wordpress_manager.py`)
- SSH into Hostinger WordPress sites
- Use WP-CLI to create products
- Update prices daily
- Handle product images

### 3. Static Site Generation
- Generate HTML from filtered deals
- Deploy to Hostinger static hosting
- Add search functionality
- Implement pagination

### 4. Analytics
- Track clicks on affiliate links
- Monitor conversion rates
- A/B test different layouts
- Revenue reporting

## 💡 Pro Tips

1. **Test locally first** - Always run `python scripts/test_scraper.py` before deploying
2. **Monitor initially** - Check logs daily for first week
3. **Adjust timing** - If conflicts, edit `deploy/crontab` times
4. **Scale gradually** - Start with 2-3 sites, add more once stable
5. **Backup data** - Periodically backup `data/scraped/` to local machine
6. **Update selectors** - Amazon changes layout quarterly
7. **Rotate IPs** - If CAPTCHAs persist, consider residential proxy
8. **Optimize pages** - Reduce `max_pages_per_category` if too slow

## 📞 Support Files

- **Full docs**: `README.md`
- **Quick start**: `QUICKSTART.md`
- **Droplet access**: `DROPLET_ACCESS.md` (delete after use!)
- **This summary**: `DEPLOYMENT_SUMMARY.md`

## ✅ Completion Checklist

- [x] Core scraper built (500+ lines)
- [x] Configuration files created
- [x] Test scripts working
- [x] Deployment scripts ready
- [x] Cron jobs configured
- [x] Documentation complete
- [x] DigitalOcean droplet provisioned
- [ ] **TODO**: Run `deploy/setup_droplet.sh`
- [ ] **TODO**: Run `deploy/deploy.sh`
- [ ] **TODO**: Test on droplet
- [ ] **TODO**: Monitor first 24 hours
- [ ] **TODO**: Build engine module (deal filtering)
- [ ] **TODO**: Integrate with WordPress

---

**Built**: 2025-11-12
**Droplet**: 146.190.240.167
**Repository**: `/home/ren/Desktop/themall`
**Cost**: $6/month ($72/year)
**Status**: Ready to deploy! 🚀
