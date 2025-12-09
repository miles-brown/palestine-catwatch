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
from datetime import datetime
from database import SessionLocal
import models
from process import process_media

# Disable SSL warnings for development
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Directory to store downloads
DOWNLOAD_DIR = "data/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

class SSLAdapter(HTTPAdapter):
    """Custom SSL adapter that disables certificate verification."""
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)

def create_scraper_session():
    """Create a requests session with SSL bypass and browser-like headers."""
    session = requests.Session()
    session.mount('https://', SSLAdapter())
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })
    return session

def scrape_images_from_url(url, protest_id=None, status_callback=None):
    """
    Scrapes images from a web page (news article, etc.) and processes them.
    """
    if status_callback:
        status_callback("status_update", "Connecting")

    # Create session with SSL bypass
    scraper = create_scraper_session()

    if status_callback:
        status_callback("log", "Attempting to scrape images from page...")

    try:
        if status_callback:
            status_callback("status_update", "Scraping")

        response = scraper.get(url, timeout=15, verify=False)
        response.raise_for_status()

        # Parse content
        soup = BeautifulSoup(response.content, 'html.parser')

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
                event_date = datetime.utcnow()
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
                        timestamp=datetime.utcnow(),
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
