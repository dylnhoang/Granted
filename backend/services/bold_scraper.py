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

def extract_description(soup):
    # 1. Primary method: exact test ID
    desc_div = soup.select_one("div[data-testid='scholarship-description']")
    if desc_div:
        paragraphs = desc_div.find_all("p")
        if paragraphs:
            return "\n\n".join(p.get_text(strip=True) for p in paragraphs)
        return desc_div.get_text(strip=True)

    # 2. Fallback: generic description class
    desc_div = soup.find("div", class_=lambda c: c and "description" in c)
    if desc_div:
        paragraphs = desc_div.find_all("p")
        if paragraphs:
            return "\n\n".join(p.get_text(strip=True) for p in paragraphs)
        return desc_div.get_text(strip=True)

    # 3. Last resort: first 2–3 <p> tags
    fallback_paragraphs = soup.find_all("p")
    if fallback_paragraphs:
        return "\n\n".join(p.get_text(strip=True) for p in fallback_paragraphs[:3])

    return "No description available"



def infer_tags(text, tag_list):
    matches = []
    text_lower = text.lower()
    
    # More specific sector matching with context requirements
    sector_mappings = {
        "STEM": [
            r'\bstem\s*(?:major|degree|field|program|student)\b',
            r'\bscience\s*(?:major|degree|field|program|student)\b',
            r'\btechnology\s*(?:major|degree|field|program|student)\b',
            r'\bengineering\s*(?:major|degree|field|program|student)\b',
            r'\bmathematics\s*(?:major|degree|field|program|student)\b'
        ],
        "AI": [
            r'\bai\s*(?:major|degree|field|program|student)\b',
            r'\bartificial\s*intelligence\s*(?:major|degree|field|program|student)\b',
            r'\bmachine\s*learning\s*(?:major|degree|field|program|student)\b',
            r'\bdeep\s*learning\s*(?:major|degree|field|program|student)\b'
        ],
        "Engineering": [
            r'\bengineering\s*(?:major|degree|field|program|student)\b',
            r'\bmechanical\s*engineering\b',
            r'\belectrical\s*engineering\b',
            r'\bcivil\s*engineering\b',
            r'\bchemical\s*engineering\b',
            r'\bbiomedical\s*engineering\b'
        ],
        "Healthcare": [
            r'\bhealthcare\s*(?:major|degree|field|program|student)\b',
            r'\bhealth\s*care\s*(?:major|degree|field|program|student)\b',
            r'\bmedical\s*(?:major|degree|field|program|student)\b',
            r'\bmedicine\s*(?:major|degree|field|program|student)\b',
            r'\bnursing\s*(?:major|degree|field|program|student)\b',
            r'\bpharmacy\s*(?:major|degree|field|program|student)\b',
            r'\bpublic\s*health\s*(?:major|degree|field|program|student)\b'
        ],
        "Computer Science": [
            r'\bcomputer\s*science\s*(?:major|degree|field|program|student)\b',
            r'\bprogramming\s*(?:major|degree|field|program|student)\b',
            r'\bsoftware\s*(?:major|degree|field|program|student)\b',
            r'\bcoding\s*(?:major|degree|field|program|student)\b',
            r'\bweb\s*development\s*(?:major|degree|field|program|student)\b'
        ],
        "Technology": [
            r'\btechnology\s*(?:major|degree|field|program|student)\b',
            r'\btech\s*(?:major|degree|field|program|student)\b',
            r'\bdigital\s*(?:major|degree|field|program|student)\b',
            r'\binformation\s*technology\s*(?:major|degree|field|program|student)\b',
            r'\bit\s*(?:major|degree|field|program|student)\b'
        ],
        "Mathematics": [
            r'\bmathematics\s*(?:major|degree|field|program|student)\b',
            r'\bmath\s*(?:major|degree|field|program|student)\b',
            r'\bstatistics\s*(?:major|degree|field|program|student)\b',
            r'\bcalculus\s*(?:major|degree|field|program|student)\b',
            r'\balgebra\s*(?:major|degree|field|program|student)\b'
        ],
        "Physics": [
            r'\bphysics\s*(?:major|degree|field|program|student)\b',
            r'\bphysical\s*science\s*(?:major|degree|field|program|student)\b',
            r'\bquantum\s*(?:major|degree|field|program|student)\b',
            r'\bmechanics\s*(?:major|degree|field|program|student)\b'
        ],
        "Chemistry": [
            r'\bchemistry\s*(?:major|degree|field|program|student)\b',
            r'\bchemical\s*(?:major|degree|field|program|student)\b',
            r'\bbiochemistry\s*(?:major|degree|field|program|student)\b',
            r'\borganic\s*chemistry\s*(?:major|degree|field|program|student)\b'
        ],
        "Biology": [
            r'\bbiology\s*(?:major|degree|field|program|student)\b',
            r'\bbiotechnology\s*(?:major|degree|field|program|student)\b',
            r'\bmicrobiology\s*(?:major|degree|field|program|student)\b',
            r'\bgenetics\s*(?:major|degree|field|program|student)\b'
        ],
        "Medicine": [
            r'\bmedicine\s*(?:major|degree|field|program|student)\b',
            r'\bmedical\s*school\s*(?:major|degree|field|program|student)\b',
            r'\bpre\s*med\s*(?:major|degree|field|program|student)\b',
            r'\bphysician\s*(?:major|degree|field|program|student)\b'
        ],
        "Nursing": [
            r'\bnursing\s*(?:major|degree|field|program|student)\b',
            r'\bnurse\s*(?:major|degree|field|program|student)\b',
            r'\bregistered\s*nurse\s*(?:major|degree|field|program|student)\b',
            r'\brn\s*(?:major|degree|field|program|student)\b'
        ],
        "Psychology": [
            r'\bpsychology\s*(?:major|degree|field|program|student)\b',
            r'\bpsychologist\s*(?:major|degree|field|program|student)\b',
            r'\bmental\s*health\s*(?:major|degree|field|program|student)\b',
            r'\bcounseling\s*(?:major|degree|field|program|student)\b'
        ],
        "Business": [
            r'\bbusiness\s*(?:major|degree|field|program|student)\b',
            r'\bentrepreneurship\s*(?:major|degree|field|program|student)\b',
            r'\bmanagement\s*(?:major|degree|field|program|student)\b',
            r'\bmarketing\s*(?:major|degree|field|program|student)\b'
        ],
        "Finance": [
            r'\bfinance\s*(?:major|degree|field|program|student)\b',
            r'\bfinancial\s*(?:major|degree|field|program|student)\b',
            r'\baccounting\s*(?:major|degree|field|program|student)\b',
            r'\bbanking\s*(?:major|degree|field|program|student)\b'
        ],
        "Economics": [
            r'\beconomics\s*(?:major|degree|field|program|student)\b',
            r'\beconomic\s*(?:major|degree|field|program|student)\b',
            r'\bmacroeconomics\s*(?:major|degree|field|program|student)\b',
            r'\bmicroeconomics\s*(?:major|degree|field|program|student)\b'
        ],
        "Education": [
            r'\beducation\s*(?:major|degree|field|program|student)\b',
            r'\bteaching\s*(?:major|degree|field|program|student)\b',
            r'\bteacher\s*(?:major|degree|field|program|student)\b',
            r'\bpedagogy\s*(?:major|degree|field|program|student)\b',
            r'\bcurriculum\s*(?:major|degree|field|program|student)\b'
        ],
        "Law": [
            r'\blaw\s*(?:major|degree|field|program|student)\b',
            r'\blegal\s*(?:major|degree|field|program|student)\b',
            r'\battorney\s*(?:major|degree|field|program|student)\b',
            r'\blawyer\s*(?:major|degree|field|program|student)\b',
            r'\bjurisprudence\s*(?:major|degree|field|program|student)\b'
        ],
        "Journalism": [
            r'\bjournalism\s*(?:major|degree|field|program|student)\b',
            r'\bjournalist\s*(?:major|degree|field|program|student)\b',
            r'\bmedia\s*(?:major|degree|field|program|student)\b',
            r'\bcommunications\s*(?:major|degree|field|program|student)\b',
            r'\breporting\s*(?:major|degree|field|program|student)\b'
        ],
        "Arts": [
            r'\barts\s*(?:major|degree|field|program|student)\b',
            r'\bart\s*(?:major|degree|field|program|student)\b',
            r'\bcreative\s*(?:major|degree|field|program|student)\b',
            r'\bdesign\s*(?:major|degree|field|program|student)\b',
            r'\bvisual\s*arts\s*(?:major|degree|field|program|student)\b'
        ],
        "Music": [
            r'\bmusic\s*(?:major|degree|field|program|student)\b',
            r'\bmusical\s*(?:major|degree|field|program|student)\b',
            r'\borchestra\s*(?:major|degree|field|program|student)\b',
            r'\bband\s*(?:major|degree|field|program|student)\b',
            r'\bcomposition\s*(?:major|degree|field|program|student)\b'
        ],
        "Theater": [
            r'\btheater\s*(?:major|degree|field|program|student)\b',
            r'\btheatre\s*(?:major|degree|field|program|student)\b',
            r'\bdrama\s*(?:major|degree|field|program|student)\b',
            r'\bacting\s*(?:major|degree|field|program|student)\b',
            r'\bperforming\s*arts\s*(?:major|degree|field|program|student)\b'
        ],
        "Literature": [
            r'\bliterature\s*(?:major|degree|field|program|student)\b',
            r'\benglish\s*(?:major|degree|field|program|student)\b',
            r'\bwriting\s*(?:major|degree|field|program|student)\b',
            r'\bcreative\s*writing\s*(?:major|degree|field|program|student)\b',
            r'\bpoetry\s*(?:major|degree|field|program|student)\b'
        ],
        "History": [
            r'\bhistory\s*(?:major|degree|field|program|student)\b',
            r'\bhistorical\s*(?:major|degree|field|program|student)\b',
            r'\bhistorian\s*(?:major|degree|field|program|student)\b',
            r'\barchaeology\s*(?:major|degree|field|program|student)\b'
        ],
        "Political Science": [
            r'\bpolitical\s*science\s*(?:major|degree|field|program|student)\b',
            r'\bpolitics\s*(?:major|degree|field|program|student)\b',
            r'\bgovernment\s*(?:major|degree|field|program|student)\b',
            r'\bpublic\s*policy\s*(?:major|degree|field|program|student)\b'
        ],
        "Sociology": [
            r'\bsociology\s*(?:major|degree|field|program|student)\b',
            r'\bsocial\s*science\s*(?:major|degree|field|program|student)\b',
            r'\bsocial\s*work\s*(?:major|degree|field|program|student)\b',
            r'\bhuman\s*services\s*(?:major|degree|field|program|student)\b'
        ],
        "Anthropology": [
            r'\banthropology\s*(?:major|degree|field|program|student)\b',
            r'\banthropological\s*(?:major|degree|field|program|student)\b',
            r'\bcultural\s*studies\s*(?:major|degree|field|program|student)\b'
        ],
        "Philosophy": [
            r'\bphilosophy\s*(?:major|degree|field|program|student)\b',
            r'\bphilosophical\s*(?:major|degree|field|program|student)\b',
            r'\bethics\s*(?:major|degree|field|program|student)\b',
            r'\blogic\s*(?:major|degree|field|program|student)\b'
        ]
    }
    
    for tag in tag_list:
        if tag in sector_mappings:
            # Check for any of the specific patterns
            for pattern in sector_mappings[tag]:
                if re.search(pattern, text_lower):
                    matches.append(tag)
                    break
        else:
            # Fallback to exact match for tags not in mappings
            pattern = r"\b" + re.escape(tag.lower()) + r"\s*(?:major|degree|field|program|student)\b"
            if re.search(pattern, text_lower):
                matches.append(tag)
    
    return matches

