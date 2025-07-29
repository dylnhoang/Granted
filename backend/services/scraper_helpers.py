import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client
from dateutil import parser as dateparser
import os
import time
import re
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

BASE_URL = "https://bold.org"
BROWSE_URL = f"{BASE_URL}/scholarships/"

# ---------- Utilities ----------

def parse_amount(text):
    if not text:
        return None
    
    # Try multiple patterns for different amount formats
    patterns = [
        # Standard dollar amounts: $1,000, $1000, $1,000-$2,000
        r"\$\d[\d,]*(?:\s*(?:to|-)\s*\$\d[\d,]*)?",
        # Amounts with K/M suffixes: $10K, $1.5M, $10k
        r"\$\d+(?:\.\d+)?[KkMm]",
        # Amounts with "thousand", "million" words
        r"\$\d+(?:\s+thousand|\s+million)",
        # Amounts in parentheses or brackets
        r"\(\$\d[\d,]*(?:\s*(?:to|-)\s*\$\d[\d,]*)?\)",
        r"\[\$\d[\d,]*(?:\s*(?:to|-)\s*\$\d[\d,]*)?\]"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            amount = match.group(0).strip()
            # Clean up the amount
            amount = re.sub(r'[()\[\]]', '', amount)  # Remove brackets/parentheses
            amount = re.sub(r'\s+', ' ', amount)      # Normalize whitespace
            return amount
    
    return None

def parse_deadline(text):
    if not text:
        return None
    match = re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}", text)
    if match:
        try:
            return dateparser.parse(match.group(0)).date().isoformat()
        except:
            return None
    return None

def extract_description(soup):
    """
    Extracts a large block of relevant paragraph text from the page body,
    skipping navbars, sidebars, and login modals.
    """
    # Attempt to skip modal
    modal = soup.select_one("#lightbox-modal")  # Unigo modal
    if modal:
        modal.decompose()

    # Find the main content area with text
    content_blocks = soup.select("main, article, div, section")
    for block in content_blocks:
        ps = block.find_all("p")
        if len(ps) >= 2:
            text = " ".join(p.get_text(strip=True) for p in ps)
            if len(text) > 200:
                return text

    return "No description available (could not extract meaningful text)"



def infer_tags(text, tag_list):
    matches = []
    for tag in tag_list:
        # Create word-boundary regex for the tag, e.g. \bAI\b
        pattern = r"\b" + re.escape(tag) + r"\b"
        if re.search(pattern, text, re.IGNORECASE):
            matches.append(tag)
    return matches