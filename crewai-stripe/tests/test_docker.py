"""Tests for the Stripe payment processing crew."""

import requests
import json

# URL for the local AWS Lambda Docker invocation
url = "http://localhost:9000/2015-03-31/functions/function/invocations" # Set to URL of Lambda function docker container

# Create the payload with the desired query
payload = {
    "body": json.dumps({
        "query": "Create a payment link for 'lawn mowing' for $10"
    })
}

# Send the POST request to the Lambda function
response = requests.post(url, json=payload)

# Print the response from the Lambda function
print(response.json())

"""
output: {'statusCode': 200, 'headers': {'Content-Type': 'application/json'}, 'body': '{"result": "SUCCESS: https://buy.stripe.com/test_xxxxxxxxxxx"}'}
"""
