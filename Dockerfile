# Use the official Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install "fastapi[standard]" uvicorn

# Copy the entire project inside the container
COPY . /app

# Create a non-root user for security
RUN useradd -m foundtel && chown -R foundtel /app
USER foundtel

# Cloud Run injects the PORT environment variable. We default to 8080 if not provided.
ENV PORT=8080
EXPOSE $PORT

# Command to run the FastAPI app on the specified PORT
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port $PORT"]
