"""
semantic_search_faiss.py

Uses FAISS (vector search library) instead of cosine similarity loop.

Technically not required for this project, but demonstrates how semantic 
search would be built to scale to a much larger dataset.

Only the actual search mechanism changes.

Run directly:
    py -m src.semantic_search_faiss
"""

import numpy as np
import faiss

from src.semantic_search_s3 import load_jobs_from_s3, embed_jobs, MODEL


def build_faiss_index(jobs):
    """
    Build a FAISS index from a list of already-embedded jobs.

    Returns:
        tuple: (index, jobs) - the FAISS index, and the same jobs list
            (kept alongside the index so we can map result positions
            back to actual job documents)
    """
   
    embeddings_matrix = np.array([job["embedding"] for job in jobs]).astype("float32")

    dimension = embeddings_matrix.shape[1]

    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings_matrix)

    return index, jobs


def semantic_search_faiss(query, index, jobs, top_n=5):
    """
    Search a pre-built FAISS index for the jobs most similar to the query.

    Args:
        query (str): plain-text search
        index (faiss.Index): an index already built via build_faiss_index()
        jobs (list[dict]): the same jobs list the index was built from,
            in the same order - needed to map result positions back to
            actual job documents
        top_n (int): how many top matches to return

    Returns:
        list[dict]: the top_n matching jobs, each with 'similarity_score' added
    """
    query_embedding = MODEL.encode(query).astype("float32").reshape(1, -1)

    # FAISS returns: 1) the similarity scores, 2) POSITIONS
    # (row numbers) of the closest matches in the original embeddings_matrix
    scores, positions = index.search(query_embedding, top_n)

    results = []
    for score, position in zip(scores[0], positions[0]):
        job = jobs[position]
        job["similarity_score"] = float(score)
        results.append(job)

    return results


if __name__ == "__main__":
    jobs = load_jobs_from_s3()
    print(f"Loaded {len(jobs)} jobs from S3 export.")

    jobs = embed_jobs(jobs)
    print("Computed embeddings in memory.")

    index, jobs = build_faiss_index(jobs)
    print(f"Built FAISS index with {index.ntotal} vectors.\n")

    example_queries = [
        "role involving dashboards and reporting",
        "entry level role working with data pipelines",
    ]

    for query in example_queries:
        print(f"--- FAISS semantic search: '{query}' ---")
        results = semantic_search_faiss(query, index, jobs, top_n=3)
        for job in results:
            print(f"{job['similarity_score']:.3f} | {job.get('title')} @ {job.get('employer', {}).get('name')}")
        print()