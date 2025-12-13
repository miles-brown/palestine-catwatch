"""
Article Summarizer using Claude API

Extracts protest details and generates concise summaries from news articles.
Uses Claude to identify:
- Protest/event name
- Date of the event
- Location
- Key details and context
- Condensed summary paragraph
"""

import os
import logging
from typing import Optional, Dict, Any
from anthropic import Anthropic

logger = logging.getLogger(__name__)

# Initialize Anthropic client
_client: Optional[Anthropic] = None


def get_client() -> Optional[Anthropic]:
    """Get or create Anthropic client."""
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("ANTHROPIC_API_KEY not set - article summarization disabled")
            return None
        _client = Anthropic(api_key=api_key)
    return _client


def summarize_article(
    article_text: str,
    article_title: str = "",
    source_name: str = "",
    max_text_length: int = 8000
) -> Dict[str, Any]:
    """
    Summarize a news article and extract protest/event details.

    Args:
        article_text: The full article text content
        article_title: Article headline
        source_name: Publisher name (e.g., "BBC News")
        max_text_length: Maximum characters to send to API

    Returns:
        Dict with:
        - event_name: Name of the protest/event
        - event_date: Date of the event (if found)
        - location: Location of the event
        - summary: 2-3 sentence summary
        - key_details: List of key points
        - police_presence: Description of police activity
        - success: Whether summarization succeeded
    """
    client = get_client()

    if not client:
        return {
            "success": False,
            "error": "Claude API not configured",
            "event_name": None,
            "event_date": None,
            "location": None,
            "summary": None,
            "key_details": [],
            "police_presence": None
        }

    # Truncate text if too long
    if len(article_text) > max_text_length:
        article_text = article_text[:max_text_length] + "..."

    prompt = f"""Analyze this news article and extract protest/event information.

Article Title: {article_title}
Source: {source_name}

Article Text:
{article_text}

Please extract and respond with ONLY a JSON object (no markdown, no explanation) with these fields:
{{
    "event_name": "Name of the protest, march, demonstration, or event (e.g., 'Pro-Palestine March', 'Ceasefire Now Rally')",
    "event_date": "Date of the event in format 'DD Month YYYY' or null if not found",
    "location": "Location where the event took place (e.g., 'Central London', 'Whitehall')",
    "summary": "A 2-3 sentence summary of the article focusing on the protest and any police interactions",
    "key_details": ["Key point 1", "Key point 2", "Key point 3"],
    "police_presence": "Description of police activity, arrests, or interactions mentioned (or null if none)",
    "estimated_attendance": "Number of protesters if mentioned (or null)"
}}

Respond with ONLY the JSON object, no other text."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        # Parse response
        response_text = response.content[0].text.strip()

        # Try to parse as JSON
        import json

        # Handle potential markdown code blocks
        if response_text.startswith("```"):
            # Extract JSON from code block
            lines = response_text.split("\n")
            json_lines = []
            in_json = False
            for line in lines:
                if line.startswith("```json"):
                    in_json = True
                    continue
                elif line.startswith("```"):
                    in_json = False
                    continue
                if in_json:
                    json_lines.append(line)
            response_text = "\n".join(json_lines)

        result = json.loads(response_text)
        result["success"] = True
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude response as JSON: {e}")
        return {
            "success": False,
            "error": f"JSON parse error: {e}",
            "event_name": None,
            "event_date": None,
            "location": None,
            "summary": None,
            "key_details": [],
            "police_presence": None
        }
    except Exception as e:
        logger.error(f"Article summarization failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "event_name": None,
            "event_date": None,
            "location": None,
            "summary": None,
            "key_details": [],
            "police_presence": None
        }


def extract_article_text(soup) -> str:
    """
    Extract clean article text from BeautifulSoup object.

    Args:
        soup: BeautifulSoup object of the page

    Returns:
        Cleaned article text
    """
    # Try common article containers
    article_selectors = [
        'article',
        '[role="main"]',
        '.article-body',
        '.story-body',
        '.article-content',
        '.post-content',
        '#article-body',
        '.entry-content',
        'main',
    ]

    article_element = None
    for selector in article_selectors:
        if selector.startswith('.') or selector.startswith('#'):
            article_element = soup.select_one(selector)
        elif selector.startswith('['):
            article_element = soup.select_one(selector)
        else:
            article_element = soup.find(selector)

        if article_element:
            break

    if not article_element:
        # Fallback to body
        article_element = soup.body

    if not article_element:
        return ""

    # Remove unwanted elements
    for unwanted in article_element.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'form']):
        unwanted.decompose()

    # Get text
    text = article_element.get_text(separator=' ', strip=True)

    # Clean up whitespace
    import re
    text = re.sub(r'\s+', ' ', text)

    return text
