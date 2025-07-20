import os
import requests

def crawl_careerjet(keyword: str, location: str = "", num_results: int = 10, publisher: str = None):
    # Use the Careerjet publisher key from env if not provided
    if publisher is None:
        publisher = os.getenv("CAREERJET_PUBLISHER", "YOUR_PUBLISHER_KEY")
    api_url = "http://public.api.careerjet.net/search"
    params = {
        "locale_code": "en_US",
        "keywords": keyword,
        "location": location,
        "page": 1,
        "page_size": num_results,
        "publisher": publisher,
    }
    resp = requests.get(api_url, params=params)
    resp.raise_for_status()  # Raise for HTTP errors
    data = resp.json()
    jobs = []
    for item in data.get("hits", []):
        job = {
            "title": item.get("title"),
            "company": item.get("company", ""),
            "location": item.get("location", ""),
            "snippet": item.get("summary", "No snippet available."),
            "url": item.get("url"),
            "full_description": item.get("description", "No description available."),
        }
        jobs.append(job)
    return jobs

# Example usage
if __name__ == "__main__":
    results = crawl_careerjet("Software Engineer", "New York", num_results=3)
    for job in results:
        print(job)