def infer_demographic_tags(text):
    """Enhanced demographic tagging with precise keyword matching"""
    tags = []
    text_lower = text.lower()
    
    # First-generation college student indicators - more specific context
    first_gen_patterns = [
        r'\bfirst\s*[-]?\s*generation\s*college\s*student\b',
        r'\bfirst\s*[-]?\s*generation\s*student\b',
        r'\bfirst\s*gen\s*college\s*student\b',
        r'\bfirst\s*gen\s*student\b',
        r'\bfirst\s*in\s*family\s*to\s*attend\s*college\b',
        r'\bfirst\s*in\s*one\s*s\s*family\s*to\s*attend\s*college\b',
        r'\bparents?\s*did\s*not\s*attend\s*college\b',
        r'\bparents?\s*did\s*not\s*graduate\s*from\s*college\b',
        r'\bno\s*parent\s*with\s*a\s*bachelor\s*degree\b',
        r'\bneither\s*parent\s*attended\s*college\b',
        r'\bparents?\s*never\s*attended\s*college\b',
        r'\bfirst\s*[-]?\s*generation\s*american\s*student\b',
        r'\bimmigrant\s*family\s*student\b',
        r'\bnew\s*american\s*student\b'
    ]
    
    # BIPOC indicators - more flexible context
    bipoc_patterns = [
        r'\bbipoc\b',
        r'\bblack\b',
        r'\bafrican\s*american\b',
        r'\bhispanic\b',
        r'\blatino\b',
        r'\blatina\b',
        r'\blatinx\b',
        r'\bindigenous\b',
        r'\bnative\s*american\b',
        r'\bamerican\s*indian\b',
        r'\bpeople\s*of\s*color\b',
        r'\bperson\s*of\s*color\b',
        r'\bminority\b',
        r'\bunderrepresented\s*minority\b',
        r'\bracial\s*minority\b',
        r'\bethnic\s*minority\b',
        r'\bafrican\s*descent\b',
        r'\bmexican\s*american\b',
        r'\bpuerto\s*rican\b',
        r'\bcuban\b',
        r'\bdominican\b',
        r'\bcaribbean\b',
        r'\bpacific\s*islander\b',
        r'\bhawaiian\b',
        r'\bsamoan\b',
        r'\btongan\b',
        r'\bchamorro\b',
        r'\bguamanian\b',
        r'\bchinese\b',
        r'\bjapanese\b',
        r'\bkorean\b',
        r'\bvietnamese\b',
        r'\bfilipino\b',
        r'\bthai\b',
        r'\bcambodian\b',
        r'\blaotian\b',
        r'\bhmong\b',
        r'\bindian\b',
        r'\bpakistani\b',
        r'\bbangladeshi\b',
        r'\bsri\s*lankan\b',
        r'\bnepali\b',
        r'\bbhutanese\b',
        r'\bmiddle\s*eastern\b',
        r'\barab\b',
        r'\bpersian\b',
        r'\bturkish\b',
        r'\barmenian\b',
        r'\bafrican\s*immigrant\b',
        r'\bcaribbean\s*immigrant\b',
        r'\blatin\s*american\b',
        r'\bsouth\s*asian\b',
        r'\beast\s*asian\b',
        r'\bsoutheast\s*asian\b',
        r'\bcentral\s*asian\b',
        r'\bwest\s*asian\b'
    ]
    
    # Low-income indicators - more specific context
    low_income_patterns = [
        r'\blow\s*income\s*student\b',
        r'\bfinancial\s*need\s*student\b',
        r'\bneed\s*based\s*student\b',
        r'\beconomic\s*disadvantage\s*student\b',
        r'\bdisadvantaged\s*background\s*student\b',
        r'\bpell\s*grant\s*eligible\s*student\b',
        r'\bqualify\s*for\s*pell\s*grant\b',
        r'\bhousehold\s*income\s*requirement\b',
        r'\bfamily\s*income\s*requirement\b',
        r'\bannual\s*income\s*requirement\b',
        r'\bincome\s*limit\s*student\b',
        r'\bincome\s*threshold\s*student\b',
        r'\bincome\s*requirement\s*student\b',
        r'\bworking\s*class\s*student\b',
        r'\bstruggling\s*financially\s*student\b',
        r'\bfinancial\s*hardship\s*student\b',
        r'\beconomic\s*hardship\s*student\b',
        r'\bstruggling\s*family\s*student\b',
        r'\bsingle\s*parent\s*household\s*student\b',
        r'\bunemployed\s*parent\s*student\b',
        r'\bunderemployed\s*parent\s*student\b',
        r'\bfood\s*stamps\s*eligible\b',
        r'\bmedicaid\s*eligible\b',
        r'\bsection\s*8\s*eligible\b',
        r'\bpublic\s*assistance\s*eligible\b',
        r'\bwelfare\s*eligible\b',
        r'\bfree\s*lunch\s*eligible\b',
        r'\breduced\s*lunch\s*eligible\b',
        r'\bqualify\s*for\s*free\s*lunch\b'
    ]
    
    # LGBTQ+ indicators - more specific context
    lgbtq_patterns = [
        r'\blgbtq\s*student\b',
        r'\blgbt\s*student\b',
        r'\blgbtq\+\s*student\b',
        r'\blgbtqia\+\s*student\b',
        r'\blesbian\s*student\b',
        r'\bgay\s*student\b',
        r'\bbisexual\s*student\b',
        r'\btransgender\s*student\b',
        r'\btrans\s*student\b',
        r'\bqueer\s*student\b',
        r'\bnon\s*binary\s*student\b',
        r'\bnonbinary\s*student\b',
        r'\bgender\s*non\s*conforming\s*student\b',
        r'\bgender\s*fluid\s*student\b',
        r'\bpansexual\s*student\b',
        r'\basexual\s*student\b',
        r'\bintersex\s*student\b',
        r'\bsexual\s*orientation\s*student\b',
        r'\bgender\s*identity\s*student\b',
        r'\bgender\s*expression\s*student\b'
    ]
    
    # Women indicators - more specific context
    women_patterns = [
        r'\bwomen\s*in\s*stem\b',
        r'\bwomen\s*in\s*science\b',
        r'\bwomen\s*in\s*engineering\b',
        r'\bwomen\s*in\s*technology\b',
        r'\bwomen\s*in\s*business\b',
        r'\bfemale\s*student\b',
        r'\bwomen\s*student\b',
        r'\bwomen\s*of\s*color\s*student\b',
        r'\bwomen\s*of\s*minority\s*student\b',
        r'\bafrican\s*american\s*women\s*student\b',
        r'\bhispanic\s*women\s*student\b',
        r'\blatina\s*student\b',
        r'\bindigenous\s*women\s*student\b',
        r'\bnative\s*american\s*women\s*student\b'
    ]
    
    # Check for first-generation patterns
    for pattern in first_gen_patterns:
        if re.search(pattern, text_lower):
            tags.append("first-gen")
            break
    
    # Check for BIPOC patterns
    for pattern in bipoc_patterns:
        if re.search(pattern, text_lower):
            tags.append("BIPOC")
            break
    
    # Check for low-income patterns
    for pattern in low_income_patterns:
        if re.search(pattern, text_lower):
            tags.append("low-income background")
            break
    
    # Check for LGBTQ+ patterns
    for pattern in lgbtq_patterns:
        if re.search(pattern, text_lower):
            tags.append("LGBTQ+")
            break
    
    # Check for women patterns
    for pattern in women_patterns:
        if re.search(pattern, text_lower):
            tags.append("women")
            break
    
    return tags

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
            description = extract_description(sub_soup)

            # 💰 Amount
            amount_tag = sub_soup.find(string=re.compile(r"\$\d[\d,]*"))
            amount = parse_amount(amount_tag if amount_tag else None)

            # 📅 Deadline
            page_text = sub_soup.get_text()
            deadline_line = next((line for line in page_text.splitlines() if "Deadline" in line), "")
            deadline = parse_deadline(deadline_line)

            # 🏷️ Inferred tags
            sectors = infer_tags(description, ["STEM", "AI", "Engineering", "Healthcare", "Computer Science", "Technology", "Mathematics", "Physics", "Chemistry", "Biology", "Medicine", "Nursing", "Psychology", "Business", "Finance", "Economics", "Education", "Law", "Journalism", "Arts", "Music", "Theater", "Literature", "History", "Political Science", "Sociology", "Anthropology", "Philosophy"])
            demographic_tags = infer_demographic_tags(description)
            
            # Combine demographic tags with general eligibility
            if demographic_tags:
                eligibility = demographic_tags
            else:
                eligibility = ["general"]

            # ✅ Construct grant object
            scholarship_data = {
                "title": title,
                "description": description,
                "amount": amount,
                "deadline": deadline,
                "location_eligible": ["USA"],
                "target_group": ["students"],
                "sectors": sectors,
                "eligibility_criteria": eligibility,
                "source_url": link,
            }
            
            # Debug: Print detected tags for scholarships with demographic criteria
            if demographic_tags:
                print(f"🏷️ {title[:50]}... → Tags: {demographic_tags}")
            
            scholarships.append(scholarship_data)

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
