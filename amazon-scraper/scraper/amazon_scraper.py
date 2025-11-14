#!/usr/bin/env python3
"""
Amazon Canada Scraper with Playwright
Works on both local Ubuntu and DigitalOcean droplet

Features:
- Stealth browser configuration (anti-bot)
- Human-like behavior simulation
- Cookie persistence
- Retry logic with backoff
- CAPTCHA detection
- Detailed logging
"""

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from datetime import datetime
import random
import time
import json
import yaml
from pathlib import Path
from colorama import Fore, Style, init

init(autoreset=True)


class AmazonScraper:
    """
    Amazon.ca scraper using Playwright with stealth features

    Usage:
        scraper = AmazonScraper('config/scraper.yaml')
        products = scraper.scrape_category('https://amazon.ca/...', max_pages=3)
    """

    def __init__(self, config_path='config/scraper.yaml', headless=True):
        """
        Initialize scraper

        Args:
            config_path: Path to YAML config file
            headless: Run browser in headless mode (True for production)
        """
        self.headless = headless
        self.config = self._load_config(config_path)
        self.session_cookies_path = Path('data/cookies/amazon_session.json')
        self.session_cookies_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_config(self, path):
        """Load scraper configuration from YAML"""
        try:
            with open(path) as f:
                config = yaml.safe_load(f)
                self._log(f"✓ Config loaded from {path}", 'success')
                return config
        except Exception as e:
            self._log(f"Config load failed: {e}", 'error')
            raise

    def scrape_category(self, category_url, max_pages=None):
        """
        Scrape Amazon category for deals

        Args:
            category_url: Full Amazon.ca category URL (with sorting params)
            max_pages: Max pages to scrape (uses config default if None)

        Returns:
            List of product dicts with fields:
                - asin, title, brand, image_url
                - price_current, price_original, discount_percent
                - rating, review_count, product_url, scraped_at
        """
        if max_pages is None:
            max_pages = self.config['limits']['max_pages_per_category']

        self._log(f"🎯 Starting scrape: {category_url}", 'info')
        self._log(f"📄 Max pages: {max_pages}", 'info')

        products = []

        with sync_playwright() as p:
            browser = self._create_browser(p)
            context = self._create_context(browser)
            page = context.new_page()

            try:
                for page_num in range(1, max_pages + 1):
                    self._log(f"\n{'='*60}", 'info')
                    self._log(f"📄 Scraping page {page_num} of {max_pages}", 'info')
                    self._log(f"{'='*60}", 'info')

                    # Navigate with retry
                    if not self._navigate_with_retry(page, category_url, page_num):
                        self._log(f"Failed to load page {page_num}, stopping", 'warning')
                        break

                    # Human-like behavior (scroll, move mouse, etc.)
                    self._human_behavior(page)

                    # Extract all products from current page
                    page_products = self._extract_products(page)
                    products.extend(page_products)

                    self._log(f"✓ Extracted {len(page_products)} products from page {page_num}", 'success')

                    # Check if there's a next page
                    if page_num < max_pages and not self._has_next_page(page):
                        self._log("No more pages available, stopping", 'info')
                        break

                    # Navigate to next page if needed
                    if page_num < max_pages:
                        self._click_next_page(page)

                    # Rate limiting (avoid detection)
                    self._rate_limit()

                # Save cookies for next session (helps avoid captchas)
                self._save_cookies(context)

            except KeyboardInterrupt:
                self._log("⚠️  Scraping interrupted by user", 'warning')

            except Exception as e:
                self._log(f"Scraping error: {e}", 'error')
                import traceback
                self._log(traceback.format_exc(), 'error')

            finally:
                browser.close()

        self._log(f"\n🎉 Scraping complete! Total products: {len(products)}", 'success')
        return products

    def _create_browser(self, playwright):
        """
        Create Chromium browser with stealth settings

        Args:
            playwright: Playwright instance

        Returns:
            Browser instance
        """
        self._log("🌐 Launching browser...", 'info')

        return playwright.chromium.launch(
            headless=self.headless,
            args=[
                # Disable automation detection
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-blink-features',
            ]
        )

    def _create_context(self, browser):
        """
        Create browser context with stealth settings

        Configures:
        - Realistic viewport size
        - Canadian locale/timezone/geolocation
        - Removes webdriver detection
        - Loads saved cookies

        Args:
            browser: Browser instance

        Returns:
            BrowserContext instance
        """
        self._log("🔧 Creating browser context...", 'info')

        # Get browser config from yaml
        browser_cfg = self.config['browser']

        context = browser.new_context(
            viewport={
                'width': browser_cfg['viewport_width'],
                'height': browser_cfg['viewport_height']
            },
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale=browser_cfg['locale'],
            timezone_id=browser_cfg['timezone'],
            geolocation={
                'latitude': browser_cfg['geolocation']['latitude'],
                'longitude': browser_cfg['geolocation']['longitude']
            },
            permissions=['geolocation'],
        )

        # Remove webdriver detection via JavaScript injection
        context.add_init_script("""
            // Override webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Add chrome property (helps detection)
            window.chrome = {
                runtime: {}
            };

            // Override plugins detection
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-CA', 'en', 'fr-CA']
            });
        """)

        # Load previously saved cookies (helps avoid captchas)
        self._load_cookies(context)

        return context

    def _navigate_with_retry(self, page, base_url, page_num, max_retries=None):
        """
        Navigate to URL with retry logic

        Handles:
        - Pagination (adds &page=N)
        - CAPTCHA detection
        - Network timeouts
        - Exponential backoff

        Args:
            page: Page instance
            base_url: Base category URL
            page_num: Page number (1-indexed)
            max_retries: Max retry attempts (from config if None)

        Returns:
            bool: True if navigation successful, False otherwise
        """
        if max_retries is None:
            max_retries = self.config['limits']['max_retries']

        # Construct URL with pagination
        url = f"{base_url}&page={page_num}" if page_num > 1 else base_url

        for attempt in range(max_retries):
            try:
                self._log(f"🌐 Navigating to: {url} (attempt {attempt + 1}/{max_retries})", 'info')

                page.goto(
                    url,
                    wait_until='networkidle',
                    timeout=self.config['limits']['timeout']
                )

                # Check if we hit a CAPTCHA
                if self._is_captcha_page(page):
                    self._log("⚠️  CAPTCHA detected! Waiting...", 'warning')
                    time.sleep(self.config['delays']['captcha_wait'])
                    continue

                self._log("✓ Page loaded successfully", 'success')
                return True

            except PlaywrightTimeoutError:
                self._log(f"⏱️  Timeout on attempt {attempt + 1}/{max_retries}", 'warning')
                if attempt < max_retries - 1:
                    # Exponential backoff
                    wait_time = self.config['delays']['retry_delay'] * (2 ** attempt)
                    self._log(f"⏳ Waiting {wait_time}s before retry...", 'info')
                    time.sleep(wait_time)

            except Exception as e:
                self._log(f"Navigation error: {e}", 'error')
                if attempt < max_retries - 1:
                    time.sleep(self.config['delays']['retry_delay'])

        return False

    def _is_captcha_page(self, page):
        """
        Check if current page is a CAPTCHA

        Detects:
        - URL contains 'captcha'
        - Captcha form element present

        Args:
            page: Page instance

        Returns:
            bool: True if CAPTCHA detected
        """
        return (
            'captcha' in page.url.lower() or
            page.locator('form[action*="captcha"]').count() > 0 or
            page.locator('#captchacharacters').count() > 0
        )

    def _human_behavior(self, page):
        """
        Simulate human-like behavior on page

        Actions:
        - Random mouse movements
        - Natural scrolling (down and back up)
        - Variable timing

        This helps avoid bot detection.

        Args:
            page: Page instance
        """
        self._log("🤖 Simulating human behavior...", 'info')

        # Random mouse movements
        for _ in range(random.randint(2, 4)):
            page.mouse.move(
                random.randint(100, 1800),
                random.randint(100, 900)
            )
            time.sleep(random.uniform(0.1, 0.3))

        # Scroll down page naturally
        scroll_steps = random.randint(3, 6)
        for i in range(scroll_steps):
            scroll_amount = random.randint(200, 500)
            page.evaluate(f'window.scrollBy(0, {scroll_amount})')
            time.sleep(random.uniform(0.5, self.config['delays']['scroll_delay']))

        # Scroll back up a bit (humans do this)
        page.evaluate('window.scrollBy(0, -300)')
        time.sleep(random.uniform(0.3, 0.8))

        # Scroll to top to see all products
        page.evaluate('window.scrollTo(0, 0)')
        time.sleep(0.5)

    def _extract_products(self, page):
        """
        Extract all products from current page

        Process:
        1. Wait for product cards to load
        2. Get all product card elements
        3. Parse each card (ASIN, title, price, etc.)
        4. Skip products without required fields

        Args:
            page: Page instance

        Returns:
            List of product dicts
        """
        products = []

        try:
            # Wait for products to load
            self._log("⏳ Waiting for products to load...", 'info')
            page.wait_for_selector(
                self.config['selectors']['product_card'],
                timeout=10000
            )

            # Get all product cards
            cards = page.locator(self.config['selectors']['product_card']).all()

            self._log(f"Found {len(cards)} product cards on page", 'info')

            # Parse each product card
            for i, card in enumerate(cards, 1):
                try:
                    product = self._parse_product_card(card)

                    if product and product.get('price_current'):
                        products.append(product)
                        self._log(
                            f"  [{i:2d}/{len(cards)}] ✓ {product['title'][:50]}... (${product['price_current']:.2f})",
                            'success'
                        )
                    else:
                        self._log(f"  [{i:2d}/{len(cards)}] ⊘ Skipped (missing required data)", 'warning')

                except Exception as e:
                    self._log(f"  [{i:2d}/{len(cards)}] ✗ Parse error: {e}", 'error')
                    continue

        except Exception as e:
            self._log(f"Extract products failed: {e}", 'error')

        return products

    def _parse_product_card(self, card):
        """
        Parse individual product card element

        Extracts:
        - ASIN (Amazon Standard Identification Number)
        - Title, brand, image
        - Current price, original price, discount %
        - Rating, review count

        Args:
            card: Locator for product card element

        Returns:
            dict: Product data, or None if ASIN missing
        """
        selectors = self.config['selectors']

        # ASIN is required (unique product ID)
        asin = card.get_attribute('data-asin')
        if not asin:
            return None

        # Title
        title = self._safe_extract_text(card, selectors['title'])
        if not title:
            return None

        # Image URL
        image_url = self._safe_extract_attribute(card, selectors['image'], 'src')

        # Prices (in CAD)
        price_current = self._extract_price(card, selectors['price_current'])
        price_original = self._extract_price(card, selectors['price_original'])

        # If no original price found, use current price (not on sale)
        if not price_original:
            price_original = price_current

        # Calculate discount percentage
        discount_percent = 0
        if price_current and price_original and price_original > price_current:
            discount_percent = int(((price_original - price_current) / price_original) * 100)

        # Rating & review count
        rating = self._extract_rating(card)
        review_count = self._extract_review_count(card)

        # Extract brand from title (usually first word)
        # This is imperfect but works for most products
        brand = title.split()[0] if title else 'Unknown'

        return {
            'asin': asin,
            'title': title,
            'brand': brand,
            'image_url': image_url,
            'price_current': price_current,
            'price_original': price_original,
            'discount_percent': discount_percent,
            'rating': rating,
            'review_count': review_count,
            'product_url': f"https://www.amazon.ca/dp/{asin}",
            'scraped_at': datetime.now().isoformat(),
        }

    def _safe_extract_text(self, element, selector):
        """Safely extract text content from element"""
        try:
            elem = element.locator(selector).first
            if elem.count() > 0:
                return elem.inner_text().strip()
        except:
            pass
        return None

    def _safe_extract_attribute(self, element, selector, attribute):
        """Safely extract attribute value from element"""
        try:
            elem = element.locator(selector).first
            if elem.count() > 0:
                return elem.get_attribute(attribute)
        except:
            pass
        return None

    def _extract_price(self, element, selector):
        """
        Extract and parse price from element

        Handles:
        - Currency symbols (CDN$, $)
        - Commas in numbers
        - Whitespace

        Args:
            element: Parent element
            selector: CSS selector for price element

        Returns:
            float: Price in CAD, or None if not found
        """
        try:
            price_text = self._safe_extract_text(element, selector)
            if price_text:
                # Remove currency symbols and parse
                # Example: "CDN$ 49.99" -> 49.99
                price_clean = price_text.replace('CDN$', '').replace('$', '').replace(',', '').strip()
                return float(price_clean)
        except:
            pass
        return None

    def _extract_rating(self, element):
        """
        Extract star rating from product

        Amazon shows ratings in aria-label like "4.5 out of 5 stars"

        Args:
            element: Parent element

        Returns:
            float: Rating (0.0-5.0)
        """
        try:
            rating_text = self._safe_extract_attribute(
                element,
                self.config['selectors']['rating'],
                'aria-label'
            )
            if rating_text:
                # Extract number from "4.5 out of 5 stars"
                rating_str = rating_text.split()[0]
                return float(rating_str)
        except:
            pass
        return 0.0

    def _extract_review_count(self, element):
        """
        Extract number of reviews

        Looks for text next to rating element

        Args:
            element: Parent element

        Returns:
            int: Review count
        """
        try:
            # Look for review count text (appears after rating)
            # Try multiple selectors as Amazon layout varies
            selectors_to_try = [
                '[aria-label*="out of 5 stars"] + span',
                '.a-size-base.s-underline-text',
                'span[aria-label*="out of 5 stars"] ~ span'
            ]

            for selector in selectors_to_try:
                review_text = self._safe_extract_text(element, selector)
                if review_text:
                    # Remove commas and parse number
                    review_clean = review_text.replace(',', '').replace('(', '').replace(')', '').strip()
                    if review_clean.isdigit():
                        return int(review_clean)
        except:
            pass
        return 0

    def _has_next_page(self, page):
        """
        Check if next page button exists and is enabled

        Args:
            page: Page instance

        Returns:
            bool: True if next page available
        """
        return page.locator(self.config['selectors']['next_page']).count() > 0

    def _click_next_page(self, page):
        """
        Click next page button and wait for load

        Args:
            page: Page instance

        Returns:
            bool: True if successful
        """
        try:
            next_button = page.locator(self.config['selectors']['next_page'])
            if next_button.count() > 0:
                self._log("▶️  Clicking next page...", 'info')
                next_button.click()
                page.wait_for_load_state('networkidle')
                return True
        except:
            pass
        return False

    def _rate_limit(self):
        """
        Rate limiting between pages

        Random delay helps avoid detection
        """
        delay = random.uniform(
            self.config['delays']['min_page_delay'],
            self.config['delays']['max_page_delay']
        )
        self._log(f"⏳ Rate limiting: waiting {delay:.1f}s before next page", 'info')
        time.sleep(delay)

    def _save_cookies(self, context):
        """
        Save browser cookies to file for next session

        Helps avoid CAPTCHAs on subsequent runs

        Args:
            context: Browser context
        """
        try:
            cookies = context.cookies()
            with open(self.session_cookies_path, 'w') as f:
                json.dump(cookies, f, indent=2)
            self._log(f"💾 Saved {len(cookies)} cookies to {self.session_cookies_path}", 'info')
        except Exception as e:
            self._log(f"Cookie save failed: {e}", 'warning')

    def _load_cookies(self, context):
        """
        Load saved cookies from previous session

        Args:
            context: Browser context
        """
        try:
            if self.session_cookies_path.exists():
                with open(self.session_cookies_path) as f:
                    cookies = json.load(f)
                context.add_cookies(cookies)
                self._log(f"🍪 Loaded {len(cookies)} cookies from previous session", 'info')
        except Exception as e:
            self._log(f"Cookie load failed: {e}", 'warning')

    def _log(self, message, level='info'):
        """
        Colored logging output

        Colors work in local terminal, plain text in cron logs

        Args:
            message: Log message
            level: 'success', 'error', 'warning', or 'info'
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        colors = {
            'success': (Fore.GREEN, '✓'),
            'error': (Fore.RED, '✗'),
            'warning': (Fore.YELLOW, '⚠'),
            'info': (Fore.CYAN, '•'),
        }

        color, prefix = colors.get(level, (Fore.WHITE, '•'))
        print(f"{color}[{timestamp}] {prefix} {message}{Style.RESET_ALL}")
