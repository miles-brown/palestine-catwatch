import requests
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
    if status_callback: status_callback("log", "Video download failed/not found. Attempting to scrape images...")
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Heuristic: Find 'large' images or images in main content
        # This is a naive implementation; specialized scrapers are better
        images = soup.find_all('img')
        
        saved_count = 0
        db = SessionLocal()
        
        try:
            # Create a protest placeholder if needed (reusing logic from ingest_video could be better refactored)
            if not protest_id:
                # Metadata extraction (simplified)
                title = soup.title.string if soup.title else "Scraped Article"
                new_protest = models.Protest(
                    name=f"Article: {title[:50]}",
                    date=datetime.utcnow(),
                    location="Unknown",
                    description=f"Scraped from {url}"
                )
                db.add(new_protest)
                db.commit()
                db.refresh(new_protest)
                protest_id = new_protest.id
                if status_callback: status_callback("log", f"Created protest record: {new_protest.name}")

            for img in images:
                src = img.get('src')
                if not src: continue
                
                # Resolve relative URLs
                img_url = urljoin(url, src)
                
                # Filter small icons/pixels (very basic)
                if 'icon' in img_url or 'logo' in img_url:
                    continue
                    
                # Download image
                try:
                    img_data = requests.get(img_url, timeout=5).content
                    if len(img_data) < 10000: # Skip images smaller than 10KB
                        continue
                        
                    ext = os.path.splitext(img_url)[1].split('?')[0]
                    if not ext or len(ext) > 5: ext = ".jpg"
                    
                    filename = f"scraped_{uuid.uuid4().hex}{ext}"
                    filepath = os.path.join(DOWNLOAD_DIR, filename)
                    
                    with open(filepath, "wb") as f:
                        f.write(img_data)
                        
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
                    if status_callback: status_callback("log", f"Scraped image: {filename}")
                    
                    # Trigger analysis immediately for each image
                    process_media(new_media.id, status_callback)
                    
                    if saved_count >= 5: # Limit to 5 images per article to avoid spam
                        break
                        
                except Exception as e:
                    print(f"Failed to download image {img_url}: {e}")
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
