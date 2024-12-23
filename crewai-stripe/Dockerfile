# Use the official AWS Lambda Python base image -- perhaps we should use 3.13?
FROM public.ecr.aws/lambda/python:3.12

# Set the working directory
WORKDIR /var/task

# Copy the project files into the container
COPY . .

# Install requirements
RUN pip install -r requirements.txt

RUN crewai install
# Set the command to the Lambda handler
CMD ["lambda_function.lambda_handler"]
