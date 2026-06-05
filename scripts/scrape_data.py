#!/usr/bin/env python3
"""
Global MaaS Dashboard — Data Scraper
Fetches latest model pricing, news, and market data from multiple sources,
then writes updated JSON files to data/ directory.

Usage:
    python scripts/scrape_data.py

GitHub Actions runs this daily via cron schedule.
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MaaS-Dashboard-Bot/1.0)"}

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------
def fetch_json(url: str, timeout: int = 30) -> dict | list | None:
    """Fetch JSON from a URL, return parsed object or None on failure."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"  [WARN] Failed to fetch {url}: {e}")
        return None


def save_json(filename: str, data):
    """Write data to a JSON file in the data/ directory."""
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  [OK] Saved {filename} ({len(data) if isinstance(data, list) else 'dict'})")


def load_existing(filename: str):
    """Load existing JSON file, return None if not found."""
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


# ---------------------------------------------------------------------------
# Scraper: Model Pricing
# ---------------------------------------------------------------------------
# Sources (add more as needed):
#   - OpenAI: https://openai.com/api/pricing/
#   - Anthropic: https://platform.claude.com/docs/en/about-claude/pricing
#   - Google: https://ai.google.dev/gemini-api/docs/pricing
#   - xAI: https://x.ai/api
#   - Mistral: https://mistral.ai/pricing/
#   - Aggregator: https://pricepertoken.com/pricing-page/provider/{provider}
#   - Aggregator: https://www.aipricing.guru/openai-pricing/
#
# NOTE: Most vendor pricing pages require JS rendering or return 403 to simple
# urllib requests. For production use, consider:
#   1. Using vendor API endpoints directly (if available)
#   2. Using a headless browser (Playwright/Selenium)
#   3. Maintaining a manual pricing CSV that this script reads
#   4. Using aggregator APIs that provide structured JSON

PRICE_SOURCES = {
    "openai": "https://www.aipricing.guru/openai-pricing/",
    "anthropic": "https://pecollective.com/tools/anthropic-api-pricing/",
    "google": "https://ai.google.dev/gemini-api/docs/pricing",
    "mistral": "https://pricepertoken.com/pricing-page/provider/mistral-ai",
    "xai": "https://mem0.ai/blog/xai-grok-api-pricing",
}


def scrape_pricing():
    """
    Attempt to fetch latest pricing from public sources.
    Falls back to existing data if scraping fails.
    Returns updated models list.
    """
    print("[1/4] Scraping model pricing data...")
    models = load_existing("models.json")
    if models is None:
        print("  [ERROR] No existing models.json found, cannot proceed")
        return None

    updated = 0

    # --- Google Gemini pricing (most reliable via WebFetch-style) ---
    google_data = fetch_json("https://generativelanguage.googleapis.com/v1/models")
    if google_data and "models" in google_data:
        # The Google API lists model names but not pricing.
        # Pricing must be scraped from the pricing page (JS-rendered).
        print("  [INFO] Google API returned model list, but pricing requires page scraping")

    # --- For now, update timestamp only ---
    # In production, replace with actual scraping logic or API calls
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"  [INFO] Pricing data timestamp: {today}")
    print(f"  [INFO] {updated} models updated (manual review recommended)")

    return models


# ---------------------------------------------------------------------------
# Scraper: News / Events
# ---------------------------------------------------------------------------
NEWS_SOURCES = [
    # Add RSS feeds or API endpoints here
    # Example: "https://techcrunch.com/category/artificial-intelligence/feed/",
    # Example: "https://36kr.com/api/newsflash",
]


def scrape_news():
    """
    Fetch latest MaaS-related news from RSS feeds and APIs.
    Appends new events to existing news.json.
    """
    print("[2/4] Scraping news events...")
    news = load_existing("news.json")
    if news is None:
        news = []

    new_items = []

    # --- Add RSS feed scrapers here ---
    # Example pattern:
    # for url in NEWS_SOURCES:
    #     feed = fetch_json(url)
    #     if feed:
    #         for item in feed["items"][:10]:
    #             new_items.append({
    #                 "date": item["published"][:10],
    #                 "title": item["title"],
    #                 "cat": "动态",
    #                 "impact": 3,
    #                 "summary": item["summary"][:200],
    #                 "source": "RSS"
    #             })

    if new_items:
        # Deduplicate by title
        existing_titles = {n["title"] for n in news}
        for item in new_items:
            if item["title"] not in existing_titles:
                news.insert(0, item)  # Prepend newest
                existing_titles.add(item["title"])
        print(f"  [OK] Added {len(new_items)} new news items")
    else:
        print(f"  [INFO] No new news fetched (add sources to NEWS_SOURCES)")

    return news


# ---------------------------------------------------------------------------
# Scraper: Market Data
# ---------------------------------------------------------------------------
def scrape_market():
    """
    Update market size data. Most market data comes from research reports
    (Gartner/IDC/Statista) and is updated infrequently.
    This function updates the last_refresh timestamp.
    """
    print("[3/4] Updating market data...")
    market = load_existing("market.json")
    if market is None:
        print("  [ERROR] No existing market.json found")
        return None

    # Update refresh timestamp
    market["last_refresh"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    print(f"  [OK] Market data refreshed: {market['last_refresh']}")
    return market


# ---------------------------------------------------------------------------
# Scraper: Industry-Vendor Matrix
# ---------------------------------------------------------------------------
def scrape_matrix():
    """
    The industry-vendor matrix is curated manually based on public case studies,
    bidding records, and industry reports. Auto-updating is not practical.
    This function just validates the existing matrix.
    """
    print("[4/4] Validating industry-vendor matrix...")
    matrix = load_existing("matrix.json")
    if matrix is None:
        print("  [ERROR] No existing matrix.json found")
        return None

    n_ind = len(matrix["industries"])
    n_ven = len(matrix["vendors"])
    print(f"  [OK] Matrix: {n_ind} industries × {n_ven} vendors")
    return matrix


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print(f"=== MaaS Dashboard Data Scraper ===")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print(f"Data dir: {DATA_DIR}")
    print()

    os.makedirs(DATA_DIR, exist_ok=True)

    models = scrape_pricing()
    news = scrape_news()
    market = scrape_market()
    matrix = scrape_matrix()

    # Save all updated data
    print()
    print("=== Saving results ===")
    if models:
        save_json("models.json", models)
    if news:
        save_json("news.json", news)
    if market:
        save_json("market.json", market)
    if matrix:
        save_json("matrix.json", matrix)

    print()
    print("Done! Files updated in data/")
    print("GitHub Actions will commit these changes automatically.")


if __name__ == "__main__":
    main()
