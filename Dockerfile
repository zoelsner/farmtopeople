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

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Set environment variables
ENV PYTHONPATH=/app
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Expose port
EXPOSE 8000

# Start the FastAPI server
CMD ["uvicorn", "server.server:app", "--host", "0.0.0.0", "--port", "8000"]
