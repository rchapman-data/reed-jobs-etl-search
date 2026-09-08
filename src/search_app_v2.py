"""
search_app_v2.py

Version 2 of search_app.py.

On top of original exact/filter and manual cosine similarity searches, adds:
    - FAISS-based semantic search
    - RAG: natural language questioning, grounded in retrieved jobs
    - Menu loop, so program doesn't need to be re-run after every search

Kept as a separate file from search_app.py so original version stays
intact and added functionality is easier to see.

Run:
    py -m src.search_app_v2

"""

from src.filter_search import filter_search
from src.semantic_search_s3 import semantic_search, load_jobs_from_s3, embed_jobs
from src.semantic_search_faiss import build_faiss_index, semantic_search_faiss
from src.rag_search import rag_answer


def format_salary(salary):
    """Turn a salary dict into a short, readable string instead of a raw dict."""
    min_salary = salary.get("min")
    max_salary = salary.get("max")
    currency = salary.get("currency") or ""
    salary_type = salary.get("type") or ""

    if min_salary is None and max_salary is None:
        return "salary not listed"

    if min_salary == max_salary:
        amount = f"{currency} {min_salary:,.0f}"
    else:
        amount = f"{currency} {min_salary:,.0f}-{max_salary:,.0f}"

    return f"{amount} {salary_type}".strip()


def print_job(job, show_score=False):
    salary_text = format_salary(job.get("salary", {}))
    line = f"- {job.get('title')} @ {job.get('employer', {}).get('name')} | {job.get('location')} | {salary_text}"
    if show_score:
        line = f"[{job.get('similarity_score'):.3f}] " + line
    print(line)


def run_exact_search():
    print("\nLeave any field blank to skip that filter.")
    location = input("Location (e.g. London): ").strip() or None
    contract_type = input("Contract type (e.g. Permanent): ").strip() or None
    role = input("Role (e.g. data analyst): ").strip() or None
    min_salary_input = input("Minimum salary (e.g. 40000): ").strip()
    min_salary = int(min_salary_input) if min_salary_input else None

    results = filter_search(
        location=location,
        contract_type=contract_type,
        role=role,
        min_salary=min_salary,
    )

    print(f"\n{len(results)} result(s):")
    for job in results[:10]:
        print_job(job)


def run_semantic_search():
    query = input("\nDescribe the kind of role you're looking for: ").strip()
    if not query:
        print("No query entered.")
        return

    print("Loading and embedding jobs from the latest S3 export...")
    jobs = load_jobs_from_s3()
    jobs = embed_jobs(jobs)

    results = semantic_search(query, jobs, top_n=5)

    print(f"\nTop {len(results)} closest matches:")
    for job in results:
        print_job(job, show_score=True)


def run_semantic_search_faiss():
    query = input("\nDescribe the kind of role you're looking for: ").strip()
    if not query:
        print("No query entered.")
        return

    print("Loading and embedding jobs from the latest S3 export...")
    jobs = load_jobs_from_s3()
    jobs = embed_jobs(jobs)

    print("Building FAISS index...")
    index, jobs = build_faiss_index(jobs)

    results = semantic_search_faiss(query, index, jobs, top_n=5)

    print(f"\nTop {len(results)} closest matches (via FAISS):")
    for job in results:
        print_job(job, show_score=True)


def run_rag_search():
    question = input("\nAsk a question about the available jobs: ").strip()
    if not question:
        print("No question entered.")
        return

    print("Loading and embedding jobs from the latest S3 export...")
    jobs = load_jobs_from_s3()
    jobs = embed_jobs(jobs)

    print("Thinking...\n")
  
    answer = rag_answer(question, jobs, top_n=50)
    print(answer)


def main():
    print("=== Reed Jobs Search ===")

    while True:
        print("\n1. Exact/filter search (location, salary, contract type, role)")
        print("2. Semantic search - manual cosine similarity (describe what you're looking for)")
        print("3. Semantic search - FAISS index (same as #2, different search engine)")
        print("4. Ask a question (RAG - generates a real answer from the data)")
        print("5. Quit")
        choice = input("Choose 1-5: ").strip()

        if choice == "1":
            run_exact_search()
        elif choice == "2":
            run_semantic_search()
        elif choice == "3":
            run_semantic_search_faiss()
        elif choice == "4":
            run_rag_search()
        elif choice == "5":
            print("Goodbye!")
            break
        else:
            print("Please enter 1, 2, 3, 4, or 5.")


if __name__ == "__main__":
    main()
