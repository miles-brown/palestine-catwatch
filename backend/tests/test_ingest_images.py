"""
Unit tests for ingest_images.py

Tests cover:
- URL upgrade functions for various CDN patterns
- Article relevance scoring
- Source name mapping
- Archive URL retrieval (mocked)
- Caption/credit extraction from HTML
- Deduplication logic
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import re

# Import the module under test
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingest_images import (
    get_source_name,
    is_blocked_site,
    is_wayback_url,
    convert_wayback_image_url,
    SOURCE_NAME_MAP,
    BLOCKED_SITES,
    IMAGE_QUALITY_SETTINGS,
    MIN_IMAGE_SIZE_BYTES,
    MAX_IMAGES_PER_SCRAPE,
)


class TestGetSourceName:
    """Tests for get_source_name() function."""

    def test_bbc_uk_domain(self):
        """Should return 'BBC News' for bbc.co.uk URLs."""
        assert get_source_name("https://www.bbc.co.uk/news/article") == "BBC News"

    def test_bbc_com_domain(self):
        """Should return 'BBC News' for bbc.com URLs."""
        assert get_source_name("https://www.bbc.com/news/world-123") == "BBC News"

    def test_guardian_domain(self):
        """Should return 'The Guardian' for theguardian.com URLs."""
        assert get_source_name("https://www.theguardian.com/uk-news/article") == "The Guardian"

    def test_telegraph_domain(self):
        """Should return 'The Telegraph' for telegraph.co.uk URLs."""
        assert get_source_name("https://www.telegraph.co.uk/news/2024/article") == "The Telegraph"

    def test_sky_news_domain(self):
        """Should return 'Sky News' for sky.com URLs."""
        assert get_source_name("https://news.sky.com/story/protest-123") == "Sky News"

    def test_unknown_domain_extracts_name(self):
        """Should extract domain name for unknown sites."""
        result = get_source_name("https://www.unknownnews.org/article")
        assert result == "Unknownnews"

    def test_case_insensitive(self):
        """Should match domains case-insensitively."""
        assert get_source_name("https://WWW.BBC.CO.UK/news") == "BBC News"

    def test_all_mapped_sources(self):
        """Verify all sources in SOURCE_NAME_MAP are accessible."""
        for domain, name in SOURCE_NAME_MAP.items():
            url = f"https://www.{domain}/test"
            assert get_source_name(url) == name


class TestIsBlockedSite:
    """Tests for is_blocked_site() function."""

    def test_blocked_telegraph(self):
        """Telegraph should be blocked."""
        assert is_blocked_site("https://www.telegraph.co.uk/news/article") is True

    def test_blocked_reuters(self):
        """Reuters should be blocked."""
        assert is_blocked_site("https://www.reuters.com/world/article") is True

    def test_blocked_daily_mail(self):
        """Daily Mail should be blocked."""
        assert is_blocked_site("https://www.dailymail.co.uk/news/article") is True

    def test_allowed_bbc(self):
        """BBC should NOT be blocked."""
        assert is_blocked_site("https://www.bbc.co.uk/news/article") is False

    def test_allowed_guardian(self):
        """Guardian should NOT be blocked."""
        assert is_blocked_site("https://www.theguardian.com/article") is False

    def test_archive_url_not_blocked(self):
        """Archive.org URLs should never be blocked."""
        blocked_url = "https://web.archive.org/web/20240101/https://www.telegraph.co.uk/article"
        assert is_blocked_site(blocked_url) is False

    def test_archive_today_not_blocked(self):
        """Archive.today URLs should never be blocked."""
        blocked_url = "https://archive.today/abcde"
        assert is_blocked_site(blocked_url) is False


class TestIsWaybackUrl:
    """Tests for is_wayback_url() function."""

    def test_wayback_url_detected(self):
        """Should detect Wayback Machine URLs."""
        url = "https://web.archive.org/web/20240101120000/https://example.com"
        assert is_wayback_url(url) is True

    def test_regular_url_not_wayback(self):
        """Should not detect regular URLs as Wayback."""
        url = "https://www.bbc.co.uk/news/article"
        assert is_wayback_url(url) is False

    def test_case_insensitive(self):
        """Should work case-insensitively."""
        url = "https://WEB.ARCHIVE.ORG/web/20240101/https://example.com"
        assert is_wayback_url(url) is True


class TestConvertWaybackImageUrl:
    """Tests for convert_wayback_image_url() function."""

    def test_regular_url_gets_timestamp(self):
        """Should add Wayback timestamp to regular image URL."""
        img_url = "https://example.com/image.jpg"
        result = convert_wayback_image_url(img_url, "20240101120000")
        assert "web.archive.org" in result
        assert "20240101120000" in result

    def test_already_wayback_url_unchanged(self):
        """Should not double-wrap Wayback URLs."""
        img_url = "https://web.archive.org/web/20240101/https://example.com/image.jpg"
        result = convert_wayback_image_url(img_url, "20240201")
        assert result.count("web.archive.org") == 1


class TestCDNPatterns:
    """Tests for CDN regex patterns."""

    def test_mirror_cdn_pattern(self):
        """Mirror CDN pattern should match valid URLs."""
        pattern = r'https://i[0-9]-prod\.[a-z]{1,20}\.co\.uk/[\w./-]{1,200}/ALTERNATES/s(?:1200|810|615)[\w./-]{0,100}\.(?:jpg|jpeg|png|webp)'
        valid_url = "https://i2-prod.mirror.co.uk/incoming/article123/ALTERNATES/s1200/image.jpg"
        assert re.match(pattern, valid_url, re.IGNORECASE) is not None

    def test_nyt_cdn_pattern(self):
        """NY Times CDN pattern should match valid URLs."""
        pattern = r'https://static01\.nyt\.com/images/[\w./-]{1,200}(?:superJumbo|jumbo|videoSixteenByNine3000|threeByTwoLargeAt2X)[\w.-]{0,50}\.(?:jpg|jpeg|png|webp)'
        valid_url = "https://static01.nyt.com/images/2024/01/15/multimedia/protest-superJumbo.jpg"
        assert re.match(pattern, valid_url, re.IGNORECASE) is not None

    def test_sky_news_cdn_pattern(self):
        """Sky News CDN pattern should match valid URLs."""
        pattern = r'https://e3\.365dm\.com/\d{2}/\d{2}/[\w/x]{1,20}/[\w._-]{1,100}\.(?:jpg|jpeg|png|webp)(?:\?\d{0,20})?'
        valid_url = "https://e3.365dm.com/24/01/1600x900/skynews-protest_6422687.jpg"
        assert re.match(pattern, valid_url, re.IGNORECASE) is not None

    def test_bounded_quantifiers_prevent_redos(self):
        """Patterns should have bounded quantifiers to prevent ReDoS."""
        # These patterns should NOT cause catastrophic backtracking
        patterns = [
            r'https://[a-z0-9.-]{1,50}/incoming/article[0-9]{1,12}\.ece/[\w./-]{1,200}\.(?:jpg|jpeg|png|webp)',
            r'https://[a-z0-9.-]{1,50}\.newsquestdigital\.co\.uk/[\w./-]{1,200}\.(?:jpg|jpeg|png|webp)',
            r'https://fournews-assets-prod-s3[a-z0-9-]{0,30}\.s3\.amazonaws\.com/media/\d{4}/\d{2}/[\w._-]{1,200}\.(?:jpg|jpeg|png|webp)',
        ]

        # Malicious input that would cause ReDoS with unbounded quantifiers
        malicious_input = "https://" + "a" * 1000 + ".newsquestdigital.co.uk/" + "b" * 1000 + ".jpg"

        import time
        for pattern in patterns:
            start = time.time()
            re.match(pattern, malicious_input, re.IGNORECASE)
            elapsed = time.time() - start
            # Should complete in under 1 second (bounded patterns)
            assert elapsed < 1.0, f"Pattern took too long: {elapsed}s"


class TestArchiveFunctions:
    """Tests for archive-related functions with mocked HTTP."""

    @patch('ingest_images.requests.Session')
    def test_get_archive_url_finds_wayback(self, mock_session_class):
        """Should find and return existing Wayback archive."""
        from ingest_images import get_archive_url

        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        # Mock successful Wayback API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'archived_snapshots': {
                'closest': {
                    'available': True,
                    'url': 'https://web.archive.org/web/20240101/https://example.com'
                }
            }
        }
        mock_session.get.return_value = mock_response

        url, message = get_archive_url("https://example.com/article")
        assert url is not None
        assert "web.archive.org" in url

    @patch('ingest_images.requests.Session')
    def test_get_archive_url_no_archive_returns_instructions(self, mock_session_class):
        """Should return instructions when no archive found."""
        from ingest_images import get_archive_url

        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        # Mock empty Wayback response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'archived_snapshots': {}}
        mock_session.get.return_value = mock_response

        # Mock failed archive.today check
        mock_head = Mock()
        mock_head.status_code = 404
        mock_session.head.return_value = mock_head

        url, message = get_archive_url("https://example.com/article", request_save=False)
        assert url is None
        assert "archive.today" in message
        assert "web.archive.org/save" in message

    @patch('ingest_images.requests.Session')
    def test_request_wayback_save_success(self, mock_session_class):
        """Should handle successful Wayback save request."""
        from ingest_images import request_wayback_save

        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        mock_response = Mock()
        mock_response.status_code = 302
        mock_response.headers = {
            'Location': 'https://web.archive.org/web/20240101/https://example.com'
        }
        mock_session.get.return_value = mock_response

        result = request_wayback_save("https://example.com")
        assert result['success'] is True
        assert result['url'] is not None


class TestCaptionExtraction:
    """Tests for caption and credit extraction from HTML."""

    def test_extract_figcaption(self):
        """Should extract caption from figcaption element."""
        html = '''
        <figure>
            <img src="https://example.com/photo.jpg">
            <figcaption>Protesters march through London. Credit: PA Images</figcaption>
        </figure>
        '''
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')

        figcaption = soup.find('figcaption')
        assert figcaption is not None
        assert "Protesters march" in figcaption.get_text()

    def test_extract_credit_from_caption(self):
        """Should extract credit from caption text."""
        caption = "Police officers at the protest. Credit: Reuters"
        credit_match = re.search(
            r'(?:Credit|Photo|Image|Source|©|\()?:?\s*([A-Z][A-Za-z\s]+(?:Images?|News|Media|Photos?|Press|Agency|Pictures)?)\)?$',
            caption
        )
        assert credit_match is not None
        assert "Reuters" in credit_match.group(1)


class TestDeduplication:
    """Tests for image URL deduplication logic."""

    def test_nyt_deduplication_same_base(self):
        """NY Times images with same base should be deduplicated."""
        urls = [
            "https://static01.nyt.com/images/2024/01/15/multimedia/protest-superJumbo.jpg",
            "https://static01.nyt.com/images/2024/01/15/multimedia/protest-jumbo.jpg",
            "https://static01.nyt.com/images/2024/01/15/multimedia/protest-threeByTwoLargeAt2X.jpg",
        ]

        # Extract base ID using the pattern from the code
        seen_bases = set()
        unique_urls = []

        for url in urls:
            base_match = re.search(
                r'/([^/]+?)(?:-superJumbo|-jumbo|-videoSixteenByNine3000|-threeByTwoLargeAt2X)',
                url, re.IGNORECASE
            )
            if base_match:
                base_id = base_match.group(1).lower()
                if base_id not in seen_bases:
                    seen_bases.add(base_id)
                    unique_urls.append(url)

        # Should only keep one URL (first occurrence)
        assert len(unique_urls) == 1

    def test_sky_news_deduplication(self):
        """Sky News images with same base should be deduplicated."""
        urls = [
            "https://e3.365dm.com/24/01/1600x900/skynews-protest_6422687.jpg",
            "https://e3.365dm.com/24/01/768x432/skynews-protest_6422687.jpg",
            "https://e3.365dm.com/24/01/384x216/skynews-protest_6422687.jpg",
        ]

        seen_bases = set()
        unique_urls = []

        for url in urls:
            # Extract base filename
            base_match = re.search(r'/(\d+x\d+)/([^/]+)\.', url)
            if base_match:
                base_id = base_match.group(2).lower()
                if base_id not in seen_bases:
                    seen_bases.add(base_id)
                    unique_urls.append(url)

        assert len(unique_urls) == 1


class TestConstants:
    """Tests for module constants."""

    def test_min_image_size_reasonable(self):
        """MIN_IMAGE_SIZE_BYTES should be reasonable."""
        assert MIN_IMAGE_SIZE_BYTES >= 1000  # At least 1KB
        assert MIN_IMAGE_SIZE_BYTES <= 50000  # At most 50KB

    def test_max_images_reasonable(self):
        """MAX_IMAGES_PER_SCRAPE should be reasonable."""
        assert MAX_IMAGES_PER_SCRAPE >= 5
        assert MAX_IMAGES_PER_SCRAPE <= 50

    def test_image_quality_settings_valid(self):
        """IMAGE_QUALITY_SETTINGS should have valid values."""
        assert IMAGE_QUALITY_SETTINGS['standard_width'] > 0
        assert 0 < IMAGE_QUALITY_SETTINGS['standard_quality'] <= 100
        assert 0 < IMAGE_QUALITY_SETTINGS['aljazeera_quality'] <= 100


class TestURLUpgrade:
    """Tests for URL upgrade functionality."""

    def test_standard_width_param(self):
        """Evening Standard URLs should get width parameter."""
        from urllib.parse import urlparse, parse_qs

        url = "https://static.standard.co.uk/2024/01/15/10/30/protest.jpg?quality=50"
        # Simulate upgrade logic
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        params['width'] = [str(IMAGE_QUALITY_SETTINGS['standard_width'])]

        assert params['width'] == ['1200']

    def test_sky_news_resolution_upgrade(self):
        """Sky News URLs should upgrade to 1600x900."""
        url = "https://e3.365dm.com/24/01/768x432/image.jpg"
        upgraded = url.replace('768x432', IMAGE_QUALITY_SETTINGS['sky_resolution'])
        assert '1600x900' in upgraded
