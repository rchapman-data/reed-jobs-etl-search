"""
extract.py

Handles all communication with Reed Jobseeker API.
Responsible for:
- Searching for jobs by keyword/location
- Fetching full details for a given job ID

Auth model:  API key is sent as  *username*; empty password.

"""

import os
import requests
from dotenv import load_dotenv

# Load variables from .env into the environment (e.g. REED_API_KEY)
load_dotenv()

API_KEY = os.getenv("REED_API_KEY")
BASE_URL = "https://www.reed.co.uk/api/1.0"


def search_jobs(keywords, location_name, results_to_take=20):
    """
    Search Reed for jobs matching the given keywords and location.

    Args:
        keywords (str): search term, e.g. "data analyst"
        location_name (str): location, e.g. "London"
        results_to_take (int): how many results to return (max 100 per Reed's docs)

    Returns:
        list[dict]: list of job summary dicts as returned by Reed, or [] on failure
    """
    if not API_KEY:
        raise ValueError("REED_API_KEY not found. Check your .env file.")

    url = f"{BASE_URL}/search"
    params = {
        "keywords": keywords,
        "locationName": location_name,
        "resultsToTake": results_to_take,
    }

    try:
        response = requests.get(url, params=params, auth=(API_KEY, ""))
        response.raise_for_status()  # raises an exception for 4xx/5xx responses
        data = response.json()
        return data.get("results", [])
    except requests.exceptions.RequestException as e:
        print(f"[search_jobs] Request failed: {e}")
        return []


def get_job_details(job_id):
    """
    Fetch full details for a single job by ID.

    Args:
        job_id (int): the Reed job ID (from a search result's 'jobId' field)

    Returns:
        dict | None: full job details, or None on failure
    """
    if not API_KEY:
        raise ValueError("REED_API_KEY not found. Check .env file.")

    url = f"{BASE_URL}/jobs/{job_id}"

    try:
        response = requests.get(url, auth=(API_KEY, ""))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"[get_job_details] Request failed for job {job_id}: {e}")
        return None


def get_enriched_jobs(keywords, location_name, results_to_take=20):
    """
    Two-stage extraction: search for jobs, then fetch full details for each one.
    Lightweight "list" endpoint and a richer "detail" endpoint.

    Args:
        keywords (str): search term, e.g. "data analyst"
        location_name (str): location, e.g. "London"
        results_to_take (int): how many search results to enrich

    Returns:
        list[dict]: enriched job detail dicts, skipping any that failed
    """
    search_results = search_jobs(keywords, location_name, results_to_take)
    enriched_jobs = []

    for job in search_results:
        job_id = job.get("jobId")
        details = get_job_details(job_id)
        if details:
            enriched_jobs.append(details)
        else:
            print(f"[get_enriched_jobs] Skipping job {job_id} - details unavailable")

    return enriched_jobs


if __name__ == "__main__":
    # manual test: confirms both endpoints work together end to end
    jobs = get_enriched_jobs(keywords="data analyst", location_name="London", results_to_take=5)
    print(f"Fetched {len(jobs)} enriched jobs")
    for job in jobs:
        print(
            f"- {job.get('jobTitle')} @ {job.get('employerName')} | "
            f"{job.get('salaryType')} | {job.get('contractType')} | expires {job.get('expirationDate')}"
        )