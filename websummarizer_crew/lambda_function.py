import json
import os
import logging
import sys
from typing import Dict, Any

# Override the HOME environment variable for Lambda environment
os.environ['HOME'] = '/tmp'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

from websummarizeragent import WebSummarizer

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for web summarization with Stripe payment.
    
    Expected input format:
    {
        "body": {
            "url": "https://example.com/page-to-summarize",
            "customer": {
                "id": "cus_xxx",
                "payment_method_id": "pm_xxx",
                "email": "customer@example.com",
                "name": "Customer Name",
                "phone": "+1234567890",  # Optional
                "address": {  # Optional
                    "line1": "123 Main St",
                    "city": "San Francisco",
                    "state": "CA",
                    "postal_code": "94105"
                }
            }
        }
    }
    """
    try:
        logger.info(f"Received event: {event}")
        
        # Parse the body from API Gateway event
        body = event.get('body', '{}')
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                return {
                    "statusCode": 400,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "Invalid JSON in request body"})
                }
        
        # Validate required fields
        if not isinstance(body, dict):
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Request body must be a JSON object"})
            }
        
        if 'url' not in body:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Missing 'url' in request body"})
            }
            
        if 'customer' not in body:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Missing 'customer' in request body"})
            }
        
        # Initialize WebSummarizer with the request data
        crew = WebSummarizer(crew_inputs={
            'url': body['url'],
            'customer': body['customer']
        })
        
        # Process the request
        result = crew.run()
        
        # Determine response based on result
        if result.get('success'):
            response_body = {
                "success": True,
                "summary": result.get('summary', 'No summary available'),
                "payment_intent": result.get('payment_intent')
            }
            status_code = 200
        else:
            response_body = {
                "success": False,
                "error": result.get('error', 'Unknown error'),
                "details": result.get('details', 'No details available')
            }
            status_code = 400
        
        response = {
            "statusCode": status_code,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "POST, OPTIONS"
            },
            "body": json.dumps(response_body)
        }
        
        logger.info(f"Returning response: {response}")
        return response
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "success": False,
                "error": "Internal server error",
                "details": str(e)
            })
        } 