import json
import os
import uuid

import boto3
from botocore.config import Config


AWS_REGION = "ap-south-1"

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    config=Config(
        signature_version="s3v4",
        s3={
            "addressing_style": "virtual"
        }
    )
)

BUCKET_NAME = os.environ["RESUME_BUCKET"]


def lambda_handler(event, context):

    try:

        body = json.loads(
            event.get("body", "{}")
        )

        # Get user ID
        user_id = body.get("user_id")

        # Get original filename
        filename = body.get("filename")

        # Validate user ID
        if not user_id:

            return {
                "statusCode": 400,
                "body": json.dumps({
                    "success": False,
                    "message": "user_id is required"
                })
            }

        # Validate filename
        if not filename:

            return {
                "statusCode": 400,
                "body": json.dumps({
                    "success": False,
                    "message": "filename is required"
                })
            }

        # Get file extension
        extension = filename.split(".")[-1].lower()

        # Allow only PDF
        if extension != "pdf":

            return {
                "statusCode": 400,
                "body": json.dumps({
                    "success": False,
                    "message": "Only PDF files are allowed"
                })
            }

        # Generate unique S3 key
        file_key = (
            f"resumes/"
            f"{user_id}/"
            f"{uuid.uuid4()}.pdf"
        )

        # Generate presigned URL
        upload_url = s3.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": BUCKET_NAME,
                "Key": file_key,
                "ContentType": "application/pdf"
            },
            ExpiresIn=300,
            HttpMethod="PUT"
        )

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "success": True,
                "message": "Upload URL generated successfully",
                "uploadUrl": upload_url,
                "fileKey": file_key,
                "userId": user_id
            })
        }

    except Exception as e:

        print("ERROR:")
        print(str(e))

        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "message": str(e)
            })
        }