import time
import random
import re
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from config import TARGET_KEYWORDS

# IMPORTANT: Change this URL to your Azure VM IP/domain once hosted
API_BASE_URL = "http://20.197.14.33:8080"
GEM_SEARCH_URL = "https://bidplus.gem.gov.in/all-bids"

# Only accept bids whose start date is within this many days (skip very old bids)
MAX_BID_AGE_DAYS = 30  # Change to 7 if you want only last 7 days

# Keywords that indicate the bid is likely NOT related to medical/lab equipment
RELEVANCE_EXCLUSIONS = [
    "mobile phone", "smartphone", "smart phone", "furniture", "vehicle", "car", 
    "truck", "cleaning service", "clothing", "uniform", "stationery", "android",
    "tablet", "laptop", "computer", "cctv", "camera", "printer", "toner",
    "hand held", "handheld", "rugged", "set", "phone"
]


def is_relevant_bid(items_text, card_text, keyword):
    """Checks if the bid is relevant to medical/lab equipment."""
    items_lower = items_text.lower()
    card_lower = card_text.lower()
    keyword_lower = keyword.lower()
    
    # Check for explicit exclusions
    for exclusion in RELEVANCE_EXCLUSIONS:
        if exclusion in items_lower or exclusion in card_lower:
            return False
            
    # Positive relevance check: must be related to medical, lab, or clinical fields
    # or match one of our keyword categories (passed via items_text)
    relevant_terms = [
        "analyzer", "medical", "laboratory", "clinical", "hospital", "healthcare",
        "ventilator", "diagnostic", "blood", "chemistry", "pathology", "test kit",
        "imaging", "scan", "x-ray", "patient monitor", "surgical", "pharmaceutical",
        keyword_lower
    ]
    
    if any(term in items_lower for term in relevant_terms):
        return True
    if any(term in card_lower for term in relevant_terms):
        return True
        
    return False

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
    """Search GeM for keyword. Returns (soup_of_first_page, list_of_ALL_bid_cards from all pages)."""
    all_cards = []
    try:
        page.goto(GEM_SEARCH_URL, wait_until="domcontentloaded")
        time.sleep(2)

        # Fill the search box
        page.wait_for_selector("input#searchBid", timeout=8000)
        page.fill("input#searchBid", "")
        page.fill("input#searchBid", keyword)
        time.sleep(0.3)
        page.click("#searchBidRA")

        try:
            page.wait_for_selector("#bidCard .card", timeout=12000)
            
            # Ensure "Ongoing Bids" is checked
            ongoing_checkbox = page.query_selector("#ongoing_bids")
            if ongoing_checkbox and not ongoing_checkbox.is_checked():
                ongoing_checkbox.check()
                time.sleep(2)
                page.wait_for_selector("#bidCard .card", timeout=8000)
        except Exception:
            pass

        time.sleep(2)

        # Sort by Bid Start Date Latest First
        try:
            page.wait_for_selector("#currentSort", state="visible", timeout=5000)
            page.click("#currentSort", force=True)
            time.sleep(1.5)
            page.wait_for_selector("#Bid-Start-Date-Latest", state="visible", timeout=5000)
            page.click("#Bid-Start-Date-Latest", force=True)
            time.sleep(5)
            page.wait_for_selector("#bidCard .card", timeout=12000)
            print("  [Sort] Applied 'Bid Start Date: Latest First' successfully.")
        except Exception as e:
            print(f"  [Sort Warning] Could not apply sort: {e}")

        # --- PAGINATION: Collect all pages ---
        page_num = 1
        while True:
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            container = soup.select_one("#bidCard")
            
            if container:
                cards = container.select(".card")
                print(f"  [Page {page_num}] Found {len(cards)} bid cards.")
                all_cards.extend(cards)
            else:
                print(f"  [Page {page_num}] #bidCard NOT found.")
                break

            # Try to click the "Next" pagination button
            try:
                next_btn = page.query_selector("li.page-item:not(.disabled) a[aria-label='Next']")
                if next_btn:
                    next_btn.click()
                    time.sleep(3)
                    page.wait_for_selector("#bidCard .card", timeout=10000)
                    page_num += 1
                    if page_num > 5:  # Safety cap: max 5 pages per keyword
                        print("  [Pagination] Reached max 5 pages, stopping.")
                        break
                else:
                    print(f"  [Pagination] No more pages after page {page_num}.")
                    break
            except Exception as e:
                print(f"  [Pagination] Stop: {e}")
                break

        return soup, all_cards

    except Exception as e:
        print(f"  [Nav Error] {e}")
        return None, []

