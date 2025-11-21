# Cryptify - BTC Price Prediction Application

A full-stack web application for Bitcoin price prediction using machine learning models, featuring real-time data collection, multiple prediction horizons, and interactive charts.

## 🏗️ Architecture

- **Frontend**: React + TypeScript + Vite - Modern UI with interactive charts
- **Backend**: FastAPI (Python) - REST API for data access
- **Database**: PostgreSQL - Stores historical data, features, and predictions
- **ML Pipeline**: Python scripts - Data collection, feature engineering, model training, and inference
- **Containerization**: Docker & Docker Compose

## 📁 Project Structure

```
Cryptify-dev/
├── frontend/              # React frontend application
│   ├── src/              # Source code
│   │   ├── components/   # React components
│   │   ├── services/     # API service
│   │   └── types/        # TypeScript types
│   ├── package.json      # Node.js dependencies
│   └── vite.config.ts    # Vite configuration
├── backend/              # FastAPI backend service
│   ├── app/              # FastAPI application
│   │   └── main.py       # Main API endpoints
│   ├── models/           # Database models (SQLAlchemy)
│   ├── services/         # Business logic services
│   ├── schemas/          # Pydantic schemas
│   ├── requirements.txt  # Python dependencies
│   └── Dockerfile        # Backend container config
├── scripts/              # ML pipeline scripts
│   ├── data_collector.py      # Data collection from exchanges
│   ├── multi_model_trainer.py # Model training
│   ├── predictor.py           # Inference/prediction
│   └── requirements.txt       # ML dependencies
├── docker/               # Docker configuration
│   └── init.sql         # Database initialization
└── docker-compose.yml   # Multi-container orchestration
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for frontend development)
- Python 3.12+ (for local development, optional)

### 1. Start Backend Services

```bash
# Start PostgreSQL and FastAPI backend
docker-compose up -d

# Check services status
docker-compose ps

# View backend logs
docker-compose logs -f backend
```

Backend will be available at: `http://localhost:8000`

- API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### 2. Start Frontend

```bash
cd frontend

# Install dependencies (first time only)
npm install

# Start development server
npm run dev
```

Frontend will be available at: `http://localhost:5173`

### 3. Collect Data and Generate Predictions

```bash
# Collect historical data (this may take a few minutes)
curl -X POST http://localhost:8000/ml/data-collector/run \
  -H "Content-Type: application/json" \
  -d '{"mode": "incremental", "timeout": 1800}'

# Generate predictions
curl -X POST http://localhost:8000/ml/predictor/run \
  -H "Content-Type: application/json" \
  -d '{"timeout": 300}'
```

Or use the API documentation at `http://localhost:8000/docs` to run these endpoints interactively.

## 📊 Features

- **Real-time Data Collection**: Automated collection of BTC/USDT OHLCV data from Binance
- **Feature Engineering**: Technical indicators (RSI, MACD, ATR, etc.) and temporal features
- **Multiple ML Models**:
  - Linear Regression
  - XGBoost
  - LSTM (Neural Network)
- **Multiple Prediction Horizons**: 6h, 12h, 24h ahead
- **Interactive Charts**: Real-time price charts with prediction overlays
- **RESTful API**: Comprehensive API for data access and ML operations

## 🔧 Configuration

### Environment Variables

Backend environment variables (see `backend/env.example`):

- `DATABASE_URL`: PostgreSQL connection string
- `API_HOST`: API host (default: 0.0.0.0)
- `API_PORT`: API port (default: 8000)

Frontend environment variables (optional):

- `VITE_API_URL`: Backend API URL (default: `/api` - uses proxy)

### Database

Default PostgreSQL credentials (configured in `docker-compose.yml`):

- Database: `criptify_db`
- User: `criptify_user`
- Password: `criptify_password`
- Port: `5432`

## 📡 API Endpoints

### Health & Status

- `GET /health` - Health check
- `GET /ml/scripts/status/{script_name}` - Check ML script status

### Data Access

- `GET /history` - Get historical data and predictions
- `GET /features/latest` - Get latest features
- `GET /predictions/latest` - Get latest predictions

### ML Operations

- `POST /ml/data-collector/run` - Run data collection
- `POST /ml/predictor/run` - Generate predictions
- `POST /ml/trainer/run` - Train models

See full API documentation at `http://localhost:8000/docs` when backend is running.

## 🛠️ Development

### Backend Development

```bash
# Run backend locally (without Docker)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

### ML Scripts Development

```bash
cd scripts
pip install -r requirements.txt

# Run data collection
python data_collector.py

# Train models
python multi_model_trainer.py

# Generate predictions
python predictor.py
```

## 🐳 Docker Commands

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f [service_name]

# Rebuild containers
docker-compose build --no-cache

# Access PostgreSQL
docker-compose exec postgres psql -U criptify_user -d criptify_db

# Access backend container
docker-compose exec backend bash
```

## 📝 License

See [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 🚀 Deployment

For detailed deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

### Quick Deployment Steps

1. Clone repository on your server
2. Run `docker-compose up -d`
3. Setup cron jobs: `./scripts/setup_cron.sh`
4. Configure Nginx (see DEPLOYMENT.md)
5. Run initial data collection and training

### Automation

The project includes automated tasks:

- **Data Collection**: Runs every hour via cron
- **Model Retraining**: Runs every Sunday at 2 AM via cron

See `scripts/` directory for automation scripts.

## 📧 Support

For issues and questions, please open an issue on GitHub.
