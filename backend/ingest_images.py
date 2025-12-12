import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
from bs4 import BeautifulSoup
from urllib.parse import urljoin
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


def get_archive_url(url):
    """
    Try to get an archived version of a blocked URL.
    Checks Wayback Machine first (more reliable), then archive.today.
    Returns the archive URL if found, None otherwise.
    """
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    })

    # Try Wayback Machine first (more reliable for automated access)
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
                return wayback_url
    except Exception as e:
        logging.debug(f"Wayback Machine check failed: {e}")

    # archive.today variants often require CAPTCHA, try anyway
    archive_services = [
        f"https://archive.today/newest/{url}",
        f"https://archive.is/newest/{url}",
    ]

    for archive_url in archive_services:
        try:
            response = session.head(archive_url, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                final_url = response.url
                # Check we got redirected to an actual archive page (not CAPTCHA)
                if final_url != archive_url and '/wip/' not in final_url:
                    # Verify it's not a CAPTCHA page
                    check_resp = session.get(final_url, timeout=10)
                    if b'security check' not in check_resp.content.lower() and b'captcha' not in check_resp.content.lower():
                        logging.info(f"Found archive at: {final_url}")
                        return final_url
        except Exception as e:
            logging.debug(f"Archive check failed for {archive_url}: {e}")
            continue

    return None


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

        # Try to find an archived version
        archive_url = get_archive_url(url)

        if archive_url:
            if status_callback:
                status_callback("log", f"Found archived version! Using: {archive_url[:60]}...")
            url = archive_url
        else:
            # No archive found - give user options
            error_msg = (
                "This site blocks automated scraping and no archive was found. "
                "Options: 1) Archive the page at archive.today first, then submit the archive URL. "
                "2) Download images manually and upload directly. "
                "3) Try a different news source covering the same event."
            )
            if status_callback:
                status_callback("log", error_msg)
                status_callback("complete", {"message": error_msg, "media_id": None})
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

        # 3. Extract images from JSON data, data attributes, and inline scripts
        # Many modern sites embed image URLs in JSON or data attributes for lazy loading
        html_text = html_content.decode('utf-8', errors='ignore') if isinstance(html_content, bytes) else html_content

        # Extract article ID from URL to prioritize related images
        # Handles formats like: /article-12345678, /article12345678.ece, or /story-name-12345678
        article_id_match = re.search(r'(?:article-?|-)(\d{7,})(?:$|[/?#])', url)
        article_id = int(article_id_match.group(1)) if article_id_match else None

        # Pattern for common news site CDN image URLs (high quality versions)
        # Matches URLs like:
        # - https://i2-prod.mirror.co.uk/incoming/article123.ece/ALTERNATES/s1200/image.jpg
        # - https://cdn.images.express.co.uk/img/dynamic/1/1200x712/secondary/London-5674436.webp
        cdn_patterns = [
            # Mirror/Reach PLC sites
            r'https://i[0-9]-prod\.[a-z]+\.co\.uk/[^"\'\s>]+/ALTERNATES/s(?:1200|810|615)[^"\'\s>]*\.(?:jpg|jpeg|png|webp)',
            r'https://[a-z0-9.-]+/incoming/article[0-9]+\.ece/[^"\'\s>]+\.(?:jpg|jpeg|png|webp)',
            # Express CDN (high quality versions: 1200x, 940x, 674x)
            r'https://cdn\.images\.express\.co\.uk/img/dynamic/[^"\'\s>]+(?:1200|940|674)[^"\'\s>]*\.(?:jpg|jpeg|png|webp)',
            # Generic CloudFront CDN
            r'https://[a-z0-9.-]+\.cloudfront\.net/[^"\'\s>]+\.(?:jpg|jpeg|png|webp)',
        ]

        # Collect all matches, prioritizing images from the same article
        all_cdn_urls = []
        for pattern in cdn_patterns:
            matches = re.findall(pattern, html_text, re.IGNORECASE)
            all_cdn_urls.extend(matches)

        # Sort: prioritize images with article/image IDs that appear multiple times
        # or are in the "secondary" folder (main article images on Express)
        def article_relevance(img_url):
            img_url_lower = img_url.lower()

            # Express: "secondary" images are main article images
            if '/secondary/' in img_url_lower:
                return 0  # High priority

            # Mirror/Reach: Match article ID
            match = re.search(r'article(\d+)', img_url)
            if match and article_id:
                img_article_id = int(match.group(1))
                # Images from same article or nearby (within 10000) are likely related
                diff = abs(img_article_id - article_id)
                if diff < 10000:
                    return 0  # High priority
                elif diff < 100000:
                    return 1  # Medium priority

            return 2  # Low priority (unrelated articles)

        all_cdn_urls.sort(key=article_relevance)
        potential_urls.extend(all_cdn_urls)

        if status_callback and len(potential_urls) > 1:
            status_callback("log", f"Found {len(potential_urls)} potential images in page.")

        saved_count = 0
        seen_urls = set()
        db = SessionLocal()

        try:
            # Create a protest placeholder if needed
            if not protest_id:
                # Metadata extraction (Smart)
                # 1. Title
                og_title = soup.find('meta', property='og:title')
                title = og_title['content'] if og_title else (soup.title.string if soup.title else "Scraped Article")
                clean_title = title.strip() if title else "Scraped Article"

                # 2. Date
                pub_time = soup.find('meta', property='article:published_time') or \
                           soup.find('meta', {'name': 'date'}) or \
                           soup.find('meta', {'name': 'parsely-pub-date'})
                event_date = datetime.now(timezone.utc)
                if pub_time and pub_time.get('content'):
                    try:
                        # Handle ISO formats roughly
                        dt_str = pub_time['content'].split('T')[0]
                        event_date = datetime.strptime(dt_str, "%Y-%m-%d")
                    except:
                        pass

                # 3. Location (Naive Heuristic via Title/Desc)
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
                    if len(img_data) < 5000:  # 5KB minimum
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

                    # Create Media Record
                    new_media = models.Media(
                        url=filepath,
                        type='image',
                        protest_id=protest_id,
                        timestamp=datetime.now(timezone.utc),
                        processed=False
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
                    if saved_count >= 15:
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
