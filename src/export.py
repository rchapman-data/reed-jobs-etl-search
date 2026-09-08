"""
export.py

Reads all job documents currently in MongoDB and serializes them to a
JSON file on disk. This JSON file is what gets uploaded to S3 as our
cloud backup.
"""

import json
import os
from datetime import datetime, timezone
from src.mongo_client import get_all_jobs

EXPORT_DIR = "data"


def export_jobs_to_json(filename=None):
    """
    Fetch all jobs from MongoDB and write them to a JSON file.

    Args:
        filename (str | None): output filename. If not given, a timestamped
            name is generated automatically so each export is preserved
            rather than overwriting the last one.

    Returns:
        str: the full path to the JSON file that was written
    """
    jobs = get_all_jobs()

    os.makedirs(EXPORT_DIR, exist_ok=True)

    if filename is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"jobs_export_{timestamp}.json"

    filepath = os.path.join(EXPORT_DIR, filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            # default=str is a safety net: covers any non-JSON-native types
            # (e.g. datetime objects) without the export crashing
            json.dump(jobs, f, indent=2, default=str, ensure_ascii=False)
    except (OSError, TypeError) as e:
        print(f"[export_jobs_to_json] Failed to write export: {e}")
        raise

    print(f"Exported {len(jobs)} jobs to {filepath}")
    return filepath


if __name__ == "__main__":
    export_jobs_to_json()