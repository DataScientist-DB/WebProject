import csv
import time
from datetime import datetime
from urllib.parse import quote_plus
from typing import Set, List, Tuple


# Customer_Service_updated.py
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ====== CONFIG ======
KEYWORD = "Small Business Owner"
USA_GEO_URN = "103644278"  # United States facet
TS = datetime.now().strftime("%Y%m%d_%H%M%S")
SAFE_KW = KEYWORD.lower().replace(" ", "_")  # Safe for filenames
CSV_BEFORE = f"{SAFE_KW}_us_before_{TS}.csv"
CSV_AFTER  = f"{SAFE_KW}_us_after_{TS}.csv"

LOAD_WAIT_SEC = 20
SCROLL_ROUNDS = 10
SCROLL_PAUSE_SEC = 1.0

# US detection helper: accept US even when “United States” isn’t printed
US_STATE_ABBR = {
    "AL","AK","AZ","AR","CA","CO","CT","DC","DE","FL","GA","HI","IA","ID","IL","IN","KS","KY","LA","MA","MD",
    "ME","MI","MN","MO","MS","MT","NC","ND","NE","NH","NJ","NM","NV","OH","OK","OR","PA","RI","SC","SD","TN",
    "TX","UT","VA","VT","WA","WI","WV","WY","PR","GU","VI"
}
US_STATE_FULL = {
    "alabama","alaska","arizona","arkansas","california","colorado","connecticut","delaware","florida","georgia",
    "hawaii","idaho","illinois","indiana","iowa","kansas","kentucky","louisiana","maine","maryland","massachusetts",
    "michigan","minnesota","mississippi","missouri","montana","nebraska","nevada","new hampshire","new jersey",
    "new mexico","north carolina","north dakota","ohio","oklahoma","oregon","pennsylvania","rhode island",
    "south carolina","south dakota","tennessee","texas","utah","vermont","virginia","washington","west virginia",
    "wisconsin","wyoming","district of columbia","washington, d.c.","washington dc","d.c.","dc"
}
EXCLUDE_TOKENS = {"new york", ", ny", " ny,", " ny "}  # exclude NY by text
MAX_PROFILE_OPENS = 80  # safety cap to avoid opening too many profile tabs
# ====================

def login_to_linkedin(driver):
    driver.get("https://www.linkedin.com/login")
    print("🔐 Log in manually in the browser window.")
    input("✅ When you’re on the LinkedIn home feed, press Enter here to continue...")

def build_search_url(page: int) -> str:
    q = quote_plus(f'"{KEYWORD}"')  # quoted for stable matching
    return (
        "https://www.linkedin.com/search/results/people/"
        f"?keywords={q}"
        "&origin=FACETED_SEARCH"
        f"&geoUrn=%5B%22{USA_GEO_URN}%22%5D"
        f"&page={page}"
    )

def wait_for_results(driver):
    wait = WebDriverWait(driver, LOAD_WAIT_SEC)
    for locator in [
        (By.CSS_SELECTOR, "ul.reusable-search__entity-result-list"),
        (By.XPATH, "//li[contains(@class,'reusable-search__result-container')]"),
        (By.XPATH, "//*[contains(@class,'search-results-container')]"),
    ]:
        try:
            wait.until(EC.presence_of_element_located(locator))
            return
        except:
            continue

def scroll_results(driver):
    last_h = 0
    for _ in range(SCROLL_ROUNDS):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE_SEC)
        new_h = driver.execute_script("return document.body.scrollHeight")
        if new_h == last_h:
            break
        last_h = new_h

def text_safe(root, by, sel) -> str:
    try:
        t = root.find_element(by, sel).text
        return (t or "").strip()
    except:
        return ""

def href_safe(root, by, sel) -> str:
    try:
        h = root.find_element(by, sel).get_attribute("href")
        return (h or "").split("?", 1)[0]
    except:
        return ""

def closest_card(link_el):
    # climb to a stable container around the profile link
    for xp in [
        "./ancestor::li[contains(@class,'reusable-search__result-container')][1]",
        "./ancestor::div[contains(@class,'reusable-search__result-container')][1]",
        "./ancestor::div[contains(@class,'entity-result')][1]",
        "./ancestor::li[1]",
        "./ancestor::div[1]",
    ]:
        try:
            return link_el.find_element(By.XPATH, xp)
        except:
            continue
    return None

def location_is_us_not_ny(location_text: str) -> bool:
    if not location_text:
        return False
    loc = location_text.lower()

    # Exclude New York explicitly
    for bad in EXCLUDE_TOKENS:
        if bad in loc:
            return False

    # Accept if explicitly mentions US
    if "united states" in loc or "u.s." in loc or "usa" in loc:
        return True

    # Accept if contains state full name (except New York, handled above)
    for st in US_STATE_FULL:
        if st in loc:
            if st == "new york":
                return False
            return True

    # Accept if ends with a state abbreviation like ", CA"
    if ", " in loc:
        abbr = loc.split(",")[-1].strip().upper()
        if abbr in US_STATE_ABBR and abbr != "NY":
            return True

    return False

def headline_or_name_has_kw(headline: str, name: str) -> bool:
    kw = KEYWORD.lower()
    return (kw in (headline or "").lower()) or (kw in (name or "").lower())

