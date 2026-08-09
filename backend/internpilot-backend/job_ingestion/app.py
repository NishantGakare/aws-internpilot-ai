import python
import json
import os
import uuid
from datetime import datetime, timezone

import boto3


# ============================================================
# AWS CLIENTS
# ============================================================

dynamodb = boto3.resource("dynamodb")

secrets_client = boto3.client(
    "secretsmanager"
)


# ============================================================
# DYNAMODB
# ============================================================

jobs_table = dynamodb.Table(
    os.environ["JOBS_TABLE"]
)


# ============================================================
# LAMBDA HANDLER
# ============================================================

def lambda_handler(event, context):

    print(
        "========== JOB INGESTION STARTED =========="
    )

    print(
        "Received event:"
    )

    print(
        json.dumps(
            event,
            indent=2
        )
    )

    try:

        # ====================================================
        # GET API SECRET
        # ====================================================

        secret_name = os.environ[
            "JOB_API_SECRET_NAME"
        ]

        print(
            f"Reading job API secret: {secret_name}"
        )

        secret_response = (
            secrets_client.get_secret_value(
                SecretId=secret_name
            )
        )

        api_key = secret_response[
            "SecretString"
        ]

        print(
            "Job API secret retrieved successfully"
        )


        # ====================================================
        # TEMPORARY TEST JOB
        # ====================================================

        job = {

            "job_id":
                "test-cloud-engineer-intern",

            "title":
                "Cloud Engineer Intern",

            "company":
                "InternPilot Test Company",

            "location":
                "Remote",

            "job_type":
                "Internship",

            "description":
                "Internship opportunity for students "
                "interested in AWS, cloud computing "
                "and DevOps.",

            "skills": [
                "AWS",
                "Python",
                "Docker",
                "DevOps"
            ],

            "experience":
                "0-1 years",

            "remote":
                True,

            "application_deadline":
                None,

            "source":
                "test",

            "source_url":
                "https://example.com/jobs/cloud-engineer-intern",

            "posted_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "created_at":
                datetime.now(
                    timezone.utc
                ).isoformat()
        }


        # ====================================================
        # SAVE JOB
        # ====================================================

        print(
            "Saving job to DynamoDB..."
        )

        jobs_table.put_item(
            Item=job
        )


        print(
            "========== JOB SAVED SUCCESSFULLY =========="
        )

        print(
            json.dumps(
                job,
                indent=2
            )
        )


        # ====================================================
        # RESPONSE
        # ====================================================

        return {

            "statusCode":
                200,

            "body":
                json.dumps({

                    "success":
                        True,

                    "message":
                        "Job inserted successfully",

                    "job":
                        job
                })
        }


    except Exception as e:

        print(
            "========== JOB INGESTION ERROR =========="
        )

        print(
            str(e)
        )

        return {

            "statusCode":
                500,

            "body":
                json.dumps({

                    "success":
                        False,

                    "message":
                        str(e)
                })
        }
