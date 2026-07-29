import json
import os
import urllib.parse

import boto3
import fitz

from groq import Groq
from botocore.exceptions import ClientError


# ============================================================
# AWS CLIENTS
# ============================================================

s3 = boto3.client("s3")

secrets_manager = boto3.client(
    "secretsmanager"
)

dynamodb = boto3.resource(
    "dynamodb"
)


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

GROQ_SECRET_NAME = os.environ[
    "GROQ_SECRET_NAME"
]

USERS_TABLE = os.environ[
    "USERS_TABLE"
]


# ============================================================
# DYNAMODB TABLE
# ============================================================

users_table = dynamodb.Table(
    USERS_TABLE
)


# ============================================================
# GET GROQ API KEY
# ============================================================

def get_groq_api_key():

    print(
        f"Reading Groq secret: "
        f"{GROQ_SECRET_NAME}"
    )

    try:

        response = secrets_manager.get_secret_value(

            SecretId=GROQ_SECRET_NAME

        )

        secret_string = response.get(
            "SecretString"
        )

        if not secret_string:

            raise Exception(
                "SecretString is empty"
            )

        secret_data = json.loads(
            secret_string
        )

        api_key = secret_data.get(
            "GROQ_API_KEY"
        )

        if not api_key:

            raise Exception(
                "GROQ_API_KEY not found "
                "inside Secrets Manager secret"
            )

        print(
            "Groq API key retrieved successfully"
        )

        return api_key


    except ClientError as e:

        print(
            "Error retrieving Groq API key:"
        )

        print(
            str(e)
        )

        raise


    except Exception as e:

        print(
            "Error parsing Groq secret:"
        )

        print(
            str(e)
        )

        raise


# ============================================================
# GET USER ID FROM S3 OBJECT KEY
# ============================================================

def get_user_id_from_s3_key(
    object_key
):

    print(
        f"Extracting user ID from S3 key: "
        f"{object_key}"
    )

    # Expected format:
    #
    # resumes/{user_id}/{filename}.pdf
    #
    # Example:
    #
    # resumes/
    # eecef2f8-d3cc-49db-af92-e4d5475574d6/
    # bcbe09d1-dff2-47c4-ae42-83d97a8635f4.pdf

    parts = object_key.split("/")

    if len(parts) < 3:

        raise Exception(

            f"Invalid S3 object key format: "
            f"{object_key}. "
            f"Expected: resumes/{{user_id}}/{{filename}}"

        )

    if parts[0] != "resumes":

        raise Exception(

            f"Invalid resume path: "
            f"{object_key}. "
            f"File must be inside resumes/"

        )

    user_id = parts[1]

    if not user_id:

        raise Exception(

            "User ID is empty in S3 object key"

        )

    print(
        f"Extracted User ID: {user_id}"
    )

    return user_id


# ============================================================
# EXTRACT PDF TEXT
# ============================================================

def extract_pdf_text(

    bucket_name,

    object_key

):

    print(
        "Downloading PDF from S3..."
    )

    response = s3.get_object(

        Bucket=bucket_name,

        Key=object_key

    )

    pdf_bytes = response[
        "Body"
    ].read()

    print(

        f"Downloaded PDF size: "
        f"{len(pdf_bytes)} bytes"

    )

    if not pdf_bytes:

        raise Exception(

            "Downloaded PDF is empty"

        )

    # ========================================================
    # OPEN PDF
    # ========================================================

    try:

        pdf_document = fitz.open(

            stream=pdf_bytes,

            filetype="pdf"

        )

    except Exception as e:

        raise Exception(

            f"Unable to open PDF: {str(e)}"

        )


    # ========================================================
    # EXTRACT TEXT
    # ========================================================

    extracted_text = ""

    try:

        for page_number, page in enumerate(

            pdf_document

        ):

            page_text = page.get_text()

            extracted_text += (

                page_text + "\n"

            )

            print(

                f"Extracted text from page "
                f"{page_number + 1}"

            )

    finally:

        pdf_document.close()


    print(

        f"Total extracted text length: "
        f"{len(extracted_text)}"

    )

    return extracted_text


