# Cryptify - BTC Price Prediction Application

A web application for BTC price prediction with multiple time horizons and ML models, built with Docker containerization.

## Architecture

- **Backend**: FastAPI (Python) - REST API for data access
- **Database**: PostgreSQL - Stores historical data and predictions
- **ML Service**: Python - Data collection, feature engineering, and model training
- **Frontend**: React/Node.js - User interface with charts
- **Containerization**: Docker & Docker Compose

## Project Structure

```
Cryptify/
├── backend/                 # FastAPI backend service
│   ├── app/                # FastAPI application
│   │   ├── main.py         # Main FastAPI app with endpoints
│   │   └── __init__.py
│   ├── models/             # Database models
│   │   ├── database.py     # SQLAlchemy models and DB connection
│   │   └── __init__.py
│   ├── services/           # 🆕 Business logic services
│   │   ├── model_service.py # ML model management service
│   │   └── __init__.py
│   ├── trained_models/     # 🆕 Directory for ML model files
│   ├── requirements.txt    # Python dependencies
│   ├── Dockerfile         # Backend container configuration
│   ├── run_dev.py         # Development server runner
│   ├── API_DOCUMENTATION.md # 🆕 Detailed API documentation
│   └── env.example        # Environment variables template
├── docker/                 # Docker configuration
│   └── init.sql           # Database initialization script
├── docker-compose.yml     # Multi-container orchestration
└── README.md              # This file
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.9+ (for local development)
- Conda (optional, for environment management)

### 1. Environment Setup

```bash
# Clone and navigate to project
cd /path/to/Cryptify

# Create conda environment (optional)
conda create -n criptify python=3.9 -y
conda activate criptify

# Install dependencies
pip install -r backend/requirements.txt
```

### 2. Environment Configuration

```bash
# Copy environment template
cp backend/env.example backend/.env

# Edit .env file with your database credentials
nano backend/.env
```

### 3. Docker Deployment

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f backend
```

### 4. Local Development

```bash
# Start PostgreSQL only
docker-compose up -d postgres

# Run backend locally
cd backend
python run_dev.py
```

## API Endpoints

### Core Endpoints

#### Health Check
```bash
GET /health
```

#### Historical Data
```bash
GET /history?from_time=2024-01-01T00:00:00&to_time=2024-01-07T23:59:59
```

#### Latest Predictions
```bash
GET /predictions/latest?limit=10&model_name=baseline&horizon=3
```

#### Model Metrics
```bash
GET /metrics/latest?model_name=baseline
```

### 🆕 Model Management Endpoints

#### List Available Models
```bash
GET /models
```

#### Register New Model
```bash
POST /models/register
Content-Type: application/json

{
  "model_name": "random_forest_v1",
  "model_type": "RandomForest",
  "prediction_horizons": [1, 3, 24, 168],
  "file_path": "/app/trained_models/rf_model.joblib"
}
```

### 🆕 Prediction Endpoints

#### Make Prediction (POST)
```bash
POST /predict
Content-Type: application/json

{
  "model_name": "baseline",
  "prediction_horizon": 24,
  "save_to_db": true
}
```

#### Make Prediction (GET)
```bash
GET /predict/{model_name}/{horizon}?save_to_db=true

# Example
GET /predict/baseline/3
GET /predict/baseline/24
GET /predict/baseline/168
```

### Supported Time Horizons

| Horizon | Hours | Use Case |
|---------|-------|----------|
| 1h      | 1     | Very short-term trading |
| 3h      | 3     | Short-term trading |
| 1d      | 24    | Day trading |
| 1w      | 168   | Swing trading |

**Note**: Check model's supported horizons via `GET /models`

## Database Schema

### Tables

1. **raw_bars** - OHLCV data from Bybit API
2. **predictions** - ML model predictions (now includes `model_name` and configurable `prediction_horizon`)
3. **model_metrics** - Model performance metrics
4. **ml_features** - Engineered features for ML pipeline
5. **ml_models** - 🆕 Model registry for managing multiple trained models

## 📚 Documentation

For detailed API documentation, see [API_DOCUMENTATION.md](backend/API_DOCUMENTATION.md)

Interactive API docs available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Usage Examples

### Make a Prediction

```bash
# Using cURL
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "baseline",
    "prediction_horizon": 24,
    "save_to_db": true
  }'

# Or use the GET endpoint
curl http://localhost:8000/predict/baseline/3
```

### List Available Models

```bash
curl http://localhost:8000/models
```

### Get Predictions with Filters

```bash
# Get last 5 predictions from baseline model with 24h horizon
curl "http://localhost:8000/predictions/latest?model_name=baseline&horizon=24&limit=5"
```

### Python Example

```python
import requests

# Make a prediction
response = requests.post(
    "http://localhost:8000/predict",
    json={
        "model_name": "baseline",
        "prediction_horizon": 3,
        "save_to_db": True
    }
)
result = response.json()
print(f"Predicted price in 3h: ${result['predicted_value']:.2f}")
print(f"Current price: ${result['current_price']:.2f}")
```

## Useful Commands

### Docker Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Rebuild and start
docker-compose up --build -d

# View logs
docker-compose logs -f [service_name]

# Execute commands in container
docker-compose exec backend bash
docker-compose exec postgres psql -U criptify_user -d criptify_db

# Clean up
docker-compose down -v  # Removes volumes
docker system prune -a  # Removes all unused containers/images
```

### Database Commands

```bash
# Connect to database
docker-compose exec postgres psql -U criptify_user -d criptify_db

# Backup database
docker-compose exec postgres pg_dump -U criptify_user criptify_db > backup.sql

# Restore database
docker-compose exec -T postgres psql -U criptify_user -d criptify_db < backup.sql
```

### Development Commands

```bash
# Run backend locally
cd backend
python run_dev.py

# Install new dependencies
pip install package_name
pip freeze > requirements.txt

# Run tests (when implemented)
pytest

# Format code
black .
isort .
```


## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://criptify_user:criptify_password@localhost:5432/criptify_db` |
| `API_HOST` | API server host | `0.0.0.0` |
| `API_PORT` | API server port | `8000` |
| `ENVIRONMENT` | Environment type | `development` |


## License

This project is licensed under the MIT License - see the LICENSE file for details.
