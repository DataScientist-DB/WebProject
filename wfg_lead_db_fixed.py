import csv
import os
import time
import pickle
import random
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup

# ========================
# CONFIGURATION
# ========================
EXCLUDE_CITY = "New York"
US_KEYWORDS = ["united states", "usa"]
START_PAGE = int(input("Enter start page (e.g., 1): "))
END_PAGE = int(input("Enter end page (max 100): "))
BATCH_SIZE = 5  # pages per session to reduce detection

OUTPUT_CSV = f"linkedin_open_to_work_p{START_PAGE}_to_p{END_PAGE}.csv"
ALL_PROFILES_CSV = f"linkedin_all_profiles_p{START_PAGE}_to_p{END_PAGE}.csv"
COOKIES_FILE = "linkedin_cookies.pkl"

# ========================
# FUNCTIONS
# ========================
def start_driver():
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = uc.Chrome(options=options)
    return driver

def save_cookies(driver):
    pickle.dump(driver.get_cookies(), open(COOKIES_FILE, "wb"))

def load_cookies(driver):
    driver.get("https://www.linkedin.com/")
    time.sleep(3)
    cookies = pickle.load(open(COOKIES_FILE, "rb"))
    for cookie in cookies:
        driver.add_cookie(cookie)
    driver.refresh()
    time.sleep(5)

def ensure_logged_in(driver):
    """Ensure manual login is complete and cookies saved."""
    if os.path.exists(COOKIES_FILE):
        print("✅ Loading cookies...")
        load_cookies(driver)

    driver.get("https://www.linkedin.com/feed/")
    time.sleep(5)

    if "login" in driver.current_url or "checkpoint" in driver.current_url:
        print("⚠ Manual login required. Please log in completely...")
        print("➡ After login, navigate to your feed, then press ENTER here.")
        input()
        save_cookies(driver)
        print("✅ Cookies saved for future sessions.")
    else:
        print("✅ Logged in successfully!")

def human_like_scroll(driver):
    """Simulate human scrolling to trigger lazy load."""
    for _ in range(random.randint(4, 6)):
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.PAGE_DOWN)
        time.sleep(random.uniform(1.5, 3.0))
    time.sleep(random.uniform(2, 4))

US_KEYWORDS = [
    "united states", "usa", "u.s.", "california", "texas", "dc", "washington",
    "los angeles", "san francisco", "new jersey", "boston", "chicago", "illinois",
    "florida", "remote", "greater"
]

def is_us_location(location: str) -> bool:
    if not location or location.lower() == "unknown":
        return False
    loc = location.lower()
    return any(key in loc for key in US_KEYWORDS)


