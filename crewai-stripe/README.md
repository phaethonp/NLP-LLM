# Stripe Payment Processing Crew -- Lambda



This is the Lambda function for the Stripe Payment Processing Crew.

## Build the Docker image
`docker build -t stripe-payment-processing-crew .`

## Run the Docker image
`docker run -p 9000:8080 stripe-payment-processing-crew`

`python test_docker.py`


## Deploy the Lambda function
`aws configure` 

`aws ecr create-repository --repository-name stripe-payment-processing-crew --region your-region`

`aws ecr get-login-password --region your-region | docker login --username AWS --password-stdin 123456789012.dkr.ecr.your-region.amazonaws.com`

`docker tag stripe-payment-processing-crew:latest 123456789012.dkr.ecr.your-region.amazonaws.com/stripe-payment-processing-crew:latest`
here 123456789012 is your AWS account number

`docker push 123456789012.dkr.ecr.your-region.amazonaws.com/stripe-payment-processing-crew:latest`
