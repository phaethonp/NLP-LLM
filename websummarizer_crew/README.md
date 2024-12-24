# Web Summarizer Lambda Function with Stripe Integration

This Lambda function provides a web page summarization service with Stripe payment integration. It charges $5 per summary and uses CrewAI agents to process payments and generate summaries.

## Features

- Web page content summarization using Selenium
- Stripe payment integration ($5 per summary)
- CrewAI agents for payment processing and content summarization
- AWS Lambda deployment ready with Docker

## Prerequisites

- AWS Account
- Stripe Account
- Docker installed locally

## Environment Variables

Create a `.env` file with the following variables:

```
STRIPE_SECRET_KEY=your_stripe_secret_key
OPENAI_API_KEY=your_openai_api_key
```

## Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run tests:
```bash
python -m pytest tests/
```

## Docker Build and Deployment

1. Build the Docker image:
```bash
docker build -t web-summarizer-lambda .
```

2. Test locally:
```bash
docker run -p 9000:8080 web-summarizer-lambda
```

3. Push to AWS ECR:
```bash
aws ecr get-login-password --region region | docker login --username AWS --password-stdin account.dkr.ecr.region.amazonaws.com
docker tag web-summarizer-lambda:latest account.dkr.ecr.region.amazonaws.com/web-summarizer-lambda:latest
docker push account.dkr.ecr.region.amazonaws.com/web-summarizer-lambda:latest
```

## API Usage

Send a POST request to the Lambda function endpoint:

```json
{
    "body": {
        "url": "https://example.com/page-to-summarize",
        "customer": {
            "id": "cus_xxx",
            "payment_method_id": "pm_xxx",
            "email": "customer@example.com"
        }
    }
}
```

Response format:

```json
{
    "success": true,
    "summary": "Three key points from the webpage...",
    "payment_intent": "pi_xxx"
}
```

## Architecture

The service uses two CrewAI agents:
1. Billing Agent: Handles Stripe payment processing
2. Web Summarizer Agent: Extracts and summarizes web content

The process is sequential:
1. Payment is processed first
2. Upon successful payment, the web content is summarized
3. Summary is returned to the customer

## Error Handling

The service handles various error cases:
- Invalid input validation
- Payment processing errors
- Web scraping failures
- Content summarization issues

All errors are properly logged and returned with appropriate HTTP status codes.
