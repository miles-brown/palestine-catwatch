import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
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
    Checks archive.today and Wayback Machine.
    Returns the archive URL if found, None otherwise.
    """
    import time

    # Try archive.today/archive.is first (usually has fresher content)
    archive_services = [
        f"https://archive.today/newest/{url}",
        f"https://archive.is/newest/{url}",
        f"https://archive.ph/newest/{url}",
    ]

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    })

    # Check archive.today variants
    for archive_url in archive_services:
        try:
            response = session.head(archive_url, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                # archive.today redirects to the actual archived page
                final_url = response.url
                if final_url != archive_url and 'archive' in final_url:
                    logging.info(f"Found archive at: {final_url}")
                    return final_url
        except Exception as e:
            logging.debug(f"Archive check failed for {archive_url}: {e}")
            continue

    # Try Wayback Machine
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

    return None


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

            # Process each potential image URL
            for img_url_raw in potential_urls:
                if not img_url_raw:
                    continue

                # Resolve relative URLs
                img_url = urljoin(url, img_url_raw)

                # Deduplicate
                if img_url in seen_urls:
                    continue
                seen_urls.add(img_url)

                # Filter small icons/pixels (very basic)
                if 'icon' in img_url.lower() or 'logo' in img_url.lower() or 'tracker' in img_url.lower():
                    continue

                # Download image
                try:
                    if status_callback:
                        status_callback("status_update", "Downloading")

                    img_data = scraper.get(img_url, timeout=5, verify=False).content

                    # Skip small files (likely icons/trackers)
                    if len(img_data) < 5000:  # 5KB minimum
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
