FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed for lxml, some Python packages)
RUN apt-get update && apt-get install -y \
    gcc \
    libxml2-dev \
    libxslt1-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Install the package in editable mode
RUN pip install -e .

# Create data directory
RUN mkdir -p /app/data /app/output

# Default command – show help
ENTRYPOINT ["python", "-m", "src.cli.main"]
CMD ["--help"]
