from playwright.sync_api import sync_playwright
import time
from scraper_helpers import parse_amount, parse_deadline, extract_description, infer_tags
from bs4 import BeautifulSoup
import os
from supabase import create_client, Client
from dotenv import load_dotenv
import re

# Load Supabase credentials
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

BASE_URL = "https://www.unigo.com/scholarships/our-scholarships"

def scrape_unigo():
    print("🚀 Launching Playwright Unigo scraper...")
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # set to False for debugging
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        
        try:
            page.goto(BASE_URL)
            page.wait_for_timeout(5000)

            # Get all scholarship links - more specific selector
            links = page.eval_on_selector_all(
                "a[href*='/scholarships/our-scholarships/']:not([href='#']):not([href*='javascript'])",
                "elements => elements.map(el => el.href).filter(href => href.includes('/scholarships/our-scholarships/'))"
            )
            print(f"📦 Found {len(links)} scholarship links")

            seen = set()
            for i, link in enumerate(links):
                if link in seen:
                    continue
                seen.add(link)

                try:
                    print(f"🔗 Scraping [{i+1}/{len(links)}]: {link}")
                    
                    # Skip non-scholarship pages early
                    skip_pages = [
                        "winners",
                        "about",
                        "contact",
                        "privacy",
                        "terms",
                        "faq",
                        "help",
                        "support"
                    ]
                    
                    if any(skip_page in link.lower() for skip_page in skip_pages):
                        print(f"⚠️ Skipping non-scholarship page: {link}")
                        continue
                    
                    # Navigate to the page
                    response = page.goto(link, wait_until='domcontentloaded')
                    if not response or response.status >= 400:
                        print(f"⚠️ Bad response for {link}: {response.status if response else 'No response'}")
                        continue
                    
                    page.wait_for_timeout(3000)

                    # Better modal handling
                    try:
                        # Try multiple ways to dismiss modals
                        modal_selectors = [
                            "button[aria-label='Close']",
                            ".modal-close",
                            ".close-button",
                            "button:has-text('×')",
                            "button:has-text('Close')",
                            ".modal button",
                            "[data-dismiss='modal']",
                            ".modal .close",
                            "button.close"
                        ]
                        
                        for selector in modal_selectors:
                            try:
                                if page.locator(selector).is_visible():
                                    page.locator(selector).click()
                                    page.wait_for_timeout(1000)
                                    break
                            except:
                                continue
                        
                        # Try escape key as fallback
                        page.keyboard.press("Escape")
                        page.wait_for_timeout(1000)
                    except:
                        pass

                    # Extract title with better selectors and fallbacks
                    title_selectors = [
                        "h1",
                        ".scholarship-title",
                        ".title",
                        "[data-testid='title']",
                        "h1.scholarship-title",
                        ".page-title",
                        "h1.page-title",
                        ".scholarship-name",
                        ".award-title",
                        "h1:first-child",
                        "title"  # fallback to page title
                    ]
                    
                    title = None
                    for selector in title_selectors:
                        try:
                            if selector == "title":
                                # Fallback to page title
                                title = page.title()
                                if title and "scholarship" in title.lower():
                                    break
                            else:
                                elements = page.locator(selector).all()
                                for element in elements:
                                    if element.is_visible():
                                        title = element.inner_text().strip()
                                        if title and len(title) > 3:
                                            break
                                if title and len(title) > 3:
                                    break
                        except Exception as e:
                            print(f"⚠️ Error with selector {selector}: {e}")
                            continue
                    
                    if not title or len(title) < 3:
                        print(f"⚠️ Could not find title for: {link}")
                        # Try to get title from URL as last resort
                        url_parts = link.split('/')
                        if len(url_parts) > 0:
                            title = url_parts[-1].replace('-', ' ').replace('?', '').title()
                            print(f"📝 Using URL-derived title: {title}")
                        else:
                            continue

                    # Initialize description variable
                    description = ""

                    # Get full page content for description and fallback parsing
                    try:
                        # Try to get main content area - focus on scholarship-specific content
                        content_selectors = [
                            ".scholarship-description",
                            ".description",
                            ".scholarship-content",
                            ".award-description",
                            ".main-content",
                            ".content",
                            "main",
                            ".scholarship-details",
                            "article",
                            ".page-content"
                        ]
                        
                        for selector in content_selectors:
                            try:
                                elements = page.locator(selector).all()
                                for element in elements:
                                    if element.is_visible():
                                        # Use innerHTML to preserve formatting, then convert to text with breaks
                                        html_content = element.inner_html()
                                        if html_content and len(html_content) > 100:
                                            # Parse HTML to preserve structure
                                            soup = BeautifulSoup(html_content, 'html.parser')
                                            
                                            # Remove unwanted elements more aggressively
                                            for unwanted in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'button', 'form', 'input', 'select', 'option', 'label']):
                                                unwanted.decompose()
                                            
                                            # Convert to text while preserving paragraph breaks
                                            paragraphs = []
                                            for tag in soup.find_all(['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']):
                                                text = tag.get_text(strip=True)
                                                if text and len(text) > 10:
                                                    # Filter out UI and navigation text
                                                    ui_indicators = [
                                                        'apply', 'apply now', 'save', 'continue', 'sign up', 'sign in',
                                                        'my education level', 'high school', 'college', 'graduate',
                                                        'application status', 'not applied', 'view scholarships',
                                                        'opens in new tab', 'continue with google', 'continue with email',
                                                        'award amount', 'application deadline', 'see past winners',
                                                        'get started', 'sign up for access', 'millions of scholarships'
                                                    ]
                                                    
                                                    # Skip if text contains too many UI indicators
                                                    ui_count = sum(1 for indicator in ui_indicators if indicator.lower() in text.lower())
                                                    if ui_count < 2:  # Allow some UI text but not too much
                                                        paragraphs.append(text)
                                            
                                            if paragraphs:
                                                description = '\n\n'.join(paragraphs)
                                                # Filter out navigation and generic content
                                                if (len(description) > 100 and 
                                                    not description.startswith('<!DOCTYPE') and
                                                    not description.startswith('FIND SCHOLARSHIPS') and
                                                    'HIGH SCHOOL SCHOLARSHIPS' not in description and
                                                    'COLLEGE SCHOLARSHIPS' not in description and
                                                    'UNIGO SCHOLARSHIPS' not in description):
                                                    
                                                    # Clean up UI elements
                                                    ui_elements = [
                                                        'ScholarshipApply withEssayVideoNEW',
                                                        'Apply withEssayVideoNEW',
                                                        'Apply withEssay',
                                                        'Apply withVideo',
                                                        'NEW',
                                                        'Award Amount',
                                                        'Application deadline',
                                                        'See Past Winners',
                                                        'Get started',
                                                        'Sign Up For Access',
                                                        'Continue With Google',
                                                        'Continue with Email',
                                                        'My Education Level',
                                                        'High School Senior',
                                                        'High School Junior',
                                                        'High School Sophomore',
                                                        'High School Freshman',
                                                        'College Student',
                                                        'Graduate Student',
                                                        'Application Status',
                                                        'Not Applied',
                                                        'Apply Now',
                                                        'Save',
                                                        'View Scholarships',
                                                        'Opens in new tab',
                                                        'Millions of Scholarships'
                                                    ]
                                                    
                                                    for element in ui_elements:
                                                        description = description.replace(element, '')
                                                    
                                                    # Clean up excessive whitespace and line breaks
                                                    description = re.sub(r'\n\s*\n\s*\n', '\n\n', description)
                                                    description = re.sub(r' +', ' ', description)
                                                    description = description.strip()
                                                    
                                                    # Only use if we have substantial content after cleaning
                                                    if len(description) > 200:
                                                        break
                                if description and len(description) > 200:
                                    break
                            except:
                                continue
                        
                        # If still no good description, try a more targeted approach
                        if not description or len(description) < 200:
                            try:
                                # Look for content that contains scholarship-specific keywords
                                page_content = page.content()
                                soup = BeautifulSoup(page_content, 'html.parser')
                                
                                # Remove all UI elements
                                for unwanted in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'button', 'form', 'input', 'select', 'option', 'label', 'a']):
                                    unwanted.decompose()
                                
                                # Find paragraphs that contain scholarship content
                                scholarship_paragraphs = []
                                for p in soup.find_all('p'):
                                    text = p.get_text(strip=True)
                                    if text and len(text) > 50:
                                        # Check if this looks like scholarship content
                                        scholarship_words = ['scholarship', 'award', 'essay', 'eligibility', 'requirements', 'deadline', 'winner', 'rules', 'sponsor']
                                        ui_words = ['apply now', 'save', 'continue', 'sign up', 'my education level', 'application status', 'view scholarships', 'opens in new tab']
                                        
                                        scholarship_count = sum(1 for word in scholarship_words if word.lower() in text.lower())
                                        ui_count = sum(1 for word in ui_words if word.lower() in text.lower())
                                        
                                        if scholarship_count > 0 and ui_count < 2:
                                            scholarship_paragraphs.append(text)
                                
                                if scholarship_paragraphs:
                                    description = '\n\n'.join(scholarship_paragraphs)
                                    # Clean up
                                    description = re.sub(r'\n\s*\n\s*\n', '\n\n', description)
                                    description = re.sub(r' +', ' ', description)
                                    description = description.strip()
                                    
                                    if len(description) > 3000:
                                        description = description[:3000] + "..."
                                        
                            except Exception as e:
                                print(f"⚠️ Error in targeted extraction: {e}")
                                description = ""
                            
                    except Exception as e:
                        print(f"⚠️ Error getting description: {e}")
                        description = ""

                    # Extract amount with better logic
                    amount_selectors = [
                        ".amount",
                        ".scholarship-amount",
                        "[data-testid='amount']",
                        ".award-amount",
                        "span:has-text('$')",
                        ".price",
                        ".award",
                        "[class*='amount']",
                        "[class*='award']"
                    ]
                    
                    amount_text = ""
                    for selector in amount_selectors:
                        try:
                            elements = page.locator(selector).all()
                            for element in elements:
                                if element.is_visible():
                                    text = element.inner_text().strip()
                                    if text and '$' in text:
                                        amount_text = text
                                        break
                            if amount_text:
                                break
                        except:
                            continue
                    
                    # Also try to extract amount from title if it contains amount info
                    if not amount_text and title:
                        # Look for patterns like "$10K", "$10,000", etc. in title
                        title_amount_match = re.search(r'\$(\d+(?:,\d{3})*(?:K|k|M|m)?)', title)
                        if title_amount_match:
                            amount_text = title_amount_match.group(0)
                            print(f"💰 Found amount in title: {amount_text}")
                    
                    # Parse values with better error handling
                    amount = parse_amount(description or amount_text) if (description or amount_text) else None
                    
                    # Special handling for K/M suffixes in amounts
                    if amount and amount.endswith(('K', 'k')):
                        try:
                            # Convert K to thousands
                            num = float(amount[1:-1])  # Remove $ and K
                            amount = f"${int(num * 1000):,}"
                            print(f"💰 Converted {amount_text} to {amount}")
                        except:
                            pass
                    elif amount and amount.endswith(('M', 'm')):
                        try:
                            # Convert M to millions
                            num = float(amount[1:-1])  # Remove $ and M
                            amount = f"${int(num * 1000000):,}"
                            print(f"💰 Converted {amount_text} to {amount}")
                        except:
                            pass
                    
                    # If still no amount found, try to extract from title more aggressively
                    if not amount and title:
                        # Look for "10K", "10k", "10,000" patterns in title
                        title_patterns = [
                            r'(\d+)K',  # 10K
                            r'(\d+)k',  # 10k
                            r'(\d{1,3}(?:,\d{3})*)',  # 10,000
                        ]
                        
                        for pattern in title_patterns:
                            match = re.search(pattern, title)
                            if match:
                                num_str = match.group(1)
                                if 'K' in pattern or 'k' in pattern:
                                    # Convert K to thousands
                                    try:
                                        num = int(num_str)
                                        amount = f"${num * 1000:,}"
                                        print(f"💰 Extracted {num_str}K from title: {amount}")
                                        break
                                    except:
                                        pass
                                else:
                                    # Already in number format
                                    try:
                                        num = int(num_str.replace(',', ''))
                                        amount = f"${num:,}"
                                        print(f"💰 Extracted {num_str} from title: {amount}")
                                        break
                                    except:
                                        pass
                    
                    # Special case for "Unigo $10K Scholarship"
                    if title and "unigo" in title.lower() and "10k" in title.lower() and (not amount or amount == "$10"):
                        amount = "$10,000"
                        print(f"💰 Fixed Unigo $10K Scholarship amount: {amount}")

                    # Extract deadline with better logic
                    deadline_selectors = [
                        ".deadline",
                        ".application-deadline",
                        "[data-testid='deadline']",
                        ".due-date",
                        "span:has-text('deadline')",
                        "span:has-text('due')",
                        "[class*='deadline']",
                        "[class*='due']"
                    ]
                    
                    deadline_text = ""
                    for selector in deadline_selectors:
                        try:
                            elements = page.locator(selector).all()
                            for element in elements:
                                if element.is_visible():
                                    text = element.inner_text().strip()
                                    if text and any(word in text.lower() for word in ['deadline', 'due', 'date']):
                                        deadline_text = text
                                        break
                            if deadline_text:
                                break
                        except:
                            continue

                    # Parse deadline
                    deadline = parse_deadline(description or deadline_text) if (description or deadline_text) else None

                    # Better tag inference
                    sectors = infer_tags(description, ["STEM", "AI", "Engineering", "Healthcare", "Business", "Arts", "Education"])
                    eligibility = infer_tags(description, ["BIPOC", "low-income", "first-gen", "LGBTQ", "women", "minority", "disability"])

                    # Debug output
                    print(f"📊 Extracted data:")
                    print(f"   Title: {title}")
                    print(f"   Amount: {amount}")
                    print(f"   Deadline: {deadline}")
                    print(f"   Description length: {len(description) if description else 0}")
                    print(f"   Description preview: {description[:100] if description else 'None'}...")

                    # Validation - make it less strict
                    if not description:
                        print(f"⚠️ Skipping due to no description: {link}")
                        continue
                    
                    # Check for login requirements more carefully
                    login_indicators = ["login", "sign in", "register", "create account", "membership required"]
                    has_login_requirement = any(indicator in description.lower() for indicator in login_indicators)
                    
                    # Only skip if there are strong indicators of login requirements
                    # Check for specific patterns that indicate login is required
                    login_required_patterns = [
                        "login to apply",
                        "sign in to apply", 
                        "register to apply",
                        "create account to apply",
                        "membership required to apply",
                        "you must login",
                        "you must sign in",
                        "login required",
                        "sign in required"
                    ]
                    
                    has_strong_login_requirement = any(pattern in description.lower() for pattern in login_required_patterns)
                    
                    if has_strong_login_requirement:
                        print(f"⚠️ Skipping due to login requirement: {link}")
                        continue
                    
                    # More lenient description length check
                    if len(description) < 10:
                        print(f"⚠️ Skipping due to very short description ({len(description)} chars): {link}")
                        continue

                    if not title:
                        print(f"⚠️ Skipping due to missing title: {link}")
                        continue
                    
                    # Amount is optional - don't skip if missing
                    if not amount:
                        print(f"⚠️ No amount found, but continuing: {link}")
                        amount = "Varies"  # Set a default value

                    results.append({
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

                    print(f"✅ Successfully scraped: {title}")
                    time.sleep(1)  # Be more respectful with delays

                except Exception as e:
                    print(f"❌ Failed scraping {link}: {str(e)}")
                    continue

        except Exception as e:
            print(f"❌ Browser error: {e}")
        finally:
            browser.close()

    print(f"✅ Total scraped: {len(results)}")
    return results


# Upload to Supabase
if __name__ == "__main__":
    data = scrape_unigo()

    if not data:
        print("⚠️ No data to upload.")
    else:
        print(f"📤 Uploading {len(data)} scholarships to Supabase...")

        for i, item in enumerate(data):
            # Skip if required fields are missing or invalid
            if not item["description"] or "No description" in item["description"] or item["amount"] is None:
                print(f"⚠️ Skipping upload: {item['title']} (invalid or incomplete data)")
                continue

            try:
                # Clean up the data before upload
                clean_item = {
                    "title": str(item["title"])[:200] if item["title"] else "",
                    "description": str(item["description"])[:5000] if item["description"] else "",
                    "amount": str(item["amount"]) if item["amount"] else "Varies",
                    "deadline": str(item["deadline"]) if item["deadline"] else None,
                    "location_eligible": item.get("location_eligible", ["USA"]),
                    "target_group": item.get("target_group", ["students"]),
                    "sectors": item.get("sectors", []),
                    "eligibility_criteria": item.get("eligibility_criteria", []),
                    "source_url": str(item["source_url"]) if item["source_url"] else "",
                }
                
                # Debug: print the data being uploaded
                print(f"📋 Uploading data for {clean_item['title']}:")
                print(f"   Title: {clean_item['title']}")
                print(f"   Amount: {clean_item['amount']}")
                print(f"   Deadline: {clean_item['deadline']}")
                print(f"   Description length: {len(clean_item['description'])}")
                
                # Check if record already exists
                existing = supabase.table("grants").select("id").eq("source_url", clean_item["source_url"]).execute()
                
                if existing.data:
                    # Update existing record
                    result = supabase.table("grants").update(clean_item).eq("source_url", clean_item["source_url"]).execute()
                    print(f"✅ Updated: {item['title']}")
                else:
                    # Insert new record
                    result = supabase.table("grants").insert([clean_item]).execute()
                    print(f"✅ Inserted: {item['title']}")
                
            except Exception as e:
                print(f"❌ Failed to upload {item['title']}: {e}")
                # Try to print more details about the error
                print(f"   Error details: {type(e).__name__}")
                if hasattr(e, 'args'):
                    print(f"   Error args: {e.args}")

        print("🎉 Upload complete.")
