"""
upload_s3.py

Uploads JSON export file to S3. Final step in the
pipeline: API -> Python -> MongoDB -> JSON Export -> S3.

AWS credentials and config are read from environment variables (.env).

"""

import os
from dotenv import load_dotenv
import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

load_dotenv()

# AWS S3 configuration
BUCKET_NAME = os.getenv("AWS_S3_BUCKET")
REGION = os.getenv("AWS_REGION", "eu-west-2")

# 
def upload_file_to_s3(filepath, s3_key=None):
    """
    Upload file to S3 bucket.

    Args:
        filepath (str): path to the local file to upload
        s3_key (str | None): the object key (path/filename) to use in S3.
            If not given, defaults to just the local filename.

    Returns:
        boolean: True if the upload succeeded, False otherwise
    """

    if not BUCKET_NAME:
        raise ValueError("AWS_S3_BUCKET not set. Check your .env file.")

    if not os.path.exists(filepath): # just in case wrong path is given, or file hasn't been exported yet
        print(f"[upload_file_to_s3] File not found: {filepath}")
        return False

    if s3_key is None:
        s3_key = f"exports/{os.path.basename(filepath)}" # basename returns the filename without any directory path

    s3_client = boto3.client("s3", region_name=REGION)

    try:
        s3_client.upload_file(filepath, BUCKET_NAME, s3_key)
        print(f"Uploaded {filepath} to s3://{BUCKET_NAME}/{s3_key}")
        return True
    except NoCredentialsError: # separate exception for missing credentials, to give a clearer error message
        print("[upload_file_to_s3] AWS credentials not found. Check your .env file.")
        return False
    except (BotoCoreError, ClientError) as e: # catch-all for any other boto3-related errors (network issues, permissions, etc.)
        print(f"[upload_file_to_s3] Upload failed: {e}")
        return False


if __name__ == "__main__":
    # Quick manual test: uploads the most recently created export in data/
    import glob # for finding files using a wildcard pattern. does pattern matching on the filename

    export_files = sorted(glob.glob("data/jobs_export_*.json")) # see it, say it... 
    if not export_files:
        print("No export files found in data/. Run 'py -m src.export' first.")
    else:
        latest_export = export_files[-1]
        upload_file_to_s3(latest_export)