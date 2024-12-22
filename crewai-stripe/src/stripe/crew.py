import stripe
from crewai import Agent, Crew, Process, Task
import os
from dotenv import load_dotenv
import json
from typing import Dict, Union, Optional, Any
import logging
import sys
from crewai.crews.crew_output import CrewOutput

# Configure logging
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(levelname)s - %(message)s',
	handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

load_dotenv()

class StripeCrew:
	"""Stripe payment processing crew"""

	def __init__(self, crew_inputs: Optional[Dict] = None):
		"""Initialize the Stripe crew with optional inputs."""
		logger.info("Initializing StripeCrew...")
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
		
		# Initialize manager agent
		logger.info("Initializing manager agent...")
		self.manager = Agent(
			role="Payment Manager",
			goal="Process payments and create payment links",
			backstory="""Expert at processing payments and creating payment links.
			
			When parsing requests:
			1. For payment links:
			   - Extract product name
			   - Extract dollar amount
			   
			2. For account payments:
			   - Look for account ID starting with 'acct_'
			   - Extract dollar amount
			   - Ensure account ID is properly formatted
			   
			3. Return data in exact JSON format""",
			verbose=True
		)
		logger.info("Agent initialized successfully")

	def parse_request(self, query: str) -> Task:
		"""Create task to parse payment request."""
		logger.info(f"Creating parse task for query: {query}")
		if not isinstance(query, str):
			raise ValueError("Query must be a string")
			
		return Task(
			description=f"""Parse payment request: "{query}"
			If the request mentions "payment link" or "create a payment link", use type "payment_link".
			If it mentions "pay to" or "send" or "transfer", use type "connect_payment".
			
			For payment_link:
			- Set product to the product name (in quotes if present)
			- Set amount to the specified dollar amount
			
			For connect_payment:
			- Set account_id to the specified account ID (must start with acct_)
			- Set amount to the specified dollar amount
			
			Return ONLY a JSON object in this exact format:
			For payment_link:
			{{"type": "payment_link", "product": "name", "amount": number}}
			
			For connect_payment:
			{{"type": "connect_payment", "account_id": "acct_*", "amount": number}}
			
			Note: Always use the amount specified in the query.
			Note: For connect_payment, extract the account ID starting with 'acct_'.
			Note: If no valid account ID is found in a payment request, return an error message.""",
			expected_output="JSON payment data",
			agent=self.manager
		)

	def process_connect_payment(self, account_id: str, amount: float) -> str:
		"""Process a payment to a connected account."""
		try:
			# Verify the account exists
			try:
				stripe.Account.retrieve(account_id)
			except stripe.error.StripeError:
				raise ValueError(f"Invalid or non-existent account ID: {account_id}")

			# Create a customer and payment method
			customer = stripe.Customer.create(
				name="Test Customer",
				email="test@example.com"
			)
			
			payment_method = stripe.PaymentMethod.create(
				type="card",
				card={"token": "tok_visa"},
				billing_details={"name": "Test Customer", "email": "test@example.com"}
			)
			
			stripe.PaymentMethod.attach(payment_method.id, customer=customer.id)
			
			# Process payment
			payment_intent = stripe.PaymentIntent.create(
				amount=int(amount * 100),
				currency="usd",
				customer=customer.id,
				payment_method=payment_method.id,
				off_session=True,
				confirm=True,
				
				transfer_data={'destination': account_id},
				metadata={'payment_type': 'connect', 'recipient_account': account_id}
			)
			
			return payment_intent.id if payment_intent.status == "succeeded" else payment_intent.client_secret
				
		except stripe.error.StripeError as e:
			logger.error(f"Failed to process connect payment: {str(e)}")
			raise

	def create_payment_link(self, product_name: str, amount_cents: int) -> str:
		"""Create a new payment link."""
		try:
			product = stripe.Product.create(
				name=product_name,
				description=f"{product_name} - One-time purchase"
			)
			
			price = stripe.Price.create(
				product=product.id,
				unit_amount=amount_cents,
				currency="usd"
			)
			
			payment_link = stripe.PaymentLink.create(
				line_items=[{"price": price.id, "quantity": 1}]
			)
			
			return payment_link.url
			
		except stripe.error.StripeError as e:
			logger.error(f"Failed to create payment link: {str(e)}")
			raise

	def handle_request(self, query: str) -> str:
		"""Process payment request end-to-end."""
		logger.info(f"Processing payment request: {query}")
		
		if not query or not isinstance(query, str):
			return "Error: Invalid payment request"

		try:
			# Parse request
			parse_crew = Crew(
				agents=[self.manager],
				tasks=[self.parse_request(query)],
				verbose=True,
				process=Process.sequential
			)
			
			parse_result = parse_crew.kickoff()
			data = self.parse_json_result(parse_result)
			
			# Process payment based on type
			if data['type'] == 'connect_payment':
				payment_id = self.process_connect_payment(data['account_id'], data['amount'])
				return f"SUCCESS: {payment_id}"
			elif data['type'] == 'payment_link':
				payment_link = self.create_payment_link(data['product'], int(data['amount'] * 100))
				return f"SUCCESS: {payment_link}"
			else:
				return "Error: Invalid payment type"

		except Exception as e:
			error_msg = str(e).lower()
			logger.error(f"Request handling failed: {error_msg}")
			
			if "rate limit" in error_msg:
				return "Error: Rate limit reached. Please try again later."
			if "api_key" in error_msg:
				return "Error: Invalid Stripe API key."
			if "no such" in error_msg:
				return "Error: Invalid resource ID."
			
			return f"Error: {str(e)}"

	def parse_json_result(self, result: Any) -> Dict:
		"""Parse and validate JSON result."""
		try:
			if isinstance(result, CrewOutput):
				result = str(result.result if hasattr(result, 'result') else result)
			
			# Extract JSON from string if needed
			if isinstance(result, str):
				json_start = result.find('{')
				json_end = result.rfind('}') + 1
				if json_start >= 0 and json_end > json_start:
					result = result[json_start:json_end]
			
			data = json.loads(result if isinstance(result, str) else json.dumps(result))
			self.validate_payment_data(data)
			return data
			
		except (json.JSONDecodeError, ValueError) as e:
			logger.error(f"Failed to parse result: {str(e)}")
			raise ValueError(f"Invalid payment request format: {str(e)}")

	def validate_payment_data(self, data: Dict) -> None:
		"""Validate payment data structure."""
		if not isinstance(data, dict):
			raise ValueError("Payment data must be a dictionary")
			
		if data.get('type') not in {'payment_link', 'connect_payment'}:
			raise ValueError("Invalid payment type")
		
		try:
			amount = float(data['amount'])
			if amount <= 0 or amount > 999999.99:
				raise ValueError("Invalid amount")
		except (KeyError, ValueError):
			raise ValueError("Invalid amount format")
		
		if data['type'] == 'payment_link':
			if not data.get('product'):
				raise ValueError("Product name is required")
		elif data['type'] == 'connect_payment':
			if not data.get('account_id', '').startswith('acct_'):
				raise ValueError("Invalid account ID format")

	def run(self) -> str:
		"""Execute the payment processing crew."""
		logger.info("Starting StripeCrew execution...")
		query = self.crew_inputs.get('query', '')
		result = self.handle_request(query)
		logger.info("StripeCrew execution completed")
		return result

def crew():
	"""Entry point for the crew command."""
	try:
		stripe_crew = StripeCrew()
		result = stripe_crew.run()
		print(result)
		# Only return 0 (success) if it's a SUCCESS message
		return 0 if result and result.startswith("SUCCESS:") else 1
	except Exception as e:
		logger.error(f"Command line execution failed: {str(e)}")
		print(f"Error: {str(e)}")
		return 1

if __name__ == "__main__":
	sys.exit(crew())
