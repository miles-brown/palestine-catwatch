import yt_dlp
import os
import re
from datetime import datetime, timezone
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
    from tqdm import tqdm
    
    # Progress bar state
    pbar = None
    last_socket_percent = -1
    
    def progress_hook(d):
        nonlocal pbar, last_socket_percent
        
        if d['status'] == 'downloading':
            # 1. Initialize TQDM if needed
            total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
            downloaded = d.get('downloaded_bytes', 0)
            
            if pbar is None and total_bytes > 0:
                pbar = tqdm(total=total_bytes, unit='B', unit_scale=True, unit_divisor=1024, desc="Downloading")
            
            # 2. Update TQDM (Terminal)
            if pbar:
                pbar.n = downloaded
                pbar.refresh()
            
            # 3. Update Frontend (Throttle to ~10%)
            if status_callback:
                # Parse percent string " 45.3%" -> 45.3
                try:
                    percent_str = d.get('_percent_str', '0%').strip().replace('%','')
                    current_percent = float(percent_str)
                    
                    # Update only if we crossed a 10% threshold or it's 100%
                    if current_percent >= 100 or (current_percent - last_socket_percent >= 10):
                        size_mb = total_bytes / (1024 * 1024)
                        status_callback("log", f"Downloading: {current_percent:.1f}% of {size_mb:.1f}MB")
                        last_socket_percent = current_percent
                        
                        if current_percent >= 100:
                            status_callback("status_update", "Extracting")
                except ValueError:
                    pass

        elif d['status'] == 'finished':
            if pbar:
                pbar.close()
            if status_callback:
                status_callback("log", "Download complete.")

    # Cookie file path (optional - export from browser for best results)
    cookie_file = os.path.join(os.path.dirname(__file__), 'cookies.txt')

    ydl_opts = {
        # Download highest quality video for frame extraction
        # Priority: best video+audio merged > best video-only > fallback to any best
        # bestvideo*+bestaudio/best gets highest res (1440p/4K) when available
        # The * allows VP9/AV1 codecs. Merges with best audio into mp4/mkv.
        'format': 'bestvideo*+bestaudio/best[ext=mp4]/best',
        'merge_output_format': 'mp4',  # Ensure output is mp4 for cv2 compatibility
        'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'progress_hooks': [progress_hook],

        # === BOT DETECTION BYPASS OPTIONS ===

        # 1. Player client rotation - try multiple clients if one fails
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android', 'web'],  # iOS client often works best
                'player_skip': ['webpage', 'configs'],  # Skip slow webpage parsing
            }
        },

        # 2. Browser-like headers
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Sec-Fetch-Mode': 'navigate',
        },

        # 3. Retry logic
        'retries': 5,
        'fragment_retries': 5,
        'file_access_retries': 3,

        # 4. Rate limiting - be polite to avoid blocks
        'sleep_interval': 1,
        'max_sleep_interval': 5,
        'sleep_interval_requests': 1,

        # 5. Age-gate bypass (for age-restricted videos)
        'age_limit': None,

        # 6. Force IPv4 (some hosts block IPv6)
        'source_address': '0.0.0.0',

        # 7. Socket timeout
        'socket_timeout': 30,

        # 8. Use cookies if available (most reliable method)
        **(({'cookiefile': cookie_file} if os.path.exists(cookie_file) else {})),

        # 9. Geo bypass
        'geo_bypass': True,
        'geo_bypass_country': 'GB',  # UK-based content
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
    date_obj = datetime.now(timezone.utc)
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
    video_domains = [
        # Major platforms
        "youtube.com", "youtu.be", "vimeo.com", "dailymotion.com",
        # Social media with video
        "twitter.com", "x.com", "instagram.com", "facebook.com", "tiktok.com",
        # Alternative platforms
        "rumble.com", "bitchute.com", "odysee.com",
        # Live streaming
        "twitch.tv"
    ]
    
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
            timestamp=datetime.now(timezone.utc),
            processed=False
        )
        db.add(new_media)
        db.commit()
        db.refresh(new_media)
        
        media_id = new_media.id
        if status_callback: status_callback("log", f"Media record created ID: {media_id}")
        if status_callback: status_callback("media_created", {"media_id": media_id})
        
    finally:
        db.close()
        
    # 4. Trigger Analysis
    # This runs the standard frame extraction, face detection, OCR, etc.
    print(f"Triggering analysis for Media {media_id}...")
    if status_callback: status_callback("log", "Starting AI Analysis...")
    process_media(media_id, status_callback)
    print(f"Workflow complete for {url}")
    # Ensure media_id is sent one last time for robustness
    if status_callback: status_callback("media_created", {"media_id": media_id})
    if status_callback: status_callback("complete", {"message": "Analysis Workflow Complete.", "media_id": media_id})