# ============================================================
# PARSE RESUME WITH GROQ
# ============================================================

def parse_resume_with_groq(

    resume_text

):

    print(
        "Starting Groq resume parsing..."
    )


    # ========================================================
    # GET API KEY
    # ========================================================

    api_key = get_groq_api_key()


    # ========================================================
    # INITIALIZE GROQ CLIENT
    # ========================================================

    client = Groq(

        api_key=api_key

    )


    # ========================================================
    # RESUME PARSING PROMPT
    # ========================================================

    prompt = f"""

You are an AI resume parser.

Analyze the following resume text and extract
structured information.

Return ONLY valid JSON.

Do not use Markdown.

Do not add explanations.

Use exactly this JSON structure:

{{
    "full_name": "",
    "email": "",
    "phone": "",
    "skills": [],
    "education": [
        {{
            "degree": "",
            "institution": "",
            "graduation_year": null
        }}
    ],
    "experience": [
        {{
            "company": "",
            "role": "",
            "duration": ""
        }}
    ],
    "projects": [
        {{
            "name": "",
            "description": "",
            "technologies": []
        }}
    ],
    "certifications": []
}}

Rules:

1. If a text field is not found, use an empty string.
2. If a list field is not found, use an empty array.
3. If graduation year is unknown, use null.
4. Do not invent information.
5. Use only information found in the resume.
6. Return valid JSON only.
7. Keep the original information accurate.
8. Do not add information that is not present in the resume.

Resume text:

{resume_text}

"""


    # ========================================================
    # CALL GROQ
    # ========================================================

    print(
        "Sending resume text to Groq..."
    )

    response = client.chat.completions.create(

        model="llama-3.1-8b-instant",

        messages=[

            {

                "role": "system",

                "content": (

                    "You are an AI resume parser. "

                    "Extract structured resume information. "

                    "Always return valid JSON only."

                )

            },

            {

                "role": "user",

                "content": prompt

            }

        ],

        temperature=0,

        response_format={

            "type": "json_object"

        }

    )


    # ========================================================
    # GET GROQ RESPONSE
    # ========================================================

    response_text = (

        response
        .choices[0]
        .message
        .content
        .strip()

    )


    print(
        "========== GROQ RESPONSE =========="
    )

    print(
        response_text
    )

    print(
        "========== END GROQ RESPONSE =========="
    )


    # ========================================================
    # PARSE JSON
    # ========================================================

    try:

        parsed_resume = json.loads(

            response_text

        )

    except json.JSONDecodeError as e:

        print(
            "Groq returned invalid JSON:"
        )

        print(
            response_text
        )

        raise Exception(

            f"Invalid JSON returned by Groq: "
            f"{str(e)}"

        )


    return parsed_resume


# ============================================================
# SAVE RESUME TO DYNAMODB
# ============================================================

