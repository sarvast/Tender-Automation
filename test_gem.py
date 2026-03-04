from playwright.sync_api import sync_playwright

def test_gem():
    print("Testing GeM...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page.goto("https://bidplus.gem.gov.in/all-bids", wait_until="networkidle")
        html = page.content()
        with open("gem_test.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("Done. Wrote gem_test.html")
        browser.close()

if __name__ == "__main__":
    test_gem()
