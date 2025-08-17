# Use Playwright's official Python image with Chrome pre-installed
FROM mcr.microsoft.com/playwright/python:v1.41.0-focal

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application
COPY . .

# Install Playwright browsers (Chromium only for efficiency)
RUN playwright install chromium

# Railway handles user security automatically

# Set environment variables
ENV PYTHONPATH=/app
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Expose port
EXPOSE 8000

# Health check will be handled by Railway

# Start the FastAPI server with dynamic port
CMD ["sh", "-c", "uvicorn server.server:app --host 0.0.0.0 --port ${PORT:-8000}"]

