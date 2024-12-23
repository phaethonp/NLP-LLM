from flask import Flask, jsonify, request, render_template_string
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import stripe
import os
from dotenv import load_dotenv
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)
stripe.api_key = os.getenv('STRIPE_API_KEY')

# Configure requests session with retries
session = requests.Session()
retries = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504],
    allowed_methods=frozenset(['GET', 'POST']),
    raise_on_status=False
)
adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=10)
session.mount('http://', adapter)
session.mount('https://', adapter)

# Lambda function URL (updated port)
LAMBDA_URL = "http://localhost:9000/2015-03-31/functions/function/invocations"

def call_lambda_function(payload: dict, max_retries: int = 5) -> dict:
    """Call Lambda function with retries and proper error handling."""
    logger.info("Attempting to call Lambda function...")
    logger.debug(f"Payload: {payload}")
    
    for attempt in range(max_retries):
        try:
            logger.debug(f"Attempt {attempt + 1} of {max_retries}")
            response = session.post(
                LAMBDA_URL,
                json=payload,
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.debug(f"Lambda response: {result}")
                return result
            
            logger.warning(f"Lambda returned status code {response.status_code}")
            if attempt == max_retries - 1:
                raise Exception(f"Lambda function returned status code {response.status_code}")
                
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Connection error on attempt {attempt + 1}: {str(e)}")
            if attempt == max_retries - 1:
                raise Exception("Could not connect to Lambda container. Please ensure it is running on port 8080.")
            time.sleep(2 ** attempt)
            
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout on attempt {attempt + 1}")
            if attempt == max_retries - 1:
                raise Exception("Lambda container connection timed out. Please try again.")
            time.sleep(2 ** attempt)
            
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt + 1}: {str(e)}")
            if attempt == max_retries - 1:
                raise Exception(f"Error calling Lambda function: {str(e)}")
            time.sleep(2 ** attempt)
    
    raise Exception("Maximum retries exceeded")

