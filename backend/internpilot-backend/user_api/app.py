import json
import os
import uuid
from datetime import datetime

import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["USERS_TABLE"])


def lambda_handler(event, context):
    try:
        # Parse request body
        body = json.loads(event.get("body", "{}"))

        # Basic validation
        required_fields = ["name", "email"]

        for field in required_fields:
            if field not in body:
                return {
                    "statusCode": 400,
                    "body": json.dumps({
                        "success": False,
                        "message": f"{field} is required"
                    })
                }

        # Create user object
        user = {
            "user_id": str(uuid.uuid4()),
            "name": body["name"],
            "email": body["email"],
            "skills": body.get("skills", []),
            "location": body.get("location", ""),
            "graduation_year": body.get("graduation_year"),
            "preferred_roles": body.get("preferred_roles", []),
            "created_at": datetime.utcnow().isoformat()
        }

        # Save to DynamoDB
        table.put_item(Item=user)

        return {
            "statusCode": 201,
            "body": json.dumps({
                "success": True,
                "message": "User created successfully",
                "data": user
            })
        }

    except Exception as e:
        print(e)

        return {
            "statusCode": 500,
            "body": json.dumps({
                "success": False,
                "message": str(e)
            })
        }