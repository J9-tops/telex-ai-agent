FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy application code
COPY src/ ./src/

# Expose port
EXPOSE 5001

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=5001

# Run the application
CMD ["python", "src/main.py"]