"""
search_app_v2.py

Version 2 of search_app.py.

On top of original exact/filter and manual cosine similarity searches, adds:
    - FAISS-based semantic search
    - RAG: natural language questioning, grounded in retrieved jobs
    - Menu loop, so program doesn't need to be re-run after every search
    - Coloured / more readable terminal output (icons, coloured scores,
      coloured prompts/headers)

Kept as a separate file from search_app.py so original version stays
intact and added functionality is easier to see.

Run:
    py -m src.search_app_v2
"""

from src.filter_search import filter_search
from src.semantic_search_s3 import semantic_search, load_jobs_from_s3, embed_jobs
from src.semantic_search_faiss import build_faiss_index, semantic_search_faiss
from src.rag_search import rag_answer


# ANSI escape codes for coloured terminal text.
class Color:
    TITLE = "\033[1;36m"      # bold cyan
    PROMPT = "\033[33m"       # yellow
    SCORE = "\033[32m"        # green
    DIM = "\033[2m"           # dim/grey
    RESET = "\033[0m"         # reset back to normal


def colored(text, color):
    return f"{color}{text}{Color.RESET}"


def print_header(text):
    print(colored(f"\n=== {text} ===", Color.TITLE))


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
    title = job.get("title")
    employer = job.get("employer", {}).get("name")
    location = job.get("location")
    salary_text = format_salary(job.get("salary", {}))

    line = f"💼 {title} @ {employer} | 📍 {location} | 💰 {salary_text}"

    if show_score:
        score = job.get("similarity_score", 0)
        score_text = colored(f"[{score:.3f}]", Color.SCORE)
        print(f"{score_text} {line}")
    else:
        print(line)


def run_exact_search():
    print_header("🔍 Exact / Filter Search")
    print(colored("Leave any field blank to skip that filter.", Color.DIM))
    location = input(colored("Location (e.g. London): ", Color.PROMPT)).strip() or None
    contract_type = input(colored("Contract type (e.g. Permanent): ", Color.PROMPT)).strip() or None
    role = input(colored("Role (e.g. data analyst): ", Color.PROMPT)).strip() or None
    min_salary_input = input(colored("Minimum salary (e.g. 40000): ", Color.PROMPT)).strip()
    min_salary = int(min_salary_input) if min_salary_input else None

    results = filter_search(
        location=location,
        contract_type=contract_type,
        role=role,
        min_salary=min_salary,
    )

    if results:
        print(colored(f"\n✅ {len(results)} result(s):", Color.TITLE))
    else:
        print(colored("\n❌ No results found.", Color.TITLE))

    for job in results[:10]:
        print_job(job)


def run_semantic_search():
    print_header("🧠 Semantic Search (manual cosine similarity)")
    query = input(colored("Describe the kind of role you're looking for: ", Color.PROMPT)).strip()
    if not query:
        print("No query entered.")
        return

    print(colored("Loading and embedding jobs from the latest S3 export...", Color.DIM))
    jobs = load_jobs_from_s3()
    jobs = embed_jobs(jobs)

    results = semantic_search(query, jobs, top_n=5)

    print(colored(f"\n✅ Top {len(results)} closest matches:", Color.TITLE))
    for job in results:
        print_job(job, show_score=True)


def run_semantic_search_faiss():
    print_header("🧠 Semantic Search (FAISS index)")
    query = input(colored("Describe the kind of role you're looking for: ", Color.PROMPT)).strip()
    if not query:
        print("No query entered.")
        return

    print(colored("Loading and embedding jobs from the latest S3 export...", Color.DIM))
    jobs = load_jobs_from_s3()
    jobs = embed_jobs(jobs)

    print(colored("Building FAISS index...", Color.DIM))
    index, jobs = build_faiss_index(jobs)

    results = semantic_search_faiss(query, index, jobs, top_n=5)

    print(colored(f"\n✅ Top {len(results)} closest matches (via FAISS):", Color.TITLE))
    for job in results:
        print_job(job, show_score=True)


def run_rag_search():
    print_header("🤖 Ask a Question (RAG)")
    question = input(colored("Ask a question about the available jobs: ", Color.PROMPT)).strip()
    if not question:
        print("No question entered.")
        return

    print(colored("Loading and embedding jobs from the latest S3 export...", Color.DIM))
    jobs = load_jobs_from_s3()
    jobs = embed_jobs(jobs)

    print(colored("Thinking...\n", Color.DIM))
    answer = rag_answer(question, jobs, top_n=50)
    print(colored("💬 Answer:", Color.TITLE))
    print(answer)


def main():
    print(colored("\n╔══════════════════════════╗", Color.TITLE))
    print(colored("║   REED JOBS SEARCH       ║", Color.TITLE))
    print(colored("╚══════════════════════════╝", Color.TITLE))

    while True:
        print(colored("\n1.", Color.PROMPT), "🔍 Exact/filter search (location, salary, contract type, role)")
        print(colored("2.", Color.PROMPT), "🧠 Semantic search - manual cosine similarity")
        print(colored("3.", Color.PROMPT), "🧠 Semantic search - FAISS index (same task, different engine)")
        print(colored("4.", Color.PROMPT), "🤖 Ask a question (RAG - generates a real answer from the data)")
        print(colored("5.", Color.PROMPT), "🚪 Quit")
        choice = input(colored("\nChoose 1-5: ", Color.PROMPT)).strip()

        if choice == "1":
            run_exact_search()
        elif choice == "2":
            run_semantic_search()
        elif choice == "3":
            run_semantic_search_faiss()
        elif choice == "4":
            run_rag_search()
        elif choice == "5":
            print(colored("\n👋 Goodbye!", Color.TITLE))
            break
        else:
            print("Please enter 1, 2, 3, 4, or 5.")


if __name__ == "__main__":
    main()
