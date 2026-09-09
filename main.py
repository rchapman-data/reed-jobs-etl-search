"""
main.py

Orchestrates the full pipeline:
1. Extract enriched job data from the Reed API
2. Transform each raw job into our document schema
3. Store in MongoDB (with a small CRUD demonstration)
4. Export everything currently in MongoDB to a JSON file
5. Upload that JSON file to S3

Run from the project root:
    py main.py
"""

from src.extract import get_enriched_jobs
from src.mongo_client import (
    build_job_document,
    insert_many_jobs,
    get_job_by_id,
    get_all_jobs,
    update_job_salary,
    delete_job,
)
from src.export import export_jobs_to_json
from src.upload_s3 import upload_file_to_s3

# Sensible defaults, used only if the user presses Enter without typing
# anything at the prompts below.
DEFAULT_KEYWORDS = ["data analyst", "data engineer", "BI analyst"]
DEFAULT_LOCATION = "London"
RESULTS_TO_FETCH = 100


def run_pipeline(search_keywords, search_location, results_to_fetch):
    all_documents = []

    for keyword in search_keywords:
        print(f"Searching Reed for '{keyword}' jobs in '{search_location}'...")
        raw_jobs = get_enriched_jobs(keyword, search_location, results_to_fetch)
        print(f"Retrieved {len(raw_jobs)} enriched job records for '{keyword}'.\n")

        documents = [
            build_job_document(job, keyword, search_location) for job in raw_jobs
        ]
        all_documents.extend(documents)

    inserted, skipped = insert_many_jobs(all_documents)
    print(f"MongoDB insert: {inserted} new, {skipped} skipped (likely duplicates).\n")

    return all_documents


def demonstrate_crud(sample_job_id):
    """Runs through Read, Update, Delete on one job to prove CRUD works end to end."""
    print(f"--- CRUD demonstration on job_id={sample_job_id} ---")

    # Read
    job = get_job_by_id(sample_job_id)
    print(f"Read: {job.get('title')} | salary: {job.get('salary')}")

    # Update
    modified_count = update_job_salary(sample_job_id, new_min=99999, new_max=100000)
    print(f"Update: {modified_count} document(s) modified.")
    updated_job = get_job_by_id(sample_job_id)
    print(f"Read after update: salary now {updated_job.get('salary')}")

    # Delete
    deleted_count = delete_job(sample_job_id)
    print(f"Delete: {deleted_count} document(s) removed.")


if __name__ == "__main__":
    print("Leave blank and press Enter to use the defaults shown.")

    titles_input = input(
        f"Job title(s), comma-separated (default: {', '.join(DEFAULT_KEYWORDS)}): "
    ).strip()
    if titles_input:
        # Split on commas, then strip whitespace from each individual title -
        # e.g. "data analyst, data engineer" -> ["data analyst", "data engineer"]
        search_keywords = [title.strip() for title in titles_input.split(",")]
    else:
        search_keywords = DEFAULT_KEYWORDS

    location_input = input(f"Location (default: {DEFAULT_LOCATION}): ").strip()
    search_location = location_input if location_input else DEFAULT_LOCATION

    print(f"\nSearching for {search_keywords} in '{search_location}'...\n")

    documents = run_pipeline(search_keywords, search_location, RESULTS_TO_FETCH)

    print(f"Total jobs currently in MongoDB: {len(get_all_jobs())}\n")

    if documents:
        # Use the first inserted job to demonstrate Read/Update/Delete
        demonstrate_crud(documents[0]["job_id"])

    # Export whatever remains in MongoDB (after the CRUD demo's delete)
    # to a timestamped JSON file, then back it up to S3.
    print()
    export_path = export_jobs_to_json()
    upload_file_to_s3(export_path)


# """
# main.py

# Orchestrates the full pipeline:
# 1. Extract enriched job data from Reed API
# 2. Transform each raw job into document schema
# 3. Store in MongoDB (with CRUD operations demo)
# 4. Export everything in MongoDB to JSON file
# 5. Upload JSON file to S3

# Run from the project root:
#     py main.py
# """

# from src.extract import get_enriched_jobs
# from src.mongo_client import (
#     build_job_document,
#     insert_many_jobs,
#     get_job_by_id,
#     get_all_jobs,
#     update_job_salary,
#     delete_job,
# )
# from src.export import export_jobs_to_json
# from src.upload_s3 import upload_file_to_s3

# SEARCH_KEYWORDS = ["data analyst", "data engineer", "BI analyst"] ##"data analyst"
# SEARCH_LOCATION = "London"
# RESULTS_TO_FETCH = 100


# # def run_pipeline():
# #     print(f"Searching Reed for '{SEARCH_KEYWORD}' jobs in '{SEARCH_LOCATION}'...")
# #     raw_jobs = get_enriched_jobs(SEARCH_KEYWORD, SEARCH_LOCATION, RESULTS_TO_FETCH)
# #     print(f"Retrieved {len(raw_jobs)} enriched job records from Reed.\n")

# #     documents = [
# #         build_job_document(job, SEARCH_KEYWORD, SEARCH_LOCATION) for job in raw_jobs
# #     ]

# #     inserted, skipped = insert_many_jobs(documents)
# #     print(f"MongoDB insert: {inserted} new, {skipped} skipped (likely duplicates).\n")

# #     return documents

# def run_pipeline():
#     all_documents = []
 
#     for keyword in SEARCH_KEYWORDS:
#         print(f"Searching Reed for '{keyword}' jobs in '{SEARCH_LOCATION}'...")
#         raw_jobs = get_enriched_jobs(keyword, SEARCH_LOCATION, RESULTS_TO_FETCH)
#         print(f"Retrieved {len(raw_jobs)} enriched job records for '{keyword}'.\n")
 
#         documents = [
#             build_job_document(job, keyword, SEARCH_LOCATION) for job in raw_jobs
#         ]
#         all_documents.extend(documents)
 
#     inserted, skipped = insert_many_jobs(all_documents)
#     print(f"MongoDB insert: {inserted} new, {skipped} skipped (likely duplicates).\n")
 
#     return all_documents


# def demonstrate_crud(sample_job_id):
#     """Runs through Read, Update, Delete on one job to prove CRUD works end to end."""
#     print(f"--- CRUD demonstration on job_id={sample_job_id} ---")

#     # Read
#     job = get_job_by_id(sample_job_id)
#     print(f"Read: {job.get('title')} | salary: {job.get('salary')}")

#     # Update
#     modified_count = update_job_salary(sample_job_id, new_min=99999, new_max=100000)
#     print(f"Update: {modified_count} document(s) modified.")
#     updated_job = get_job_by_id(sample_job_id)
#     print(f"Read after update: salary now {updated_job.get('salary')}")

#     # Delete
#     deleted_count = delete_job(sample_job_id)
#     print(f"Delete: {deleted_count} document(s) removed.")


# if __name__ == "__main__":
#     documents = run_pipeline()

#     print(f"Total jobs currently in MongoDB: {len(get_all_jobs())}\n")

#     if documents:
#         # Use the first inserted job to demonstrate Read/Update/Delete
#         demonstrate_crud(documents[0]["job_id"])

#     # Export whatever remains in MongoDB (after the CRUD demo's delete)
#     # to a timestamped JSON file, then back it up to S3.
#     print()
#     export_path = export_jobs_to_json()
#     upload_file_to_s3(export_path)