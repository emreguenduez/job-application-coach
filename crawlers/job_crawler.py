from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
from urllib.robotparser import RobotFileParser

def init_driver():
    # Initialize headless Chrome driver
    options = Options()
    options.add_argument("--headless")
    # Add additional options as needed
    driver = webdriver.Chrome(options=options)
    return driver

# New: function to load and check robots.txt for Indeed
def is_url_allowed(url: str, user_agent: str = "*") -> bool:
    rp = RobotFileParser()
    rp.set_url("https://www.indeed.com/robots.txt")
    rp.read()
    return rp.can_fetch(user_agent, url)

def crawl_indeed(keyword: str, location: str = "", num_results: int = 10):
    driver = init_driver()
    
    # Base URL – ensure to check indeed's robots.txt & TOS
    url = f"https://www.indeed.com/jobs?q={keyword}&l={location}"
    
    # Check if URL is allowed by robots.txt
    if not is_url_allowed(url):
        driver.quit()
        raise RuntimeError("Crawling disallowed by robots.txt")
    
    driver.get(url)
    
    # Wait for dynamic content to load (this may need adjustments)
    time.sleep(3)
    
    # Parse page with BeautifulSoup
    soup = BeautifulSoup(driver.page_source, "html.parser")
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

# Example usage
if __name__ == "__main__":
    listings = crawl_indeed("Software Engineer", "New York", num_results=5)
    for job in listings:
        print(job)
