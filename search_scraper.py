import asyncio
import os
import pandas as pd
import random
import json
import shutil
import re
import time
from datetime import datetime
from playwright.async_api import async_playwright
from colorama import init, Fore, Style
import urllib.parse
import argparse
import yaml

# Themall engine imports
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_DIR, 'themall'))

# Import directly from module files to bypass __init__.py PA-API dependencies
import importlib.util
import sys

# Load DatabaseManager directly
db_spec = importlib.util.spec_from_file_location(
    "database",
    os.path.join(SCRIPT_DIR, 'themall', 'engine', 'database.py')
)
database_module = importlib.util.module_from_spec(db_spec)
db_spec.loader.exec_module(database_module)
DatabaseManager = database_module.DatabaseManager

# Load WordPressWPCLI directly
wp_spec = importlib.util.spec_from_file_location(
    "wordpress_wpcli",
    os.path.join(SCRIPT_DIR, 'themall', 'engine', 'wordpress_wpcli.py')
)
wp_module = importlib.util.module_from_spec(wp_spec)
wp_spec.loader.exec_module(wp_module)
WordPressWPCLI = wp_module.WordPressWPCLI

# Initialize colorama for colored output
init(autoreset=True)

# Configuration
AMAZON_AFFILIATE_TAG = "promopenguin-20"
ENABLE_WORDPRESS_POSTING = True  # Set to True to enable WordPress posting, False for JSON-only mode

