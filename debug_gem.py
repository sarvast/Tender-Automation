"""
Quick debug: fetches a real search result page and shows exactly 
what the first 3 div.card elements contain.
"""
import time
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from datetime import datetime

keyword = "Ventilator"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    url = f"https://bidplus.gem.gov.in/all-bids?searchBid=Ventilator"
    print(f"Navigating to: {url}")
    page.goto(url, wait_until="domcontentloaded")
    time.sleep(5)
    
    html = page.content()
    
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.card")
    print(f"\nTotal div.card elements: {len(cards)}")
    print("="*70)
    
    for i, card in enumerate(cards[:5]):
        print(f"\n--- Card #{i+1} ---")
        text = card.text.strip()[:300]
        print(f"Text snippet: {text}")
        
        bid_match = re.search(r"GEM/\d{4}/[BR]/\d+", card.text)
        print(f"Bid number found: {bid_match.group(0) if bid_match else 'NONE'}")
        
        end_date_elem = card.select_one(".end_date")
        print(f".end_date element: {end_date_elem.text.strip() if end_date_elem else 'NOT FOUND'}")
        
        bid_no_elem = card.select_one(".bid_no")
        print(f".bid_no element: {bid_no_elem.text.strip() if bid_no_elem else 'NOT FOUND'}")
        print("-"*70)
    
    browser.close()
    print("\nDone!")
