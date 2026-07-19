import json
import os
import uuid

import boto3
from botocore.config import Config

# AWS Configuration
AWS_REGION = "ap-south-1"

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    config=Config(
        signature_version="s3v4",
        s3={"addressing_style": "virtual"}
    )
)

BUCKET_NAME = os.environ["RESUME_BUCKET"]


def lambda_handler(event, context):
    try:
        # Parse request body
        body = json.loads(event.get("body", "{}"))

        filename = body.get("filename")

        if not filename:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "success": False,
                    "message": "filename is required"
                })
            }

        # Get file extension
        extension = filename.split(".")[-1]

        # Generate unique S3 object key
        file_key = f"resumes/{uuid.uuid4()}.{extension}"

        # Generate Presigned URL
        upload_url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": BUCKET_NAME,
                "Key": file_key
            },
            ExpiresIn=300,
            HttpMethod="PUT"
        )

        # Debug Logs
        print("========== Resume Upload ==========")
        print("Bucket :", BUCKET_NAME)
        print("Region :", AWS_REGION)
        print("FileKey:", file_key)
        print("Upload URL:", upload_url)
        print("===================================")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "success": True,
                "bucket": BUCKET_NAME,
                "region": AWS_REGION,
                "fileKey": file_key,
                "uploadUrl": upload_url
            })
        }

    except Exception as e:
        print("ERROR:", str(e))

        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "message": str(e)
            })
        }