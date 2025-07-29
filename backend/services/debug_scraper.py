from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re

def debug_scholarship_page():
    url = "https://www.unigo.com/scholarships/our-scholarships/i-have-a-dream-scholarship"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        
        try:
            page.goto(url, wait_until='domcontentloaded')
            page.wait_for_timeout(3000)
            
            # Get the page content
            page_content = page.content()
            soup = BeautifulSoup(page_content, 'html.parser')
            
            # Remove UI elements
            for unwanted in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'button', 'form', 'input', 'select', 'option', 'label', 'a']):
                unwanted.decompose()
            
            print("=== DEBUGGING SCHOLARSHIP PAGE ===")
            print(f"URL: {url}")
            print("\n=== ALL STRONG TAGS ===")
            
            # Find all strong tags
            strong_tags = soup.find_all('strong')
            for i, strong in enumerate(strong_tags):
                text = strong.get_text(strip=True)
                print(f"{i+1}. '{text}'")
                
                # Check if it matches contextual patterns
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
                if has_context:
                    print(f"   -> MATCHES CONTEXTUAL PATTERN!")
            
            print("\n=== ALL ELEMENTS WITH CONTEXTUAL KEYWORDS ===")
            # Search for contextual keywords in any element
            contextual_keywords = ['applicants must', 'submit', 'online written response', 'question', 'eligibility', 'requirements', 'how to apply', 'application', 'essay', 'deadline', 'winner', 'notification']
            
            for element in soup.find_all(['p', 'strong', 'b', 'span', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                text = element.get_text(strip=True)
                if text and len(text) > 5:
                    for keyword in contextual_keywords:
                        if keyword in text.lower():
                            print(f"'{text}' (tag: {element.name})")
                            break
            
            print("\n=== SAMPLE PARAGRAPH CONTENT ===")
            paragraphs = soup.find_all('p')
            for i, p in enumerate(paragraphs[:5]):  # First 5 paragraphs
                text = p.get_text(strip=True)
                if text and len(text) > 20:
                    print(f"{i+1}. '{text[:100]}...'")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    debug_scholarship_page()