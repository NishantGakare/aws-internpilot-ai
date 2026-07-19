import json

def lambda_handler(event, context):

    print("========== S3 EVENT ==========")
    print(json.dumps(event, indent=2))

    return {
        "statusCode": 200
    }