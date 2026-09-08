"""
semantic_search.py

Adds semantic search on top of jobs already stored in MongoDB. Does
two things:

1. embed_all_jobs() - generates embedding for every job that doesn't
   already have one, saves it back onto that document.
2. semantic_search(query) - given a plain-text search, finds jobs
   whose embeddings are closest in meaning to query.

Run directly to embed all jobs:
    py -m src.semantic_search
"""

import numpy as np
from sentence_transformers import SentenceTransformer
from src.mongo_client import get_collection

MODEL = SentenceTransformer("all-MiniLM-L6-v2")


def build_embedding_text(job):
 
    title = job.get("title") or ""
    description = job.get("description") or ""
    return f"{title}. {description}"


def embed_all_jobs():
    """
    Generate and store embedding for every job in MongoDB that doesn't
    already have one. Already embedded jobs are skipped.
    """
    collection = get_collection()

    # Only fetch jobs that don't have an "embedding" field yet
    jobs_to_embed = list(collection.find({"embedding": {"$exists": False}}))
    print(f"Found {len(jobs_to_embed)} job(s) without an embedding.")

    for job in jobs_to_embed:
        text = build_embedding_text(job)
        embedding = MODEL.encode(text)

        collection.update_one(
            {"_id": job["_id"]},
            {"$set": {"embedding": embedding.tolist()}},
        )

    print(f"Embedded {len(jobs_to_embed)} job(s).")


def cosine_similarity(vec_a, vec_b):
    """measure of how aligned two vectors are, from -1 to 1."""
    return np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b))


def semantic_search(query, top_n=5):
    """
    Find the jobs whose stored embeddings are most similar in meaning
    to query text.

    Args:
        query (str): a plain-text search, e.g. "role involving dashboards"
        top_n (int): how many top matches to return

    Returns:
        list[dict]: the top_n matching job documents, each with a
            'similarity_score' field added, sorted highest first
    """
    collection = get_collection()
    query_embedding = MODEL.encode(query)

    jobs = list(collection.find({"embedding": {"$exists": True}}))

    scored_jobs = []
    for job in jobs:
        score = cosine_similarity(query_embedding, np.array(job["embedding"]))
        job["similarity_score"] = float(score)
        scored_jobs.append(job)

    scored_jobs.sort(key=lambda j: j["similarity_score"], reverse=True)

    return scored_jobs[:top_n]


if __name__ == "__main__":
    embed_all_jobs()

    example_queries = [
        "role involving dashboards and reporting",
        "entry level role working with data pipelines",
    ]

    for query in example_queries:
        print(f"\n--- Semantic search: '{query}' ---")
        results = semantic_search(query, top_n=3)
        for job in results:
            print(f"{job['similarity_score']:.3f} | {job.get('title')} @ {job.get('employer', {}).get('name')}")