def open_profile_and_scrape(driver, url: str) -> Tuple[str, str, str]:
    """Open profile in a background tab; scrape name/headline/location from top card."""
    try:
        driver.execute_script("window.open(arguments[0], '_blank');", url)
        driver.switch_to.window(driver.window_handles[-1])
        WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(3)

        # Name
        name = ""
        for sel in [
            (By.CSS_SELECTOR, "h1"),
            (By.CSS_SELECTOR, "div.ph5 h1"),
            (By.CSS_SELECTOR, "[data-test-profile-card-headline] h1"),
        ]:
            name = text_safe(driver, *sel)
            if name: break

        # Headline
        headline = ""
        for sel in [
            (By.CSS_SELECTOR, "div.text-body-medium.break-words"),
            (By.CSS_SELECTOR, "div.text-body-medium"),
            (By.XPATH, "//div[contains(@class,'pv-text-details__left-panel')]/div[1]"),
        ]:
            headline = text_safe(driver, *sel)
            if headline: break

        # Location
        location = ""
        for sel in [
            (By.CSS_SELECTOR, "span.text-body-small.inline.t-black--light.break-words"),
            (By.XPATH, "//span[contains(@class,'text-body-small') and contains(.,',')]"),
            (By.XPATH, "//div[contains(@class,'pv-text-details__left-panel')]//span[contains(@class,'text-body-small')]"),
        ]:
            location = text_safe(driver, *sel)
            if location: break

        # Close the tab and return
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return name, headline, location

    except Exception:
        try:
            if len(driver.window_handles) > 1:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
        except:
            pass
        return "", "", ""

def scrape_pages(driver, start_page: int, end_page: int):
    seen_all: Set[str] = set()
    seen_after: Set[str] = set()
    rows_before: List[List[str]] = []
    rows_after:  List[List[str]] = []
    opened = 0

    for page in range(start_page, end_page + 1):
        url = build_search_url(page)
        print(f"🔎 Page {page}: {url}")
        driver.get(url)
        wait_for_results(driver)
        scroll_results(driver)

        # all /in/ links on the page
        links = driver.find_elements(By.XPATH, "//a[contains(@href,'/in/')]")
        print(f"   ➕ Raw /in/ links: {len(links)}")

        for link in links:
            profile_url = (link.get_attribute("href") or "").split("?", 1)[0]
            if not profile_url or "/in/" not in profile_url:
                continue
            if profile_url in seen_all:
                continue

            card = closest_card(link)

            # Try to scrape from the card
            name, headline, location = "", "", ""
            if card:
                # name
                for sel in [
                    (By.CSS_SELECTOR, "span.entity-result__title-text a span[aria-hidden='true']"),
                    (By.XPATH, ".//span[@dir='ltr']"),
                ]:
                    name = text_safe(card, *sel)
                    if name: break
                # headline
                for sel in [
                    (By.CSS_SELECTOR, "div.entity-result__primary-subtitle"),
                    (By.CSS_SELECTOR, "div.t-14.t-normal.t-black"),
                ]:
                    headline = text_safe(card, *sel)
                    if headline: break
                # location
                for sel in [
                    (By.CSS_SELECTOR, "div.entity-result__secondary-subtitle"),
                    (By.CSS_SELECTOR, "div.t-12.t-normal.t-black--light"),
                    (By.CSS_SELECTOR, "span[data-anonymize='location']"),
                ]:
                    location = text_safe(card, *sel)
                    if location: break

            # If missing key bits, open profile (bounded)
            if (not location or not headline) and opened < MAX_PROFILE_OPENS:
                opened += 1
                pn, ph, pl = open_profile_and_scrape(driver, profile_url)
                name = pn or name
                headline = ph or headline
                location = pl or location

            # Add to BEFORE CSV (raw capture)
            rows_before.append([name, headline, profile_url, headline, location])
            seen_all.add(profile_url)

            # Apply filters for AFTER CSV
            if not location_is_us_not_ny(location):
                continue
            if not headline_or_name_has_kw(headline, name):
                continue

            if profile_url not in seen_after:
                rows_after.append([name, headline, profile_url, headline, location])
                seen_after.add(profile_url)

    return rows_before, rows_after

def main():
    start_page = int(input("Enter start page (e.g., 1): ").strip())
    end_page   = int(input("Enter end page (e.g., 5): ").strip())

    options = Options()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)  # Selenium Manager fetches driver automatically

    login_to_linkedin(driver)
    rows_before, rows_after = scrape_pages(driver, start_page, end_page)

    # Save BEFORE (raw) CSV
    with open(CSV_BEFORE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Headline", "LinkedIn URL", "Company/Title", "Location"])
        writer.writerows(rows_before)

    # Save AFTER (filtered) CSV
    with open(CSV_AFTER, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Headline", "LinkedIn URL", "Company/Title", "Location"])
        writer.writerows(rows_after)

    print(f"\n✅ BEFORE CSV: {CSV_BEFORE} ({len(rows_before)} rows)")
    print(f"✅ AFTER  CSV: {CSV_AFTER}  ({len(rows_after)} rows)")
    input("Press Enter to close the browser...")
    driver.quit()

if __name__ == "__main__":
    main()