# HTML template with Stripe.js integration
PAYMENT_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Stripe Connect Payment Interface</title>
    <script src="https://js.stripe.com/v3/"></script>
    <style>
        body { font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; }
        .form-row { margin: 10px 0; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input { width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; }
        button { background: #635BFF; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: pointer; width: 100%; margin-top: 20px; }
        button:hover { background: #524DFF; }
        button:disabled { background: #cccccc; cursor: not-allowed; }
        #card-element { padding: 15px; border: 1px solid #ccc; border-radius: 4px; background: white; }
        #card-errors { color: #dc3545; margin-top: 5px; font-size: 0.9em; min-height: 20px; }
        .section { margin-bottom: 20px; padding: 15px; border: 1px solid #e0e0e0; border-radius: 4px; }
        h3 { margin-top: 0; color: #32325d; }
        .StripeElement { width: 100%; }
        .StripeElement--focus { border-color: #80bdff; box-shadow: 0 0 0 0.2rem rgba(0,123,255,.25); }
        .StripeElement--invalid { border-color: #dc3545; }
        .StripeElement--complete { border-color: #28a745; }
        .spinner { display: none; }
        button.loading .spinner { display: inline-block; margin-right: 10px; }
        .hidden { display: none; }
        .alert { padding: 15px; margin-bottom: 20px; border: 1px solid transparent; border-radius: 4px; }
        .alert-success { color: #155724; background-color: #d4edda; border-color: #c3e6cb; }
        .alert-danger { color: #721c24; background-color: #f8d7da; border-color: #f5c6cb; }
        .help-text { color: #6c757d; font-size: 0.9em; margin-top: 5px; }
        #result-section { display: none; margin-top: 20px; }
        #result-section.visible { display: block; }
        .result-box { background: #f8f9fa; padding: 15px; border-radius: 4px; border: 1px solid #dee2e6; }
        .result-box pre { margin: 0; white-space: pre-wrap; }
    </style>
</head>
<body>
    <h2>Stripe Connect Payment Interface</h2>
    <div id="alert" class="alert hidden"></div>
    
    <form id="payment-form">
        <div class="section">
            <h3>Payment Query</h3>
            <div class="form-row">
                <label for="query">Payment Instructions</label>
                <input type="text" id="query" required 
                       placeholder="Example: Pay $50 to account acct_123456789">
                <div class="help-text">
                    Format: "Pay $[amount] to account [account_id]"<br>
                    Example: "Pay $100 to account acct_123456789"
                </div>
            </div>
        </div>

        <div class="section">
            <h3>Customer Information</h3>
            <div class="form-row">
                <label for="name">Full Name</label>
                <input type="text" id="name" required placeholder="John Doe">
            </div>
            <div class="form-row">
                <label for="email">Email</label>
                <input type="email" id="email" required placeholder="john@example.com">
            </div>
            <div class="form-row">
                <label for="phone">Phone Number</label>
                <input type="tel" id="phone" placeholder="+1234567890">
            </div>
            <div class="form-row">
                <label for="address">Address</label>
                <input type="text" id="address" placeholder="123 Main St">
            </div>
            <div class="form-row">
                <label for="city">City</label>
                <input type="text" id="city" placeholder="San Francisco">
            </div>
            <div class="form-row">
                <label for="state">State</label>
                <input type="text" id="state" placeholder="CA">
            </div>
            <div class="form-row">
                <label for="zip">ZIP Code</label>
                <input type="text" id="zip" placeholder="94105">
            </div>
        </div>

        <div class="section">
            <h3>Card Information</h3>
            <div class="form-row">
                <div id="card-element"></div>
                <div id="card-errors" role="alert"></div>
            </div>
        </div>

        <button type="submit">
            <span class="spinner">↻</span>
            <span class="button-text">Process Payment</span>
        </button>
    </form>

    <div id="result-section">
        <h3>Transaction Result</h3>
        <div class="result-box">
            <pre id="result-content"></pre>
        </div>
    </div>

    <script>
        const stripe = Stripe('{{ stripe_public_key }}');
        const elements = stripe.elements();
        
        // Create and mount the card Element
        const cardElement = elements.create('card', {
            style: {
                base: {
                    color: '#32325d',
                    fontFamily: '"Helvetica Neue", Helvetica, sans-serif',
                    fontSmoothing: 'antialiased',
                    fontSize: '16px',
                    '::placeholder': { color: '#aab7c4' }
                },
                invalid: {
                    color: '#fa755a',
                    iconColor: '#fa755a'
                }
            }
        });
        cardElement.mount('#card-element');

        // Show alert message
        function showAlert(message, type) {
            const alert = document.getElementById('alert');
            alert.className = `alert alert-${type}`;
            alert.textContent = message;
            alert.classList.remove('hidden');
            setTimeout(() => alert.classList.add('hidden'), 5000);
        }

        // Show result
        function showResult(result) {
            const resultSection = document.getElementById('result-section');
            const resultContent = document.getElementById('result-content');
            resultContent.textContent = JSON.stringify(result, null, 2);
            resultSection.classList.add('visible');
        }

        // Handle form submission
        const form = document.getElementById('payment-form');
        const submitButton = form.querySelector('button[type="submit"]');

        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            
            submitButton.disabled = true;
            submitButton.classList.add('loading');
            
            const query = document.getElementById('query').value.trim();
            
            // Basic query validation
            if (!query.toLowerCase().includes('pay') || !query.includes('acct_')) {
                showAlert('Invalid query format. Please use format: "Pay $[amount] to account [account_id]"', 'danger');
                submitButton.disabled = false;
                submitButton.classList.remove('loading');
                return;
            }

            try {
                const billingDetails = {
                    name: document.getElementById('name').value,
                    email: document.getElementById('email').value,
                    phone: document.getElementById('phone').value,
                    address: {
                        line1: document.getElementById('address').value,
                        city: document.getElementById('city').value,
                        state: document.getElementById('state').value,
                        postal_code: document.getElementById('zip').value,
                    }
                };

                const {paymentMethod, error} = await stripe.createPaymentMethod({
                    type: 'card',
                    card: cardElement,
                    billing_details: billingDetails
                });

                if (error) {
                    showAlert(error.message, 'danger');
                    return;
                }

                const response = await fetch('/process-payment', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        query: query,
                        payment_method_id: paymentMethod.id,
                        name: billingDetails.name,
                        email: billingDetails.email,
                        phone: billingDetails.phone,
                        address: billingDetails.address
                    })
                });

                const result = await response.json();
                if (result.error) {
                    showAlert(result.error, 'danger');
                } else {
                    showAlert('Payment processed successfully!', 'success');
                    showResult(result);
                    form.reset();
                    cardElement.clear();
                }
            } catch (err) {
                showAlert(err.message, 'danger');
            } finally {
                submitButton.disabled = false;
                submitButton.classList.remove('loading');
            }
        });

        // Handle real-time validation errors
        cardElement.on('change', ({error}) => {
            const displayError = document.getElementById('card-errors');
            if (error) {
                displayError.textContent = error.message;
            } else {
                displayError.textContent = '';
            }
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(
        PAYMENT_TEMPLATE, 
        stripe_public_key=os.getenv('STRIPE_PUBLISHABLE_KEY')
    )

@app.route('/process-payment', methods=['POST'])
def process_payment():
    try:
        data = request.json
        logger.info(f"Processing payment request: {data['query']}")
        
        # Create a Customer with full details
        try:
            customer = stripe.Customer.create(
                name=data['name'],
                email=data['email'],
                phone=data['phone'],
                address=data['address'],
                description="Connect payment customer",
                metadata={
                    'source': 'test_ui',
                    'query': data['query']
                }
            )
            logger.info(f"Created customer: {customer.id}")
        except stripe.error.StripeError as e:
            logger.error(f"Stripe customer creation failed: {str(e)}")
            return jsonify({"error": str(e)}), 400

        try:
            # Attach the payment method to the customer
            stripe.PaymentMethod.attach(
                data['payment_method_id'],
                customer=customer.id
            )
            logger.info(f"Attached payment method to customer")

            # Set this customer as the default payment method
            stripe.Customer.modify(
                customer.id,
                invoice_settings={
                    'default_payment_method': data['payment_method_id']
                }
            )
            logger.info("Set default payment method")
        except stripe.error.StripeError as e:
            logger.error(f"Payment method attachment failed: {str(e)}")
            stripe.Customer.delete(customer.id)
            return jsonify({"error": str(e)}), 400

        # Prepare the payload for Lambda function
        lambda_payload = {
            "body": json.dumps({
                "query": data['query'],
                "customer": {
                    "id": customer.id,
                    "payment_method_id": data['payment_method_id'],
                    "name": data['name'],
                    "email": data['email'],
                    "phone": data['phone'],
                    "address": data['address']
                }
            })
        }

        try:
            logger.info("Calling Lambda function...")
            result = call_lambda_function(lambda_payload)
            logger.info("Lambda function call successful")
            
            # Parse the result
            if isinstance(result, dict) and 'body' in result:
                try:
                    body = json.loads(result['body']) if isinstance(result['body'], str) else result['body']
                    return jsonify({
                        "success": True,
                        "message": body.get('result', 'Payment processed'),
                        "details": body
                    })
                except (json.JSONDecodeError, AttributeError) as e:
                    logger.error(f"Failed to parse Lambda response: {str(e)}")
                    raise Exception("Invalid response from Lambda function")
            else:
                raise Exception("Invalid response format from Lambda function")
                
        except Exception as lambda_error:
            logger.error(f"Lambda function call failed: {str(lambda_error)}")
            try:
                stripe.Customer.delete(customer.id)
                logger.info("Cleaned up customer after Lambda failure")
            except stripe.error.StripeError as e:
                logger.warning(f"Failed to clean up customer: {str(e)}")
            return jsonify({
                "error": str(lambda_error),
                "details": "Lambda function call failed. Please try again."
            }), 500

    except Exception as e:
        error_message = str(e)
        logger.error(f"Payment processing error: {error_message}")
        return jsonify({
            "error": error_message,
            "details": "Please ensure the Lambda container is running and try again."
        }), 400

if __name__ == '__main__':
    print("\n��� Starting Stripe Connect Payment Interface")
    print("Make sure the Lambda container is running with:")
    print("docker run -p 9000:8080 stripe-payment-crew\n")
    app.run(debug=True, port=5000)
