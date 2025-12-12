"""
Enhanced URL Reconnaissance System

Analyzes URLs to determine page type, content types, and recommended extraction tools.
Supports video platforms, social media, news articles, galleries, and more.
"""
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, parse_qs
from datetime import datetime


# =============================================================================
# PAGE TYPE CONFIGURATION
# =============================================================================

PAGE_TYPE_DOMAINS = {
    "VIDEO_PLATFORM": [
        "youtube.com", "youtu.be", "vimeo.com", "rumble.com",
        "dailymotion.com", "bitchute.com", "odysee.com"
    ],
    "SOCIAL_MEDIA": [
        "twitter.com", "x.com", "instagram.com", "facebook.com",
        "tiktok.com", "threads.net"
    ],
    "NEWS_ARTICLE": [
        "bbc.co.uk", "bbc.com", "theguardian.com", "mirror.co.uk",
        "dailymail.co.uk", "independent.co.uk", "telegraph.co.uk",
        "sky.com", "itv.com", "channel4.com", "standard.co.uk",
        "metro.co.uk", "express.co.uk", "manchestereveningnews.co.uk",
        "liverpoolecho.co.uk", "walesonline.co.uk", "scotsman.com",
        "heraldscotland.com", "middleeasteye.net", "aljazeera.com"
    ],
    "PHOTO_GALLERY": [
        "flickr.com", "gettyimages.com", "shutterstock.com",
        "alamy.com", "rexfeatures.com", "paimages.co.uk"
    ],
    "FORUM": [
        "reddit.com", "mumsnet.com", "pistonheads.com"
    ],
    "BLOG": [
        "medium.com", "wordpress.com", "substack.com", "blogger.com"
    ],
    "CAMPAIGN_SITE": [
        "palestinecampaign.org", "psc.org.uk", "stopthewar.org.uk",
        "waronwant.org", "amnesty.org.uk"
    ]
}

# UK cities for location detection
UK_CITIES = [
    "london", "manchester", "birmingham", "leeds", "glasgow", "liverpool",
    "bristol", "sheffield", "edinburgh", "cardiff", "belfast", "newcastle",
    "nottingham", "leicester", "brighton", "oxford", "cambridge", "york",
    "coventry", "bradford", "hull", "plymouth", "portsmouth", "bournemouth"
]

# Weighted keywords for relevance scoring
KEYWORDS = {
    # Protest-related
    "protest": 15, "demonstration": 15, "rally": 12, "march": 12,
    "vigil": 10, "encampment": 12, "occupation": 10, "blockade": 10,
    # Police-related
    "police": 20, "officer": 15, "met police": 18, "metropolitan": 12,
    "arrest": 20, "detained": 15, "clash": 15, "kettling": 18,
    "tsg": 15, "riot": 12, "baton": 12, "shield": 10,
    # Palestine-related
    "palestine": 15, "gaza": 12, "ceasefire": 10, "free palestine": 15,
    "israel": 8, "solidarity": 8,
    # Location
    "london": 8, "westminster": 10, "whitehall": 10, "downing": 10,
    "embankment": 8, "trafalgar": 8, "parliament": 10
}


class ReconReport:
    """Structured report from URL analysis."""

    def __init__(self, url):
        self.url = url
        self.page_type = "UNKNOWN"
        self.page_type_detail = None  # e.g., "NEWS_ARTICLE_WITH_VIDEO"
        self.title = None
        self.description = None

        # Content detection
        self.detected_content = {
            "has_video": False,
            "has_images": False,
            "image_count": 0,
            "has_article_text": False,
            "has_embedded_video": False,
        }

        # Recommended extraction tools
        self.extraction_tools = []

        # Protest context
        self.protest_context = {
            "detected_date": None,
            "detected_location": None,
            "detected_city": None,
            "confidence": 0.0
        }

        # Legacy fields for compatibility
        self.keywords_found = []
        self.score = 0
        self.recommendation = "SKIP"
        self.meta = {}

    def to_dict(self):
        return {
            "url": self.url,
            "page_type": self.page_type,
            "page_type_detail": self.page_type_detail,
            "title": self.title,
            "description": self.description,
            "detected_content": self.detected_content,
            "extraction_tools": self.extraction_tools,
            "protest_context": self.protest_context,
            # Legacy fields
            "category": self.page_type.replace("_", " ").title(),
            "stats": {
                "images": self.detected_content["image_count"],
                "video": self.detected_content["has_video"]
            },
            "keywords": self.keywords_found,
            "score": self.score,
            "recommendation": self.recommendation,
            "meta": self.meta
        }


