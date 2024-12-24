import pytest
from websummarizeragent.crew import WebSummarizer
import stripe
import os
from dotenv import load_dotenv

load_dotenv()

@pytest.fixture
def web_summarizer():
    return WebSummarizer()

@pytest.fixture
def test_customer():
    # Create a test customer with a test card
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

def test_process_payment(web_summarizer, test_customer):
    payment_intent_id = web_summarizer.process_payment(test_customer)
    assert payment_intent_id is not None
    
    # Verify payment intent
    payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
    assert payment_intent.status == 'succeeded'
    assert payment_intent.amount == 500  # $5.00

def test_summarize_webpage(web_summarizer):
    url = "https://example.com"
    summary = web_summarizer.summarize_webpage(url)
    assert summary is not None
    assert isinstance(summary, str)

def test_handle_request(web_summarizer, test_customer):
    url = "https://example.com"
    result = web_summarizer.handle_request(url, test_customer)
    
    assert result is not None
    assert isinstance(result, dict)
    assert 'success' in result
    
    if result.get('success'):
        assert 'summary' in result
        assert 'payment_intent' in result
    else:
        assert 'error' in result
        assert 'details' in result 