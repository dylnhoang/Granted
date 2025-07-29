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

def extract_official_rules(soup):
    """
    Extract and format the official rules section from scholarship pages.
    This is often the most structured and important part of the description.
    """
    rules_sections = []
    seen_sections = set()  # Track unique sections to avoid repetition
    
    # Look for sections that contain "OFFICIAL" or "RULES"
    for tag in soup.find_all(['div', 'section', 'article']):
        text = tag.get_text(strip=True)
        if text and ('OFFICIAL' in text.upper() or 'RULES' in text.upper() or 'ELIGIBILITY' in text.upper()):
            # Extract structured content from this section
            for element in tag.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li']):
                element_text = element.get_text(strip=True)
                if element_text and len(element_text) > 10:
                    # Filter out UI elements
                    ui_indicators = [
                        'apply', 'apply now', 'save', 'continue', 'sign up', 'sign in',
                        'my education level', 'high school', 'college', 'graduate',
                        'application status', 'not applied', 'view scholarships',
                        'opens in new tab', 'continue with google', 'continue with email',
                        'award amount', 'application deadline', 'see past winners',
                        'get started', 'sign up for access', 'millions of scholarships',
                        'education', 'due', 'award:', 'to', 'scholarships', 'our scholarships',
                        'apply for the', 'submit an online', 'submit online', 'online written response',
                        'written response to', 'response to the question', 'to the question', 'the question',
                        'question:', 'words or less', 'or less', 'less'
                    ]
                    
                    has_ui_content = any(indicator.lower() in element_text.lower() for indicator in ui_indicators)
                    
                    if not has_ui_content:
                        # Check for scholarship-specific content
                        scholarship_keywords = ['scholarship', 'award', 'essay', 'eligibility', 'requirements', 'deadline', 'winner', 'rules', 'sponsor', 'official', 'general', 'selection', 'judging', 'must', 'applicants', 'residents', 'legal', 'united states', 'district of columbia', 'years of age', 'notified', 'email', 'phone', 'march', 'december', 'january', 'february', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november']
                        scholarship_count = sum(1 for keyword in scholarship_keywords if keyword.lower() in element_text.lower())
                        
                        if scholarship_count > 0 and len(element_text) > 20:
                            # Create a normalized version for deduplication
                            normalized_text = re.sub(r'\s+', ' ', element_text.strip())
                            if normalized_text not in seen_sections:
                                seen_sections.add(normalized_text)
                                # Format based on element type
                                if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                                    rules_sections.append(f"\n{element_text.upper()}\n")
                                elif element.name == 'li':
                                    rules_sections.append(f"• {element_text}")
                                else:
                                    rules_sections.append(element_text)
    
    if rules_sections:
        return '\n\n'.join(rules_sections)
    return None

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

            # Normalize links to remove query parameters and track duplicates
            normalized_links = []
            seen = set()
            
            for link in links:
                # Remove query parameters to normalize the URL
                normalized_link = link.split('?')[0] if '?' in link else link
                
                if normalized_link not in seen:
                    seen.add(normalized_link)
                    normalized_links.append(link)  # Keep original link for scraping
            
            print(f"📦 After deduplication: {len(normalized_links)} unique scholarship links")

            for i, link in enumerate(normalized_links):
                try:
                    print(f"🔗 Scraping [{i+1}/{len(normalized_links)}]: {link}")
                    
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

                    # Get full page content for description and fallback parsing
                    try:
                        # First, try to find the main scholarship description content
                        # Look for specific content areas that contain the actual scholarship information
                        page_content = page.content()
                        soup = BeautifulSoup(page_content, 'html.parser')
                        
                        # Remove all UI elements first
                        for unwanted in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'button', 'form', 'input', 'select', 'option', 'label', 'a']):
                            unwanted.decompose()
                        
                        # Look for the main scholarship description - focus on paragraphs that contain actual scholarship info
                        scholarship_paragraphs = []
                        seen_paragraphs = set()  # Track unique paragraphs to avoid repetition
                        
                        # Extract content in the proper order as it appears on the page
                        # First, find all content elements and their positions
                        content_elements = []
                        
                        # First, find all strong tags specifically for contextual headers
                        for strong in soup.find_all('strong'):
                            text = strong.get_text(strip=True)
                            if text and len(text) > 5:
                                # Check if it's a contextual header
                                contextual_patterns = [
                                    r'applicants must:?',
                                    r'submit.*online.*written.*response.*question:?',
                                    r'eligibility.*requirements:?',
                                    r'how.*to.*apply:?',
                                    r'application.*requirements:?',
                                    r'essay.*prompt:?',
                                    r'question:?',
                                    r'winner.*notification:?'
                                ]
                                
                                has_context = any(re.search(pattern, text.lower()) for pattern in contextual_patterns)
                                
                                if has_context and len(text) < 100:  # Reasonable length for headers
                                    # Get the element's position in the document
                                    position = len(str(soup)[:str(soup).find(str(strong))])
                                    content_elements.append((position, strong, text, 'contextual_header'))
                        
                        # Then find all other relevant elements
                        for element in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'b', 'span', 'div', 'li']):
                            text = element.get_text(strip=True)
                            if text and len(text) > 5:
                                # Get the element's position in the document
                                position = len(str(soup)[:str(soup).find(str(element))])
                                content_elements.append((position, element, text, 'normal'))
                        
                        # Sort by position to maintain original order
                        content_elements.sort(key=lambda x: x[0])
                        
                        # Process elements in order
                        for position, element, text, element_type in content_elements:
                            # Skip if already seen
                            normalized_text = re.sub(r'\s+', ' ', text.strip())
                            if normalized_text in seen_paragraphs:
                                continue
                            
                            # Check for scholarship content
                            scholarship_keywords = ['scholarship', 'award', 'essay', 'eligibility', 'requirements', 'deadline', 'winner', 'rules', 'sponsor', 'official', 'general', 'selection', 'judging', 'must', 'applicants', 'residents', 'legal', 'united states', 'district of columbia', 'years of age', 'notified', 'email', 'phone', 'march', 'december', 'january', 'february', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'being funny', 'smart people', 'rich people', 'important to be happy', 'would you rather', 'help increase your education', 'enrolled', 'accredited', 'postsecondary', 'institution', 'higher education', 'letter to', 'explaining why', 'high five', 'original']
                            
                            # Skip UI elements
                            ui_indicators = ['apply now', 'save', 'continue', 'sign up', 'get started', 'view scholarships', 'award amount', 'application deadline', 'not applied', 'scholarship contests', 'sweepstakes', 'opens in new tab', 'continue with google', 'continue with email', 'my education level', 'application status', 'apply with', 'essay', 'video', 'new']
                            has_ui = any(ui in text.lower() for ui in ui_indicators)
                            
                            # Also skip navigation-style elements
                            if len(text) < 50 and any(nav in text.lower() for nav in ['unigo', 'scholarship', 'education matters', 'superpower', 'i have a dream', 'zombie apocalypse', 'flavor of the month', 'make me laugh', 'shout it out', 'top ten list', 'sweet and simple', 'fifth month', 'do over']):
                                has_ui = True
                            
                            # Special handling for contextual headers - they should always be included
                            if element_type == 'contextual_header':
                                seen_paragraphs.add(normalized_text)
                                scholarship_paragraphs.append(f"\n{text.upper()}\n")
                            elif not has_ui:
                                scholarship_count = sum(1 for keyword in scholarship_keywords if keyword.lower() in text.lower())
                                
                                if scholarship_count > 0 and len(text) > 20:
                                    seen_paragraphs.add(normalized_text)
                                    
                                    # Format based on element type and content
                                    if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                                        # Only format as header if it's actually a header element
                                        scholarship_paragraphs.append(text)
                                    elif element.name == 'li':
                                        scholarship_paragraphs.append(f"• {text}")
                                    else:
                                        # For other elements, just add the text as-is
                                        scholarship_paragraphs.append(text)
                        
                        # If we found good paragraphs, use them
                        if scholarship_paragraphs:
                            description = '\n\n'.join(scholarship_paragraphs)
                            print(f"📝 Using paragraph-based extraction")
                        else:
                            # Fallback: try to extract from specific content areas
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
                                            html_content = element.inner_html()
                                            if html_content and len(html_content) > 100:
                                                soup = BeautifulSoup(html_content, 'html.parser')
                                                
                                                # Remove unwanted elements
                                                for unwanted in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'button', 'form', 'input', 'select', 'option', 'label']):
                                                    unwanted.decompose()
                                                
                                                # Extract content in the proper order as it appears on the page
                                                paragraphs = []
                                                seen_paragraphs = set()  # Track unique paragraphs
                                                content_elements = []
                                                
                                                # First, find all strong tags specifically for contextual headers
                                                for strong in soup.find_all('strong'):
                                                    text = strong.get_text(strip=True)
                                                    if text and len(text) > 5:
                                                        # Check if it's a contextual header
                                                        contextual_patterns = [
                                                            r'applicants must:?',
                                                            r'submit.*online.*written.*response.*question:?',
                                                            r'eligibility.*requirements:?',
                                                            r'how.*to.*apply:?',
                                                            r'application.*requirements:?',
                                                            r'essay.*prompt:?',
                                                            r'question:?',
                                                            r'winner.*notification:?'
                                                        ]
                                                        
                                                        has_context = any(re.search(pattern, text.lower()) for pattern in contextual_patterns)
                                                        
                                                        if has_context and len(text) < 100:  # Reasonable length for headers
                                                            # Get the element's position in the document
                                                            position = len(str(soup)[:str(soup).find(str(strong))])
                                                            content_elements.append((position, strong, text, 'contextual_header'))
                                                
                                                # Then find all other relevant elements
                                                for element in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'b', 'span', 'div', 'li']):
                                                    text = element.get_text(strip=True)
                                                    if text and len(text) > 5:
                                                        # Get the element's position in the document
                                                        position = len(str(soup)[:str(soup).find(str(element))])
                                                        content_elements.append((position, element, text, 'normal'))
                                                
                                                # Sort by position to maintain original order
                                                content_elements.sort(key=lambda x: x[0])
                                                
                                                # Process elements in order
                                                for position, element, text, element_type in content_elements:
                                                    # Skip if already seen
                                                    normalized_text = re.sub(r'\s+', ' ', text.strip())
                                                    if normalized_text in seen_paragraphs:
                                                        continue
                                                    
                                                    # Check for scholarship content
                                                    scholarship_keywords = ['scholarship', 'award', 'essay', 'eligibility', 'requirements', 'deadline', 'winner', 'rules', 'sponsor', 'official', 'general', 'selection', 'judging', 'must', 'applicants', 'residents', 'legal', 'united states', 'district of columbia', 'years of age', 'notified', 'email', 'phone', 'march', 'december', 'january', 'february', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'being funny', 'smart people', 'rich people', 'important to be happy', 'would you rather', 'help increase your education', 'enrolled', 'accredited', 'postsecondary', 'institution', 'higher education', 'letter to', 'explaining why', 'high five', 'original']
                                                    
                                                    # Skip UI elements
                                                    ui_indicators = ['apply now', 'save', 'continue', 'sign up', 'get started', 'view scholarships', 'award amount', 'application deadline', 'not applied', 'scholarship contests', 'sweepstakes', 'opens in new tab', 'continue with google', 'continue with email', 'my education level', 'application status', 'apply with', 'essay', 'video', 'new']
                                                    has_ui = any(ui in text.lower() for ui in ui_indicators)
                                                    
                                                    # Also skip navigation-style elements
                                                    if len(text) < 50 and any(nav in text.lower() for nav in ['unigo', 'scholarship', 'education matters', 'superpower', 'i have a dream', 'zombie apocalypse', 'flavor of the month', 'make me laugh', 'shout it out', 'top ten list', 'sweet and simple', 'fifth month', 'do over']):
                                                        has_ui = True
                                                    
                                                    # Special handling for contextual headers - they should always be included
                                                    if element_type == 'contextual_header':
                                                        seen_paragraphs.add(normalized_text)
                                                        paragraphs.append(f"\n{text.upper()}\n")
                                                    elif not has_ui:
                                                        scholarship_count = sum(1 for keyword in scholarship_keywords if keyword.lower() in text.lower())
                                                        
                                                        if scholarship_count > 0 and len(text) > 20:
                                                            seen_paragraphs.add(normalized_text)
                                                            
                                                            # Format based on element type and content
                                                            if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                                                                # Only format as header if it's actually a header element
                                                                paragraphs.append(text)
                                                            elif element.name == 'li':
                                                                paragraphs.append(f"• {text}")
                                                            else:
                                                                # For other elements, just add the text as-is
                                                                paragraphs.append(text)
                                                
                                                if paragraphs:
                                                    description = '\n\n'.join(paragraphs)
                                                    print(f"📝 Using selector-based extraction: {selector}")
                                                    break
                                    if description:
                                        break
                                except:
                                    continue
                            
                            # If still no description, try the official rules approach
                            if not description:
                                official_rules = extract_official_rules(soup)
                                if official_rules and len(official_rules) > 200:
                                    description = official_rules
                                    print(f"📋 Using official rules section for description")
                            
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
                    
                    # Also look for amounts in the page content
                    if not amount_text:
                        try:
                            page_content = page.content()
                            # Look for common amount patterns in the content
                            amount_patterns = [
                                r'\$\d+(?:,\d{3})*(?:K|k|M|m)?',
                                r'\$\d+(?:,\d{3})*',
                                r'\d+(?:,\d{3})*\s*(?:dollars?|USD)',
                                r'\d+(?:,\d{3})*\s*(?:K|k|M|m)'
                            ]
                            
                            for pattern in amount_patterns:
                                matches = re.findall(pattern, page_content, re.IGNORECASE)
                                for match in matches:
                                    if '$' in match or any(suffix in match.upper() for suffix in ['K', 'M', 'DOLLAR', 'USD']):
                                        amount_text = match
                                        print(f"💰 Found amount in content: {amount_text}")
                                        break
                                if amount_text:
                                    break
                        except:
                            pass
                    
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
                    
                    # Special case for "Unigo $10K Scholarship" and similar patterns
                    if title and "unigo" in title.lower() and "10k" in title.lower() and (not amount or amount == "$10"):
                        amount = "$10,000"
                        print(f"💰 Fixed Unigo $10K Scholarship amount: {amount}")
                    
                    # Additional special cases for common patterns
                    if title and not amount:
                        # Look for any number followed by K in the title
                        k_match = re.search(r'(\d+)K', title, re.IGNORECASE)
                        if k_match:
                            try:
                                num = int(k_match.group(1))
                                amount = f"${num * 1000:,}"
                                print(f"💰 Extracted {num}K from title: {amount}")
                            except:
                                pass

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

                    # Parse deadline from both description and extracted text
                    deadline = parse_deadline(description or deadline_text) if (description or deadline_text) else None
                    
                    # If still no deadline, try to extract from the entire page content
                    if not deadline:
                        try:
                            page_content = page.content()
                            deadline = parse_deadline(page_content)
                            if deadline:
                                print(f"📅 Found deadline in page content: {deadline}")
                        except:
                            pass

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
                    
                    # Clean up the description to remove any remaining UI artifacts
                    if description:
                        # Simple cleanup - remove obvious UI elements
                        ui_artifacts = [
                            'Education', 'Due', 'Award:', 'Apply Now', 'Save', 'View Scholarships',
                            'Opens in new tab', 'Millions of Scholarships', 'Get started',
                            'Sign Up For Access', 'Continue With Google', 'Continue with Email',
                            'My Education Level', 'High School Senior', 'High School Junior', 
                            'High School Sophomore', 'High School Freshman', 'College Student', 
                            'Graduate Student', 'Application Status', 'Not Applied',
                            'AWARD AMOUNT', 'APPLICATION DEADLINE', 'GET STARTED',
                            'scholarship contests', 'sweepstakes'
                        ]
                        for artifact in ui_artifacts:
                            description = description.replace(artifact, '')
                        
                        # Clean up pipe separators and convert to proper formatting
                        if '|' in description:
                            # Split by pipe and format as bullet points
                            lines = description.split('\n')
                            cleaned_lines = []
                            for line in lines:
                                if '|' in line:
                                    parts = [part.strip() for part in line.split('|') if part.strip()]
                                    for part in parts:
                                        if part and len(part) > 5:
                                            cleaned_lines.append(f"• {part}")
                                else:
                                    cleaned_lines.append(line)
                            description = '\n'.join(cleaned_lines)
                        
                        # Basic whitespace cleanup
                        description = re.sub(r'\n\s*\n\s*\n', '\n\n', description)
                        description = re.sub(r' +', ' ', description)
                        description = description.strip()
                        
                        # Ensure we still have meaningful content after cleaning
                        if len(description) < 50:
                            print(f"⚠️ Description too short after cleaning ({len(description)} chars): {link}")
                            continue
                        
                        # Add some final formatting improvements
                        # Ensure headers are properly spaced
                        description = re.sub(r'\n([A-Z\s]+)\n', r'\n\n\1\n\n', description)
                        
                        # Ensure bullet points are properly formatted
                        description = re.sub(r'\n•\s*', r'\n• ', description)
                        
                        # Clean up any remaining excessive whitespace
                        description = re.sub(r'\n\s*\n\s*\n', '\n\n', description)
                        description = description.strip()
                        
                        # Final check - remove any lines that are just UI elements
                        lines = description.split('\n')
                        cleaned_lines = []
                        for line in lines:
                            line = line.strip()
                            if line and len(line) > 5:
                                # Check if this line is just UI content
                                ui_check = any(ui in line.lower() for ui in ['apply', 'save', 'continue', 'sign up', 'get started', 'view scholarships', 'award amount', 'application deadline', 'not applied', 'scholarship contests', 'sweepstakes'])
                                if not ui_check:
                                    # Clean up pipe separators and replace with proper formatting
                                    if '|' in line:
                                        # Split by pipe and format as bullet points
                                        parts = [part.strip() for part in line.split('|') if part.strip()]
                                        if len(parts) > 1:
                                            for part in parts:
                                                if part and len(part) > 5:
                                                    cleaned_lines.append(f"• {part}")
                                        else:
                                            cleaned_lines.append(line)
                                    else:
                                        cleaned_lines.append(line)
                        
                        description = '\n'.join(cleaned_lines)
                        
                        # Remove any remaining navigation-style bullet points
                        description = re.sub(r'•\s*(scholarship contests|sweepstakes|unigo 10k scholarship|education matters scholarship|superpower scholarship|i have a dream scholarship|zombie apocalypse scholarship|flavor of the month scholarship|make me laugh scholarship|shout it out scholarship|top ten list scholarship|sweet and simple scholarship|fifth month scholarship|do-over scholarship)\s*\n?', '', description, flags=re.IGNORECASE)

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
