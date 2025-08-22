import csv
import time
from datetime import datetime
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

# ---------------- CONFIG ----------------
KEYWORDS = [
    "Customer Service", "Sales Associate", "Sales Consultant", "Realtor",
    "Real Estate Agent", "Mortgage Advisor", "Loan Officer", "Insurance Agent",
    "Financial Advisor", "Teacher", "Educator"
]
EXCLUDED_LOCATIONS = ["New York"]
RECENT_DAYS = 21  # activity window in days
CSV_FILE = f"linkedin_us_profiles_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

# -----------------------------------------

def login_to_linkedin(driver):
    print("🔐 Browser is open. Please log in manually.")
    input("✅ Once logged in and redirected to the LinkedIn homepage, press Enter here to start scraping...")

def is_recent_activity(driver, profile_url):
    """Check if the profile has activity in the last RECENT_DAYS days."""
    try:
        driver.get(profile_url + "/recent-activity/")
        time.sleep(3)
        posts = driver.find_elements(By.XPATH, "//span[contains(@class,'update-components-actor__sub-description')]")
        for post in posts:
            text = post.text.lower()
            if any(x in text for x in ["h", "hour", "minute", "day", "week"]):
                if "week" in text:
                    weeks = int(''.join(filter(str.isdigit, text)) or "0")
                    if weeks <= RECENT_DAYS // 7:
                        return True
                elif "day" in text:
                    days = int(''.join(filter(str.isdigit, text)) or "0")
                    if days <= RECENT_DAYS:
                        return True
                else:
                    return True
        return False
    except:
        return False

def matches_filters(name, headline, location):
    """Check location and keyword filters."""
    if not location or "united states" not in location.lower():
        return False
    if any(ex.lower() in location.lower() for ex in EXCLUDED_LOCATIONS):
        return False
    if not any(kw.lower() in (headline or "").lower() for kw in KEYWORDS):
        return False
    return True

def scrape_search_results(driver, start_page, end_page):
    results = []
    for page in range(start_page, end_page + 1):
        print(f"🔎 Scraping page {page}")
        driver.get(f"https://www.linkedin.com/search/results/people/?page={page}")
        time.sleep(4)

        # Save raw HTML for debugging before filtering
        with open(f"debug_page_{page}.html", "w", encoding="utf-8") as dbg:
            dbg.write(driver.page_source)
        print(f"    💾 Saved raw HTML to debug_page_{page}.html")

        profiles = driver.find_elements(By.XPATH, "//li[contains(@class,'reusable-search__result-container')]")
        print(f"  ➕ Found {len(profiles)} profiles on page {page}")

        for prof in profiles:
            try:
                name_el = prof.find_element(By.XPATH, ".//span[@dir='ltr']")
                headline_el = prof.find_element(By.CLASS_NAME, "entity-result__primary-subtitle")
                location_el = prof.find_element(By.CLASS_NAME, "entity-result__secondary-subtitle")
                link_el = prof.find_element(By.TAG_NAME, "a")

                name = name_el.text.strip()
                headline = headline_el.text.strip() if headline_el else ""
                location = location_el.text.strip() if location_el else ""
                profile_url = link_el.get_attribute("href").split("?")[0]

                if matches_filters(name, headline, location):
                    if is_recent_activity(driver, profile_url):
                        print(f"    ✅ Match: {name} ({location})")
                        results.append([name, headline, profile_url, headline])
                    else:
                        print(f"    ⏩ Skipped (no recent activity): {name}")
                else:
                    print(f"    ⏩ Skipped (filters): {name}")

            except Exception as e:
                print("    ⚠️ Error parsing profile:", e)
    return results

def main():
    start_page = int(input("Enter start page (e.g., 1): "))
    end_page = int(input("Enter end page (e.g., 5): "))

    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = uc.Chrome(options=options)

    login_to_linkedin(driver)
    data = scrape_search_results(driver, start_page, end_page)

    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Headline", "LinkedIn URL", "Company/Title"])
        writer.writerows(data)

    print(f"✅ Done. {len(data)} profiles saved to {CSV_FILE}")
    input("Press Enter to close the browser...")
    driver.quit()

if __name__ == "__main__":
    main()

