import stripe
from crewai import Agent, Crew, Process, Task
from crewai_tools import WebsiteSearchTool
import os
from dotenv import load_dotenv
import json
from typing import Dict, Union, Optional, Any
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

load_dotenv()

class WebSummarizer():
    """WebSummarizer crew that handles billing and web summarization"""

    # Service provider's Stripe Connect account ID
    CONNECT_ACCOUNT_ID = "acct_1QYv4YCd615Z2gbp"
    SUMMARY_PRICE = 500  # $5.00 in cents

    def __init__(self, crew_inputs: Optional[Dict] = None):
        """Initialize the web summarizer crew with optional inputs."""
        logger.info("Initializing WebSummarizer...")
        if crew_inputs is None:
            crew_inputs = {}
        if not isinstance(crew_inputs, dict):
            raise ValueError("crew_inputs must be a dictionary")
        self.crew_inputs = crew_inputs
        
        # Initialize Stripe
        logger.info("Initializing Stripe...")
        self.api_key = os.getenv("STRIPE_API_KEY")
        if not self.api_key:
            raise ValueError("STRIPE_API_KEY environment variable is required")
        if not self.api_key.startswith(('sk_test_', 'sk_live_')):
            raise ValueError("Invalid Stripe API key format")
        
        # Configure Stripe with the API key
        stripe.api_key = self.api_key
        
        # Configure WebsiteSearchTool with HuggingFace embeddings
        self.search_tool = WebsiteSearchTool(
            config=dict(
                embedder=dict(
                    provider="huggingface",
                    config=dict(
                        model="sentence-transformers/all-MiniLM-L6-v2"
                    ),
                ),
            )
        )
        
        # Initialize agents
        self.billing_agent = Agent(
            role="Billing Manager",
            goal="Process Stripe Connect payments and ensure successful transactions",
            backstory="""Expert at processing Stripe Connect payments and verifying transactions.
            You handle customer payments through Stripe and ensure they are completed
            before allowing the service to proceed. You ensure the payment is properly
            routed to the service provider's Stripe Connect account.""",
            verbose=True
        )

        self.web_summarizer_agent = Agent(
            role="Web Content Summarizer",
            goal="Create concise and accurate summaries of web content",
            backstory="""Expert at analyzing web content and extracting key information.
            You create clear, concise summaries that capture the three most important
            points from any webpage. You use the WebsiteSearchTool to extract and
            understand content, ensuring the summary is valuable to the customer.""",
            tools=[self.search_tool],
            verbose=True
        )

    def create_tasks(self, url: str) -> list[Task]:
        """Create tasks for the crew."""
        tasks = []
        
        # Payment task
        payment_task = Task(
            description=f"""
            Process a Stripe Connect payment of ${self.SUMMARY_PRICE/100:.2f} for web summarization service.
            The payment should be routed to the service provider's Stripe Connect account: {self.CONNECT_ACCOUNT_ID}
            
            Steps:
            1. Process payment using customer's payment method
            2. Ensure payment is routed to the Connect account
            3. Verify payment was successful
            4. Return payment intent ID
            """,
            expected_output="""A confirmed payment intent ID indicating successful payment processing and routing to the Connect account.""",
            agent=self.billing_agent
        )
        tasks.append(payment_task)
        
        # Updated summarization task for more detailed output
        summary_task = Task(
            description=f"""
            Analyze and create a detailed summary of the content from: {url}
            
            Create a comprehensive summary with exactly three sections in markdown format:
            
            1. Key Points (3-5 bullet points)
            - List the most important takeaways
            - Focus on main arguments or findings
            - Include critical data points or statistics
            
            2. Detailed Analysis (2-3 paragraphs)
            - Provide deeper context and background
            - Explain relationships between key concepts
            - Include relevant examples or case studies
            
            3. Implications & Conclusions (2-3 bullet points)
            - Discuss potential impact or consequences
            - Highlight recommendations if any
            - Note limitations or areas for further consideration
            
            Format the output in proper markdown with headers, bullet points, and paragraphs.
            Ensure the summary is both comprehensive and easy to read.
            """,
            expected_output="""A structured markdown summary with three distinct sections: Key Points, Detailed Analysis, and Implications & Conclusions.""",
            agent=self.web_summarizer_agent
        )
        tasks.append(summary_task)
        
        return tasks

    def process_payment(self, customer: Dict) -> str:
        """Process the Stripe Connect payment."""
        try:
            # Create a payment intent with transfer data
            payment_intent = stripe.PaymentIntent.create(
                amount=self.SUMMARY_PRICE,
                currency="usd",
                customer=customer['id'],
                payment_method=customer['payment_method_id'],
                off_session=True,
                confirm=True,
                transfer_data={
                    'destination': self.CONNECT_ACCOUNT_ID,
                },
                metadata={
                    'service': 'web_summarizer',
                    'price': '$5.00',
                    'customer_email': customer.get('email', ''),
                    'connect_account': self.CONNECT_ACCOUNT_ID
                }
            )
            
            if payment_intent.status != 'succeeded':
                raise Exception(f"Payment failed: {payment_intent.last_payment_error}")
                
            return payment_intent.id
            
        except stripe.error.StripeError as e:
            logger.error(f"Payment processing failed: {str(e)}")
            raise

    def handle_request(self, url: str, customer: Dict) -> Dict:
        """Process the web summarization request with payment."""
        try:
            # Process payment first
            logger.info("Processing Stripe Connect payment...")
            payment_intent_id = self.process_payment(customer)
            logger.info(f"Payment successful: {payment_intent_id}")
            
            # Create tasks
            tasks = self.create_tasks(url)
            
            # Create and run the crew
            crew = Crew(
                agents=[self.billing_agent, self.web_summarizer_agent],
                tasks=tasks,
                process=Process.sequential,
                verbose=True
            )
            
            # Execute the tasks
            result = crew.kickoff()
            
            return {
                'success': True,
                'summary': result,
                'payment_intent': payment_intent_id
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Payment error: {str(e)}")
            return {
                'error': 'Payment processing error',
                'details': str(e)
            }
        except Exception as e:
            logger.error(f"Service error: {str(e)}")
            return {
                'error': 'Service error',
                'details': str(e)
            }

    def run(self) -> Dict:
        """Run the crew with the provided inputs."""
        url = self.crew_inputs.get('url')
        customer = self.crew_inputs.get('customer', {})
        
        if not url:
            raise ValueError("URL is required in crew_inputs")
        
        try:
            # Process payment first
            logger.info("Processing Stripe Connect payment...")
            payment_intent_id = self.process_payment(customer)
            logger.info(f"Payment successful: {payment_intent_id}")
            
            # Create tasks
            tasks = self.create_tasks(url)
            
            # Create and run the crew
            crew = Crew(
                agents=[self.billing_agent, self.web_summarizer_agent],
                tasks=tasks,
                process=Process.sequential,
                verbose=True
            )
            
            # Execute the tasks and format the output
            result = crew.kickoff()
            
            # Format the summary if it's successful
            summary = str(result)
            if not summary.startswith('#'):
                # If the output isn't already in markdown format, structure it
                summary = f"""
# Web Page Summary

## Key Points
{summary}

## Detailed Analysis
Analysis not available for this content.

## Implications & Conclusions
* Further analysis may be needed
* Consider reviewing source material for more details
"""
            
            return {
                'success': True,
                'summary': summary,
                'payment_intent': payment_intent_id
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Payment error: {str(e)}")
            return {
                'success': False,
                'error': 'Payment processing error',
                'details': str(e)
            }
        except Exception as e:
            logger.error(f"Service error: {str(e)}")
            return {
                'success': False,
                'error': 'Service error',
                'details': str(e)
            } 