import json
import os
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

from src.stripe.crew import StripeCrew

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for Stripe payment processing.
    """
    try:
        # Parse the body from API Gateway event
        body = event.get('body', '{}')
        if isinstance(body, str):
            body = json.loads(body)
        
        # Extract query from body
        if not isinstance(body, dict) or 'query' not in body:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Missing 'query' in request body"})
            }
        
        query = body['query']
        logger.info(f"Processing query: {query}")
        
        # Initialize crew
        stripe_crew = StripeCrew()
        result = stripe_crew.handle_request(query)
        
        # Determine status code based on result
        status_code = 200 if result.startswith("SUCCESS:") else 400
        
        response = {
            "statusCode": status_code,
            "headers": {"Content-Type": "application/json"},
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