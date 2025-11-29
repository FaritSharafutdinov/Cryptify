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

# Install Python dependencies
# Install numpy first, then scikit-learn to ensure binary compatibility
RUN pip install --no-cache-dir numpy==1.26.3

# Install other base dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install ML scripts dependencies
# Note: pandas_ta 0.3.14b0 is compatible with numpy 1.26.3
# Newer versions (0.4+) require numpy>=2.2.6
RUN pip install --no-cache-dir \
    "pandas_ta==0.3.14b0" \
    ccxt \
    yfinance \
    xgboost \
    tensorflow

# Reinstall scikit-learn to ensure binary compatibility with numpy
# This fixes the "numpy.dtype size changed" error
RUN pip install --no-cache-dir --force-reinstall scikit-learn==1.4.0

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
