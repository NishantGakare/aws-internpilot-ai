import json
import urllib.parse
import boto3
import fitz  # PyMuPDF


s3 = boto3.client("s3")


def lambda_handler(event, context):

    print("Received S3 event:")
    print(json.dumps(event, indent=2))

    try:
        # Get S3 event details
        record = event["Records"][0]

        bucket_name = record["s3"]["bucket"]["name"]

        object_key = urllib.parse.unquote_plus(
            record["s3"]["object"]["key"]
        )

        print(f"Bucket: {bucket_name}")
        print(f"Object Key: {object_key}")

        # Download PDF from S3
        response = s3.get_object(
            Bucket=bucket_name,
            Key=object_key
        )

        pdf_bytes = response["Body"].read()

        print(f"Downloaded PDF size: {len(pdf_bytes)} bytes")

        # Open PDF from memory
        pdf_document = fitz.open(
            stream=pdf_bytes,
            filetype="pdf"
        )

        # Extract text
        extracted_text = ""

        for page_number, page in enumerate(pdf_document):
            page_text = page.get_text()

            extracted_text += page_text

            print(
                f"Extracted text from page {page_number + 1}"
            )

        pdf_document.close()

        print("========== RESUME TEXT ==========")
        print(extracted_text)
        print("========== END RESUME TEXT ==========")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "success": True,
                "message": "Resume processed successfully",
                "fileKey": object_key,
                "textLength": len(extracted_text)
            })
        }

    except Exception as e:

        print("ERROR PROCESSING RESUME:")
        print(str(e))

        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "message": str(e)
            })
        }