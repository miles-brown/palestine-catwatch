import requests
import cloudscraper
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os
import uuid
import logging
from datetime import datetime
from database import SessionLocal
import models
from process import process_media

# Directory to store downloads
DOWNLOAD_DIR = "data/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def scrape_images_from_url(url, protest_id=None, status_callback=None):
    """
    Fallback: If video fails, try to scrape images.
    """
    # Cloudscraper handles User-Agent and TLS fingerprinting automatically
    scraper = cloudscraper.create_scraper()
    
    if status_callback: status_callback("log", "Video download failed/not found. Attempting to scrape images...")
    
    try:
        response = scraper.get(url, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract meaningful text for description
        article_text = ""
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = p.get_text().strip()
            if len(text) > 50: # Filter short snippets
                article_text += text + "\n\n"
        
        # Truncate for DB
        description_text = f"Scraped from {url}\n\n{article_text[:1000]}"
        if len(article_text) > 1000: description_text += "..."
        
        # 1. Open Graph Image (Highest Quality usually)
        og_image = soup.find('meta', property='og:image')
        potential_urls = []
        if og_image and og_image.get('content'):
            potential_urls.append(og_image['content'])
            if status_callback: status_callback("log", "Found Article Main Image (OpenGraph).")

        # 2. Main Content Images (handling lazy loading)
        images = soup.find_all('img')
        for img in images:
            # Check common lazy loading attributes in order of preference
            src = img.get('data-src') or img.get('data-original') or img.get('data-lazy-src') or img.get('src')
            
            # Handle srcset - parse and get the largest (simplified: get last url)
            srcset = img.get('srcset')
            if srcset and not src:
                # format: url 100w, url 200w. Split by comma, extract url.
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
                clean_title = title.strip()
                
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
                
                new_protest = models.Protest(
                    name=f"{clean_title[:80]}", # Cleaner name
                    date=event_date,
                    location=loc,
                    description=description_text
                )
                db.add(new_protest)
                db.commit()
                db.refresh(new_protest)
                protest_id = new_protest.id
                if status_callback: status_callback("log", f"Created protest record from article: {clean_title}")

            for img_url_raw in potential_urls:
                if not img_url_raw: continue
                
                # Resolve relative URLs
                img_url = urljoin(url, img_url_raw)
                
                # Deduplicate
                if img_url in seen_urls: continue
                seen_urls.add(img_url)
                
                # Filter small icons/pixels (very basic)
                if 'icon' in img_url.lower() or 'logo' in img_url.lower() or 'tracker' in img_url.lower():
                    continue
                    
                # Download image
                try:
                    img_data = scraper.get(img_url, timeout=5).content
                    if len(img_data) < 5000: # Lowered to 5KB to catch more images
                        continue
                        
                    ext = os.path.splitext(img_url)[1].split('?')[0]
                    if not ext or len(ext) > 5: ext = ".jpg"
                    
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
                    process_media(new_media.id, status_callback)
                    
                    if saved_count >= 15: # Increased limit since we finding better images
                        break
                        
                except Exception as e:
                    continue

                    
        finally:
            db.close()
            
        if saved_count > 0:
            if status_callback: status_callback("complete", f"Successfully scraped {saved_count} images.")
        else:
            if status_callback: status_callback("log", "No suitable images found on page.")
            
    except Exception as e:
        print(f"Scraping failed: {e}")
        if status_callback: status_callback("log", f"Scraping failed: {e}")
