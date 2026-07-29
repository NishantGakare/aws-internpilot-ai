import json
import os
import uuid

import boto3
from botocore.config import Config


# ============================================================
# AWS CONFIGURATION
# ============================================================

AWS_REGION = os.environ.get(
    "AWS_REGION",
    "ap-south-1"
)


# ============================================================
# S3 CLIENT
# ============================================================

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


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

BUCKET_NAME = os.environ[
    "RESUME_BUCKET"
]


# ============================================================
# LAMBDA HANDLER
# ============================================================

def lambda_handler(
    event,
    context
):

    print(
        "========== RESUME UPLOAD API =========="
    )

    print(
        "========== RAW EVENT =========="
    )

    print(
        json.dumps(
            event,
            indent=2
        )
    )

    print(
        "========== END RAW EVENT =========="
    )


    try:

        # ====================================================
        # PARSE REQUEST BODY
        # ====================================================

        body = event.get(
            "body",
            "{}"
        )


        # API Gateway normally sends body as a string

        if isinstance(
            body,
            str
        ):

            body = json.loads(
                body
            )


        # Make sure body is a dictionary

        if not isinstance(
            body,
            dict
        ):

            return {

                "statusCode":
                    400,

                "headers": {
                    "Content-Type":
                        "application/json"
                },

                "body":
                    json.dumps({

                        "success":
                            False,

                        "message":
                            "Request body must be a valid JSON object"

                    })

            }


        # ====================================================
        # GET FILENAME
        # ====================================================

        filename = body.get(
            "filename"
        )


        # ====================================================
        # GET USER ID
        # ====================================================

        user_id = body.get(
            "user_id"
        )


        # ====================================================
        # VALIDATE FILENAME
        # ====================================================

        if not filename:

            return {

                "statusCode":
                    400,

                "headers": {
                    "Content-Type":
                        "application/json"
                },

                "body":
                    json.dumps({

                        "success":
                            False,

                        "message":
                            "filename is required"

                    })

            }


        # ====================================================
        # VALIDATE USER ID
        # ====================================================

        if not user_id:

            return {

                "statusCode":
                    400,

                "headers": {
                    "Content-Type":
                        "application/json"
                },

                "body":
                    json.dumps({

                        "success":
                            False,

                        "message":
                            "user_id is required"

                    })

            }


        # ====================================================
        # CLEAN VALUES
        # ====================================================

        filename = str(
            filename
        ).strip()


        user_id = str(
            user_id
        ).strip()


        # ====================================================
        # VALIDATE USER ID
        # ====================================================

        if not user_id:

            return {

                "statusCode":
                    400,

                "headers": {
                    "Content-Type":
                        "application/json"
                },

                "body":
                    json.dumps({

                        "success":
                            False,

                        "message":
                            "user_id cannot be empty"

                    })

            }


        # ====================================================
        # ONLY ALLOW PDF FILES
        # ====================================================

        if not filename.lower().endswith(
            ".pdf"
        ):

            return {

                "statusCode":
                    400,

                "headers": {
                    "Content-Type":
                        "application/json"
                },

                "body":
                    json.dumps({

                        "success":
                            False,

                        "message":
                            "Only PDF files are allowed"

                    })

            }


        # ====================================================
        # GENERATE UNIQUE FILE NAME
        # ====================================================

        unique_filename = (

            f"{uuid.uuid4()}.pdf"

        )


        # ====================================================
        # GENERATE S3 OBJECT KEY
        # ====================================================

        # Format:
        #
        # resumes/{user_id}/{uuid}.pdf
        #
        # Example:
        #
        # resumes/abc-123/550e8400-e29b-41d4-a716-446655440000.pdf

        file_key = (

            f"resumes/"
            f"{user_id}/"
            f"{unique_filename}"

        )


        print(
            f"User ID: {user_id}"
        )


        print(
            f"Generated S3 Key: {file_key}"
        )


        # ====================================================
        # GENERATE PRESIGNED PUT URL
        # ====================================================

        upload_url = (

            s3.generate_presigned_url(

                ClientMethod=
                    "put_object",

                Params={

                    "Bucket":
                        BUCKET_NAME,

                    "Key":
                        file_key,

                    "ContentType":
                        "application/pdf"

                },

                ExpiresIn=
                    300,

                HttpMethod=
                    "PUT"

            )

        )


        print(
            "Presigned URL generated successfully"
        )


        # ====================================================
        # RETURN RESPONSE
        # ====================================================

        return {

            "statusCode":
                200,

            "headers": {

                "Content-Type":
                    "application/json",

                "Access-Control-Allow-Origin":
                    "*",

                "Access-Control-Allow-Headers":
                    "Content-Type",

                "Access-Control-Allow-Methods":
                    "POST,OPTIONS"

            },

            "body":
                json.dumps({

                    "success":
                        True,

                    "message":
                        "Presigned upload URL generated successfully",

                    "user_id":
                        user_id,

                    "originalFilename":
                        filename,

                    "uploadUrl":
                        upload_url,

                    "fileKey":
                        file_key

                })

        }


    # ========================================================
    # ERROR HANDLING
    # ========================================================

    except json.JSONDecodeError:

        print(
            "Invalid JSON request body"
        )


        return {

            "statusCode":
                400,

            "headers": {
                "Content-Type":
                    "application/json"
            },

            "body":
                json.dumps({

                    "success":
                        False,

                    "message":
                        "Invalid JSON request body"

                })

        }


    except Exception as e:

        print(
            "========== ERROR =========="
        )


        print(
            str(e)
        )


        print(
            "============================"
        )


        return {

            "statusCode":
                500,

            "headers": {
                "Content-Type":
                    "application/json"
            },

            "body":
                json.dumps({

                    "success":
                        False,

                    "message":
                        str(e)

                })

        }