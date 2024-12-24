#!/usr/bin/env python
import sys
import warnings
import argparse
from .crew import WebSummarizer
import stripe
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress pysbd warnings
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

def create_test_customer():
    """Create a test customer with a test card for local testing."""
    try:
        # Create a test customer
        customer = stripe.Customer.create(
            name="Test Customer",
            email="test@example.com",
            source="tok_visa"  # Test card token
        )
        
        # Create a payment method
        payment_method = stripe.PaymentMethod.create(
            type="card",
            card={"token": "tok_visa"}
        )
        
        # Attach payment method to customer
        stripe.PaymentMethod.attach(
            payment_method.id,
            customer=customer.id
        )
        
        return {
            "id": customer.id,
            "payment_method_id": payment_method.id,
            "email": "test@example.com",
            "name": "Test Customer"
        }
    except stripe.error.StripeError as e:
        logger.error(f"Failed to create test customer: {str(e)}")
        raise

def get_url_from_user():
    """Get URL from user input if not provided as argument."""
    while True:
        url = input("\nEnter the URL to summarize: ").strip()
        try:
            from urllib.parse import urlparse
            result = urlparse(url)
            if all([result.scheme, result.netloc]):
                return url
            else:
                print("Invalid URL format. Please enter a valid URL (e.g., https://example.com)")
        except Exception:
            print("Invalid URL format. Please enter a valid URL (e.g., https://example.com)")

def run():
    """Run the web summarizer crew."""
    # Load environment variables
    load_dotenv()
    stripe.api_key = os.getenv('STRIPE_API_KEY')

    if not stripe.api_key:
        logger.error("STRIPE_API_KEY environment variable is required")
        return 1

    try:
        # Get URL from user input
        url = get_url_from_user()

        logger.info("Creating test customer...")
        customer = create_test_customer()
        logger.info(f"Test customer created: {customer['id']}")

        logger.info(f"Processing URL: {url}")
        crew = WebSummarizer(crew_inputs={
            'url': url,
            'customer': customer
        })
        result = crew.run()

        if result.get('success'):
            print("\n✅ Summary generated successfully!")
            print("\nSummary:")
            print(result['summary'])
            print(f"\nPayment Intent ID: {result['payment_intent']}")
            return 0
        else:
            print("\n❌ Error:")
            print(result.get('error', 'Unknown error'))
            print("\nDetails:")
            print(result.get('details', 'No details available'))
            return 1

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Error running web summarizer: {str(e)}")
        print(f"\n❌ Error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(run()) 