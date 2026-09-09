# Reed Jobs ETL & Search

Pipeline that pulls job listings from the Reed API, stores them in MongoDB, backs them up to S3, and supports exact, semantic (including FAISS), and RAG-based search.

[TODO: intro]

## Core requirements

- [x] Extract from an API (Reed)
- [x] Store raw data in MongoDB
- [x] Transform data, store in S3
- [x] Exact/filter search
- [x] Semantic/vector search
- [x] RAG (optional stretch goal)

## Pipeline

```
Reed API → Python → MongoDB → JSON export → S3
```

- `src/extract.py` — searches Reed + fetches full job details (two-stage: search, then per-job details)
- `src/mongo_client.py` — MongoDB connection + CRUD
- `src/export.py` — exports MongoDB → timestamped JSON
- `src/upload_s3.py` — uploads export to S3
- `main.py` — runs the full pipeline end to end

## Search

Two different search types, deliberately using two different data sources:

- `src/filter_search.py` — exact search (location, salary range, contract type, role) — queries **MongoDB** (the live operational store) directly
- `src/semantic_search.py` — meaning-based search, queries MongoDB — original version
- `src/semantic_search_s3.py` — same as above, but loads from the **latest S3 export** instead — matches the brief's "leverage transformed data" guidance
- `src/semantic_search_faiss.py` — same task as `semantic_search_s3.py`, but uses FAISS (a vector search library/index) instead of a manual loop — proof-of-concept for scaling to a much larger dataset; not necessary at our current size, but demonstrates the approach
- `src/rag_search.py` — retrieval (via semantic search) + generation (Claude Haiku) for natural-language Q&A, grounded only in retrieved jobs
- `src/search_app.py` — original terminal interface (exact + semantic search)
- `src/search_app_v2.py` — adds FAISS option, RAG option, a menu loop (no need to re-run the program each search), and coloured/formatted output

Run: `py -m src.search_app_v2`

**[include video: search_app_v2.py run, showing all 5 menu options?]**

[TODO: maybe a short table summarising which file uses MongoDB vs S3, and why]

## Setup

- Python 3.x, MongoDB running locally
- `pip install -r requirements.txt`
- Copy `.env.example` → `.env`, fill in:
  - `REED_API_KEY`
  - `MONGO_URI`
  - `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_S3_BUCKET` / `AWS_REGION`
  - `ANTHROPIC_API_KEY` (for RAG)
- Run pipeline: `py main.py`
- Run search: `py -m src.search_app_v2`

[TODO: any setup gotchas to mention?]

## Data

- Source: Reed API (`reed.co.uk/developers`). Free but email required.
- Searches: "data analyst", "data engineer", "BI analyst" — London  - 
- ~267 jobs currently in MongoDB (grew from an initial ~24-30 job test run)
- **[MongoDB Compass showing jobs collection screenshot]**
- **[S3 bucket `exports/` folder screenshot?]**
- **[anthropic screenshot?]**
- **Data cleaning: out of scope, by choice.** The raw Reed data is broadly usable as-is (not a total mess) - real issues exist (see Known limitations below) but were judged not severe enough to justify cleaning within this project's scope/timeline. Downstream code handles gaps (e.g. `format_salary()` shows "salary not listed" instead of crashing on `None`), but no values are corrected or deduplicated.

## Document schema

```
{
  _id, job_id, title, employer: {id, name},
  description, location,
  salary: {min, max, currency, type},
  contract_type, job_type, expiration_date, url,
  search_keyword, search_location, date_scraped
}
```

[explanations: why _id vs job_id]

## Semantic search & RAG details

