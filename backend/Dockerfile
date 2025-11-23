FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies (includes numpy and scikit-learn)
RUN pip install --no-cache-dir -r requirements.txt

# Install ML scripts dependencies
# Note: pandas_ta requires Python 3.12+
# numpy and scikit-learn are already installed from requirements.txt
RUN pip install --no-cache-dir \
    pandas_ta \
    ccxt \
    yfinance \
    xgboost \
    tensorflow

# Reinstall numpy and scikit-learn to ensure binary compatibility
# This fixes the "numpy.dtype size changed" error
RUN pip install --no-cache-dir --force-reinstall --no-deps \
    numpy==1.26.3 \
    scikit-learn==1.4.0

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
