# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the backend code into the container
COPY . .

# Expose port 8000 for the API
EXPOSE 8000

# The default command to run when the container starts.
# This will be overridden in the docker-compose.yml for the api service.
CMD ["python", "core/main.py"]