- Embedding model: `sentence-transformers` (`all-MiniLM-L6-v2`), 384-dim vectors
- Embeds `title + description` combined
- Cosine similarity computed manually (numpy) in `semantic_search.py`/`semantic_search_s3.py` to help understanding before using 
- `semantic_search_faiss.py` uses FAISS's `IndexFlatIP` (exact search, no approximation) — confirmed to produce identical results/scores to the manual version on a controlled test (same query string, same rankings and scores to 3 decimal places). **Note: FAISS is standalone (own file, own app menu option) — `rag_search.py` currently retrieves via the manual `semantic_search_s3.py`, not FAISS.**
- RAG (`rag_search.py`): retrieves top ~50 jobs via semantic search, builds a prompt instructing the model to answer using ONLY the retrieved postings, calls Claude Haiku (`claude-haiku-4-5-20251001`)
- Cost: RAG testing (many queries) cost under $0.10 total on the Anthropic API
- **[📸 screenshot here: Anthropic Console credit balance, showing real usage/cost]**

## Known limitations & findings

These were found through deliberate testing, not assumed:

- **Small/narrow dataset**: 267 jobs, 3 roles, London only — no location/time-trend analysis possible
- **Exact search is case-sensitive**: e.g. `role="Data Engineer"` returns 0 results; must match stored casing exactly (`"data engineer"`). Contrast with semantic search, which is meaning-based and doesn't care about case. [TODO: fix this?]
- **Typos measurably reduce semantic search confidence**: tested "data warehouses and ETL pipelines" correctly spelled vs. deliberately misspelled — similarity scores dropped from ~0.6-0.67 to ~0.22-0.26 (roughly 60-65% lower), and top results shifted from specific ("Data Engineer") to more generic ("Data Analyst") matches. **[📸 screenshot here: both terminal outputs side by side]**
- **Cosine similarity ≠ "confidence"**: it measures how aligned two embedding vectors are in meaning-space, not a probability. Correlates with match quality but isn't literally a confidence percentage, so shouldn't be taken to mean that the job posting is more suitable. 
- **RAG can give inconsistent answers to superlative/aggregate questions**: e.g. "highest paid data job" vs "highest paid data engineer job" returned different top results, because retrieval (similarity-based) doesn't guarantee scanning every candidate the way a true database aggregate would. **[📸 screenshot here: both RAG answers side by side]**
- **Prompt-engineering test: competing instructions.** Added "make a joke about the job market" to the RAG prompt alongside the strict grounding instruction ("answer using only the retrieved postings"). Result: the grounding instruction held - factual accuracy didn't degrade - but the joke itself was consistently forced/low-quality (never skipped, but never funny), likely because dry job posting data (salary, contract type, employer) gives the model little genuinely humorous material to draw on. Suggests the model treats a strict factual constraint as higher-priority than a creative one, rather than blending them.
- **Reed's own search results aren't always tightly on-topic**: `search_keyword="data engineer"` results include some loosely-related titles (e.g. "AI Engineer", "Service Desk Engineer") — this reflects Reed's search relevance, not a bug in our filtering
- **Duplicate postings**: some jobs appear twice under different Reed job IDs (e.g. agency re-posts of the same real listing) — current dedup only catches exact duplicate Reed job IDs, not re-posts
- **Inconsistent salary units**: a small number of listings show implausible salary figures (e.g. "51" instead of "51000") — likely a Reed/employer data entry inconsistency, not a bug in our extraction
- **Embeddings recomputed in memory every run** (not cached/persisted) — fine at current scale, would need caching at larger scale

## Safe practices

- Personal AWS account (separate from shared course account) with a dedicated IAM user (least privilege - S3 access only, not root)
- Budget/spend alerts set on both AWS (Zero Spend Budget) and Anthropic Console
- All secrets in `.env` (gitignored), never hardcoded; `.env.example` documents required variables

## Possible next steps

- Proper data cleaning (fix salary-unit inconsistencies, dedupe re-posts across different Reed job IDs) - consciously left out of this project's scope, see Data section above
- Fix exact search case-sensitivity (case-insensitive matching)
- Recommendations: "find jobs similar to this one" using existing embeddings
- Embedding caching (persist embeddings instead of recomputing every run)
- MongoDB Atlas Vector Search as an alternative to FAISS/manual cosine similarity
- Expand to multiple locations (currently London only)
- [TODO: anything else worth mentioning???
- 
