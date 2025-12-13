import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse, parse_qs, urlencode
import os
import re
import ssl
import uuid
import logging
import urllib3
from datetime import datetime, timezone
from database import SessionLocal
import models
from process import process_media

# Try to import cloudscraper for bypassing Cloudflare protection
try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False
    logging.warning("cloudscraper not installed - some sites may block scraping")

# Disable SSL warnings for development
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Directory to store downloads
DOWNLOAD_DIR = "data/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Image quality settings for URL upgrades
IMAGE_QUALITY_SETTINGS = {
    'standard_width': 1200,
    'standard_quality': 75,
    'sky_resolution': '1600x900',
    'aljazeera_resize': '1920,1440',
    'aljazeera_quality': 80,
}

# Article ID matching thresholds for image relevance
# Images with article IDs within these ranges are considered related
ARTICLE_ID_HIGH_PRIORITY_THRESHOLD = 10000    # Within 10k = same article cluster
ARTICLE_ID_MEDIUM_PRIORITY_THRESHOLD = 100000  # Within 100k = related content

# Scraping limits
MIN_IMAGE_SIZE_BYTES = 5000  # Skip images smaller than 5KB (likely icons/trackers)
MAX_IMAGES_PER_SCRAPE = 15   # Maximum images to download per article

# Sites known to use Cloudflare or aggressive bot protection
CLOUDFLARE_SITES = [
    'dailymail.co.uk',
    'mirror.co.uk',
    'express.co.uk',
    'thesun.co.uk',
    'metro.co.uk',
    'standard.co.uk',
    'independent.co.uk',
]

# Sites that completely block automated access (need archive workaround)
BLOCKED_SITES = [
    'dailymail.co.uk',  # Uses Akamai with strict bot detection
    'mailonline.co.uk',
    'nytimes.com',  # Uses CAPTCHA/Cloudflare protection
    'telegraph.co.uk',  # 403 Forbidden
    'reuters.com',  # 401 Unauthorized
    'itv.com',  # 403 Forbidden
    'cnn.com',  # 451 Geo-blocked
    'inews.co.uk',  # Blocked
    'thetimes.com',  # Paywall + blocked
    'thetimes.co.uk',  # Paywall + blocked
]

def is_blocked_site(url):
    """Check if site is known to completely block automated scraping."""
    url_lower = url.lower()
    # Don't block if already using an archive service
    if 'archive.is' in url_lower or 'archive.today' in url_lower or 'archive.ph' in url_lower:
        return False
    if 'web.archive.org' in url_lower:
        return False
    return any(site in url_lower for site in BLOCKED_SITES)


# Source name mapping for provenance tracking
SOURCE_NAME_MAP = {
    'bbc.co.uk': 'BBC News',
    'bbc.com': 'BBC News',
    'theguardian.com': 'The Guardian',
    'mirror.co.uk': 'Daily Mirror',
    'independent.co.uk': 'The Independent',
    'standard.co.uk': 'Evening Standard',
    'mylondon.news': 'MyLondon',
    'theargus.co.uk': 'The Argus',
    'sky.com': 'Sky News',
    'aljazeera.com': 'Al Jazeera',
    'nytimes.com': 'The New York Times',
    'express.co.uk': 'Daily Express',
    'telegraph.co.uk': 'The Telegraph',
    'metro.co.uk': 'Metro',
    'dailymail.co.uk': 'Daily Mail',
    'thesun.co.uk': 'The Sun',
    'reuters.com': 'Reuters',
    'apnews.com': 'AP News',
    'middleeasteye.net': 'Middle East Eye',
    # Additional sites tested
    'gbnews.com': 'GB News',
    'timesofisrael.com': 'Times of Israel',
    'thejc.com': 'The Jewish Chronicle',
    'channel4.com': 'Channel 4 News',
    'itv.com': 'ITV News',
    'cnn.com': 'CNN',
    'inews.co.uk': 'The i',
    'thetimes.com': 'The Times',
    'thetimes.co.uk': 'The Times',
}


def get_source_name(url: str) -> str:
    """
    Extract source name from URL for provenance tracking.

    Args:
        url: The article URL

    Returns:
        Human-readable source name or domain if unknown
    """
    url_lower = url.lower()
    for domain, name in SOURCE_NAME_MAP.items():
        if domain in url_lower:
            return name

    # Fallback: extract domain name
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace('www.', '')
        return domain.split('.')[0].title()
    except Exception:
        return "Unknown Source"


