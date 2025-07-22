import os
import requests
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

def crawl_jsearch(keyword: str, location: str = "", num_results: int = 10, country: str = "US", work_from_home: bool = False, rapidapi_key: str = None):
    if rapidapi_key is None:
        rapidapi_key = os.getenv("RAPIDAPI_KEY", "")
        print("RapidAPI Key:", rapidapi_key)
    base_url = "https://jsearch.p.rapidapi.com/search"
    # Build query string, include location if provided
    if location:
        query = f"{keyword} jobs in {location}"
    else:
        query = f"{keyword} jobs"
    params = {
        "query": query,
        "page": 1,
        "num_pages": 1,
        "results_per_page": num_results,
        "country": country.lower(),
        "date_posted": "all",
        "work_from_home": str(work_from_home).lower()
    }
    full_url = base_url + "?" + requests.compat.urlencode(params)
    headers = {
        "content-type": "application/json",
        "X-RapidAPI-Key": rapidapi_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    response = requests.get(full_url, headers=headers)
    response.raise_for_status()
    data = response.json()
    jobs = []
    for item in data.get("data", []):
        job = {
            "title": item.get("job_title"),
            "company": item.get("employer_name", ""),
            "location": ", ".join(filter(None, [item.get("job_city", ""), item.get("job_country", "")])),
            "snippet": (item.get("job_description", "")[:100] + "...") if item.get("job_description") else "No snippet available.",
            "url": item.get("job_apply_link", ""),
            "full_description": item.get("job_description", "No description available.")
        }
        jobs.append(job)
    return jobs

# Example usage
if __name__ == "__main__":
    results = crawl_jsearch("Software Engineer", "New York", num_results=3, country="us", work_from_home=True)
    for job in results:
        print(job)