class ReconAgent:
    """Intelligent URL analysis agent."""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-GB,en;q=0.9',
        }

    def _get_domain(self, url):
        """Extract clean domain from URL."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
        return domain

    def _detect_page_type(self, url, domain):
        """Determine page type from URL patterns."""
        path = urlparse(url).path.lower()

        # Check each category
        for page_type, domains in PAGE_TYPE_DOMAINS.items():
            for d in domains:
                if d in domain:
                    # Refine social media type based on URL path
                    if page_type == "SOCIAL_MEDIA":
                        if "/video" in path or "/reel" in path or "/watch" in path:
                            return "SOCIAL_MEDIA_VIDEO"
                        elif "/photo" in path or "/media" in path:
                            return "SOCIAL_MEDIA_IMAGE"
                        elif "/status" in path or "/posts" in path:
                            return "SOCIAL_MEDIA_POST"
                    return page_type

        return "WEB_PAGE"

    def _detect_embedded_video(self, soup):
        """Check for embedded video content."""
        # Direct video tags
        if soup.find('video'):
            return True

        # YouTube/Vimeo embeds
        iframes = soup.find_all('iframe')
        for iframe in iframes:
            src = iframe.get('src', '')
            if any(v in src for v in ['youtube', 'vimeo', 'dailymotion', 'rumble']):
                return True

        # OpenGraph video
        og_video = soup.find("meta", property="og:video")
        if og_video:
            return True

        # Twitter player
        twitter_player = soup.find("meta", attrs={"name": "twitter:player"})
        if twitter_player:
            return True

        return False

    def _count_quality_images(self, soup):
        """Count images likely to be content (not icons/logos)."""
        imgs = soup.find_all('img')
        quality_count = 0

        for img in imgs:
            # Check various size indicators
            width = img.get('width', '')
            height = img.get('height', '')
            src = img.get('src', '') or img.get('data-src', '')

            # Skip likely icons/logos
            if any(x in src.lower() for x in ['icon', 'logo', 'avatar', 'emoji', 'badge', 'sprite']):
                continue

            # Check dimensions if available
            try:
                w = int(width) if width else 0
                h = int(height) if height else 0
                if w > 100 or h > 100:
                    quality_count += 1
                    continue
            except (ValueError, TypeError):
                pass

            # Check for lazy-loaded images (usually content)
            if img.get('data-src') or img.get('data-lazy-src'):
                quality_count += 1
                continue

            # Check srcset (responsive images are usually content)
            if img.get('srcset'):
                quality_count += 1
                continue

            # Default: count if src looks like content
            if src and len(src) > 20 and not src.startswith('data:'):
                quality_count += 1

        return quality_count

    def _extract_date(self, soup, text_content):
        """Extract publication/event date from page."""
        # Try structured data first
        time_tag = soup.find('time')
        if time_tag:
            datetime_attr = time_tag.get('datetime')
            if datetime_attr:
                return datetime_attr[:10]  # YYYY-MM-DD

        # OpenGraph date
        og_date = soup.find("meta", property="article:published_time")
        if og_date:
            return og_date.get("content", "")[:10]

        # Schema.org datePublished
        script_tags = soup.find_all('script', type='application/ld+json')
        for script in script_tags:
            try:
                import json
                data = json.loads(script.string)
                if isinstance(data, dict):
                    date = data.get('datePublished') or data.get('uploadDate')
                    if date:
                        return date[:10]
            except Exception:
                pass

        # Regex patterns for dates
        patterns = [
            r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+202[3-5]',
            r'202[3-5]-\d{2}-\d{2}',
            r'\d{1,2}/\d{1,2}/202[3-5]',
        ]

        for pattern in patterns:
            match = re.search(pattern, text_content, re.IGNORECASE)
            if match:
                return match.group(0)

        return None

    def _detect_city(self, text_content):
        """Detect UK city from content."""
        text_lower = text_content.lower()

        for city in UK_CITIES:
            if city in text_lower:
                return city.title()

        return None

    def _calculate_score(self, report, text_content):
        """Calculate relevance score based on keywords and content."""
        total_score = 0
        found_words = set()
        text_lower = text_content.lower()

        for keyword, weight in KEYWORDS.items():
            if keyword in text_lower:
                total_score += weight
                found_words.add(keyword)

        # Bonus for media presence
        if report.detected_content["image_count"] > 3:
            total_score += 10
        if report.detected_content["has_video"]:
            total_score += 20
        if report.detected_content["has_embedded_video"]:
            total_score += 15

        report.keywords_found = list(found_words)
        report.score = min(100, total_score)

        # Determine recommendation
        if report.score > 40:
            report.recommendation = "SCRAPE"
        elif report.score > 20:
            report.recommendation = "REVIEW"
        else:
            report.recommendation = "SKIP"

    def _determine_extraction_tools(self, report):
        """Determine which extraction tools should be used."""
        tools = []

        if report.page_type in ["VIDEO_PLATFORM", "SOCIAL_MEDIA_VIDEO"]:
            tools.append("video_downloader")

        if report.detected_content["has_embedded_video"]:
            tools.append("video_downloader")

        if report.detected_content["has_images"] or report.detected_content["image_count"] > 0:
            tools.append("image_scraper")

        if report.page_type in ["NEWS_ARTICLE", "BLOG"] or report.detected_content["has_article_text"]:
            tools.append("article_parser")

        if report.page_type == "PHOTO_GALLERY":
            tools.append("gallery_scraper")

        # Deduplicate and set
        report.extraction_tools = list(set(tools))

    def analyze(self, url):
        """Perform comprehensive URL analysis."""
        report = ReconReport(url)

        try:
            domain = self._get_domain(url)

            # 1. Determine base page type
            report.page_type = self._detect_page_type(url, domain)

            # Mark video platforms
            if report.page_type == "VIDEO_PLATFORM":
                report.detected_content["has_video"] = True

            # 2. Fetch page content
            response = requests.get(url, headers=self.headers, timeout=15)
            if response.status_code != 200:
                report.recommendation = "ERROR"
                report.meta["error"] = f"HTTP {response.status_code}"
                return report.to_dict()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 3. Extract metadata
            report.title = ""
            if soup.title:
                report.title = soup.title.string or ""

            og_title = soup.find("meta", property="og:title")
            if og_title and og_title.get("content"):
                report.title = og_title.get("content")

            og_desc = soup.find("meta", property="og:description")
            if og_desc:
                report.description = og_desc.get("content")

            # 4. Detect content types
            report.detected_content["has_embedded_video"] = self._detect_embedded_video(soup)
            report.detected_content["has_video"] = (
                report.detected_content["has_video"] or
                report.detected_content["has_embedded_video"]
            )

            image_count = self._count_quality_images(soup)
            report.detected_content["image_count"] = image_count
            report.detected_content["has_images"] = image_count > 0

            # Check for article text
            article = soup.find('article') or soup.find('main')
            if article:
                text_length = len(article.get_text(strip=True))
                report.detected_content["has_article_text"] = text_length > 500

            # 5. Build detailed page type
            details = []
            if report.detected_content["has_video"]:
                details.append("VIDEO")
            if report.detected_content["has_images"]:
                details.append("IMAGES")
            if report.detected_content["has_article_text"]:
                details.append("ARTICLE")

            if details:
                report.page_type_detail = f"{report.page_type}_WITH_{'_'.join(details)}"
            else:
                report.page_type_detail = report.page_type

            # 6. Extract protest context
            text_content = (
                (report.title or "") + " " +
                (report.description or "") + " " +
                (soup.body.get_text()[:3000] if soup.body else "")
            )

            report.protest_context["detected_date"] = self._extract_date(soup, text_content)
            report.protest_context["detected_city"] = self._detect_city(text_content)

            if report.protest_context["detected_city"]:
                report.protest_context["detected_location"] = f"{report.protest_context['detected_city']}, UK"
                report.meta["location"] = report.protest_context["detected_city"]

            if report.protest_context["detected_date"]:
                report.meta["date"] = report.protest_context["detected_date"]

            # 7. Calculate relevance score
            self._calculate_score(report, text_content)

            # 8. Determine extraction tools
            self._determine_extraction_tools(report)

            # Calculate context confidence
            confidence = 0.0
            if report.protest_context["detected_date"]:
                confidence += 0.3
            if report.protest_context["detected_city"]:
                confidence += 0.3
            if len(report.keywords_found) >= 3:
                confidence += 0.4
            report.protest_context["confidence"] = min(1.0, confidence)

        except requests.exceptions.Timeout:
            report.recommendation = "ERROR"
            report.meta["error"] = "Request timeout"
        except requests.exceptions.RequestException as e:
            report.recommendation = "ERROR"
            report.meta["error"] = str(e)
        except Exception as e:
            print(f"Recon failed: {e}")
            report.recommendation = "ERROR"
            report.meta["error"] = str(e)

        return report.to_dict()


# Singleton instance
agent = ReconAgent()


def analyze_url(url):
    """Analyze a URL and return a structured report."""
    return agent.analyze(url)
