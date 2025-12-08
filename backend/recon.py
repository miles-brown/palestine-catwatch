import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse

class ReconReport:
    def __init__(self, url):
        self.url = url
        self.category = "Unknown"
        self.title = None
        self.description = None
        self.image_count = 0
        self.has_video = False
        self.keywords_found = []
        self.score = 0
        self.recommendation = "SKIP"
        self.meta = {}

    def to_dict(self):
        return {
            "url": self.url,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "stats": {
                "images": self.image_count,
                "video": self.has_video
            },
            "keywords": self.keywords_found,
            "score": self.score,
            "recommendation": self.recommendation,
            "meta": self.meta
        }

class ReconAgent:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Weighted Keywords
        self.keywords = {
            "protest": 15, "demonstration": 15, "rally": 10, "march": 10,
            "police": 20, "officer": 15, "cop": 10, "arrest": 20, "clash": 15,
            "metropolitan": 5, "london": 5, "palestine": 10, "gaza": 5
        }

    def analyze(self, url):
        report = ReconReport(url)
        
        try:
            # 1. Determine Category from URL
            domain = urlparse(url).netloc.lower()
            if "youtube.com" in domain or "youtu.be" in domain:
                report.category = "Video Platform"
                report.has_video = True
            elif "twitter.com" in domain or "x.com" in domain or "instagram.com" in domain or "facebook.com" in domain:
                report.category = "Social Media"
            elif "bbc" in domain or "guardian" in domain or "mirror" in domain or "news" in domain or "daily" in domain:
                report.category = "News Article"
            else:
                report.category = "Web Page"

            # 2. Fetch Content (Lightweight)
            # Use cloudscraper logic via requests for now (simple)
            # In real system, might reuse the cloudscraper instance
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                report.score = 0
                report.recommendation = "ERROR"
                return report.to_dict()

            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 3. Extract Metadata
            report.title = soup.title.string if soup.title else ""
            og_title = soup.find("meta", property="og:title")
            if og_title: report.title = og_title.get("content")
            
            og_desc = soup.find("meta", property="og:description")
            if og_desc: report.description = og_desc.get("content")
            
            # 4. Count Assets
            imgs = soup.find_all('img')
            report.image_count = len([img for img in imgs if int(img.get('width', 100)) > 50]) # Simple filter
            
            if soup.find('video') or "video" in str(soup).lower():
                report.has_video = True

            # 5. Keyword Analysis (AI "Reading")
            text_content = (report.title + " " + (report.description or "")).lower()
            
            # Scan also the first 2000 chars of body text for depth
            body_text = soup.body.get_text()[:2000].lower() if soup.body else ""
            full_scan_text = text_content + " " + body_text
            
            total_score = 0
            found_words = set()
            
            for word, weight in self.keywords.items():
                if word in full_scan_text:
                    total_score += weight
                    found_words.add(word)
            
            report.keywords_found = list(found_words)
            
            # 6. Scoring Logic
            # Baseline for media presence
            if report.image_count > 3: total_score += 10
            if report.has_video: total_score += 20
            
            # Cap at 100
            report.score = min(100, total_score)
            
            # 7. Recommendation
            if report.score > 40:
                report.recommendation = "SCRAPE"
            elif report.score > 20:
                report.recommendation = "REVIEW"
            else:
                report.recommendation = "SKIP"
                
            # Context Guess
            # Simple heuristic for now
            if "london" in full_scan_text:
                report.meta["location"] = "London"
            
            # Extract date - simple regex for now 2024 or 2025
            date_match = re.search(r'202[3-5]', full_scan_text)
            if date_match:
                report.meta["year"] = date_match.group(0)

        except Exception as e:
            print(f"Recon failed: {e}")
            report.category = "Error"
            
        return report.to_dict()

# Pattern Singleton
agent = ReconAgent()

def analyze_url(url):
    return agent.analyze(url)