def request_wayback_save(url: str) -> dict:
    """
    Request Wayback Machine to save a page. Returns status info.

    Args:
        url: The URL to archive

    Returns:
        Dict with 'success', 'job_id', and 'message' keys
    """
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    })

    try:
        # Use Save Page Now API
        save_url = f"https://web.archive.org/save/{url}"
        response = session.get(save_url, timeout=30, allow_redirects=False)

        if response.status_code in [302, 200]:
            # Redirect means save initiated
            location = response.headers.get('Location', '')
            if 'web.archive.org/web/' in location:
                return {
                    'success': True,
                    'url': location,
                    'message': 'Archive created successfully'
                }
            return {
                'success': True,
                'url': None,
                'message': 'Archive save initiated. Please wait 1-2 minutes and retry.'
            }
    except Exception as e:
        logging.debug(f"Wayback save request failed: {e}")

    return {
        'success': False,
        'url': None,
        'message': 'Could not initiate archive save'
    }


def get_archive_url(url: str, request_save: bool = False) -> tuple:
    """
    Try to get an archived version of a blocked URL.
    Checks multiple archive services and can request a new archive.

    Args:
        url: The original URL to find archived
        request_save: If True, request Wayback Machine to save if not found

    Returns:
        Tuple of (archive_url, message) - archive_url is None if not found
    """
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    })

    # Try Wayback Machine first (most reliable for automated access)
    try:
        wayback_api = f"https://archive.org/wayback/available?url={url}"
        response = session.get(wayback_api, timeout=10)
        if response.status_code == 200:
            data = response.json()
            snapshots = data.get('archived_snapshots', {})
            closest = snapshots.get('closest', {})
            if closest.get('available') and closest.get('url'):
                wayback_url = closest['url']
                logging.info(f"Found Wayback Machine archive: {wayback_url}")
                return (wayback_url, "Found existing Wayback Machine archive")
    except Exception as e:
        logging.debug(f"Wayback Machine check failed: {e}")

    # Try archive.today/archive.is variants
    archive_services = [
        f"https://archive.today/newest/{url}",
        f"https://archive.is/newest/{url}",
        f"https://archive.ph/newest/{url}",
    ]

    for archive_url in archive_services:
        try:
            response = session.head(archive_url, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                final_url = response.url
                # Check we got redirected to an actual archive page (not CAPTCHA/404)
                if final_url != archive_url and '/wip/' not in final_url:
                    # Verify it's not a CAPTCHA page
                    check_resp = session.get(final_url, timeout=10)
                    content_lower = check_resp.content.lower()
                    if b'security check' not in content_lower and b'captcha' not in content_lower:
                        logging.info(f"Found archive at: {final_url}")
                        return (final_url, "Found existing archive.today snapshot")
        except Exception as e:
            logging.debug(f"Archive check failed for {archive_url}: {e}")
            continue

    # No existing archive found - try to create one if requested
    if request_save:
        save_result = request_wayback_save(url)
        if save_result['success'] and save_result['url']:
            return (save_result['url'], save_result['message'])
        elif save_result['success']:
            return (None, save_result['message'])

    # Build helpful instructions for the user
    archive_today_url = f"https://archive.today/?run=1&url={url}"
    wayback_save_url = f"https://web.archive.org/save/{url}"

    instructions = (
        f"No archive found for this blocked site. To scrape images:\n"
        f"1. Open: {archive_today_url}\n"
        f"   (Complete any CAPTCHA, wait for archive to complete)\n"
        f"2. Or open: {wayback_save_url}\n"
        f"   (Wait 1-2 minutes for processing)\n"
        f"3. Then paste the archive URL here instead of the original URL."
    )

    return (None, instructions)


def is_wayback_url(url):
    """Check if URL is from Wayback Machine."""
    return 'web.archive.org' in url.lower()


def convert_wayback_image_url(img_url, page_timestamp=None):
    """
    Convert a regular image URL found on a Wayback page to the proper Wayback image URL format.
    Wayback uses /web/TIMESTAMP_im_/URL format for images.
    """
    if 'web.archive.org' in img_url:
        # Already a Wayback URL, ensure it has im_ modifier for images
        if '/web/' in img_url and 'im_/' not in img_url:
            # Add im_ modifier before the original URL
            parts = img_url.split('/web/')
            if len(parts) == 2:
                rest = parts[1]
                # Format: timestamp/original_url
                if '/' in rest:
                    timestamp_end = rest.find('/')
                    timestamp = rest[:timestamp_end]
                    original = rest[timestamp_end+1:]
                    return f"https://web.archive.org/web/{timestamp}im_/{original}"
        return img_url
    elif page_timestamp:
        # Convert regular URL to Wayback format
        return f"https://web.archive.org/web/{page_timestamp}im_/{img_url}"
    return img_url


def request_archive_save(url):
    """
    Request archive.today to save a new snapshot of the URL.
    Returns the job URL to check status, or None if failed.
    """
    try:
        # archive.today submit endpoint
        submit_url = "https://archive.today/submit/"
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
        })

        response = session.post(
            submit_url,
            data={'url': url},
            timeout=30,
            allow_redirects=True
        )

        if response.status_code == 200:
            # Returns the archived page URL
            return response.url

    except Exception as e:
        logging.warning(f"Failed to request archive save: {e}")

    return None