# LocalWordPress class for Docker-based WordPress posting
class LocalWordPress:
    """WordPress manager for local Docker containers using docker exec"""

    def __init__(self, container, wp_url, dry_run=False):
        self.container = container
        self.wp_url = wp_url
        self.dry_run = dry_run
        print(f"{Fore.CYAN}LocalWordPress initialized for container: {container}{Style.RESET_ALL}")

    def create_post(self, title, content, featured_image_url=None, tags=None, status='publish'):
        """Create a WordPress post using docker exec wp-cli"""
        try:
            if self.dry_run:
                print(f"{Fore.YELLOW}[DRY RUN] Would create post: {title}{Style.RESET_ALL}")
                return 99999

            print(f"{Fore.CYAN}Creating WordPress post via Docker: {title}{Style.RESET_ALL}")

            # Escape quotes in title and content for shell
            title_escaped = title.replace('"', '\\"').replace("'", "\\'")
            content_escaped = content.replace('"', '\\"').replace("'", "\\'")

            # Create the post
            import subprocess
            cmd = [
                'docker', 'exec', self.container,
                'wp', 'post', 'create',
                '--post_title=' + title,
                '--post_content=' + content,
                '--post_status=' + status,
                '--porcelain'  # Returns just the post ID
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                print(f"{Fore.RED}Error creating post: {result.stderr}{Style.RESET_ALL}")
                return None

            post_id = int(result.stdout.strip())
            print(f"{Fore.GREEN}✅ Post created with ID: {post_id}{Style.RESET_ALL}")

            # Add tags if provided
            if tags and len(tags) > 0:
                tags_str = ','.join(tags)
                tag_cmd = [
                    'docker', 'exec', self.container,
                    'wp', 'post', 'term', 'add', str(post_id), 'post_tag', tags_str
                ]
                subprocess.run(tag_cmd, capture_output=True, timeout=15)
                print(f"{Fore.GREEN}✅ Added tags: {tags_str}{Style.RESET_ALL}")

            # Set featured image if provided
            if featured_image_url:
                self._set_featured_image(post_id, featured_image_url)

            return post_id

        except subprocess.TimeoutExpired:
            print(f"{Fore.RED}Timeout creating post{Style.RESET_ALL}")
            return None
        except Exception as e:
            print(f"{Fore.RED}Error creating post: {e}{Style.RESET_ALL}")
            return None

    def _set_featured_image(self, post_id, image_url):
        """Download and set featured image"""
        try:
            import subprocess

            # Download image and import to media library
            cmd = [
                'docker', 'exec', self.container,
                'wp', 'media', 'import', image_url,
                '--post_id=' + str(post_id),
                '--featured_image',
                '--porcelain'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                print(f"{Fore.GREEN}✅ Featured image set{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}⚠️  Could not set featured image: {result.stderr}{Style.RESET_ALL}")

        except Exception as e:
            print(f"{Fore.YELLOW}⚠️  Could not set featured image: {e}{Style.RESET_ALL}")

def save_products_json(products_df, output_path="themall/frontend/data/products.json", site_category="audio"):
    """Save products to JSON format for custom PHP frontend"""
    import os
    from datetime import datetime

    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Build products array
    products_array = []
    for _, row in products_df.iterrows():
        # Parse prices with better error handling
        try:
            orig_price_str = str(row.get('originalPrice', '0')).replace('$', '').replace(',', '').replace('\n', '').strip()
            original_price = float(orig_price_str) if orig_price_str else 0.0
        except (ValueError, AttributeError):
            original_price = 0.0

        try:
            sale_price_str = str(row.get('salePrice', '0')).replace('$', '').replace(',', '').replace('\n', '').strip()
            current_price = float(sale_price_str) if sale_price_str else 0.0
        except (ValueError, AttributeError):
            current_price = 0.0

        try:
            discount_str = str(row.get('discount', '0')).replace('%', '').replace('-', '').strip()
            savings_percent = int(discount_str) if discount_str else 0
        except (ValueError, AttributeError):
            savings_percent = 0

        # Add affiliate tag to URL (check for actual tag parameter, not dib_tag)
        base_url = str(row.get('productUrl', ''))
        if base_url and '&tag=' not in base_url and '?tag=' not in base_url:
            separator = '&' if '?' in base_url else '?'
            amazon_url_with_tag = f"{base_url}{separator}tag={AMAZON_AFFILIATE_TAG}"
        else:
            amazon_url_with_tag = base_url

        product = {
            "asin": str(row.get('asin', '')),
            "title": str(row.get('title', '')),
            "brand": str(row.get('brand', '')),  # May need to extract from title
            "description": str(row.get('title', '')),  # Use title as description for now
            "image_url": str(row.get('imageUrl', '')),
            "original_price": original_price,
            "current_price": current_price,
            "savings_percent": savings_percent,
            "currency": "CAD",
            "features": [],  # Scraper doesn't get features yet
            "category": str(row.get('category', site_category)),
            "date_added": datetime.now().strftime('%Y-%m-%d'),
            "affiliate_tag": AMAZON_AFFILIATE_TAG,
            "in_stock": True,
            "amazon_url": amazon_url_with_tag
        }
        products_array.append(product)

    # Build JSON structure matching frontend expectations
    output_data = {
        "meta": {
            "generated_at": datetime.now().isoformat() + "Z",
            "site_category": site_category,
            "total_products": len(products_array),
            "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        },
        "products": products_array
    }

    # Save to file
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"{Fore.GREEN}✅ Saved {len(products_array)} products to {output_path}{Style.RESET_ALL}")
    return output_path

# Function to read search terms from file
def read_search_terms_from_file(filename="search_terms.txt"):
    """Read search terms from a file, skipping lines that start with #"""
    terms = []
    try:
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    terms.append(line)
    except FileNotFoundError:
        print(f"{Fore.YELLOW}Warning: {filename} not found. Using default terms.{Style.RESET_ALL}")
        # Default search terms if file not found
        terms = [
            "solar panel",
            "carhart",
            "yeti",
            "generator",
            "jackery"
        ]
    
    if not terms:
        print(f"{Fore.RED}Error: No valid search terms found in {filename}. Using default terms.{Style.RESET_ALL}")
        terms = ["solar panel", "generator"]
    
    return terms

def load_site_config(site_name):
    """Load site configuration from YAML file"""
    config_path = os.path.join(SCRIPT_DIR, 'sites', f'{site_name}.yaml')

    if not os.path.exists(config_path):
        print(f"{Fore.RED}Error: Site config not found: {config_path}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Available sites:{Style.RESET_ALL}")
        sites_dir = os.path.join(SCRIPT_DIR, 'sites')
        if os.path.exists(sites_dir):
            for f in os.listdir(sites_dir):
                if f.endswith('.yaml'):
                    print(f"  - {f.replace('.yaml', '')}")
        return None

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            print(f"{Fore.GREEN}✅ Loaded config for site: {config.get('site_title', site_name)}{Style.RESET_ALL}")
            return config
    except Exception as e:
        print(f"{Fore.RED}Error loading site config: {e}{Style.RESET_ALL}")
        return None

async def human_like_scroll(page):
    """Scroll in a human-like pattern to render products."""
    last_height = await page.evaluate("document.body.scrollHeight")
    for _ in range(10):  # Reduced for search results
        scroll_amount = random.randint(300, 600)
        await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
        await asyncio.sleep(random.uniform(1, 2))  # Faster for search
        new_height = await page.evaluate("document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        await asyncio.sleep(random.uniform(1, 2))

async def clean_duplicates(df):
    """Remove duplicate entries from the DataFrame."""
    # Get initial row count
    initial_count = len(df)
    
    # Remove duplicates based on ASIN (keeping the first occurrence)
    df.drop_duplicates(subset=['asin'], keep='first', inplace=True)
    
    # Calculate how many duplicates were removed
    duplicates_removed = initial_count - len(df)
    
    if duplicates_removed > 0:
        print(f"{Fore.GREEN}Removed {duplicates_removed} duplicate products based on ASIN{Style.RESET_ALL}")
    else:
        print(f"{Fore.GREEN}No duplicate ASINs found{Style.RESET_ALL}")
    
    return df


def create_offgrid_format(df):
    """Convert scraped data to Off-Grid Discounts format (A-I columns)"""
    from datetime import datetime, timedelta
    
    offgrid_data = pd.DataFrame()
    
    # A: Product Name
    offgrid_data['Product Name'] = df['title']
    
    # B: Image URL
    offgrid_data['Image URL'] = df['imageUrl']
    
    # C: Amazon Price - just use the scraped sale price directly
    offgrid_data['Amazon Price'] = df['salePrice']
    
    # D: Cabela's Price (empty for now)
    offgrid_data['Cabela\'s Price'] = ''
    
    # E: Amazon Link (with affiliate tag)
    amazon_links = []
    for url in df['productUrl']:
        if pd.notna(url) and url:
            # Add affiliate tag
            separator = '&' if '?' in str(url) else '?'
            amazon_links.append(f"{url}{separator}tag={AMAZON_AFFILIATE_TAG}")
        else:
            amazon_links.append('')
    offgrid_data['Amazon Link'] = amazon_links
    
    # F: Cabela's Link (empty for now)
    offgrid_data['Cabela\'s Link'] = ''
    
    # G: Deal End Date (7 days from now)
    deal_end_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    offgrid_data['Deal End Date'] = deal_end_date
    
    # H: Category - map based on search term
    categories = []
    for i, row in df.iterrows():
        search_term = row.get('searchTerm', '').lower()
        if 'solar' in search_term:
            categories.append('solar')
        elif 'generator' in search_term or 'jackery' in search_term:
            categories.append('generators')
        elif 'battery' in search_term or 'power' in search_term:
            categories.append('batteries')
        elif 'yeti' in search_term:
            categories.append('coolers')
        elif 'carhart' in search_term:
            categories.append('clothing')
        else:
            categories.append('power')
    offgrid_data['Category'] = categories
    
    # I: Featured
    offgrid_data['Featured'] = 'false'
    
    # J: Original Price - non-sale price from <span aria-hidden="true">$39.99</span>
    offgrid_data['Original Price'] = df['originalPrice']
    
    # K: Discount - full discount text (e.g., "-10%" or "Save 15%")
    offgrid_data['Discount'] = df['discount']
    
    # L: % Off - just the percentage number with % symbol
    percent_off_values = []
    for i, row in df.iterrows():
        discount = row.get('discount', '')
        if pd.notna(discount) and discount:
            # Extract just the percentage number with % symbol
            percent_match = re.search(r'(\d+)%', str(discount))
            if percent_match:
                percent_off_values.append(percent_match.group(0))  # e.g., "10%"
            else:
                percent_off_values.append('')
        else:
            percent_off_values.append('')
    offgrid_data['% Off'] = percent_off_values
    
    # Filter out invalid products (less strict)
    offgrid_data = offgrid_data[
        (offgrid_data['Product Name'] != '') & 
        (offgrid_data['Product Name'].notna())
    ]
    
    print(f"After filtering: {len(offgrid_data)} products with valid names")
    
    return offgrid_data

def initialize_themall_system():
    """Initialize themall database and configuration system (simplified for scraping)"""
    print(Fore.CYAN + "Initializing themall system..." + Style.RESET_ALL)

    try:
        # Load secrets manually (no PA-API needed)
        import json
        import yaml

        config_dir = os.path.join(SCRIPT_DIR, 'themall', 'config')
        secrets_file = os.path.join(config_dir, 'secrets.json')
        categories_file = os.path.join(config_dir, 'amazon_categories.yaml')

        with open(secrets_file, 'r') as f:
            secrets = json.load(f)

        with open(categories_file, 'r') as f:
            categories = yaml.safe_load(f)['categories']  # Extract inner dict

        # Initialize database manager
        data_dir = os.path.join(SCRIPT_DIR, 'themall', 'data')
        db = DatabaseManager(data_dir=data_dir)

        settings = {}  # Not needed for scraping

        print(Fore.GREEN + "Themall system initialized successfully" + Style.RESET_ALL)
        return db, categories, settings, secrets
    except Exception as e:
        print(Fore.RED + f"Error initializing themall system: {e}" + Style.RESET_ALL)
        print(Fore.YELLOW + "Make sure themall/config/ directory exists with secrets.json and amazon_categories.yaml" + Style.RESET_ALL)
        raise

def determine_site_for_product(search_term, categories):
    """Determine which WordPress site a product should be posted to based on search term"""
    search_lower = search_term.lower()

    # Iterate through all sites in categories config
    for site_key, site_config in categories.items():
        search_terms = site_config.get('search_terms', [])
        # Check if the search term matches any of the site's configured search terms
        for term in search_terms:
            if term.lower() in search_lower or search_lower in term.lower():
                return site_key

    # Default to first available site if no match found
    if categories:
        default_site = list(categories.keys())[0]
        print(Fore.YELLOW + f"No specific site match for '{search_term}', using default: {default_site}" + Style.RESET_ALL)
        return default_site

    return None

def get_random_user_agent():
    """Get a random realistic user agent to avoid detection - UPDATED 2025"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    ]
    return random.choice(user_agents)

def get_random_viewport():
    """Get a random viewport size to appear more human"""
    viewports = [
        {'width': 1920, 'height': 1080},
        {'width': 1366, 'height': 768},
        {'width': 1440, 'height': 900},
        {'width': 1536, 'height': 864},
    ]
    return random.choice(viewports)

async def human_mouse_move(page, x, y):
    """Move mouse in a natural curve, not straight line - humans don't move mice in perfect lines!"""
    # Get current position (start from somewhere random if first move)
    current_x = random.randint(100, 500)
    current_y = random.randint(100, 500)

    # Calculate steps for smooth movement
    steps = random.randint(10, 25)

    for i in range(steps):
        # Add some randomness to the path (not a perfect line)
        progress = i / steps
        new_x = current_x + (x - current_x) * progress + random.randint(-5, 5)
        new_y = current_y + (y - current_y) * progress + random.randint(-5, 5)

        await page.mouse.move(new_x, new_y)
        await asyncio.sleep(random.uniform(0.01, 0.03))  # Tiny delays between moves

    # Final position
    await page.mouse.move(x, y)

async def human_scroll(page):
    """Scroll like a human - random amounts, random speeds. Sometimes scroll down, sometimes back up"""
    scroll_amount = random.randint(200, 600)
    direction = random.choice([1, -1])  # Sometimes scroll up!

    print(f"{Fore.MAGENTA}📜 Scrolling {'DOWN' if direction == 1 else 'UP'} {scroll_amount}px (human-like){Style.RESET_ALL}")

    # Multiple small scrolls instead of one big jump
    chunks = random.randint(3, 7)
    chunk_size = scroll_amount // chunks

    for _ in range(chunks):
        await page.mouse.wheel(0, chunk_size * direction)
        await asyncio.sleep(random.uniform(0.1, 0.3))

async def random_mouse_jitter(page):
    """Random mouse movements - humans don't keep mouse still!"""
    if random.random() < 0.3:  # 30% chance to jitter
        x = random.randint(200, 1700)
        y = random.randint(200, 900)
        print(f"{Fore.MAGENTA}🎲 Random mouse jitter to ({x}, {y}){Style.RESET_ALL}")
        await human_mouse_move(page, x, y)

async def random_hover_element(page):
    """Hover over random elements - humans do this while reading"""
    if random.random() < 0.4:  # 40% chance to hover something
        selectors = [
            'h2', 'h3', '.s-image', 'span.a-price',
            '.a-button', '.s-result-item', 'a.a-link-normal'
        ]

        try:
            selector = random.choice(selectors)
            elements = await page.query_selector_all(selector)

            if elements:
                element = random.choice(elements)
                box = await element.bounding_box()

                if box:
                    x = box['x'] + box['width'] / 2
                    y = box['y'] + box['height'] / 2

                    print(f"{Fore.MAGENTA}👆 Hovering over element: {selector}{Style.RESET_ALL}")
                    await human_mouse_move(page, x, y)
                    await asyncio.sleep(random.uniform(0.5, 1.5))
        except Exception as e:
            pass  # Hover failed, not critical

async def random_mouse_movement(page):
    """Simulate random mouse movements."""
    for _ in range(random.randint(3, 8)):
        x = random.randint(0, await page.evaluate("window.innerWidth"))
        y = random.randint(0, await page.evaluate("window.innerHeight"))
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.1, 0.3))

async def login_and_save_cookies(page):
    """Log in to Amazon using credentials from config file."""
    # Load credentials from file
    try:
        with open(os.path.join(SCRIPT_DIR, "amazon_credentials.json"), "r") as f:
            creds = json.load(f)
            email = creds.get("email")
            password = creds.get("password")
    except FileNotFoundError:
        print(f"{Fore.RED}Error: amazon_credentials.json not found. Please create it with email and password fields.{Style.RESET_ALL}")
        return False
    except json.JSONDecodeError:
        print(f"{Fore.RED}Error: Invalid JSON in amazon_credentials.json{Style.RESET_ALL}")
        return False
    
    await page.goto("https://www.amazon.ca/ap/signin?openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fwww.amazon.ca%2F%3Fref_%3Dnav_signin&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=caflex&openid.mode=checkid_setup&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0")
    print("Navigating to login page.")
    
    # Wait for page to load and try multiple email field selectors
    await asyncio.sleep(3)
    email_filled = False
    
    # Try different email field selectors
    email_selectors = ["#ap_email", "#ap_email_login", "input[name='email']", "input[type='email']", "#signInFormEmail"]
    for selector in email_selectors:
        try:
            await page.wait_for_selector(selector, timeout=5000)
            # Type like a human - character by character with random delays
            print(f"{Fore.CYAN}📧 Typing email character by character (human-like){Style.RESET_ALL}")
            for char in email:
                await page.type(selector, char, delay=random.randint(50, 150))
            print(f"✅ Filled email using selector: {selector}")
            email_filled = True
            break
        except:
            continue
    
    if not email_filled:
        print("Could not find email field. Amazon may have changed their login page.")
        return False
    
    # Add a delay and try to continue
    await asyncio.sleep(2)
    
    # Try to press Enter or click Continue button
    try:
        await page.press("#ap_email", "Enter")
        print("Pressed Enter after email.")
    except:
        try:
            await page.click("#continue")
            print("Clicked Continue button.")
        except:
            print("Could not proceed after email entry.")
    
    await asyncio.sleep(3)
    
    # Try different password field selectors
    password_filled = False
    password_selectors = ["#ap_password", "#ap_password_login", "input[name='password']", "input[type='password']", "#signInFormPassword"]
    for selector in password_selectors:
        try:
            await page.wait_for_selector(selector, timeout=5000)
            # Type like a human - character by character with random delays
            print(f"{Fore.CYAN}🔑 Typing password character by character (human-like){Style.RESET_ALL}")
            for char in password:
                await page.type(selector, char, delay=random.randint(50, 150))
            print(f"✅ Filled password using selector: {selector}")
            password_filled = True
            break
        except:
            continue
    
    if not password_filled:
        print("Could not find password field.")
        return False
    
    # Try different sign-in button selectors
    await asyncio.sleep(1)
    signin_clicked = False
    signin_selectors = ["#signInSubmit", "#auth-signin-button", "input[type='submit']", "#signInButton"]
    for selector in signin_selectors:
        try:
            await page.click(selector)
            print(f"Clicked sign-in button using selector: {selector}")
            signin_clicked = True
            break
        except:
            continue
    
    if not signin_clicked:
        print("Could not find sign-in button.")
        return False

    # Verify login by checking for the account list selector
    try:
        await page.wait_for_selector("#nav-link-accountList", timeout=60000)
        print("Login verified successfully.")
    except Exception as e:
        print("Failed to verify login:", e)
        return False

    # Check if login was successful
    if not await page.is_visible("#nav-link-accountList"):
        print("Login verification failed. Exiting.")
        return False

    return True

async def search_and_scrape(page, search_term):
    """Search for a term and scrape the results."""
    print(f"{Fore.CYAN}Searching for: '{search_term}'{Style.RESET_ALL}")
    
    # Navigate to Amazon.ca search
    search_url = f"https://www.amazon.ca/s?k={urllib.parse.quote(search_term)}&ref=nb_sb_noss"
    await page.goto(search_url)

    # HUMAN BEHAVIORS BEFORE SCRAPING - look like a real person browsing
    print(f"{Fore.MAGENTA}🎭 Performing human-like behaviors...{Style.RESET_ALL}")
    await asyncio.sleep(random.uniform(1.5, 3.0))  # Initial page load delay

    # Scroll down a bit (like you're browsing)
    await human_scroll(page)
    await asyncio.sleep(random.uniform(1, 2))

    # Move mouse around randomly
    await random_mouse_jitter(page)
    await asyncio.sleep(random.uniform(0.5, 1.5))

    # Hover over a random product (like reading)
    await random_hover_element(page)
    await asyncio.sleep(random.uniform(1, 2))

    # Scroll some more
    await human_scroll(page)
    await asyncio.sleep(random.uniform(1, 2))

    # Extract product information (check up to 15 products, filter for sales only)
    products = await page.evaluate(f"""
        (searchTerm) => {{
            const items = [];
            
            // Try multiple selectors for search results
            let productCards = document.querySelectorAll('[data-component-type="s-search-result"]');
            if (productCards.length === 0) {{
                productCards = document.querySelectorAll('[data-cy="product-card"]');
            }}
            if (productCards.length === 0) {{
                productCards = document.querySelectorAll('.s-result-item[data-asin]');
            }}
            if (productCards.length === 0) {{
                productCards = document.querySelectorAll('.s-widget-container');
            }}
            
            console.log('Found', productCards.length, 'product cards');
            
            const limitedCards = Array.from(productCards).slice(0, 20); // Get first 20 products to find sales
            
            limitedCards.forEach((item, index) => {{
                try {{
                    // Product title - try multiple selectors
                    let titleElement = item.querySelector('[data-cy="title-recipe-title"] span');
                    if (!titleElement) titleElement = item.querySelector('h2 a span');
                    if (!titleElement) titleElement = item.querySelector('.s-size-mini span');
                    if (!titleElement) titleElement = item.querySelector('h2 span');
                    if (!titleElement) titleElement = item.querySelector('.a-link-normal span');
                    
                    const title = titleElement ? titleElement.innerText.trim() : '';
                    
                    // Product URL and ASIN - try multiple selectors
                    let linkElement = item.querySelector('[data-cy="title-recipe-title"]');
                    if (!linkElement) linkElement = item.querySelector('h2 a');
                    if (!linkElement) linkElement = item.querySelector('.a-link-normal');
                    if (!linkElement) linkElement = item.querySelector('a[href*="/dp/"]');
                    
                    const productUrl = linkElement ? linkElement.href : '';
                    const asin = productUrl.match(/\\/dp\\/([A-Z0-9]{{10}})/) ? productUrl.match(/\\/dp\\/([A-Z0-9]{{10}})/)[1] : '';
                    
                    // Image URL - try multiple selectors and optimize size
                    let imageElement = item.querySelector('img[data-image-latency="s-product-image"]');
                    if (!imageElement) imageElement = item.querySelector('.s-product-image-container img');
                    if (!imageElement) imageElement = item.querySelector('img[src*="images-amazon"]');
                    if (!imageElement) imageElement = item.querySelector('img');
                    
                    let imageUrl = '';
                    if (imageElement) {{
                        imageUrl = imageElement.src || imageElement.getAttribute('data-src') || '';
                        
                        // Optimize Amazon image size for better performance
                        if (imageUrl && imageUrl.includes('images-amazon')) {{
                            // Try to get 500px version (optimal for web)
                            if (imageUrl.includes('._SL') || imageUrl.includes('._AC_')) {{
                                imageUrl = imageUrl.replace(/\\._SL\\d+_/, '._SL500_').replace(/\\._AC_[^.]*/, '._AC_SL500_');
                            }} else if (!imageUrl.includes('_SL500_')) {{
                                // Add size parameter if not present
                                const urlParts = imageUrl.split('.');
                                if (urlParts.length > 1) {{
                                    urlParts[urlParts.length - 2] += '._SL500_';
                                    imageUrl = urlParts.join('.');
                                }}
                            }}
                        }}
                    }}
                    
                    // Price information - using your specific selectors
                    let salePrice = '';
                    let originalPrice = '';
                    let discount = '';
                    
                    // Extract sale price - using your specific selectors
                    // First try the a-offscreen method inside a-price (most reliable)
                    let priceElement = item.querySelector('.a-price[data-a-size="xl"] .a-offscreen');
                    if (!priceElement) priceElement = item.querySelector('.a-price .a-offscreen');
                    if (priceElement) {{
                        salePrice = priceElement.innerText || priceElement.textContent;
                    }}
                    
                    // Fallback to a-price-whole method
                    if (!salePrice) {{
                        const salePriceWhole = item.querySelector('.a-price-whole');
                        if (salePriceWhole) {{
                            const decimal = item.querySelector('.a-price-decimal');
                            const fraction = item.querySelector('.a-price-fraction');
                            salePrice = '$' + salePriceWhole.innerText + (decimal ? decimal.innerText : '.') + (fraction ? fraction.innerText : '00');
                        }}
                    }}
                    
                    // Additional fallback
                    if (!salePrice) {{
                        priceElement = item.querySelector('.a-price-range .a-offscreen');
                        if (priceElement) {{
                            salePrice = priceElement.innerText || priceElement.textContent;
                        }}
                    }}
                    
                    // Extract original price - try multiple methods
                    // Method 1: Look for "List: $XX.XX" pattern in a-offscreen elements
                    const listPriceElements = item.querySelectorAll('.a-offscreen');
                    for (const priceEl of listPriceElements) {{
                        const text = priceEl.innerText || priceEl.textContent || '';
                        if (text.includes('List:') && text.includes('$')) {{
                            // Extract just the price part after "List: "
                            const priceMatch = text.match(/List:\\s*\\$([\\d,]+\\.\\d{{2}})/);
                            if (priceMatch) {{
                                originalPrice = '$' + priceMatch[1];
                                break;
                            }}
                        }}
                    }}
                    
                    // Method 2: Look for text-decoration: line-through styles (crossed out prices)
                    if (!originalPrice) {{
                        const crossedOutPrices = item.querySelectorAll('[style*="text-decoration"], .a-text-strike, [class*="strike"]');
                        for (const priceEl of crossedOutPrices) {{
                            const text = priceEl.innerText || priceEl.textContent || '';
                            if (text.includes('$') && text.match(/\\$\\d+\\.\\d{{2}}/)) {{
                                originalPrice = text.trim();
                                break;
                            }}
                        }}
                    }}
                    
                    // Method 3: Look for .a-text-price (usually crossed out)
                    if (!originalPrice) {{
                        const textPriceEl = item.querySelector('.a-text-price .a-offscreen, .a-text-price');
                        if (textPriceEl) {{
                            originalPrice = textPriceEl.innerText || textPriceEl.textContent || '';
                        }}
                    }}
                    
                    // Method 3: Try to find aria-hidden price elements that are higher than sale price
                    if (!originalPrice) {{
                        const ariaHiddenPrices = item.querySelectorAll('[aria-hidden="true"]');
                        for (const priceEl of ariaHiddenPrices) {{
                            const text = priceEl.innerText.trim();
                            if (text.includes('$') && text.match(/\\$\\d+\\.\\d{{2}}/) && text !== salePrice) {{
                                // Check if this price is higher than sale price
                                const potentialOriginal = parseFloat(text.replace(/[^0-9.]/g, ''));
                                const saleNum = parseFloat((salePrice || '').replace(/[^0-9.]/g, ''));
                                if (!isNaN(potentialOriginal) && !isNaN(saleNum) && potentialOriginal > saleNum) {{
                                    originalPrice = text;
                                    break;
                                }}
                            }}
                        }}
                    }}
                    
                    // Method 4: Look for data-a-strike or similar attributes
                    if (!originalPrice) {{
                        const strikeElements = item.querySelectorAll('[data-a-strike="true"], .a-price[data-a-strike="true"] .a-offscreen');
                        for (const el of strikeElements) {{
                            const text = el.innerText || el.textContent || '';
                            if (text.includes('$')) {{
                                originalPrice = text.trim();
                                break;
                            }}
                        }}
                    }}
                    
                    // Extract discount percentage - using your specific selectors
                    // Method 1: Try the a-badge-text selector with data-a-badge-color="sx-white" (your specific example)
                    const badgeDiscountEl = item.querySelector('.a-badge-text[data-a-badge-color="sx-white"]');
                    if (badgeDiscountEl) {{
                        const text = badgeDiscountEl.innerText.trim();
                        // Only accept valid discount text
                        if (text && (text.includes('%') || text.match(/save\\s*\\$?\\d+/i)) && 
                            !text.toLowerCase().includes('price') && 
                            !text.toLowerCase().includes('product') && 
                            !text.toLowerCase().includes('page')) {{
                            discount = text;
                        }}
                    }}
                    
                    // Method 2: Try any a-badge-text element
                    if (!discount) {{
                        const badgeEl = item.querySelector('.a-badge-text');
                        if (badgeEl) {{
                            const text = badgeEl.innerText.trim();
                            // Only accept text that contains % or starts with "Save" and has numbers
                            if (text && (text.includes('%') || (text.toLowerCase().includes('save') && text.match(/\\d+/)))) {{
                                // Skip irrelevant text like "Price, product page"
                                if (!text.toLowerCase().includes('price') && !text.toLowerCase().includes('product') && !text.toLowerCase().includes('page')) {{
                                    discount = text;
                                }}
                            }}
                        }}
                    }}
                    
                    // Method 3: Try the specific selector you mentioned first (exact match)
                    if (!discount) {{
                        const discountPercentageEl = item.querySelector('span[aria-hidden="true"].a-size-large.a-color-price.savingPriceOverride.aok-align-center.reinventPriceSavingsPercentageMargin.savingsPercentage');
                        if (discountPercentageEl) {{
                            const text = discountPercentageEl.innerText.trim();
                            if (text && (text.includes('%') || text.match(/save\\s*\\$?\\d+/i)) && 
                                !text.toLowerCase().includes('price') && 
                                !text.toLowerCase().includes('product') && 
                                !text.toLowerCase().includes('page')) {{
                                discount = text;
                            }}
                        }}
                    }}
                    
                    // Method 4: Try shorter savingsPercentage selector
                    if (!discount) {{
                        const shortDiscountEl = item.querySelector('.savingsPercentage');
                        if (shortDiscountEl) {{
                            const text = shortDiscountEl.innerText.trim();
                            if (text && (text.includes('%') || text.match(/save\\s*\\$?\\d+/i)) && 
                                !text.toLowerCase().includes('price') && 
                                !text.toLowerCase().includes('product') && 
                                !text.toLowerCase().includes('page')) {{
                                discount = text;
                            }}
                        }}
                    }}
                    
                    // Method 5: Try any element with savingsPercentage class
                    if (!discount) {{
                        const savingsEls = item.querySelectorAll('[class*="savingsPercentage"]');
                        for (const el of savingsEls) {{
                            const text = el.innerText.trim();
                            if (text && text.includes('%') && 
                                !text.toLowerCase().includes('price') && 
                                !text.toLowerCase().includes('product') && 
                                !text.toLowerCase().includes('page')) {{
                                discount = text;
                                break;
                            }}
                        }}
                    }}
                    
                    // Look for discount badge/label
                    if (!discount) {{
                        const discountBadge = item.querySelector('.s-coupon-highlight-color, .s-discount-text, [class*="discount"], [class*="save"], [class*="off"]');
                        if (discountBadge) {{
                            const text = discountBadge.innerText.trim();
                            // Only accept valid discount text
                            if (text && (text.includes('%') || text.match(/save\\s*\\$?\\d+/i)) && 
                                !text.toLowerCase().includes('price') && 
                                !text.toLowerCase().includes('product') && 
                                !text.toLowerCase().includes('page')) {{
                                discount = text;
                            }}
                        }}
                    }}
                    
                    // Try any element with percentage symbol
                    if (!discount) {{
                        const percentageEls = item.querySelectorAll('span');
                        for (const el of percentageEls) {{
                            const text = el.innerText || '';
                            if (text.match(/\\d+%\\s*(off|OFF)/i) || text.match(/Save\\s*\\d+%/i)) {{
                                discount = text;
                                break;
                            }}
                        }}
                    }}
                    
                    // Calculate discount if we have both prices but no discount found
                    if (!discount && salePrice && originalPrice) {{
                        try {{
                            const saleNum = parseFloat(salePrice.replace(/[^0-9.]/g, ''));
                            const origNum = parseFloat(originalPrice.replace(/[^0-9.]/g, ''));
                            if (!isNaN(saleNum) && !isNaN(origNum) && origNum > saleNum) {{
                                const discountPercent = Math.round(((origNum - saleNum) / origNum) * 100);
                                discount = discountPercent + '%';
                            }}
                        }} catch (e) {{
                            // Ignore calculation errors
                        }}
                    }}
                    
                    // Clean discount text: strip all alphabetic characters, keep only numbers and %
                    if (discount) {{
                        const cleanedDiscount = discount.replace(/[a-zA-Z\\s]/g, '');
                        // Only keep if it has numbers and optionally %
                        if (cleanedDiscount.match(/\\d+%?/)) {{
                            discount = cleanedDiscount;
                        }} else {{
                            discount = ''; // Clear if no valid numbers found
                        }}
                    }}
                    
                    // Clean up title (keep full title, only remove hyphens)
                    let cleanTitle = title.replace(/-/g, ''); // Remove hyphens only
                    
                    console.log('Product', index + 1, ':', {{
                        title: cleanTitle,
                        asin: asin,
                        hasUrl: !!productUrl,
                        hasImage: !!imageUrl,
                        salePrice: salePrice,
                        originalPrice: originalPrice,
                        discount: discount,
                        hasDiscount: !!(discount && discount.trim() !== '')
                    }});
                    
                    // Check if product is on sale (has discount OR has both prices with original > sale)
                    let isOnSale = false;
                    if (discount && discount.trim() !== '') {{
                        isOnSale = true;
                    }} else if (salePrice && originalPrice) {{
                        // Compare prices to determine if on sale
                        const saleNum = parseFloat(salePrice.replace(/[^0-9.]/g, ''));
                        const origNum = parseFloat(originalPrice.replace(/[^0-9.]/g, ''));
                        if (!isNaN(saleNum) && !isNaN(origNum) && origNum > saleNum) {{
                            isOnSale = true;
                        }}
                    }}
                    
                    // Only add products that are on sale
                    if (cleanTitle && productUrl && asin && isOnSale) {{
                        items.push({{
                            title: cleanTitle,
                            discount: discount,
                            imageUrl: imageUrl,
                            asin: asin,
                            productUrl: productUrl,
                            category: searchTerm,
                            salePrice: salePrice,
                            originalPrice: originalPrice,
                            savings: '',
                            searchTerm: searchTerm
                        }});
                    }}
                }} catch (e) {{
                    console.log('Error processing product', index + 1, ':', e);
                }}
            }});
            
            console.log('Successfully extracted', items.length, 'products on sale');
            // Limit to first 3 sale items
            return items.slice(0, 3);
        }}
    """, search_term)
    
    print(f"{Fore.GREEN}Found {len(products)} products for '{search_term}'{Style.RESET_ALL}")
    return products

def get_browser_executable_path():
    """Get the path to the browser executable"""
    import os
    import platform
    
    system = platform.system()
    home = os.path.expanduser("~")
    
    # Different paths based on operating system
    if system == "Windows":
        # Windows paths
        paths = [
            os.path.join(home, ".cache", "ms-playwright", "chromium-*", "chrome-win", "chrome.exe"),
            os.path.join(home, "AppData", "Local", "ms-playwright", "chromium-*", "chrome-win", "chrome.exe"),
            os.path.join(home, "AppData", "Roaming", "ms-playwright", "chromium-*", "chrome-win", "chrome.exe"),
        ]
    elif system == "Darwin":  # macOS
        paths = [
            os.path.join(home, "Library", "Caches", "ms-playwright", "chromium-*", "chrome-mac", "Chromium.app", "Contents", "MacOS", "Chromium"),
        ]
    else:  # Linux and others
        paths = [
            os.path.join(home, ".cache", "ms-playwright", "chromium-*", "chrome-linux", "chrome"),
        ]
    
    # Try to find the browser in the possible paths
    import glob
    for path_pattern in paths:
        matches = glob.glob(path_pattern)
        if matches:
            return matches[0]
    
    return None

async def ensure_browser_installed():
    """Ensure that the browser is installed for Playwright"""
    try:
        # Check if we're running as a PyInstaller bundle
        import sys
        if getattr(sys, 'frozen', False):
            print(Fore.YELLOW + "Running as executable. Checking browser installation..." + Style.RESET_ALL)
            import subprocess
            import os
            
            # Get the directory where the executable is located
            exe_dir = os.path.dirname(os.path.abspath(sys.executable))
            
            # Try to find the browser executable
            browser_path = get_browser_executable_path()
            
            if browser_path and os.path.exists(browser_path):
                print(Fore.GREEN + f"Browser found at: {browser_path}" + Style.RESET_ALL)
                # Set environment variable for Playwright to use this browser
                os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.dirname(os.path.dirname(os.path.dirname(browser_path)))
            else:
                print(Fore.RED + "Browser not found. Please install it first." + Style.RESET_ALL)
                print(Fore.YELLOW + "Run 'install_browser.bat' from the same directory as this executable." + Style.RESET_ALL)
                print(Fore.YELLOW + "Or run 'playwright install chromium' if you have Python installed." + Style.RESET_ALL)
                input("Press Enter to exit...")
                sys.exit(1)
    except Exception as e:
        print(Fore.RED + f"Error checking browser installation: {e}" + Style.RESET_ALL)
        print(Fore.YELLOW + "Please make sure the browser is installed." + Style.RESET_ALL)
        print(Fore.YELLOW + "Run 'install_browser.bat' from the same directory as this executable." + Style.RESET_ALL)
        input("Press Enter to continue anyway...")

async def main():
    # Ensure browser is installed
    await ensure_browser_installed()

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Amazon Deal Scraper - Multi-Site Support')
    parser.add_argument('--site', type=str, help='Site name (loads config from sites/<name>.yaml)')
    parser.add_argument('--list-sites', action='store_true', help='List available sites')
    args = parser.parse_args()

    # List available sites if requested
    if args.list_sites:
        print(f"{Fore.CYAN}Available sites:{Style.RESET_ALL}")
        sites_dir = os.path.join(SCRIPT_DIR, 'sites')
        if os.path.exists(sites_dir):
            for f in sorted(os.listdir(sites_dir)):
                if f.endswith('.yaml'):
                    site_name = f.replace('.yaml', '')
                    config_path = os.path.join(sites_dir, f)
                    try:
                        with open(config_path, 'r') as cf:
                            config = yaml.safe_load(cf)
                            print(f"  {Fore.GREEN}• {site_name:<15}{Style.RESET_ALL} - {config.get('site_title', 'N/A')}")
                    except:
                        print(f"  {Fore.YELLOW}• {site_name:<15}{Style.RESET_ALL} - (error loading config)")
        else:
            print(f"{Fore.RED}No sites directory found{Style.RESET_ALL}")
        return

    # Load site config if specified
    site_config = None
    if args.site:
        site_config = load_site_config(args.site)
        if not site_config:
            print(f"{Fore.RED}Failed to load site config. Exiting.{Style.RESET_ALL}")
            return

    # Initialize themall system (database, configs, etc.)
    try:
        db, categories, settings, secrets = initialize_themall_system()

        # Check if WordPress is configured (optional)
        has_wordpress = 'wordpress' in secrets and len(secrets.get('wordpress', {})) > 0
        if not has_wordpress:
            print(Fore.YELLOW + "Note: No WordPress configuration found. Will cache to database only." + Style.RESET_ALL)
            print(Fore.YELLOW + "Tip: Use WP-CLI separately to create posts from database cache." + Style.RESET_ALL)

    except Exception as e:
        print(Fore.RED + f"Failed to initialize themall system: {e}" + Style.RESET_ALL)
        print(Fore.YELLOW + "Continuing without database/WordPress integration..." + Style.RESET_ALL)
        db = None
        categories = {}
        secrets = {}
        has_wordpress = False

    # Read search terms from site config or file
    if site_config and 'search_terms' in site_config:
        search_terms = site_config['search_terms']
        print(Fore.CYAN + f"Loaded {len(search_terms)} search terms from {args.site} config" + Style.RESET_ALL)
    else:
        search_terms = read_search_terms_from_file()
        print(Fore.CYAN + f"Loaded {len(search_terms)} search terms from file" + Style.RESET_ALL)

    # Load proxy configuration
    proxy_config = None
    proxy_config_path = os.path.join(SCRIPT_DIR, 'proxy_config.json')
    if os.path.exists(proxy_config_path):
        try:
            with open(proxy_config_path, 'r') as f:
                proxy_data = json.load(f)
                if proxy_data.get('enabled', False):
                    proxy_config = {
                        'server': proxy_data['server']
                    }
                    if proxy_data.get('username') and proxy_data.get('password'):
                        proxy_config['username'] = proxy_data['username']
                        proxy_config['password'] = proxy_data['password']
                    print(Fore.GREEN + f"✅ Proxy enabled: {proxy_data['server']}" + Style.RESET_ALL)
                else:
                    print(Fore.YELLOW + "⚠️  Proxy disabled in config" + Style.RESET_ALL)
        except Exception as e:
            print(Fore.RED + f"Error loading proxy config: {e}" + Style.RESET_ALL)
    else:
        print(Fore.YELLOW + "⚠️  No proxy_config.json found - running without proxy (may be blocked on datacenter IPs)" + Style.RESET_ALL)

    async with async_playwright() as p:
        try:
            # Try to use the browser executable path if found
            browser_path = get_browser_executable_path()
            if browser_path:
                print(Fore.GREEN + f"Using browser at: {browser_path}" + Style.RESET_ALL)
                # Set environment variable for Playwright
                os.environ["PLAYWRIGHT_BROWSERS_PATH"] = os.path.dirname(os.path.dirname(os.path.dirname(browser_path)))

            # Launch the browser with stealth settings
            # Use headless=True for Digital Ocean servers, headless=False for local testing
            print(Fore.CYAN + "Launching browser with stealth mode..." + Style.RESET_ALL)

            launch_options = {
                'headless': False,  # Set to True for Digital Ocean, False for local testing
                'args': [
                    '--disable-blink-features=AutomationControlled',  # Hide automation
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                ]
            }

            # Add proxy if configured
            if proxy_config:
                launch_options['proxy'] = proxy_config
                print(Fore.GREEN + "🌐 Browser will use proxy" + Style.RESET_ALL)

            browser = await p.chromium.launch(**launch_options)
        except Exception as e:
            print(Fore.RED + f"Error launching browser: {e}" + Style.RESET_ALL)
            print(Fore.YELLOW + "Make sure Playwright browsers are installed." + Style.RESET_ALL)
            print(Fore.YELLOW + "Run 'install_browser.bat' to install browsers." + Style.RESET_ALL)
            print(Fore.YELLOW + "Or run 'playwright install chromium' if you have Python installed." + Style.RESET_ALL)
            input("Press Enter to exit...")
            return

        # Create context with anti-detection settings
        user_agent = get_random_user_agent()
        viewport = get_random_viewport()

        print(Fore.CYAN + f"Using stealth settings - Viewport: {viewport['width']}x{viewport['height']}" + Style.RESET_ALL)

        # Skipping cookies - using text login only
        print(Fore.YELLOW + "Skipping session cookies - using fresh text login..." + Style.RESET_ALL)

        context = await browser.new_context(
            user_agent=user_agent,
            viewport=viewport,
            screen={'width': viewport['width'], 'height': viewport['height']},  # Match viewport to screen
            locale='en-CA',
            timezone_id='America/Toronto',
            geolocation={'latitude': 43.6532, 'longitude': -79.3832},  # Toronto
            permissions=['geolocation'],
            color_scheme='light',  # Real humans use light mode mostly
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-CA,en-US;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',  # Do Not Track
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            }
        )

        # Override navigator.webdriver property to hide automation
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Mock chrome object
            window.chrome = {
                runtime: {}
            };

            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-CA', 'en-US', 'en']
            });

            // Permissions API mock (looks more human)
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)

        page = await context.new_page()

        login_successful = await login_and_save_cookies(page)
        if not login_successful:
            print(Fore.RED + "Failed to log in. Exiting." + Style.RESET_ALL)
            await browser.close()
            return

        # Skipping cookie save - using fresh login each time
        print(Fore.YELLOW + "Skipping cookie save - fresh login complete" + Style.RESET_ALL)

        print(Fore.GREEN + "Login successful. Starting search scraping process." + Style.RESET_ALL)
        print(Fore.YELLOW + "⚠️  Using stealth mode with slow rate limiting to avoid detection" + Style.RESET_ALL)

        all_products = []
        for search_term in search_terms:
            try:
                products = await search_and_scrape(page, search_term)
                
                # Print detailed information about each product
                for i, product in enumerate(products):
                    print(Fore.YELLOW + f"Product {i+1}/{len(products)} for '{search_term}':" + Style.RESET_ALL)
                    print(Fore.MAGENTA + f"  Title: {product['title']}" + Style.RESET_ALL)
                    print(Fore.BLUE + f"  ASIN: {product['asin']}" + Style.RESET_ALL)
                    print(Fore.RED + f"  Discount: {product['discount']}" + Style.RESET_ALL)
                    if product['salePrice']:
                        print(Fore.GREEN + f"  Sale Price: {product['salePrice']}" + Style.RESET_ALL)
                    if product['originalPrice']:
                        print(Fore.RED + f"  Original Price: {product['originalPrice']}" + Style.RESET_ALL)
                    print(Fore.CYAN + f"  Category: {product['category']}" + Style.RESET_ALL)
                    print(Fore.WHITE + f"  URL: {product['productUrl']}" + Style.RESET_ALL)
                    print(Fore.WHITE + f"  Image: {product['imageUrl']}" + Style.RESET_ALL)
                    print()
                
                all_products.extend(products)

                # Aggressive rate limiting between searches to avoid detection
                # Amazon WILL block you if you scrape too fast
                delay = random.uniform(30, 60)  # 30-60 seconds between searches
                print(Fore.YELLOW + f"⏳ Rate limiting: waiting {delay:.1f} seconds before next search..." + Style.RESET_ALL)
                await asyncio.sleep(delay)
                
            except Exception as e:
                print(Fore.RED + f"Error searching for '{search_term}': {e}" + Style.RESET_ALL)
                continue

        await browser.close()

        # Save to Excel with date stamp
        df = pd.DataFrame(all_products)
        df = await clean_duplicates(df)
        print(f"Scraped {len(all_products)} products from search terms")
        timestamp = datetime.now().strftime('%y%m%d-%H%M')

        # Determine output filename from site config or use default
        current_dir = os.getcwd()
        if site_config and 'output' in site_config and 'xlsx_path' in site_config['output']:
            filename = os.path.join(current_dir, site_config['output']['xlsx_path'])
        else:
            filename = os.path.join(current_dir, f'search_scraped_data_{timestamp}.xlsx')
        
        # Save the original Excel file
        df.to_excel(filename, index=False)
        print(f"Original data saved to {filename}")
        
        # Create Off-Grid formatted version
        offgrid_df = create_offgrid_format(df)
        offgrid_filename = os.path.join(current_dir, f'search_offgrid_scraped_{timestamp}.xlsx')
        offgrid_df.to_excel(offgrid_filename, index=False)
        
        # Also print a more visible message
        print(f"\\n\\n{'*'*50}")
        print(f"ORIGINAL FILE SAVED TO: {filename}")
        print(f"OFFGRID FILE SAVED TO: {offgrid_filename}")
        print(f"{'*'*50}\\n\\n")

        # Save to JSON for custom PHP frontend (use original df, not offgrid_df)
        print(Fore.CYAN + "\n" + "=" * 60)
        print(Fore.CYAN + "SAVING TO JSON FOR PHP FRONTEND")
        print(Fore.CYAN + "=" * 60)

        # Determine JSON output path from site config or use default
        if site_config and 'output' in site_config and 'json_path' in site_config['output']:
            json_output_path = site_config['output']['json_path']
            site_category = site_config.get('site_category', 'audio')
        else:
            json_output_path = "themall/frontend/v0-audiogear-pro/data/products.json"
            site_category = "audio"

        json_path = save_products_json(
            df,  # Use original df with correct column names
            output_path=json_output_path,
            site_category=site_category
        )
        print(Fore.GREEN + f"✅ Frontend JSON ready at: {json_path}")
        print(Fore.CYAN + "=" * 60 + "\n")

        # Database caching and WordPress posting (optional)
        if db and ENABLE_WORDPRESS_POSTING:
            print(Fore.CYAN + "=" * 60)
            print(Fore.CYAN + "CACHING TO DATABASE & POSTING TO WORDPRESS")
            print(Fore.CYAN + "=" * 60)
        elif db:
            print(Fore.CYAN + "=" * 60)
            print(Fore.CYAN + "CACHING TO DATABASE (WordPress posting disabled)")
            print(Fore.CYAN + "=" * 60)

            cached_count = 0
            posted_count = 0
            duplicate_count = 0
            error_count = 0

            for _, row in df.iterrows():
                asin = row['asin']
                search_term = row.get('searchTerm', '')

                try:
                    # Extract discount percentage
                    discount_text = row.get('discount', '')
                    savings_percent = 0
                    if discount_text:
                        match = re.search(r'(\d+)%?', str(discount_text))
                        if match:
                            savings_percent = float(match.group(1))

                    # Parse prices (clean newlines, whitespace, and handle duplicates like "499.95499.95")
                    price_current = None
                    price_original = None

                    if row.get('salePrice'):
                        sale_str = str(row['salePrice']).replace('$', '').replace(',', '').replace('\n', '').strip()
                        # Handle duplicated prices like "499.95499.95" - extract first occurrence
                        if sale_str and not ' ' in sale_str:
                            # Try to find pattern like XX.XXXX.XX (duplicated decimal price)
                            match = re.match(r'^(\d+\.\d{2})', sale_str)
                            if match:
                                sale_str = match.group(1)
                        price_current = float(sale_str)

                    if row.get('originalPrice'):
                        orig_str = str(row['originalPrice']).replace('$', '').replace(',', '').replace('\n', '').strip()
                        # Handle duplicated prices like "499.95499.95" - extract first occurrence
                        if orig_str and not ' ' in orig_str:
                            match = re.match(r'^(\d+\.\d{2})', orig_str)
                            if match:
                                orig_str = match.group(1)
                        price_original = float(orig_str)

                    # Cache product in database (pass as dictionary)
                    db.cache_product(asin, {
                        'title': row['title'],
                        'price_current': price_current,
                        'price_original': price_original,
                        'savings_percent': savings_percent,
                        'features': [],  # Scraper doesn't get features
                        'image_url': row['imageUrl'],
                        'category': row.get('category', 'general')
                    })
                    cached_count += 1

                    # Determine which site this product should go to
                    site_key = determine_site_for_product(search_term, categories)

                    if ENABLE_WORDPRESS_POSTING and site_key and site_key in secrets.get('wordpress', {}):
                        # Check if already posted
                        if db.is_product_posted(asin, site_key):
                            print(Fore.YELLOW + f"  Skipping {asin} - already posted to {site_key}" + Style.RESET_ALL)
                            duplicate_count += 1
                            continue

                        # Initialize WordPress manager for this site (Docker or SSH)
                        wp_config = secrets['wordpress'][site_key]
                        wp_type = wp_config.get('type', 'ssh')  # Default to SSH for backward compatibility

                        if wp_type == 'docker':
                            # Use Docker exec for local WordPress
                            wp = LocalWordPress(
                                container=wp_config['container'],
                                wp_url=wp_config['wp_url'],
                                dry_run=False
                            )
                        else:
                            # Use SSH for remote WordPress (Hostinger, etc.)
                            wp = WordPressWPCLI(
                                ssh_host=wp_config['ssh_host'],
                                ssh_port=wp_config['ssh_port'],
                                ssh_user=wp_config['ssh_user'],
                                wp_path=wp_config['wp_path'],
                                dry_run=False
                            )

                        # Simple content generation (no PA-API ContentGenerator needed)

                        # Build product URL with affiliate tag
                        product_url = row['productUrl']
                        separator = '&' if '?' in product_url else '?'
                        affiliate_url = f"{product_url}{separator}tag={AMAZON_AFFILIATE_TAG}"

                        # Generate post content
                        post_title = f"{row['title'][:80]} - {savings_percent:.0f}% OFF Deal!"

                        # Simple post content
                        post_content = f"""
                        <div class="deal-content">
                            <img src="{row['imageUrl']}" alt="{row['title']}" style="max-width: 500px; height: auto;"/>
                            <h2>{row['title']}</h2>
                            <div class="price-info">
                                <p class="sale-price">Sale Price: <strong>{row['salePrice']}</strong></p>
                                <p class="original-price">Original Price: <s>{row['originalPrice']}</s></p>
                                <p class="discount">Save: <strong>{discount_text}</strong></p>
                            </div>
                            <p><a href="{affiliate_url}" class="deal-button" target="_blank" rel="nofollow">Get This Deal on Amazon →</a></p>
                        </div>
                        """

                        # Get category name from site config
                        category_name = categories[site_key].get('category', 'Deals')

                        # Post to WordPress via WP-CLI
                        try:
                            post_id = wp.create_post(
                                title=post_title,
                                content=post_content,
                                featured_image_url=row['imageUrl'],
                                tags=['sale', 'amazon deal', f'{savings_percent:.0f}% off'],
                                status='publish'
                            )

                            post_url = f"https://lawngreen-butterfly-111020.hostingersite.com/?p={post_id}"

                            # Save to database
                            db.save_posted_product(
                                asin=asin,
                                site_key=site_key,
                                wp_post_id=post_id,
                                price=price_current,
                                savings_percent=savings_percent
                            )

                            posted_count += 1
                            print(Fore.GREEN + f"  ✓ Posted {asin} to {site_key}: {post_url}" + Style.RESET_ALL)

                        except Exception as wp_error:
                            print(Fore.RED + f"  ✗ WordPress error for {asin}: {wp_error}" + Style.RESET_ALL)
                            error_count += 1

                    else:
                        print(Fore.YELLOW + f"  No WordPress site configured for '{search_term}'" + Style.RESET_ALL)

                except Exception as e:
                    print(Fore.RED + f"  Error processing {asin}: {e}" + Style.RESET_ALL)
                    error_count += 1
                    continue

            # Print summary
            print(Fore.CYAN + "\\n" + "=" * 60)
            print(Fore.CYAN + "SUMMARY")
            print(Fore.CYAN + "=" * 60)
            print(Fore.GREEN + f"  Scraped: {len(all_products)} products")
            print(Fore.BLUE + f"  Cached: {cached_count} products")
            if ENABLE_WORDPRESS_POSTING:
                print(Fore.GREEN + f"  Posted to WordPress: {posted_count} products")
                print(Fore.YELLOW + f"  Duplicates skipped: {duplicate_count} products")
            else:
                print(Fore.YELLOW + f"  WordPress posting: DISABLED (using JSON mode)")
            print(Fore.MAGENTA + f"  JSON frontend: ENABLED")
            if error_count > 0:
                print(Fore.RED + f"  Errors: {error_count} products")
            print(Fore.CYAN + "=" * 60 + Style.RESET_ALL)
        else:
            print(Fore.YELLOW + "Database not initialized. Skipping database caching and WordPress posting." + Style.RESET_ALL)

        print("\\nSearch scraping completed!")

if __name__ == "__main__":
    asyncio.run(main())