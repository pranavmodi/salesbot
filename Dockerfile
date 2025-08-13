# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for WeasyPrint and PostgreSQL
RUN apt-get clean && \
    apt-get update --fix-missing && \
    apt-get install -y --no-install-recommends \
    gcc \
    pkg-config \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libglib2.0-0 \
    libfontconfig1 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make start script executable
RUN chmod +x start.sh

# Set Python path for proper module imports
ENV PYTHONPATH=/app

# Expose port (Railway will set PORT env var)
EXPOSE $PORT

# Use our startup script
CMD ["./start.sh"]