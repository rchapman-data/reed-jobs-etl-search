"""
semantic_search.py

Adds semantic (meaning-based) search on top of the jobs data.
Loads data from the latest S3 export.

Run directly to try a couple of example searches:
    py -m src.semantic_search
"""

import os
import json
import numpy as np
import boto3
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

BUCKET_NAME = os.getenv("AWS_S3_BUCKET")
REGION = os.getenv("AWS_REGION", "eu-west-2")

MODEL = SentenceTransformer("all-MiniLM-L6-v2")


def download_latest_export(local_path="data/latest_export.json"):
    """
    Find the most recently uploaded export in the S3 bucket's exports/
    folder, and download it locally.

    Returns:
        str: the local path the file was downloaded to
    """
    s3_client = boto3.client("s3", region_name=REGION)

    response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix="exports/")
    objects = response.get("Contents", [])

    if not objects:
        raise FileNotFoundError("No exports found in S3 bucket under 'exports/'.")

    # Each object has a 'LastModified' timestamp - pick the newest one
    latest = max(objects, key=lambda obj: obj["LastModified"])
    latest_key = latest["Key"]

    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    s3_client.download_file(BUCKET_NAME, latest_key, local_path)

    print(f"Downloaded s3://{BUCKET_NAME}/{latest_key} to {local_path}")
    return local_path


def load_jobs_from_s3():
    """
    Download the latest S3 export and load it as a list of job dicts.
    """
    local_path = download_latest_export()
    with open(local_path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_embedding_text(job):
    """Combine title + description into one string to represent a job's meaning."""
    title = job.get("title") or ""
    description = job.get("description") or ""
    return f"{title}. {description}"


def embed_jobs(jobs):
    """
    Compute an embedding for every job in the given list, in memory.
    Returns the same list with an 'embedding' field added to each job.
    """
    for job in jobs:
        text = build_embedding_text(job)
        job["embedding"] = MODEL.encode(text)
    return jobs


def cosine_similarity(vec_a, vec_b):
    """Standard measure of how aligned two vectors are, from -1 to 1."""
    return np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b))


def semantic_search(query, jobs, top_n=5):
    """
    Find the jobs whose embeddings are most similar in meaning to the query.

    Args:
        query (str): plain-text search, e.g. "role involving dashboards"
        jobs (list[dict]): jobs already embedded via embed_jobs()
        top_n (int): how many top matches to return

    Returns:
        list[dict]: the top_n matching jobs, each with 'similarity_score' added
    """
    query_embedding = MODEL.encode(query)

    for job in jobs:
        score = cosine_similarity(query_embedding, job["embedding"])
        job["similarity_score"] = float(score)

    jobs_sorted = sorted(jobs, key=lambda j: j["similarity_score"], reverse=True)
    return jobs_sorted[:top_n]


if __name__ == "__main__":
    jobs = load_jobs_from_s3()
    print(f"Loaded {len(jobs)} jobs from S3 export.")

    jobs = embed_jobs(jobs)
    print("Computed embeddings in memory.\n")

    example_queries = [
        "role involving dashboards and reporting",
        "entry level role working with data pipelines",
    ]

    for query in example_queries:
        print(f"--- Semantic search: '{query}' ---")
        results = semantic_search(query, jobs, top_n=3)
        for job in results:
            print(f"{job['similarity_score']:.3f} | {job.get('title')} @ {job.get('employer', {}).get('name')}")
        print()