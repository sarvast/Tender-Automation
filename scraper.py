import time
import random
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from config import TARGET_KEYWORDS
from models import SessionLocal
from database_manager import process_and_save_bids, check_bid_exists

# Note: GeM Advanced Search URL is a placeholder
GEM_SEARCH_URL = "https://bidplus.gem.gov.in/advance-search"

def parse_date(date_str):
    """
    Placeholder function to parse the bid end date string.
    Will be updated based on actual GeM portal format.
    """
    try:
        # Assuming format "2024-12-31 23:59:59" for now
        return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        # Fallback to current time if parsing fails
        return datetime.now()

def parse_float(value_str):
    """
    Placeholder function to extract float values from strings like '₹ 1,50,000.00'.
    """
    try:
        cleaned = "".join([c for c in value_str if c.isdigit() or c == '.'])
        return float(cleaned) if cleaned else None
    except Exception:
        return None

def run_scraper():
    """
    Main extraction loop to scrape GeM portal bids based on configured brands/keywords.
    """
    print("Initializing Playwright scraper...")
    # Using Playwright's sync manager
    with sync_playwright() as p:
        # headless=True for production
        # NOTE FOR DEVELOPER: Change to headless=False during development/debugging to watch the automation
        browser = p.chromium.launch(headless=True)
        # Adding a common user agent to reduce bot detection
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # The Extraction Loop
        for brand, keywords in TARGET_KEYWORDS.items():
            print(f"\n--- Starting extraction for Brand: {brand} ---")
            
            for keyword in keywords:
                print(f"Scraping keyword: '{keyword}'")
                scraped_data = [] # Data Structure array
                
                try:
                    # Instruct browser to navigate to advanced search
                    page.goto(GEM_SEARCH_URL, wait_until="networkidle")
                    
                    # Anti-Bot Evasion: Sleep for random uniform delay between 3 and 7 seconds
                    delay = random.uniform(3.0, 7.0)
                    print(f"  [Anti-Bot] Sleeping for {delay:.2f} seconds...")
                    time.sleep(delay)
                    
                    # Ensure latest bids are on top by clicking Sort -> Published Date (Descending)
                    print("  [UI] Simulating click to sort by 'Published Date (Descending)'...")
                    # Note to developer: Update this placeholder selector with actual GeM UI button
                    try:
                         page.click("button.sort-by-date-desc", timeout=5000)
                         page.wait_for_load_state("networkidle")
                         time.sleep(2) # brief pause after sort
                    except Exception as e:
                         print(f"  [UI Warning] Could not click sort button (selector might need updating): {e}")

                    # Retrieve the HTML DOM state
                    html_content = page.content()
                    
                    # DOM Parsing using BeautifulSoup
                    soup = BeautifulSoup(html_content, "html.parser")
                    
                    # Notebook: Generic CSS selector placeholders
                    bid_cards = soup.select("div.bid-card")
                    print(f"  Found {len(bid_cards)} bid cards on the page.")
                    
                    for card in bid_cards:
                        try:
                            # Use generic placeholder selectors that the dev can update easily later via inspection
                            bid_number_elem = card.select_one("span.bid-number")
                            
                            if not bid_number_elem:
                                continue # Invalid card if no bid number
                                
                            bid_number = bid_number_elem.text.strip()
                            
                            # The Break Logic: Short-Circuit Incremental Scraping
                            # Open a quick session just for checking
                            with SessionLocal() as check_session:
                                if check_bid_exists(bid_number, check_session):
                                    print(f"  [Short-Circuit] Bid '{bid_number}' already exists. Breaking loop for keyword '{keyword}' to save resources.")
                                    break # Exit the bid cards loop immediately, moving to the next keyword
                            
                            dept_elem = card.select_one("span.department")
                            items_elem = card.select_one("span.items")
                            value_elem = card.select_one("span.estimated-value")
                            emd_elem = card.select_one("span.emd-amount")
                            date_elem = card.select_one("span.end-date")
                            mii_elem = card.select_one("span.mii-flag")
                            mse_elem = card.select_one("span.mse-flag")
                            
                            # Dictionary holding current bid state
                            bid_data = {
                                'gem_bid_number': bid_number,
                                'department_name': dept_elem.text.strip() if dept_elem else None,
                                'item_categories': [i.strip() for i in items_elem.text.split(",")] if items_elem else [],
                                'estimated_value': parse_float(value_elem.text.strip()) if value_elem else None,
                                'emd_amount': parse_float(emd_elem.text.strip()) if emd_elem else None,
                                'bid_end_date': parse_date(date_elem.text.strip()) if date_elem else None,
                                'mii_applicable': True if mii_elem and "Yes" in mii_elem.text else False,
                                'mse_preference': True if mse_elem and "Yes" in mse_elem.text else False
                            }
                            
                            # Append successfully parsed bid Dict
                            scraped_data.append(bid_data)
                            
                        except Exception as e:
                            # Try-except block around individual bids so script doesn't crash on slightly broken HTML
                            print(f"  [Error] Failed to parse a bid card for '{keyword}': {e}")
                            continue
                            
                except Exception as e:
                    print(f"  [Error] Failed to scrape page for '{keyword}': {e}")
                
                # Data Handoff step
                if scraped_data:
                    print(f"  -> Extracted {len(scraped_data)} bids. Passing to database manager...")
                    # Open a fresh Database session
                    db = SessionLocal()
                    try:
                        # Call logic from database_manager
                        new_inserts = process_and_save_bids(scraped_data, db)
                        print(f"  Saved {new_inserts} NEW bids to the database.")
                    except Exception as e:
                        db.rollback()
                        print(f"  [DB Error] Failed to save bids: {e}")
                    finally:
                        # Close DB Session
                        db.close()
                else:
                    print(f"  -> No data parsed for keyword: {keyword}")

        print("\nAll brand keywords scraped successfully.")
        browser.close()

if __name__ == "__main__":
    run_scraper()
