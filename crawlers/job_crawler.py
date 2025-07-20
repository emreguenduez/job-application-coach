from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
from urllib.robotparser import RobotFileParser
import ssl  # Add this import if missing

def init_driver():
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    return driver

def is_url_allowed(url: str, user_agent: str = "*") -> bool:
    # Bypass SSL certificate verification
    ssl._create_default_https_context = ssl._create_unverified_context
    rp = RobotFileParser()
    rp.set_url(url.rsplit("/", 1)[0] + "/robots.txt")
    rp.read()
    return rp.can_fetch(user_agent, url)

def crawl_indeed(keyword: str, location: str = "", num_results: int = 10, ignore_robots: bool = False):
    driver = init_driver()
    base_url = "https://www.indeed.com/jobs"
    url = f"{base_url}?q={keyword}&l={location}"
    if not ignore_robots and not is_url_allowed(url):
        driver.quit()
        raise RuntimeError("Crawling disallowed by robots.txt on Indeed")
    driver.get(url)
    time.sleep(3)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    # ...adjust selectors as necessary...
    job_cards = soup.find_all("div", class_="jobsearch-SerpJobCard")
    results = []
    for card in job_cards[:num_results]:
        title_elem = card.find("h2", class_="title")
        company_elem = card.find("span", class_="company")
        location_elem = card.find("div", class_="location") or card.find("span", class_="location")
        job_url_elem = title_elem.find("a") if title_elem else None
        job = {
            "title": title_elem.text.strip() if title_elem else None,
            "company": company_elem.text.strip() if company_elem else None,
            "location": location_elem.text.strip() if location_elem else None,
            "url": f"https://www.indeed.com{job_url_elem['href']}" if job_url_elem and job_url_elem.get("href") else None,
        }
        results.append(job)
    driver.quit()
    return results

def crawl_linkedin(keyword: str, location: str = "", num_results: int = 10):
    # IMPORTANT: LinkedIn's robots.txt explicitly disallows automated crawling.
    # Do not run this function without obtaining explicit permission from LinkedIn.
    raise RuntimeError("Automated crawling of LinkedIn is prohibited by its robots.txt. Please obtain permission.")

if __name__ == "__main__":
    print("Indeed Jobs:")
    indeed_jobs = crawl_indeed("Software Engineer", "New York", num_results=3)
    for job in indeed_jobs:
        print(job)

    # Uncomment only if permission is granted for LinkedIn crawling:
    # print("\nLinkedIn Jobs:")
    # linkedin_jobs = crawl_linkedin("Software Engineer", "New York", num_results=3)
    # for job in linkedin_jobs:
    #     print(job)
