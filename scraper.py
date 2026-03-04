import time
import random
import re
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from config import TARGET_KEYWORDS
from models import SessionLocal
from database_manager import process_and_save_bids, check_bid_exists

GEM_SEARCH_URL = "https://bidplus.gem.gov.in/all-bids"

def parse_date(date_str):
    try:
        date_str = date_str.replace('\xa0', ' ').replace('\n', ' ').strip()
        # Try multiple GeM date formats
        for fmt in ["%d-%m-%Y %I:%M %p", "%d-%m-%Y %H:%M"]:
            try:
                return datetime.strptime(date_str, fmt)
            except Exception:
                continue
        return None
    except Exception:
        return None

def scrape_keyword(page, keyword):
    """Search GeM for keyword and return parsed bid cards."""
    try:
        page.goto(GEM_SEARCH_URL, wait_until="domcontentloaded")
        time.sleep(2)

        # Fill the search box (id="searchBid" on all-bids page)
        page.wait_for_selector("input#searchBid", timeout=8000)
        page.fill("input#searchBid", "")
        page.fill("input#searchBid", keyword)
        time.sleep(0.3)
        # Press Enter to trigger search (most reliable cross-browser method)
        page.press("input#searchBid", "Enter")

        # Wait for results to load - check either results or "no records" message
        try:
            page.wait_for_function(
                """
                document.querySelectorAll('#pagi_content .card').length > 0 ||
                document.querySelector('#pagi_content') !== null
                """,
                timeout=12000
            )
        except Exception:
            pass

        time.sleep(2)  # Buffer for full AJAX render

        # Try to click Sort -> "Bid Start Date: Latest First"
        try:
            sort_btn = page.query_selector(".sort button, button.sort, .sort-dropdown button")
            if sort_btn:
                sort_btn.click()
                time.sleep(0.8)
                page.click("text=Bid Start Date: Latest First")
                time.sleep(2)
        except Exception as e:
            pass  # Sort failed silently - still proceed

        html = page.content()

        # Debug: Check what's in #pagi_content
        soup = BeautifulSoup(html, "html.parser")
        container = soup.select_one("#pagi_content")
        if container:
            cards = container.select(".card")
            print(f"  [Debug] #pagi_content found. .card inside: {len(cards)}")
            if len(cards) == 0:
                # Print snippet of container to understand structure
                snippet = container.text.strip()[:200]
                print(f"  [Debug] Container snippet: {snippet}")
        else:
            print(f"  [Debug] #pagi_content NOT found in HTML!")
            # Save HTML for inspection
            with open("debug_last_page.html", "w", encoding="utf-8") as f:
                f.write(html)
            print(f"  [Debug] Saved debug_last_page.html for inspection")

        return soup, container

    except Exception as e:
        print(f"  [Nav Error] {e}")
        return None, None

def run_scraper():
    print("Initializing Playwright scraper...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        for brand, keywords in TARGET_KEYWORDS.items():
            print(f"\n--- Brand: {brand} ---")
            for keyword in keywords:
                print(f"  Searching: '{keyword}'")
                scraped_data = []

                soup, results_container = scrape_keyword(page, keyword)
                if not results_container:
                    print(f"  -> No results container found, skipping.")
                    continue

                bid_cards = results_container.select(".card")
                print(f"  Found {len(bid_cards)} bid cards.")

                for card in bid_cards:
                    try:
                        card_text = card.get_text(separator=" ", strip=True)

                        # Extract Bid Number
                        bid_match = re.search(r"GEM/\d{4}/[BR]/\d+", card_text)
                        if not bid_match:
                            print(f"    [Skip] No bid number in card: {card_text[:80]}")
                            continue
                        bid_number = bid_match.group(0).strip()
                        print(f"    Processing: {bid_number}")

                        # Skip duplicates
                        with SessionLocal() as check_session:
                            if check_bid_exists(bid_number, check_session):
                                print(f"    [Dup] Already in DB")
                                continue

                        # End Date
                        end_date_elem = card.select_one(".end_date")
                        if end_date_elem:
                            bid_end_date = parse_date(end_date_elem.get_text(strip=True))
                        else:
                            # Try regex fallback
                            end_match = re.search(r"End Date:\s*(\d{2}-\d{2}-\d{4}\s+\d+:\d+\s*[AP]M)", card_text)
                            bid_end_date = parse_date(end_match.group(1)) if end_match else None

                        # Skip expired bids
                        if bid_end_date and bid_end_date < datetime.now():
                            print(f"    [Expired] {bid_end_date.strftime('%d %b %Y')}")
                            continue

                        # Items
                        items_match = re.search(r"Items:\s*(.+?)(?:Quantity:|Department Name|$)", card_text, re.DOTALL)
                        items_text = items_match.group(1).strip()[:200] if items_match else keyword

                        # Department
                        dept_match = re.search(r"Department Name And Address:\s*(.+?)(?:Start Date:|$)", card_text, re.DOTALL)
                        dept_text = dept_match.group(1).strip()[:300] if dept_match else "N/A"

                        scraped_data.append({
                            'gem_bid_number': bid_number,
                            'department_name': dept_text,
                            'item_categories': [items_text],
                            'estimated_value': None,
                            'emd_amount': None,
                            'bid_end_date': bid_end_date,
                            'mii_applicable': "MII" in card_text,
                            'mse_preference': "MSE" in card_text
                        })

                    except Exception as e:
                        print(f"    [Card Error] {e}")
                        continue

                if scraped_data:
                    db = SessionLocal()
                    try:
                        new_inserts = process_and_save_bids(scraped_data, db)
                        print(f"  -> Saved {new_inserts} NEW bids to DB.")
                    except Exception as e:
                        db.rollback()
                        print(f"  [DB Error] {e}")
                    finally:
                        db.close()
                else:
                    print(f"  -> No new bids to save for: '{keyword}'")

                time.sleep(random.uniform(1.5, 2.5))

        print("\nAll brands scraped.")
        browser.close()

if __name__ == "__main__":
    run_scraper()
