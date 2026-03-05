import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

def test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://bidplus.gem.gov.in/all-bids", wait_until="domcontentloaded")
        time.sleep(3)
        
        page.wait_for_selector("#searchBid", timeout=10000)
        page.fill("#searchBid", "monitor")
        page.click("#searchBidRA")
        
        page.wait_for_selector("#bidCard .card", timeout=10000)
        time.sleep(2)
        
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        card = soup.select_one(".card")
        
        if card:
            # Print physical HTML tags string
            html_snippet = str(card)
            print("--- HTML ---")
            print(html_snippet[:1500])
            
            # Print text
            text = card.get_text(separator=" | ", strip=True)
            print("\n--- TEXT ---")
            print(text)
        else:
            print("No card found")
            
        browser.close()

if __name__ == "__main__":
    test()
