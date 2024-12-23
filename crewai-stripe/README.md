# Stripe Payment Agent

## Overview
This is a stripe Payment agent that can create payment links and connect payments.
It uses a default customer and test payment method for testing purposes.
You can ask the agent to create a payment link, or transfer a payment to an account(give the account id). 

## Usage

Fill .env with the appropriate information:

```
MODEL=provider/model_name 
PROVIDER_API_KEY="your_api_key"
STRIPE_API_KEY="your_stripe_api_key"
```
These were tested using Groq, as it's free API is sufficient. Model tested was llama-3.3-70b-versatile.


## Running the agent

Set up a virtual environment:

```
conda create -n crew python=3.12
conda activate crew
```

Install crewai:

``` 
pip install crewai
```

Run the agent:

```
crewai run
```

