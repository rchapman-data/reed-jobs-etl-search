"""
search_app.py

A simple terminal interface tying together exact/filter search
(filter_search.py) and semantic/meaning-based search (semantic_search.py).

Run:
    py -m src.search_app
"""

from src.filter_search import filter_search
from src.semantic_search import semantic_search


def print_job(job, show_score=False):
    salary = job.get("salary", {})
    line = f"- {job.get('title')} @ {job.get('employer', {}).get('name')} | {job.get('location')} | {salary}"
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

    results = semantic_search(query, top_n=5)

    print(f"\nTop {len(results)} closest matches:")
    for job in results:
        print_job(job, show_score=True)


def main():
    print("=== Reed Jobs Search ===")
    print("1. Exact/filter search (location, salary, contract type, role)")
    print("2. Semantic search (describe what you're looking for)")
    choice = input("Choose 1 or 2: ").strip()

    if choice == "1":
        run_exact_search()
    elif choice == "2":
        run_semantic_search()
    else:
        print("Please enter 1 or 2.")


if __name__ == "__main__":
    main()