def save_resume_to_dynamodb(
    user_id,
    parsed_resume,
    file_key
):

    print(
        f"Updating DynamoDB user: {user_id}"
    )

    # ========================================================
    # GET GRADUATION YEAR FROM RESUME
    # ========================================================

    graduation_year = None

    education_list = parsed_resume.get(
        "education",
        []
    )

    if education_list:

        education = education_list[0]

        graduation_year = education.get(
            "graduation_year"
        )

    # ========================================================
    # UPDATE BASE RESUME DATA
    # ========================================================

    update_expression = (
        "SET "
        "resume_data = :resume_data, "
        "resume_file_key = :file_key, "
        "resume_processed = :processed"
    )

    expression_values = {

        ":resume_data":
            parsed_resume,

        ":file_key":
            file_key,

        ":processed":
            True

    }

    # ========================================================
    # UPDATE GRADUATION YEAR IF FOUND
    # ========================================================

    if graduation_year is not None:

        graduation_year = str(
            graduation_year
        )

        update_expression += (
            ", graduation_year = :graduation_year"
        )

        expression_values[
            ":graduation_year"
        ] = graduation_year

    # ========================================================
    # UPDATE DYNAMODB
    # ========================================================

    response = users_table.update_item(

        Key={
            "user_id": user_id
        },

        UpdateExpression=
            update_expression,

        ExpressionAttributeValues=
            expression_values,

        ReturnValues="ALL_NEW"

    )

    # ========================================================
    # GET UPDATED USER
    # ========================================================

    updated_attributes = response.get(

        "Attributes",

        {}

    )

    # ========================================================
    # LOG RESULT
    # ========================================================

    print(
        "========== DYNAMODB UPDATE SUCCESS =========="
    )

    print(
        f"Graduation Year: "
        f"{graduation_year}"
    )

    print(
        json.dumps(

            updated_attributes,

            default=str,

            indent=2

        )
    )

    print(
        "=============================================="
    )

    return updated_attributes


# ============================================================
# PROCESS SINGLE RESUME
# ============================================================

def process_resume(

    bucket_name,

    object_key

):

    print(
        "=============================================="
    )

    print(
        "PROCESSING RESUME"
    )

    print(
        f"Bucket: {bucket_name}"
    )

    print(
        f"Object Key: {object_key}"
    )

    print(
        "=============================================="
    )


    # ========================================================
    # ONLY PROCESS PDF
    # ========================================================

    if not object_key.lower().endswith(

        ".pdf"

    ):

        print(

            f"Skipping non-PDF file: "
            f"{object_key}"

        )

        return {

            "success":
                False,

            "skipped":
                True,

            "reason":
                "Not a PDF",

            "fileKey":
                object_key

        }


    # ========================================================
    # GET USER ID
    # ========================================================

    user_id = get_user_id_from_s3_key(

        object_key

    )


    print(

        f"Processing resume "
        f"for user: {user_id}"

    )


    # ========================================================
    # EXTRACT PDF TEXT
    # ========================================================

    extracted_text = extract_pdf_text(

        bucket_name,

        object_key

    )


    print(

        f"Extracted text length: "
        f"{len(extracted_text)}"

    )


    # ========================================================
    # VALIDATE TEXT
    # ========================================================

    if not extracted_text.strip():

        raise Exception(

            "No text could be extracted "
            "from the PDF. "
            "The PDF may be scanned/image-based."

        )


    # ========================================================
    # PARSE RESUME WITH GROQ
    # ========================================================

    parsed_resume = parse_resume_with_groq(

        extracted_text

    )


    # ========================================================
    # PRINT PARSED RESUME
    # ========================================================

    print(

        "========== PARSED RESUME =========="

    )

    print(

        json.dumps(

            parsed_resume,

            indent=2

        )

    )

    print(

        "========== END PARSED RESUME =========="

    )


    # ========================================================
    # SAVE TO DYNAMODB
    # ========================================================

    saved_user = save_resume_to_dynamodb(

        user_id,

        parsed_resume,

        object_key

    )


    # ========================================================
    # RETURN RESULT
    # ========================================================

    return {

        "success":
            True,

        "userId":
            user_id,

        "fileKey":
            object_key,

        "parsedResume":
            parsed_resume

    }


# ============================================================
# LAMBDA HANDLER
# ============================================================

