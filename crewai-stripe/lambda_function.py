import json
import os

# Override the HOME environment variable for Lambda environment
os.environ['HOME'] = '/tmp'

from typing import Dict, Any
import logging
import sys
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

from src.stripe_crew.crew import StripeCrew

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for Stripe payment processing.
    
    Expected input format:
    {
        "body": {
            "query": "The payment request query",
            "customer": {  # Optional
                "id": "cus_xxx",
                "payment_method_id": "pm_xxx",
                "name": "Customer Name",
                "email": "customer@example.com",
                "phone": "+1234567890",
                "address": {
                    "line1": "123 Main St",
                    "city": "San Francisco",
                    "state": "CA",
                    "postal_code": "94105"
                },
                "description": "Optional description"
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
        
        if 'query' not in body:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Missing 'query' in request body"})
            }
        
        query = body['query']
        logger.info(f"Processing query: {query}")
        
        # Initialize crew with the complete event body
        stripe_crew = StripeCrew(crew_inputs=event)
        result = stripe_crew.handle_request(query)
        
        # Determine status code based on result
        status_code = 200 if result.startswith("SUCCESS:") else 400
        
        response = {
            "statusCode": status_code,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",  # Enable CORS for local testing
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "POST, OPTIONS"
            },
            "body": json.dumps({"result": result})
        }
        logger.info(f"Returning response: {response}")
        return response
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Invalid JSON in request body"})
        }
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": f"Internal server error - {str(e)}"})
        }