class SSLAdapter(HTTPAdapter):
    """Custom SSL adapter that disables certificate verification."""
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)

def needs_cloudscraper(url):
    """Check if URL is from a site that needs cloudscraper."""
    url_lower = url.lower()
    return any(site in url_lower for site in CLOUDFLARE_SITES)

def create_scraper_session(url=None):
    """
    Create a scraper session appropriate for the target URL.
    Uses cloudscraper for Cloudflare-protected sites, regular requests otherwise.
    """
    # Use cloudscraper for protected sites
    if url and needs_cloudscraper(url) and HAS_CLOUDSCRAPER:
        logging.info(f"Using cloudscraper for protected site: {url}")
        try:
            scraper = cloudscraper.create_scraper(
                browser={
                    'browser': 'chrome',
                    'platform': 'windows',
                    'desktop': True
                },
                # Disable SSL verification for sites with cert issues
                # This is safe since we're just scraping public news pages
            )
            # Try to set SSL verify to False at session level
            scraper.verify = False
            return scraper
        except Exception as e:
            logging.warning(f"Failed to create cloudscraper: {e}, falling back to requests")

    # Fallback to regular requests with browser headers
    session = requests.Session()
    session.mount('https://', SSLAdapter())
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
    })
    return session


def fetch_with_curl_fallback(url, timeout=15):
    """
    Fallback to curl subprocess if Python requests fail.
    Used for stubborn sites that block all Python HTTP libraries.
    """
    import subprocess
    import tempfile

    try:
        # Use curl with browser-like headers
        result = subprocess.run([
            'curl', '-s', '-L',
            '-H', 'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            '-H', 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            '-H', 'Accept-Language: en-US,en;q=0.9',
            '--connect-timeout', str(timeout),
            url
        ], capture_output=True, text=True, timeout=timeout + 5)

        if result.returncode == 0:
            return result.stdout
    except Exception as e:
        logging.warning(f"curl fallback failed: {e}")

    return None

