# Proxy Setup for Digital Ocean Scraper

Amazon blocks datacenter IPs. You need a residential proxy to scrape from DO.

---

## Recommended Proxy Providers

### 1. **BrightData** (formerly Luminati) - Most Reliable
- **Cost:** ~$500/month for residential IPs
- **Setup:** Get credentials from dashboard
- **URL format:** `http://username:password@brd.superproxy.io:22225`
- **Pros:** Best success rate, rotating IPs, Canadian residential IPs available
- **Cons:** Expensive

### 2. **Smartproxy** - Budget-Friendly
- **Cost:** $50-75/month for 8GB
- **Setup:** Get credentials from dashboard
- **URL format:** `http://username:password@gate.smartproxy.com:7000`
- **Pros:** Affordable, good for Amazon
- **Cons:** Lower success rate than BrightData

### 3. **IPRoyal** - Cheapest
- **Cost:** $1.75/GB (~$30/month for 20GB)
- **Setup:** Get credentials from dashboard
- **URL format:** `http://username:password@geo.iproyal.com:12321`
- **Pros:** Very cheap, pay-as-you-go
- **Cons:** Slower, less reliable

### 4. **Oxylabs** - Enterprise
- **Cost:** $300+/month
- **URL format:** `http://username:password@pr.oxylabs.io:7777`
- **Pros:** Very reliable, dedicated account manager
- **Cons:** Expensive, min commitment

---

## Setup Instructions

### Step 1: Get Proxy Credentials

Sign up for one of the providers above and get:
- Proxy server URL
- Username
- Password

### Step 2: Configure Locally

Edit `proxy_config.json`:

```json
{
  "enabled": true,
  "server": "http://gate.smartproxy.com:7000",
  "username": "your_username",
  "password": "your_password"
}
```

**For rotating residential proxies (recommended for Amazon):**
```json
{
  "enabled": true,
  "server": "http://brd.superproxy.io:22225",
  "username": "brd-customer-USERNAME-zone-residential",
  "password": "YOUR_PASSWORD"
}
```

### Step 3: Test Locally

```bash
cd /home/ren/Desktop/themall
python3 search_scraper.py
```

Look for:
```
✅ Proxy enabled: http://gate.smartproxy.com:7000
🌐 Browser will use proxy
```

### Step 4: Deploy to Digital Ocean

```bash
# Upload proxy config
scp proxy_config.json root@146.190.240.167:/root/themall/

# Upload updated scraper
scp search_scraper.py root@146.190.240.167:/root/themall/

# Or use rsync for everything:
rsync -avz --exclude 'node_modules' --exclude '__pycache__' \
  proxy_config.json \
  search_scraper.py \
  root@146.190.240.167:/root/themall/
```

### Step 5: Test on DO

```bash
ssh root@146.190.240.167
cd /root/themall
source venv/bin/activate
python3 search_scraper.py
```

---

## Proxy Configuration Examples

### BrightData (Rotating Residential)
```json
{
  "enabled": true,
  "server": "http://brd.superproxy.io:22225",
  "username": "brd-customer-YOUR_CUSTOMER_ID-zone-residential",
  "password": "YOUR_PASSWORD"
}
```

### BrightData (Sticky Session - Canada)
```json
{
  "enabled": true,
  "server": "http://brd.superproxy.io:22225",
  "username": "brd-customer-YOUR_CUSTOMER_ID-zone-residential-country-ca-session-random123",
  "password": "YOUR_PASSWORD"
}
```

### Smartproxy
```json
{
  "enabled": true,
  "server": "http://gate.smartproxy.com:7000",
  "username": "YOUR_USERNAME",
  "password": "YOUR_PASSWORD"
}
```

### Smartproxy (Canada-specific)
```json
{
  "enabled": true,
  "server": "http://ca.smartproxy.com:10000",
  "username": "YOUR_USERNAME",
  "password": "YOUR_PASSWORD"
}
```

### IPRoyal
```json
{
  "enabled": true,
  "server": "http://geo.iproyal.com:12321",
  "username": "YOUR_USERNAME",
  "password": "YOUR_PASSWORD"
}
```

---

## Verifying Proxy Works

### Check Your IP

Before running scraper, verify proxy works:

```python
# test_proxy.py
import requests

proxies = {
    'http': 'http://username:password@gate.smartproxy.com:7000',
    'https': 'http://username:password@gate.smartproxy.com:7000'
}

try:
    response = requests.get('https://api.ipify.org?format=json', proxies=proxies, timeout=10)
    print(f"Your IP via proxy: {response.json()['ip']}")

    # Check location
    response = requests.get('http://ip-api.com/json/', proxies=proxies, timeout=10)
    data = response.json()
    print(f"Location: {data['city']}, {data['regionName']}, {data['country']}")
    print(f"ISP: {data['isp']}")
except Exception as e:
    print(f"Proxy test failed: {e}")
```

Run it:
```bash
python3 test_proxy.py
```

Expected output:
```
Your IP via proxy: 74.123.45.67 (not a datacenter IP!)
Location: Toronto, Ontario, Canada
ISP: Bell Canada (residential ISP, not "DigitalOcean")
```

---

## Cost Estimates

**For scraping every 6 hours (4 times/day):**

### Data Usage per Run:
- Login page: ~2MB
- Search results: ~5MB per page × 5 pages = 25MB
- Product images: ~10MB
- **Total per run:** ~40MB

### Monthly Usage:
- 4 runs/day × 30 days = 120 runs
- 120 runs × 40MB = 4.8GB/month

### Provider Costs:
| Provider    | Monthly Cost | GB Included | Best For            |
|-------------|--------------|-------------|---------------------|
| IPRoyal     | ~$10         | 5GB         | Budget/testing      |
| Smartproxy  | $50          | 8GB         | Good balance        |
| BrightData  | $500+        | Lots        | Enterprise/reliable |

**Recommendation:** Start with **Smartproxy ($50/month)** for 8GB

---

## Troubleshooting

### "Proxy authentication failed"
- Check username/password in proxy_config.json
- Verify your proxy account is active
- Check if IP whitelist is required (some providers)

### "Proxy connection timeout"
- Proxy server might be down
- Try different proxy port
- Check firewall settings on DO

### "Still getting blocked by Amazon"
- Make sure you're using **residential** proxies, not datacenter
- Enable session stickiness (same IP for entire scrape)
- Add longer delays between requests
- Rotate proxies more frequently

### "Proxy too slow"
- Residential proxies are slower than datacenter
- Increase timeouts in scraper
- Consider premium proxy tier

---

## Without Proxy (Not Recommended for DO)

If you run without a proxy from Digital Ocean:
- ⚠️ High chance of being blocked
- ⚠️ May get CAPTCHA on every request
- ⚠️ Amazon may ban the IP permanently
- ⚠️ Better to run locally without proxy than on DO without proxy

---

## Quick Deploy Commands

### Update Code + Proxy Config:
```bash
rsync -avz --exclude 'node_modules' \
  proxy_config.json search_scraper.py \
  root@146.190.240.167:/root/themall/
```

### Test on DO:
```bash
ssh root@146.190.240.167 "/root/auto_deploy.sh"
```

### Monitor Logs:
```bash
ssh root@146.190.240.167 "tail -f /var/log/themall-deploy.log"
```

---

**Ready to scrape from Digital Ocean without getting blocked! 🚀**

Get proxy credentials → Update `proxy_config.json` → Deploy to DO → Profit!
