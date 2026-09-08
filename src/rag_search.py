"""
rag_search.py

RAG (Retrieval-Augmented Generation). Sits on top of the existing 
semantic search.

Run directly: py -m src.rag_search
"""

import os
from dotenv import load_dotenv
import anthropic

from src.semantic_search_s3 import load_jobs_from_s3, embed_jobs, semantic_search

load_dotenv()

API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL_NAME = "claude-haiku-4-5-20251001"

client = anthropic.Anthropic(api_key=API_KEY)


def build_context(jobs):
    """
    Turn a list of retrieved job documents into a plain-text block,
    to insert into a prompt as background information.
    """
    lines = []
    for job in jobs:
        salary = job.get("salary", {})
        lines.append(
            f"- {job.get('title')} at {job.get('employer', {}).get('name')} "
            f"({job.get('location')}), salary: {salary.get('min')}-{salary.get('max')} "
            f"{salary.get('currency')}, contract: {job.get('contract_type')}"
        )
    return "\n".join(lines)


def rag_answer(question, jobs, top_n=5):
    """
    Answer a question using retrieval-augmented generation.
 
    Args:
        question (str): a natural-language question about the job data
        jobs (list[dict]): jobs already embedded via embed_jobs()
        top_n (int): how many jobs to retrieve

    Returns:
        str: the LLM's answer
    """
    if not API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not found. Check your .env file.")

    relevant_jobs = semantic_search(question, jobs, top_n=top_n)
    context = build_context(relevant_jobs)

    prompt = (
        "Here are some relevant job postings:\n\n"
        f"{context}\n\n"
        f"Question: {question}\n\n"
        "Answer using only the information in the job postings above. "
        "If the postings don't contain enough information to answer, say so."
        "Make a joke about the job market at the end of your answer."
    )

    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text


if __name__ == "__main__":
    jobs = load_jobs_from_s3()
    print(f"Loaded {len(jobs)} jobs from S3 export.")

    jobs = embed_jobs(jobs)
    print("Computed embeddings in memory.\n")

    example_questions = [
        "Which companies are hiring for remote roles?",
        "What are the top 3 highest-paying data analyst jobs in London?",
    ]

    # example_questions = [
    #     "What's the typical salary range for BI-focused roles, and which company pays the most?",
    #     "Are there any permanent, entry-level data roles available?",
    # ]

    for question in example_questions:
        print(f"--- Question: {question} ---")
        answer = rag_answer(question, jobs)
        print(answer)
        print()