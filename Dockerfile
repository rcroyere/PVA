FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for reports and logs
RUN mkdir -p reports logs

# Set Python to run in unbuffered mode
ENV PYTHONUNBUFFERED=1

# Default command
ENTRYPOINT ["python", "main.py"]
CMD ["--help"]
