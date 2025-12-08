import yt_dlp
import os
import re
from datetime import datetime
from database import SessionLocal
import models
from process import process_media
from ingest import ingest_media # Reuse logic if possible, or replicate for flexibility

# Directory to store downloads
DOWNLOAD_DIR = "data/downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def download_video(url, protest_id=None, status_callback=None):
    """
    Downloads video using yt-dlp.
    Returns: file_path, info_dict
    """
    def progress_hook(d):
        if d['status'] == 'downloading' and status_callback:
            percent = d.get('_percent_str', '').strip()
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            size_mb = total_bytes / (1024 * 1024)
            msg = f"Downloading: {percent} of {size_mb:.1f}MB"
            status_callback("log", msg)
            if '100%' in percent:
                status_callback("status_update", "Extracting")

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'progress_hooks': [progress_hook],
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        return filename, info

def extract_metadata(info):
    """
    Extracts City, Date, and Protest Name from video title/description.
    """
    title = info.get('title', '')
    description = info.get('description', '')
    upload_date_str = info.get('upload_date', '') # YYYYMMDD
    
    text_content = f"{title} {description}"
    
    # 1. Date
    date_obj = datetime.utcnow()
    if upload_date_str:
        try:
            date_obj = datetime.strptime(upload_date_str, '%Y%m%d')
        except ValueError:
            pass
            
    # 2. City (Simple Keyword Matching for Demo)
    cities = ["London", "Manchester", "Birmingham", "Leeds", "Glasgow", "Liverpool", "Bristol", "Cardiff"]
    found_city = "Unknown Location"
    for city in cities:
        if city.lower() in text_content.lower():
            found_city = city
            break
            
    # 3. Protest Name
    protest_name = f"Protest in {found_city}"
    
    return {
        "date": date_obj,
        "city": found_city,
        "name": protest_name,
        "description": description[:500] + "..." if len(description) > 500 else description
    }

def process_video_workflow(url, answers, user_provided_protest_id=None, status_callback=None):
    """
    Full workflow: Download -> Extract Metadata -> DB Record -> AI Analysis
    """
    print(f"Starting workflow for {url}")
    if status_callback: status_callback("log", f"Starting workflow for {url}")
    
    # 0. Smart Routing (Heuristic)
    # If the URL is likely a news article (text/images) and NOT a dedicated video site, capture content first.
    IS_VIDEO_SITE = False
    video_domains = ["youtube.com", "youtu.be", "vimeo.com", "dailymotion.com", "twitch.tv", "tiktok.com", "instagram.com", "facebook.com", "twitter.com", "x.com"]
    
    for domain in video_domains:
        if domain in url.lower():
            IS_VIDEO_SITE = True
            break
            
    # If it is NOT a known video site, it's likely a news article (e.g. dailymail, bbc news text)
    # Strategy: Try to scrape article content/images FIRST.
    # If we find a video embedded later, we can process that too (future work), but photos are priority for articles.
    if not IS_VIDEO_SITE:
        print(f"URL {url} identified as Article/Page. Routing to Image Scraper first.")
        if status_callback: status_callback("log", "URL identified as Article/Page. Priority: Scrape Images & Text.")
        
        try:
             from ingest_images import scrape_images_from_url
             scrape_images_from_url(url, user_provided_protest_id, status_callback)
             # Should we also try to find video? Maybe. For now, if scraper succeeds, we are good.
             return
        except Exception as e:
             print(f"Scraper failed: {e}. Falling back to Video Downloader just in case...")
    
    # ... Fallthrough to Video Logic if it IS a video site, OR if scraper failed ...
    
    # 1. Download
    try:
        if status_callback: status_callback("log", "Processing Video content...")
        file_path, info = download_video(url, status_callback=status_callback)
        if status_callback: status_callback("log", "Video download complete.")
    except Exception as e:
        # Only log error if we were sure it was a video site.
        # If it was an article and we fell back here, it implies it had no video either.
        print(f"Video process failed: {e}")
        
        if IS_VIDEO_SITE:
            if status_callback: status_callback("log", f"Error: Video download failed - {e}")
            # Try scraper as last resort even for video sites (maybe it's a page with a video that failed, but headers work)
            try:
                from ingest_images import scrape_images_from_url
                scrape_images_from_url(url, user_provided_protest_id, status_callback)
            except:
                pass
        else:
             if status_callback: status_callback("log", "No video found on page either.")
        
        return

    # 2. Metadata / Protest Association
    db = SessionLocal()
    try:
        protest_id = user_provided_protest_id
        
        # If no protest ID provided, try to find or create one based on metadata
        if not protest_id:
            metadata = extract_metadata(info)
            
            # Simple logic: Create a new protest record for this video
            # In production, we'd fuzzy match existing protests
            new_protest = models.Protest(
                name=metadata['name'],
                date=metadata['date'],
                location=metadata['city'],
                description=f"Auto-generated from video: {info.get('title')}"
            )
            db.add(new_protest)
            db.commit()
            db.refresh(new_protest)
            protest_id = new_protest.id
            print(f"Created new protest: {new_protest.name} (ID: {protest_id})")
            if status_callback: status_callback("log", f"Created new protest record: {new_protest.name}")

        # 3. Create Media Record
        # We store the LOCAL file path now, not the URL (since we downloaded it)
        # But we might want to keep the source URL in description or a separate field.
        # For now, let's abuse the Schema: Media.url = local path? 
        # Or should Media.url be the YouTube URL and we assume file is in downloads?
        # The AI `process_media` expects Media.url to be a file path if it's processing.
        # Let's use the local file path as the Media.url for processing purposes.
        
        # Note: If we want to display key metadata (like "Source: YouTube"), we can append to description?
        # Media model doesn't have description. 
        
        new_media = models.Media(
            url=file_path, # Local path for processing
            type='video',
            protest_id=protest_id,
            timestamp=datetime.utcnow(),
            processed=False
        )
        db.add(new_media)
        db.commit()
        db.refresh(new_media)
        
        media_id = new_media.id
        if status_callback: status_callback("log", f"Media record created ID: {media_id}")
        
    finally:
        db.close()
        
    # 4. Trigger Analysis
    # This runs the standard frame extraction, face detection, OCR, etc.
    print(f"Triggering analysis for Media {media_id}...")
    if status_callback: status_callback("log", "Starting AI Analysis...")
    process_media(media_id, status_callback)
    print(f"Workflow complete for {url}")
    if status_callback: status_callback("complete", "Analysis Workflow Complete.")
