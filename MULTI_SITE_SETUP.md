# Multi-Site Setup Guide

The scraper now supports multiple affiliate sites using a config-based architecture. Each site has its own:
- Search terms
- Output paths
- Categories
- Deployment settings

## Architecture

```
/root/themall/
├── search_scraper.py          # Shared scraper code
├── run_scraper.sh             # Wrapper script for running sites
├── sites/                     # Site configurations
│   ├── audiogear.yaml         # Audio equipment site
│   ├── camping.yaml           # Camping gear site
│   └── photography.yaml       # Photography equipment site
├── frontends/                 # Frontend builds
│   ├── audiogear/
│   │   └── data/products.json
│   ├── camping/
│   │   └── data/products.json
│   └── photography/
│       └── data/products.json
└── themall/frontend/v0-audiogear-pro/  # Original audiogear frontend
```

## Quick Start

### List Available Sites
```bash
python3 search_scraper.py --list-sites
```

### Run Scraper for a Specific Site
```bash
# Using the wrapper script (recommended)
./run_scraper.sh audiogear
./run_scraper.sh camping
./run_scraper.sh photography

# Or directly with Python
python3 search_scraper.py --site audiogear
python3 search_scraper.py --site camping
```

### Backward Compatibility
The scraper still works without --site argument (uses search_terms.txt):
```bash
python3 search_scraper.py
```

## Site Configuration

Each site config (YAML file in `sites/`) contains:

```yaml
site_name: audiogear
site_title: "AudioGear Pro"
site_category: audio
affiliate_tag: promopenguin-20

search_terms:
  - studio headphones
  - studio microphone
  - audio interface

categories:
  - name: headphones
    keywords: [headphone, earphone]
  - name: microphones
    keywords: [microphone, mic]

output:
  json_path: themall/frontend/v0-audiogear-pro/data/products.json
  xlsx_path: search_scraped_audiogear.xlsx

deploy:
  enabled: true
  hostinger_user: u943122315
  hostinger_host: 147.93.42.128
  hostinger_port: 65002
  hostinger_path: ~/sitename.hostingersite.com/
  frontend_build_path: frontends/sitename/out/
```

## Adding a New Site

### 1. Create Site Config
```bash
cp sites/audiogear.yaml sites/mysite.yaml
nano sites/mysite.yaml  # Edit to customize
```

### 2. Update Configuration
- Change `site_name`, `site_title`, `site_category`
- Update `search_terms` list
- Update `categories` for filtering
- Set `output` paths
- Configure `deploy` settings (set `enabled: false` initially)

### 3. Create Frontend Directory
```bash
mkdir -p frontends/mysite/data
```

### 4. Run Scraper
```bash
./run_scraper.sh mysite
```

## Automation on Digital Ocean

### Option A: Run All Sites Sequentially (Current 1GB Droplet)
```cron
# Run audiogear every 6 hours
0 */6 * * * cd /root/themall && ./run_scraper.sh audiogear >> /var/log/scraper-audiogear.log 2>&1

# Run camping every 6 hours (offset by 2 hours)
0 2,8,14,20 * * * cd /root/themall && ./run_scraper.sh camping >> /var/log/scraper-camping.log 2>&1

# Run photography every 6 hours (offset by 4 hours)
0 4,10,16,22 * * * cd /root/themall && ./run_scraper.sh photography >> /var/log/scraper-photography.log 2>&1
```

### Option B: Run All Sites in One Cron (Lower Frequency)
```cron
# Run all sites once per day
0 2 * * * cd /root/themall && ./run_scraper.sh audiogear && ./run_scraper.sh camping && ./run_scraper.sh photography >> /var/log/scraper-all.log 2>&1
```

### Option C: Master Script (Recommended)
Create `/root/themall/run_all_sites.sh`:
```bash
#!/bin/bash
cd /root/themall
./run_scraper.sh audiogear
./run_scraper.sh camping
./run_scraper.sh photography
```

Then in cron:
```cron
0 2 * * * /root/themall/run_all_sites.sh >> /var/log/scraper-all.log 2>&1
```

## Deployment

### Manual Deployment
```bash
# On Digital Ocean - run scraper
./run_scraper.sh audiogear

# Build frontend (if you have a Next.js frontend for this site)
cd frontends/audiogear
npm run build

# Deploy to Hostinger
rsync -avz -e "ssh -p 65002" out/ u943122315@147.93.42.128:~/audiogear.hostingersite.com/
```

### Automated Deployment
The `auto_deploy.sh` script can be updated to support multiple sites. See `DO_FINAL_SETUP.md` for details.

## Resource Considerations

### Current Setup (1GB RAM, $6/month)
- ✅ Can run sites sequentially (one at a time)
- ✅ Works with staggered cron jobs
- ⚠️ Cannot run multiple sites in parallel

### Upgrade Options
If you need parallel execution:
- **2GB RAM ($12/month)**: Run 2 sites in parallel
- **4GB RAM ($24/month)**: Run 3-4 sites in parallel
- **Docker**: Containerize each site for better isolation

## Monitoring

### Check Logs
```bash
# On Digital Ocean
tail -f /var/log/scraper-audiogear.log
tail -f /var/log/scraper-camping.log
tail -f /var/log/scraper-photography.log
```

### Check Outputs
```bash
# Verify JSON files were created
ls -lh frontends/*/data/products.json
ls -lh themall/frontend/*/data/products.json

# Check content
cat frontends/camping/data/products.json | jq '.products | length'
```

### Cron Job Status
```bash
# View active cron jobs
crontab -l

# Check cron execution
grep CRON /var/log/syslog | tail -20
```

## Troubleshooting

### Site Not Found
```bash
# List available sites
python3 search_scraper.py --list-sites

# Check sites directory
ls -la sites/
```

### YAML Parse Error
```bash
# Validate YAML syntax
python3 -c "import yaml; yaml.safe_load(open('sites/audiogear.yaml'))"
```

### Output Path Issues
```bash
# Create output directories
mkdir -p frontends/audiogear/data
mkdir -p frontends/camping/data
mkdir -p frontends/photography/data
```

### Memory Issues on Digital Ocean
```bash
# Check memory usage
free -h

# Add swap if needed (see DO_FINAL_SETUP.md)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## Next Steps

1. ✅ Test locally: `./run_scraper.sh audiogear`
2. Create frontends for new sites (clone and customize v0-audiogear-pro)
3. Deploy to Digital Ocean using `quick_deploy.sh`
4. Set up cron jobs for automation
5. Monitor logs and outputs
6. Scale as needed (upgrade droplet or add more sites)

## Tips

- Start with **Option B** (all sites once per day) to test
- Monitor memory usage before adding more sites
- Use different search terms to avoid duplicate products across sites
- Keep site configs in version control (already gitignored secrets)
- Test new sites locally before deploying to DO