def scan_search_page(driver, page_number, processed_urls):
    search_url = f"https://www.linkedin.com/search/results/people/?geoUrn=%5B%22103644278%22%5D&page={page_number}"
    driver.get(search_url)
    print(f"🔹 Scanning search results on page {page_number}...")
    time.sleep(random.uniform(5, 7))

    human_like_scroll(driver)

    page_all_urls = []
    page_open_urls = []

    soup = BeautifulSoup(driver.page_source, "lxml")
    # Flexible profile card matching: includes 'search' and 'result' in class name
    profile_links = soup.find_all("a", href=True)
    cards = []

    for link in profile_links:
        if "/in/" in link["href"]:
            parent_li = link.find_parent("li")
            if parent_li and parent_li not in cards:
                cards.append(parent_li)

    # Save debug HTML regardless of profile detection
    debug_filename = f"debug_page_{page_number}.html"
    with open(debug_filename, "w", encoding="utf-8") as f:
        f.write(driver.page_source)
        print(f"💾 Debug HTML saved: {debug_filename}")

    # Check for cards
    if not cards:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(f"debug_page_{timestamp}.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"⚠️ No cards found. Saved HTML to debug_page_{timestamp}.html")

        print(f"⚠ No profiles detected on page {page_number}.")

    for idx, card in enumerate(cards, 1):
        link = card.find("a", href=True)
        if not link or "/in/" not in link["href"]:
            print(f"⚠️ Card {idx}: No valid profile link found.")
            print(card.prettify()[:500])  # Print trimmed HTML for inspection
            continue

        url = link["href"].split("?")[0]
        if url in processed_urls or url in page_all_urls:
            continue

        card_html = str(card).lower()
        open_to_work = (
            "open to work" in card_html
            or "opentowork" in card_html
            or 'alt="open to work"' in card_html
        )

        page_all_urls.append(url)
        if open_to_work:
            page_open_urls.append(url)
            print(f"  ✅ Found Open-to-Work: {url}")
        else:
            print(f"  ❌ No Open-to-Work badge: {url}")

    return page_all_urls, page_open_urls

def get_profile_data(driver, url):
    driver.get(url)
    human_like_scroll(driver)

    try:
        name = driver.find_element(By.XPATH, "//h1").text.strip()
    except:
        name = "Unknown"
    try:
        headline = driver.find_element(By.XPATH, "//div[contains(@class,'text-body-medium')]").text.strip()
    except:
        headline = "Unknown"
    try:
        location = driver.find_element(By.XPATH, "//span[contains(@class,'text-body-small')]").text.strip()
    except:
        location = "Unknown"

    return name, headline, location

# ========================
# STEP 1: Prepare CSV files
# ========================
if not os.path.exists(OUTPUT_CSV):
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Headline", "Location", "LinkedIn URL"])
    open_to_work_results = []
else:
    with open(OUTPUT_CSV, "r", encoding="utf-8") as f:
        open_to_work_results = list(csv.reader(f))[1:]

if not os.path.exists(ALL_PROFILES_CSV):
    with open(ALL_PROFILES_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Headline", "Location", "LinkedIn URL", "OpenToWork"])
    all_profiles_results = []
else:
    with open(ALL_PROFILES_CSV, "r", encoding="utf-8") as f:
        all_profiles_results = list(csv.reader(f))[1:]

processed_urls = {row[3] for row in all_profiles_results}

# ========================
# STEP 2: Process in batches
# ========================
current_page = START_PAGE

while current_page <= END_PAGE:
    batch_end = min(current_page + BATCH_SIZE - 1, END_PAGE)
    print(f"\n=== Starting batch {current_page}-{batch_end} ===")

    driver = start_driver()
    ensure_logged_in(driver)

    batch_all_urls = []
    batch_open_urls = []

    for page in range(current_page, batch_end + 1):
        page_all, page_open = scan_search_page(driver, page, processed_urls)
        batch_all_urls.extend(page_all)
        batch_open_urls.extend(page_open)

    for idx, url in enumerate(batch_all_urls, 1):
        if url in processed_urls:
            continue

        name, headline, location = get_profile_data(driver, url)
        is_open = url in batch_open_urls
        is_us = is_us_location(location)

        all_profiles_results.append([name, headline, location, url, "Yes" if is_open else "No"])

        print(f"    └─ Open: {is_open}, US: {is_us}, Location: {location}")

        if is_open and is_us and EXCLUDE_CITY.lower() not in location.lower():
            open_to_work_results.append([name, headline, location, url])
            print(f"[{idx}/{len(batch_all_urls)}] ✅ Saved Open-to-Work: {name} | {headline} | {location}")
        else:
            print(f"[{idx}/{len(batch_all_urls)}] ❌ Non-qualified or Excluded: {name}")

        processed_urls.add(url)

        with open(ALL_PROFILES_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "Headline", "Location", "LinkedIn URL", "OpenToWork"])
            writer.writerows(all_profiles_results)

        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "Headline", "Location", "LinkedIn URL"])
            writer.writerows(open_to_work_results)

    driver.quit()
    current_page = batch_end + 1
    time.sleep(random.uniform(20, 35))  # cooldown

print(f"\n🎉 Scraping completed.")
print(f"  • {len(open_to_work_results)} Open-to-Work leads saved to {OUTPUT_CSV}")
print(f"  • {len(all_profiles_results)} total profiles saved to {ALL_PROFILES_CSV}")