def lambda_handler(event, context):

    print(
        "========== RESUME PROCESSOR STARTED =========="
    )

    print(
        "========== RECEIVED EVENT =========="
    )

    print(
        json.dumps(
            event,
            indent=2
        )
    )

    print(
        "========== END RECEIVED EVENT =========="
    )

    try:

        # ====================================================
        # CHECK EVENTBRIDGE EVENT
        # ====================================================

        if "detail" not in event:

            raise Exception(
                "Invalid EventBridge event: "
                "'detail' not found"
            )


        detail = event["detail"]


        # ====================================================
        # GET S3 BUCKET NAME
        # ====================================================

        if "bucket" not in detail:

            raise Exception(
                "Invalid EventBridge event: "
                "'detail.bucket' not found"
            )


        bucket_name = detail[
            "bucket"
        ][
            "name"
        ]


        # ====================================================
        # GET S3 OBJECT KEY
        # ====================================================

        if "object" not in detail:

            raise Exception(
                "Invalid EventBridge event: "
                "'detail.object' not found"
            )


        object_key = detail[
            "object"
        ][
            "key"
        ]


        # ====================================================
        # URL DECODE S3 OBJECT KEY
        # ====================================================

        object_key = urllib.parse.unquote_plus(
            object_key
        )


        print(
            f"Bucket: {bucket_name}"
        )


        print(
            f"Object Key: {object_key}"
        )


        # ====================================================
        # ONLY PROCESS PDF FILES
        # ====================================================

        if not object_key.lower().endswith(
            ".pdf"
        ):

            print(
                f"Skipping non-PDF file: "
                f"{object_key}"
            )

            return {

                "statusCode":
                    200,

                "body":
                    json.dumps({

                        "success":
                            True,

                        "message":
                            "Skipped non-PDF file",

                        "fileKey":
                            object_key

                    })

            }


        # ====================================================
        # GET USER ID FROM S3 KEY
        #
        # Expected format:
        #
        # resumes/{user_id}/{file_id}.pdf
        #
        # Example:
        #
        # resumes/
        # b48746f5-5cac-4527-aabf-7c66f40c9101/
        # 1dbb0255-d796-49d9-a638-c59b57d7ea27.pdf
        #
        # User ID:
        #
        # b48746f5-5cac-4527-aabf-7c66f40c9101
        # ====================================================

        user_id = get_user_id_from_s3_key(

            object_key

        )


        print(
            f"User ID: {user_id}"
        )


        # ====================================================
        # EXTRACT PDF TEXT
        # ====================================================

        extracted_text = extract_pdf_text(

            bucket_name,

            object_key

        )


        print(
            f"Extracted text length: "
            f"{len(extracted_text)}"
        )


        # ====================================================
        # VALIDATE EXTRACTED TEXT
        # ====================================================

        if not extracted_text.strip():

            raise Exception(

                "No text could be extracted "
                "from the PDF. "
                "The PDF may be scanned/image-based."

            )


        # ====================================================
        # PARSE RESUME WITH GROQ
        # ====================================================

        parsed_resume = parse_resume_with_groq(

            extracted_text

        )


        # ====================================================
        # PRINT PARSED RESUME
        # ====================================================

        print(
            "========== PARSED RESUME =========="
        )


        print(

            json.dumps(

                parsed_resume,

                indent=2

            )

        )


        print(
            "========== END PARSED RESUME =========="
        )


        # ====================================================
        # SAVE PARSED RESUME TO DYNAMODB
        # ====================================================

        saved_user = save_resume_to_dynamodb(

            user_id,

            parsed_resume,

            object_key

        )


        # ====================================================
        # SUCCESS
        # ====================================================

        print(
            "========== RESUME PROCESSING COMPLETE =========="
        )


        return {

            "statusCode":
                200,

            "body":
                json.dumps({

                    "success":
                        True,

                    "message":
                        "Resume processed successfully",

                    "userId":
                        user_id,

                    "fileKey":
                        object_key,

                    "parsedResume":
                        parsed_resume

                })

        }


    # ========================================================
    # ERROR HANDLING
    # ========================================================

    except Exception as e:

        print(
            "========== ERROR PROCESSING RESUME =========="
        )


        print(
            f"Error: {str(e)}"
        )


        print(
            "=============================================="
        )


        # IMPORTANT:
        # Raise the exception instead of returning
        # statusCode 500.
        #
        # This allows EventBridge/Lambda monitoring
        # to correctly identify the invocation as failed.

        raise