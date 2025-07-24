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
    match = re.search(r"\$\d[\d,]*(?:\s*(?:to|-)\s*\$\d[\d,]*)?", text)
    return match.group(0).replace("Up to ", "").strip() if match else None

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


def infer_tags(text, tag_list):
    return [tag for tag in tag_list if tag.lower() in text.lower()]

# ---------- Scraper ----------

def scrape_bold_page(page=1):
    print(f"🔍 Scraping page {page}...")
    scholarships = []

    # Step 1: Request the listing page
    res = requests.get(f"{BROWSE_URL}?page={page}", headers={"User-Agent": "Mozilla/5.0"})
    if res.status_code != 200:
        print(f"❌ Failed to fetch page {page}: {res.status_code}")
        return []

    soup = BeautifulSoup(res.text, "html.parser")
    cards = soup.select("a[href^='/scholarships/']")

    seen = set()
    unique_links = []

    for tag in cards:
        href = tag.get("href")
        text = tag.get_text(strip=True).lower()

        if not href or href.count("/") != 3 or any(term in href.lower() for term in ["see-all", "groups", "access", "all-scholarship"]):
            continue

        if any(term in text for term in ["find college", "access exclusive", "see all", "search", "explore"]):
            continue

        full_url = BASE_URL + href
        if full_url not in seen:
            seen.add(full_url)
            unique_links.append(full_url)


    print(f"Found {len(unique_links)} scholarships on page {page}")

    # Step 3: Visit each detail page and extract real data
    for link in unique_links:
        try:
            sub_res = requests.get(link, headers={"User-Agent": "Mozilla/5.0"})
            sub_soup = BeautifulSoup(sub_res.text, "html.parser")

            # 🎯 Title (strictly required)
            title_tag = sub_soup.select_one("h1")
            title = title_tag.get_text(strip=True) if title_tag else None

            # ❌ Skip garbage pages based on title
            if title.lower().startswith("access ") or title.lower().startswith("see all") or title.lower().startswith("find"):
                print(f"🗑️ Skipped invalid title: {title} → {link}")
                continue

            # 📝 Description
            desc_tag = sub_soup.select_one("div[data-testid='scholarship-description']")
            if not desc_tag:
                desc_tag = sub_soup.find("p")
            description = desc_tag.get_text(strip=True) if desc_tag else "No description available"

            # 💰 Amount
            amount_tag = sub_soup.find(string=re.compile(r"\$\d[\d,]*"))
            amount = parse_amount(amount_tag if amount_tag else None)

            # 📅 Deadline
            page_text = sub_soup.get_text()
            deadline_line = next((line for line in page_text.splitlines() if "Deadline" in line), "")
            deadline = parse_deadline(deadline_line)

            # 🏷️ Inferred tags
            sectors = infer_tags(description, ["STEM", "AI", "Engineering", "Healthcare"])
            eligibility = infer_tags(description, ["BIPOC", "low-income", "first-gen", "women", "LGBTQ"])
            if not eligibility:
                eligibility = ["general"]

            # ✅ Construct grant object
            scholarships.append({
                "title": title,
                "description": description,
                "amount": amount,
                "deadline": deadline,
                "location_eligible": ["USA"],
                "target_group": ["students"],
                "sectors": sectors,
                "eligibility_criteria": eligibility,
                "source_url": link,
            })

            time.sleep(0.5)

        except Exception as e:
            print(f"❌ Error scraping {link}: {e}")
            continue

    return scholarships



# ---------- Supabase Upload ----------

def upload_to_supabase(data):
    for item in data:
        if not item["title"] or item["title"].lower().startswith("access exclusive"):
            continue
        if item["amount"] and "$" in item["amount"]:
            try:
                raw_amount = int(item["amount"].replace("$", "").replace(",", ""))
                if raw_amount < 100 or raw_amount > 100_000:
                    item["amount"] = None
            except:
                item["amount"] = None

        response = supabase.table("grants").upsert(item, on_conflict=["source_url"]).execute()
        if response.data:
            print(f"✅ Uploaded: {item['title']}")
        elif response.error:
            print(f"❌ Failed: {item['title']}")
            print(response.error.message)
        else:
            print(f"⚠️ Unknown issue with: {item['title']}")

# ---------- Run Script ----------

if __name__ == "__main__":
    all_data = []
    for i in range(1, 3):  # Change to more pages if needed
        all_data.extend(scrape_bold_page(i))
    upload_to_supabase(all_data)