def scrape_images_from_url(url, protest_id=None, status_callback=None):
    """
    Scrapes images from a web page (news article, etc.) and processes them.
    Uses cloudscraper for Cloudflare-protected sites.
    For blocked sites, attempts to use archive.is/archive.org as fallback.
    """
    original_url = url

    # Check if site is known to block all automated access
    if is_blocked_site(url):
        if status_callback:
            status_callback("log", "This site blocks direct scraping. Checking for archived version...")
            status_callback("status_update", "Checking Archives")

        # Try to find an archived version (with request_save to try Wayback if not found)
        archive_url, archive_message = get_archive_url(url, request_save=True)

        if archive_url:
            if status_callback:
                status_callback("log", f"Found archive! Using: {archive_url[:60]}...")
            url = archive_url
        else:
            # No archive found - provide detailed instructions
            if status_callback:
                status_callback("log", archive_message)
                status_callback("complete", {
                    "message": archive_message,
                    "media_id": None,
                    "blocked_site": True,
                    "archive_instructions": True
                })
            return

    if status_callback:
        status_callback("status_update", "Connecting")

    # Create appropriate scraper session for the URL
    scraper = create_scraper_session(url)

    # Log which scraper is being used
    using_cloudscraper = needs_cloudscraper(url) and HAS_CLOUDSCRAPER
    if status_callback:
        if using_cloudscraper:
            status_callback("log", "Using advanced scraper to bypass site protection...")
        else:
            status_callback("log", "Attempting to scrape images from page...")

    try:
        if status_callback:
            status_callback("status_update", "Scraping")

        html_content = None

        # Try scraper first
        try:
            response = scraper.get(url, timeout=15, verify=False)
            response.raise_for_status()
            html_content = response.content
        except Exception as e:
            logging.warning(f"Primary scraper failed: {e}, trying curl fallback...")
            if status_callback:
                status_callback("log", "Primary method blocked, trying alternative...")

            # Fallback to curl
            html_text = fetch_with_curl_fallback(url)
            if html_text:
                html_content = html_text.encode('utf-8')
            else:
                raise Exception(f"All scraping methods failed for {url}")

        # Parse content
        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract meaningful text for description
        article_text = ""
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = p.get_text().strip()
            if len(text) > 50:  # Filter short snippets
                article_text += text + "\n\n"

        # Truncate for DB
        description_text = f"Scraped from {url}\n\n{article_text[:1000]}"
        if len(article_text) > 1000:
            description_text += "..."

        # Collect potential image URLs
        potential_urls = []

        # 1. Open Graph Image (Highest Quality usually)
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            potential_urls.append(og_image['content'])
            if status_callback:
                status_callback("log", "Found Article Main Image (OpenGraph).")

        # 2. Main Content Images (handling lazy loading)
        images = soup.find_all('img')
        for img in images:
            # Check common lazy loading attributes in order of preference
            src = img.get('data-src') or img.get('data-original') or img.get('data-lazy-src') or img.get('src')

            # Handle srcset - parse and get the largest (simplified: get last url)
            srcset = img.get('srcset')
            if srcset and not src:
                try:
                    candidates = srcset.split(',')
                    last_candidate = candidates[-1].strip().split(' ')[0]
                    src = last_candidate
                except:
                    pass

            if src:
                potential_urls.append(src)

        # 3. Extract captions and credits for images
        # Build a map of image URL -> caption/credit info
        image_captions = {}  # Maps image URL (or partial) to caption
        image_credits = {}   # Maps image URL (or partial) to rights holder/photographer

        # Extract from <figure> elements (most common pattern)
        for figure in soup.find_all('figure'):
            # Find image in figure
            img = figure.find('img')
            if not img:
                continue

            img_src = img.get('data-src') or img.get('src') or ''

            # Find figcaption
            figcaption = figure.find('figcaption')
            if figcaption:
                caption_text = figcaption.get_text(strip=True)
                if caption_text and len(caption_text) > 10:
                    image_captions[img_src] = caption_text

                    # Try to extract credit (often in parentheses or after "Credit:", "Photo:", etc.)
                    credit_match = re.search(
                        r'(?:Credit|Photo|Image|Source|©|\()?:?\s*([A-Z][A-Za-z\s]+(?:Images?|News|Media|Photos?|Press|Agency|Pictures)?)\)?$',
                        caption_text
                    )
                    if credit_match:
                        image_credits[img_src] = credit_match.group(1).strip()

            # Also check for data-caption attribute
            data_caption = img.get('data-caption') or figure.get('data-caption')
            if data_caption and img_src not in image_captions:
                image_captions[img_src] = data_caption

        # Extract credits from dedicated credit elements
        for credit_elem in soup.find_all(['span', 'div', 'p'], class_=re.compile(r'credit|source|photographer', re.I)):
            credit_text = credit_elem.get_text(strip=True)
            if credit_text and len(credit_text) < 100:
                # Try to associate with nearby image
                parent = credit_elem.find_parent(['figure', 'div'])
                if parent:
                    img = parent.find('img')
                    if img:
                        img_src = img.get('data-src') or img.get('src') or ''
                        if img_src:
                            image_credits[img_src] = credit_text

        if status_callback and (image_captions or image_credits):
            status_callback("log", f"Extracted {len(image_captions)} captions, {len(image_credits)} credits")

        def find_caption_for_url(target_url: str) -> tuple:
            """
            Find caption and credit for an image URL.

            Args:
                target_url: The image URL to look up

            Returns:
                Tuple of (caption, rights_holder) - either may be None
            """
            # Try exact match first
            if target_url in image_captions:
                return (image_captions.get(target_url), image_credits.get(target_url))

            # Try partial match (URLs may differ in params or protocol)
            target_lower = target_url.lower()
            for stored_url, caption in image_captions.items():
                # Match by filename
                stored_filename = stored_url.split('/')[-1].split('?')[0].lower()
                target_filename = target_lower.split('/')[-1].split('?')[0]
                if stored_filename and target_filename and stored_filename == target_filename:
                    return (caption, image_credits.get(stored_url))

            return (None, None)

        # 4. Extract images from JSON data, data attributes, and inline scripts
        # Many modern sites embed image URLs in JSON or data attributes for lazy loading
        html_text = html_content.decode('utf-8', errors='ignore') if isinstance(html_content, bytes) else html_content

        # Extract article ID from URL to prioritize related images
        # Handles formats like: /article-12345678, /article12345678.ece, or /story-name-12345678
        article_id_match = re.search(r'(?:article-?|-)(\d{7,})(?:$|[/?#])', url)
        article_id = int(article_id_match.group(1)) if article_id_match else None

        # Extract Sky News video ID from URL (e.g., -13444801 at end)
        sky_video_id = None
        sky_match = re.search(r'-(\d{7,})$', url.split('?')[0])
        if sky_match and 'sky.com' in url.lower():
            sky_video_id = sky_match.group(1)

        # Pattern for common news site CDN image URLs (high quality versions)
        # Matches URLs like:
        # - https://i2-prod.mirror.co.uk/incoming/article123.ece/ALTERNATES/s1200/image.jpg
        # - https://cdn.images.express.co.uk/img/dynamic/1/1200x712/secondary/London-5674436.webp
        # Note: Using length-limited patterns to prevent ReDoS attacks
        cdn_patterns = [
            # Mirror/Reach PLC sites (mirror.co.uk, mylondon.news, etc.)
            # All quantifiers bounded to prevent ReDoS attacks
            r'https://i[0-9]-prod\.[a-z]{1,20}\.co\.uk/[\w./-]{1,200}/ALTERNATES/s(?:1200|810|615)[\w./-]{0,100}\.(?:jpg|jpeg|png|webp)',
            r'https://i[0-9]-prod\.mylondon\.news/[\w./-]{1,200}/ALTERNATES/s(?:1200|810|615)[\w./-]{0,100}\.(?:jpg|jpeg|png|webp)',
            r'https://[a-z0-9.-]{1,50}/incoming/article[0-9]{1,12}\.ece/[\w./-]{1,200}\.(?:jpg|jpeg|png|webp)',
            # NY Times CDN (high quality: superJumbo, jumbo, videoSixteenByNine3000, threeByTwoLargeAt2X)
            r'https://static01\.nyt\.com/images/[\w./-]{1,200}(?:superJumbo|jumbo|videoSixteenByNine3000|threeByTwoLargeAt2X)[\w.-]{0,50}\.(?:jpg|jpeg|png|webp)',
            # Evening Standard CDN (static.standard.co.uk) - date + time path
            r'https://static\.standard\.co\.uk/\d{4}/\d{2}/\d{2}/\d{1,2}/\d{2}/[\w.()\-]{1,150}\.(?:jpg|jpeg|png|webp)(?:\?[\w=&%]{0,100})?',
            # Sky News CDN (e3.365dm.com) - capture various sizes
            r'https://e3\.365dm\.com/\d{2}/\d{2}/[\w/x]{1,20}/[\w._-]{1,100}\.(?:jpg|jpeg|png|webp)(?:\?\d{0,20})?',
            # Al Jazeera (wp-content/uploads) - length limited to prevent ReDoS
            r'https://www\.aljazeera\.com/wp-content/uploads/\d{4}/\d{2}/[\w._-]{1,200}\.(?:jpg|jpeg|png|webp)',
            # Express CDN (high quality versions: 1200x, 940x, 674x)
            r'https://cdn\.images\.express\.co\.uk/img/dynamic/[\w/-]{1,100}(?:1200|940|674)[\w/-]{0,50}\.(?:jpg|jpeg|png|webp)',
            # Independent CDN (static.independent.co.uk)
            r'https://static\.independent\.co\.uk/[\d/]{1,30}/[\w._()-]{1,200}\.(?:jpg|jpeg|png|webp)(?:\?[\w=&%]{0,100})?',
            # The Argus / Newsquest CDN (theargus.co.uk, brightonandhoveindependent.co.uk)
            r'https://www\.theargus\.co\.uk/resources/images/[\w/-]{1,150}\.(?:jpg|jpeg|png|webp)',
            r'https://[a-z0-9.-]{1,50}\.newsquestdigital\.co\.uk/[\w./-]{1,200}\.(?:jpg|jpeg|png|webp)',
            # GB News (RebelMouse CDN with media-library path)
            r'https://www\.gbnews\.com/media-library/[\w./-]{1,200}\.(?:jpg|jpeg|png|webp)(?:\?[\w=&%-]{0,200})?',
            # Times of Israel CDN
            r'https://static-cdn\.toi-media\.com/www/uploads/\d{4}/\d{2}/[\w._-]{1,200}\.(?:jpg|jpeg|png|webp)',
            # The Jewish Chronicle (Atex Cloud)
            r'https://api\.thejc\.atexcloud\.io/image-service/[\w/.-]{1,200}\.(?:jpg|jpeg|png|webp)(?:\?[\w=&%.:-]{0,100})?',
            # Channel 4 News (AWS S3)
            r'https://fournews-assets-prod-s3[a-z0-9-]{0,30}\.s3\.amazonaws\.com/media/\d{4}/\d{2}/[\w._-]{1,200}\.(?:jpg|jpeg|png|webp)',
            # Generic CloudFront CDN
            r'https://[a-z0-9.-]{1,50}\.cloudfront\.net/[\w./-]{1,200}\.(?:jpg|jpeg|png|webp)',
        ]

        # Collect all matches, prioritizing images from the same article
        all_cdn_urls = []
        for pattern in cdn_patterns:
            matches = re.findall(pattern, html_text, re.IGNORECASE)
            all_cdn_urls.extend(matches)

        # Upgrade image URLs to highest quality versions
        def upgrade_image_url(img_url: str) -> str:
            """
            Upgrade image URL to highest quality version available.

            Args:
                img_url: Original image URL from the page

            Returns:
                Modified URL with parameters for highest quality version
            """
            img_url_lower = img_url.lower()

            # Evening Standard: upgrade width parameter using proper URL parsing
            if 'static.standard.co.uk' in img_url_lower:
                parsed = urlparse(img_url)
                params = parse_qs(parsed.query)
                params['width'] = [str(IMAGE_QUALITY_SETTINGS['standard_width'])]
                params['quality'] = [str(IMAGE_QUALITY_SETTINGS['standard_quality'])]
                params['auto'] = ['webp']
                new_query = urlencode(params, doseq=True)
                return urlunparse(parsed._replace(query=new_query, fragment=''))

            # Sky News: upgrade to highest resolution
            if 'e3.365dm.com' in img_url_lower:
                return re.sub(
                    r'/\d+x\d+/',
                    f'/{IMAGE_QUALITY_SETTINGS["sky_resolution"]}/',
                    img_url
                )

            # Al Jazeera: upgrade to highest quality using proper URL parsing
            if 'aljazeera.com/wp-content/uploads' in img_url_lower:
                parsed = urlparse(img_url)
                new_query = urlencode({
                    'resize': IMAGE_QUALITY_SETTINGS['aljazeera_resize'],
                    'quality': IMAGE_QUALITY_SETTINGS['aljazeera_quality']
                })
                return urlunparse(parsed._replace(query=new_query, fragment=''))

            # Independent: upgrade quality parameter
            if 'static.independent.co.uk' in img_url_lower:
                parsed = urlparse(img_url)
                params = parse_qs(parsed.query)
                params['width'] = [str(IMAGE_QUALITY_SETTINGS['standard_width'])]
                params['quality'] = [str(IMAGE_QUALITY_SETTINGS['standard_quality'])]
                new_query = urlencode(params, doseq=True)
                return urlunparse(parsed._replace(query=new_query, fragment=''))

            return img_url

        # Sort: prioritize images by relevance (all return 0-2 for consistent sorting)
        def article_relevance(img_url: str) -> int:
            """
            Calculate relevance score for an image URL.

            Args:
                img_url: Image URL to evaluate

            Returns:
                Priority score: 0 = high priority, 1 = medium, 2 = low
            """
            img_url_lower = img_url.lower()

            # NY Times: prioritize by size (superJumbo > jumbo > others)
            if 'static01.nyt.com' in img_url_lower:
                if 'superjumbo' in img_url_lower:
                    return 0  # Highest quality
                elif 'jumbo' in img_url_lower:
                    return 1
                return 2

            # Sky News: prioritize images matching article ID, then by size
            if 'e3.365dm.com' in img_url_lower:
                try:
                    img_id_match = re.search(r'_(\d{7,})\.', img_url)
                    if img_id_match and sky_video_id:
                        if img_id_match.group(1) == sky_video_id:
                            return 0  # Exact match - highest priority
                except re.error:
                    pass
                # Fallback to size-based priority (normalized to 0-2)
                if '1600x900' in img_url:
                    return 0
                elif '768x432' in img_url:
                    return 1
                return 2

            # Express: "secondary" images are main article images
            if '/secondary/' in img_url_lower:
                return 0  # High priority

            # Mirror/Reach: Match article ID using defined thresholds
            try:
                match = re.search(r'article(\d+)', img_url)
                if match and article_id:
                    img_article_id = int(match.group(1))
                    diff = abs(img_article_id - article_id)
                    if diff < ARTICLE_ID_HIGH_PRIORITY_THRESHOLD:
                        return 0  # High priority
                    elif diff < ARTICLE_ID_MEDIUM_PRIORITY_THRESHOLD:
                        return 1  # Medium priority
            except (re.error, ValueError):
                pass

            return 2  # Low priority (unrelated articles)

        all_cdn_urls.sort(key=article_relevance)

        # Deduplicate images - keep only highest quality version of each unique image
        seen_bases = set()
        deduped_urls = []
        for img_url in all_cdn_urls:
            try:
                img_url_lower = img_url.lower()

                # NY Times deduplication - extract base name without size suffix
                if 'static01.nyt.com' in img_url_lower:
                    base_match = re.search(
                        r'/([^/]+?)(?:-superJumbo|-jumbo|-videoSixteenByNine3000|-threeByTwoLargeAt2X)',
                        img_url, re.IGNORECASE
                    )
                    if base_match:
                        base_id = base_match.group(1).lower()
                        if base_id in seen_bases:
                            continue
                        seen_bases.add(base_id)

                # Sky News deduplication (by image name without size)
                elif 'e3.365dm.com' in img_url_lower:
                    base_match = re.search(r'/\d+x\d+/([^?]+)', img_url)
                    if base_match:
                        base_id = base_match.group(1).lower()
                        if base_id in seen_bases:
                            continue
                        seen_bases.add(base_id)

                # Evening Standard deduplication (by filename)
                elif 'static.standard.co.uk' in img_url_lower:
                    base_match = re.search(r'/([^/?]+\.(?:jpg|jpeg|png|webp))', img_url, re.IGNORECASE)
                    if base_match:
                        base_id = base_match.group(1).lower()
                        if base_id in seen_bases:
                            continue
                        seen_bases.add(base_id)

                # Al Jazeera deduplication (by filename)
                elif 'aljazeera.com/wp-content/uploads' in img_url_lower:
                    base_match = re.search(r'/([^/?]+\.(?:jpg|jpeg|png|webp))', img_url, re.IGNORECASE)
                    if base_match:
                        base_id = base_match.group(1).lower()
                        if base_id in seen_bases:
                            continue
                        seen_bases.add(base_id)

                # Independent deduplication (by filename)
                elif 'static.independent.co.uk' in img_url_lower:
                    base_match = re.search(r'/([^/?]+\.(?:jpg|jpeg|png|webp))', img_url, re.IGNORECASE)
                    if base_match:
                        base_id = base_match.group(1).lower()
                        if base_id in seen_bases:
                            continue
                        seen_bases.add(base_id)

                # The Argus / Newsquest deduplication (by filename)
                elif 'theargus.co.uk' in img_url_lower or 'newsquestdigital.co.uk' in img_url_lower:
                    base_match = re.search(r'/([^/?]+\.(?:jpg|jpeg|png|webp))', img_url, re.IGNORECASE)
                    if base_match:
                        base_id = base_match.group(1).lower()
                        if base_id in seen_bases:
                            continue
                        seen_bases.add(base_id)

                # MyLondon deduplication (same as Mirror/Reach)
                elif 'mylondon.news' in img_url_lower:
                    base_match = re.search(r'article(\d+)', img_url)
                    if base_match:
                        base_id = base_match.group(1)
                        if base_id in seen_bases:
                            continue
                        seen_bases.add(base_id)

                # Upgrade URL to highest quality and add
                deduped_urls.append(upgrade_image_url(img_url))
            except (re.error, AttributeError):
                # Skip URLs that cause regex errors, still add them unprocessed
                deduped_urls.append(img_url)

        potential_urls.extend(deduped_urls)

        if status_callback and len(potential_urls) > 1:
            status_callback("log", f"Found {len(potential_urls)} potential images in page.")

        saved_count = 0
        seen_urls = set()
        db = SessionLocal()

        try:
            # Extract article metadata for provenance tracking (always needed)
            og_title = soup.find('meta', property='og:title')
            title = og_title['content'] if og_title else (soup.title.string if soup.title else "Scraped Article")
            clean_title = title.strip() if title else "Scraped Article"

            # Extract publication date
            pub_time = soup.find('meta', property='article:published_time') or \
                       soup.find('meta', {'name': 'date'}) or \
                       soup.find('meta', {'name': 'parsely-pub-date'})
            event_date = datetime.now(timezone.utc)
            if pub_time and pub_time.get('content'):
                try:
                    dt_str = pub_time['content'].split('T')[0]
                    event_date = datetime.strptime(dt_str, "%Y-%m-%d")
                except Exception:
                    pass

            # Create a protest placeholder if needed
            if not protest_id:
                # Location detection (Naive Heuristic via Title/Desc)
                loc = "Unknown"
                text_lower = (clean_title + description_text[:200]).lower()
                if "london" in text_lower: loc = "London, UK"
                elif "manchester" in text_lower: loc = "Manchester, UK"
                elif "glasgow" in text_lower: loc = "Glasgow, UK"
                elif "birmingham" in text_lower: loc = "Birmingham, UK"
                elif "liverpool" in text_lower: loc = "Liverpool, UK"
                elif "bristol" in text_lower: loc = "Bristol, UK"
                elif "leeds" in text_lower: loc = "Leeds, UK"
                elif "cardiff" in text_lower: loc = "Cardiff, UK"

                new_protest = models.Protest(
                    name=f"{clean_title[:80]}",
                    date=event_date,
                    location=loc,
                    description=description_text
                )
                db.add(new_protest)
                db.commit()
                db.refresh(new_protest)
                protest_id = new_protest.id
                if status_callback:
                    status_callback("log", f"Created protest record from article: {clean_title[:50]}...")

            # Extract Wayback timestamp if we're scraping from archive
            wayback_timestamp = None
            if is_wayback_url(url):
                # Extract timestamp from URL like: web.archive.org/web/20241231215734/...
                match = re.search(r'web\.archive\.org/web/(\d{14})/', url)
                if match:
                    wayback_timestamp = match.group(1)
                    if status_callback:
                        status_callback("log", f"Scraping from Wayback Machine archive ({wayback_timestamp[:8]})")

            # Process each potential image URL
            for img_url_raw in potential_urls:
                if not img_url_raw:
                    continue

                # Resolve relative URLs
                img_url = urljoin(url, img_url_raw)

                # For Wayback pages, convert image URLs to proper format
                if wayback_timestamp and 'web.archive.org' not in img_url:
                    img_url = convert_wayback_image_url(img_url, wayback_timestamp)
                elif is_wayback_url(img_url):
                    img_url = convert_wayback_image_url(img_url)

                # Deduplicate (use original URL for dedup to catch Wayback variants)
                dedup_key = img_url.split('im_/')[-1] if 'im_/' in img_url else img_url
                if dedup_key in seen_urls:
                    continue
                seen_urls.add(dedup_key)

                # Filter out irrelevant images
                img_url_lower = img_url.lower()

                # Skip icons, logos, trackers
                if any(x in img_url_lower for x in ['icon', 'logo', 'tracker', 'pixel', 'badge', 'avatar']):
                    continue

                # Skip unrelated content sections (celebrity, sports, entertainment, etc.)
                # These are often in sidebar/related articles on news sites
                unrelated_keywords = [
                    '/royals/', '/celeb', '/sport/', '/football/', '/showbiz/',
                    '/tv-news/', '/lifestyle/', '/money/', '/travel/',
                    'meghan', 'kardashian', 'taylor-swift', 'strictly',
                ]
                if any(kw in img_url_lower for kw in unrelated_keywords):
                    continue

                # Download image
                try:
                    if status_callback:
                        status_callback("status_update", "Downloading")

                    # Use a simple requests session for image downloads
                    # Images are typically served from CDNs that don't need Cloudflare bypass
                    img_session = requests.Session()
                    img_session.mount('https://', SSLAdapter())
                    img_session.headers.update({
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                        'Referer': url,  # Some CDNs check referer
                    })
                    img_data = img_session.get(img_url, timeout=10, verify=False).content

                    # Skip small files (likely icons/trackers)
                    if len(img_data) < MIN_IMAGE_SIZE_BYTES:
                        continue

                    # Verify we got actual image data, not HTML error page
                    if img_data[:5] == b'<!DOC' or img_data[:5] == b'<html':
                        logging.debug(f"Got HTML instead of image for {img_url[:60]}")
                        continue

                    ext = os.path.splitext(img_url)[1].split('?')[0]
                    if not ext or len(ext) > 5:
                        ext = ".jpg"

                    filename = f"scraped_{uuid.uuid4().hex}{ext}"
                    filepath = os.path.join(DOWNLOAD_DIR, filename)

                    with open(filepath, "wb") as f:
                        f.write(img_data)

                    # Calculate web-accessible URL
                    web_url = f"/data/downloads/{filename}"

                    # Emit event for UI
                    if status_callback:
                        status_callback("scraped_image", {
                            "url": web_url,
                            "filename": filename
                        })
                        status_callback("log", f"Scraped image: {filename}")

                    # Look up caption and credit for this image
                    img_caption, img_credit = find_caption_for_url(img_url_raw)

                    # Create Media Record with provenance tracking
                    new_media = models.Media(
                        url=filepath,
                        type='image',
                        protest_id=protest_id,
                        timestamp=datetime.now(timezone.utc),
                        processed=False,
                        # Provenance fields
                        source_url=original_url,
                        source_name=get_source_name(original_url),
                        caption=img_caption,
                        rights_holder=img_credit,
                        article_headline=clean_title[:500] if clean_title else None,
                        article_summary=description_text[:1000] if description_text else None,
                        scraped_at=datetime.now(timezone.utc)
                    )
                    db.add(new_media)
                    db.commit()
                    db.refresh(new_media)

                    saved_count += 1

                    # Trigger analysis immediately for each image
                    if status_callback:
                        status_callback("status_update", "Analyzing")
                    process_media(new_media.id, status_callback)

                    # Limit to 15 images max
                    if saved_count >= MAX_IMAGES_PER_SCRAPE:
                        break

                except Exception as e:
                    print(f"Failed to download image {img_url}: {e}")
                    continue

        finally:
            db.close()

        if saved_count > 0:
            if status_callback:
                status_callback("complete", {"message": f"Successfully scraped {saved_count} images.", "media_id": None})
                status_callback("status_update", "Completed")
        else:
            if status_callback:
                status_callback("log", "No suitable images found on page.")
                status_callback("complete", {"message": "No suitable images found.", "media_id": None})

    except Exception as e:
        print(f"Scraping failed: {e}")
        if status_callback:
            status_callback("log", f"Scraping failed: {e}")
            status_callback("complete", {"message": f"Scraping failed: {e}", "media_id": None})