def run_scraper():
    print("Initializing Playwright scraper...")
    
    # --- HEARTBEAT: Tell backend we are alive ---
    try:
        requests.post(f"{API_BASE_URL}/api/heartbeat", timeout=5)
        print("[Heartbeat] Pinged backend successfully.")
    except Exception as e:
        print(f"[Heartbeat] Could not reach backend: {e}")

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

                soup, bid_cards = scrape_keyword(page, keyword)
                if not bid_cards:
                    print(f"  -> No results found, skipping.")
                    continue

                print(f"  Total cards to process: {len(bid_cards)}")  

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
                        
                        # Document URL (Link to PDF)
                        doc_link_elem = card.select_one("a[href^='/showbidDocument/']")
                        if doc_link_elem:
                            doc_url = "https://bidplus.gem.gov.in" + doc_link_elem['href']
                        else:
                            doc_url = None

                        # Check if bid exists via API (Optional future enhancement)
                        # For now, the API backend will handle deduplication gracefully

                        # Start Date
                        start_date_elem = card.select_one(".start_date")
                        if start_date_elem:
                            bid_start_date = parse_date(start_date_elem.get_text(strip=True))
                        else:
                            start_match = re.search(r"Start Date:\s*(\d{2}-\d{2}-\d{4}\s+\d+:\d+\s*[AP]M)", card_text)
                            bid_start_date = parse_date(start_match.group(1)) if start_match else None

                        # End Date
                        end_date_elem = card.select_one(".end_date")
                        if end_date_elem:
                            bid_end_date = parse_date(end_date_elem.get_text(strip=True))
                        else:
                            # Try regex fallback
                            end_match = re.search(r"End Date:\s*(\d{2}-\d{2}-\d{4}\s+\d+:\d+\s*[AP]M)", card_text)
                            bid_end_date = parse_date(end_match.group(1)) if end_match else None

                        # Skip expired bids
                        if not bid_end_date:
                            print(f"    [Skip] Could not parse End Date for {bid_number}")
                            continue

                        if bid_end_date < datetime.now():
                            print(f"    [Expired] {bid_end_date.strftime('%d %b %Y')}")
                            continue

                        # Items
                        items_elem = card.select_one("div.bid_item_desc a")
                        items_text = items_elem.get_text(strip=True) if items_elem else keyword
                        
                        # Full text of the card for broader relevance check
                        full_card_text = card.get_text(separator=" ", strip=True)

                        # Relevance Check
                        if not is_relevant_bid(items_text, full_card_text, keyword):
                            print(f"    [Irrelevant] Skipping {bid_number} - ({items_text[:50]}...)")
                            continue


                        # Department
                        dept_match = re.search(r"Department Name And Address:\s*(.+?)(?:Start Date:|$)", card_text, re.DOTALL)
                        dept_text = dept_match.group(1).strip()[:300] if dept_match else "N/A"
                        
                        # EMD Amount
                        emd_match = re.search(r"EMD Amount\s*:\s*Rs\.?\s*([\d,]+(?:\.\d+)?)", card_text, re.IGNORECASE)
                        if emd_match:
                            emd_str = emd_match.group(1).replace(",", "")
                            try:
                                emd_amount = float(emd_str)
                            except:
                                emd_amount = None
                        else:
                            emd_amount = None

                        # Quantity
                        qty_match = re.search(r"(?:Quantity|Qty)\s*:\s*([\d,]+)", card_text, re.IGNORECASE)
                        if qty_match:
                            qty_str = qty_match.group(1).replace(",", "")
                            quantity = int(qty_str) if qty_str.isdigit() else 1
                        else:
                            quantity = 1
                            
                        print(f"    Extracted Qty: {quantity}")

                        # --- DATE FILTER: Skip bids that are too old ---
                        if bid_start_date is not None:
                            age_days = (datetime.now() - bid_start_date).days
                            if age_days > MAX_BID_AGE_DAYS:
                                print(f"    [Skip] Bid too old ({age_days} days): {bid_number}")
                                continue

                        scraped_data.append({
                            'gem_bid_number': bid_number,
                            'department_name': dept_text,
                            'category': brand,
                            'item_categories': [items_text],
                            'quantity': quantity,
                            'estimated_value': None,
                            'emd_amount': emd_amount,
                            'bid_start_date': bid_start_date,
                            'bid_end_date': bid_end_date,
                            'mii_applicable': "MII" in card_text,
                            'mse_preference': "MSE" in card_text,
                            'document_url': doc_url
                        })

                    except Exception as e:
                        print(f"    [Card Error] {e}")
                        continue

                if scraped_data:
                    # Send data to FastAPI backend instead of local SQLite
                    try:
                        # Convert datetime objects to ISO strings for JSON serialization
                        for item in scraped_data:
                            if item['bid_start_date']:
                                item['bid_start_date'] = item['bid_start_date'].isoformat()
                            if item['bid_end_date']:
                                item['bid_end_date'] = item['bid_end_date'].isoformat()
                                
                        response = requests.post(
                            f"{API_BASE_URL}/api/tenders/upload",
                            json={"bids": scraped_data},
                            timeout=10
                        )
                        
                        if response.status_code == 200:
                            api_response = response.json()
                            print(f"  -> API Upload Success: Saved {api_response.get('inserted', 0)} NEW bids to DB via HTTP.")
                        else:
                            print(f"  [API Error] Status {response.status_code}: {response.text}")
                    except requests.exceptions.RequestException as e:
                        print(f"  [Network Error] Could not reach API backend: {e}")
                else:
                    print(f"  -> No new bids to save for: '{keyword}'")

                time.sleep(random.uniform(1.5, 2.5))

        print("\nAll brands scraped.")
        browser.close()

if __name__ == "__main__":
    run_scraper()
