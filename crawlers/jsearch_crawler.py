import os
import requests
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file

def crawl_jsearch2(keyword: str, location: str = "", num_results: int = 10, country: str = "US", work_from_home: bool = False, job_platform: str = "LinkedIn", rapidapi_key: str = None):
    # Return 3 dummy jobs with keys matching the app's expectations
    dummy_jobs = [
        {
            "title": "Web Developer (m/f/d)",
            "company": "aconium GmbH",
            "location": "Berlin, DE",
            "snippet": "We are currently looking for a Web Developer (m/f/d) for our Berlin office.",
            "url": "https://www.xing.com/jobs/berlin-web-developer-130273527",
            "full_description": "Full description for Web Developer (m/f/d) at aconium GmbH in Berlin."
        },
        {
            "title": "Java Entwickler:in (m/w/d)",
            "company": "aconium GmbH",
            "location": "Berlin, DE",
            "snippet": "Wir suchen wir ab sofort eine:n Java Entwickler:in (m/w/d) zur Unterstützung.",
            "url": "https://www.xing.com/jobs/berlin-java-entwickler-137546218",
            "full_description": "Full description for Java Entwickler:in (m/w/d) at aconium GmbH in Berlin."
        },
        {
            "title": "Full-stack engineer (TS, React, Node)",
            "company": "Feather",
            "location": "Berlin, DE",
            "snippet": "We are looking for a full-stack engineer to join our product team at Feather.",
            "url": "https://www.xing.com/jobs/berlin-full-stack-engineer-ts-react-node-feather-130614098",
            "full_description": "Full description for Full-stack engineer (TS, React, Node) at Feather in Berlin."
        }
    ]
    return dummy_jobs[:num_results]

def crawl_jsearch(keyword: str, location: str = "", num_results: int = 10, country: str = "US", work_from_home: bool = False, job_platform: str = "LinkedIn", rapidapi_key: str = None):
    if rapidapi_key is None:
        rapidapi_key = os.getenv("RAPIDAPI_KEY", "")
        print("RapidAPI Key:", rapidapi_key)
    base_url = "https://jsearch.p.rapidapi.com/search"
    # Build query string to include location and job platform if provided
    if location:
        query = f"{keyword} in {location} via {job_platform}"
    else:
        query = f"{keyword} via {job_platform}"
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
    results = crawl_jsearch("Software Engineer", "New York", num_results=3, country="us", work_from_home=True, job_platform="LinkedIn")
    for job in results:
        print(job)
