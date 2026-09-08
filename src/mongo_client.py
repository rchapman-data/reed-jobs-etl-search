"""
mongo_client.py

Handles all MongoDB interaction: connection setup and CRUD operations
on the 'jobs' collection.
"""

import os
from datetime import datetime, timezone
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "reed_etl"
COLLECTION_NAME = "jobs"


def get_collection():
    """
    Create a MongoDB client and return the jobs collection.

    Returns:
        pymongo.collection.Collection
    """
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client[DB_NAME]
    return db[COLLECTION_NAME]


def build_job_document(raw_job, search_keyword, search_location):
    """
    Transform a raw Reed job-details dict into our own document shape:
    nested 'employer' and 'salary' sub-documents, plus metadata about
    how/when this record was collected.

    Args:
        raw_job (dict): the enriched job dict from extract.get_enriched_jobs
        search_keyword (str): the keyword used to find this job
        search_location (str): the location used to find this job

    Returns:
        dict: a document ready to insert into MongoDB
    """
    return {
        "_id": f"reed_job_{raw_job.get('jobId')}",
        "job_id": raw_job.get("jobId"),
        "title": raw_job.get("jobTitle"),
        "employer": {
            "id": raw_job.get("employerId"),
            "name": raw_job.get("employerName"),
        },
        "description": raw_job.get("jobDescription"),
        "location": raw_job.get("locationName"),
        "salary": {
            "min": raw_job.get("minimumSalary"),
            "max": raw_job.get("maximumSalary"),
            "currency": raw_job.get("currency"),
            "type": raw_job.get("salaryType"),
        },
        "contract_type": raw_job.get("contractType"),
        "job_type": raw_job.get("jobType"),
        "expiration_date": raw_job.get("expirationDate"),
        "url": raw_job.get("jobUrl"),
        "search_keyword": search_keyword,
        "search_location": search_location,
        "date_scraped": datetime.now(timezone.utc).isoformat(),
    }


# ---------- CRUD operations ----------

def insert_job(document):
    """Create: insert a single job document. Skips if _id already exists."""
    collection = get_collection()
    try:
        collection.insert_one(document)
        return True
    except PyMongoError as e:
        # Duplicate _id (job already scraped before) or other write error
        print(f"[insert_job] Failed to insert {document.get('_id')}: {e}")
        return False


def insert_many_jobs(documents):
    """Create: bulk insert, skipping duplicates rather than failing the whole batch."""
    collection = get_collection()
    inserted, skipped = 0, 0
    for doc in documents:
        if insert_job(doc):
            inserted += 1
        else:
            skipped += 1
    return inserted, skipped


def get_job_by_id(job_id):
    """Read: fetch a single job document by its Reed job_id."""
    collection = get_collection()
    return collection.find_one({"job_id": job_id})


def get_all_jobs(filter_query=None):
    """Read: fetch all job documents matching an optional filter."""
    collection = get_collection()
    return list(collection.find(filter_query or {}))


def update_job_salary(job_id, new_min, new_max):
    """Update: change the salary range for a given job."""
    collection = get_collection()
    result = collection.update_one(
        {"job_id": job_id},
        {"$set": {"salary.min": new_min, "salary.max": new_max}},
    )
    return result.modified_count


def delete_job(job_id):
    """Delete: remove a job document by its Reed job_id."""
    collection = get_collection()
    result = collection.delete_one({"job_id": job_id})
    return result.deleted_count


if __name__ == "__main__":
    # Quick manual test of the connection - just confirms Mongo is reachable
    try:
        collection = get_collection()
        count = collection.count_documents({})
        print(f"Connected to MongoDB. '{COLLECTION_NAME}' currently has {count} documents.")
    except PyMongoError as e:
        print(f"Could not connect to MongoDB: {e}")