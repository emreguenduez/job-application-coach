from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
from urllib.robotparser import RobotFileParser
import ssl

import streamlit as st
import base64
import os

# Import crawl_jsearch from jsearch_crawler.py
import sys
sys.path.append(os.path.dirname(__file__))
from jsearch_crawler import crawl_jsearch

def init_driver():
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    return driver

def is_url_allowed(url: str, user_agent: str = "*") -> bool:
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
    raise RuntimeError("Automated crawling of LinkedIn is prohibited by its robots.txt. Please obtain permission.")

def preview_pdf(pdf_bytes):
    """
    Display a PDF preview in Streamlit.
    """
    try:
        st.header("CV Preview")
        st.pdf(pdf_bytes)
    except AttributeError:
        b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        pdf_display = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)

def main():
    st.title("Job Application Coach")
    st.write("Search for jobs and generate your CV!")

    # Get job listings from jsearch_crawler.py
    jobs = crawl_jsearch(keyword="developer", location="Berlin", num_results=3, country="de", work_from_home=False, job_platform="XING")

    st.subheader("Job Listings")
    for job in jobs:
        title = job.get("title") or job.get("job_title")
        company = job.get("company") or job.get("employer_name")
        location = job.get("location") or job.get("job_location")
        url = job.get("url") or job.get("job_apply_link")
        st.markdown(f"**{title}** at {company} ({location})  \n[Job Link]({url})")

    st.subheader("CV Generator")
    if st.button("Generate CV"):
        sample_pdf_path = os.path.join(os.path.dirname(__file__), "sample_cv.pdf")
        if os.path.exists(sample_pdf_path):
            with open(sample_pdf_path, "rb") as f:
                pdf_bytes = f.read()
            with st.expander("Preview Generated CV", expanded=True):
                preview_pdf(pdf_bytes)
            st.success("CV generated and previewed below!")
            st.download_button("Download CV PDF", pdf_bytes, "cv.pdf", "application/pdf")
        else:
            st.error("sample_cv.pdf not found. Please add a sample PDF for preview.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Indeed Jobs:")
        indeed_jobs = crawl_indeed("Software Engineer", "New York", num_results=3)
        for job in indeed_jobs:
            print(job)
