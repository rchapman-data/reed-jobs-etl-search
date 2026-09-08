"""
filter_search.py

Exact/filter search over jobs stored in MongoDB - the counterpart to
semantic_search.py's meaning-based search. This is for precise criteria
like "London", "salary above 40000", "Permanent contracts only".

Run directly for a couple of example searches:
    py -m src.filter_search
"""

from src.mongo_client import get_collection


def filter_search(location=None, min_salary=None, max_salary=None,
                   contract_type=None, role=None):
    """
    Search jobs by exact criteria. Any argument left as None is ignored -
    only the filters you actually supply are applied.

    Args:
        location (str | None): exact location, e.g. "London"
        min_salary (int | None): only jobs with salary.max >= this value
        max_salary (int | None): only jobs with salary.min <= this value
        contract_type (str | None): e.g. "Permanent", "Contract"
        role (str | None): the search_keyword used to find the job,
            e.g. "data analyst"

    Returns:
        list[dict]: matching job documents
    """
    collection = get_collection()
    query = {}

    if location is not None:
        query["location"] = location

    if contract_type is not None:
        query["contract_type"] = contract_type

    if role is not None:
        query["search_keyword"] = role

    if min_salary is not None:
        # A job "qualifies" for a minimum salary filter if its own
        # maximum salary is at least that much - i.e. it's plausible
        # the role could pay at least what was asked for.
        query["salary.max"] = {"$gte": min_salary}

    if max_salary is not None:
        # Similarly, a job fits under a salary cap if its own minimum
        # salary doesn't exceed the cap.
        query["salary.min"] = {"$lte": max_salary}

    return list(collection.find(query))


if __name__ == "__main__":
    print("--- Filter search: location='London', contract_type='Permanent' ---")
    results = filter_search(location="London", contract_type="Permanent")
    print(f"{len(results)} result(s)")
    for job in results[:5]:
        print(f"- {job.get('title')} | {job.get('salary')}")

    print("\n--- Filter search: role='BI analyst', min_salary=40000 ---")
    results = filter_search(role="BI analyst", min_salary=40000)
    print(f"{len(results)} result(s)")
    for job in results[:5]:
        print(f"- {job.get('title')} | {job.get('salary')}")