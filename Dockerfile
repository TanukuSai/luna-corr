# Production and Reproducibility Container for LUNA-CORR
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for OpenCV and image I/O
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy repository source code
COPY lunacorr/ lunacorr/
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# Copy test suite and benchmark runners
COPY tests/ tests/
COPY BENCHMARK_MANIFEST.md .

# Default entrypoint runs unit tests to verify installation
CMD ["pytest", "tests/"]
