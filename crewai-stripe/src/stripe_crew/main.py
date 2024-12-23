#!/usr/bin/env python3
from dotenv import load_dotenv
import os
import sys
from typing import Optional, Dict

from src.stripe.crew import StripeCrew

load_dotenv()

def get_user_input() -> str:
    """Get and validate user input."""
    print("\nWelcome to Stripe Payment Processing!")
    print("\nExample queries:")
    print("1. Process a payment of $25 to account acct_1QYv4YCd615Z2kol")
    print("2. Create a payment link for 'Product Name' for $19.99")
    
    while True:
        query = input("\nWhat would you like to do? ").strip()
        if query:  # Check if input is not empty
            return query
        print("Please enter a valid query. Cannot be empty.")

def run(crew_inputs: Optional[Dict] = None) -> int:
    """Run the Stripe payment processing crew."""
    try:
        # Ensure API key is set
        if not os.getenv("STRIPE_API_KEY"):
            print("Error: STRIPE_API_KEY environment variable is not set")
            return 1

        # Initialize crew with inputs
        if crew_inputs is None:
            crew_inputs = {'query': get_user_input()}
        
        # Run crew
        stripe_crew = StripeCrew(crew_inputs)
        result = stripe_crew.run()
        print(result)
        return 0 if result.startswith("SUCCESS:") else 1

    except Exception as e:
        print(f"Error running crew: {str(e)}")
        return 1

def train() -> int:
    """Train the Stripe payment processing crew."""
    print("Training functionality not implemented yet.")
    return 0

def test() -> int:
    """Test the Stripe payment processing crew."""
    print("Testing functionality not implemented yet.")
    return 0

def replay() -> int:
    """Replay the Stripe payment processing crew."""
    print("Replay functionality not implemented yet.")
    return 0

if __name__ == "__main__":
    sys.exit(run())
