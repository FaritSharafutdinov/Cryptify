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
Cryptify/
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

## 🚀 Quick Start (Local Development)

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

### 3. Initial Data Setup

```bash
# Collect historical data (this may take 10-30 minutes)
curl -X POST http://localhost:8000/ml/data-collector/run \
  -H "Content-Type: application/json" \
  -d '{"mode": "batch", "timeout": 3600}'

# Train models (this may take 30-60 minutes)
curl -X POST http://localhost:8000/ml/trainer/run \
  -H "Content-Type: application/json" \
  -d '{"mode": "batch", "timeout": 7200}'

# Generate predictions
curl -X POST http://localhost:8000/ml/predictor/run \
  -H "Content-Type: application/json" \
  -d '{"timeout": 300}'
```

Or use the API documentation at `http://localhost:8000/docs` to run these endpoints interactively.

## 🌐 Deployment on Server

### Prerequisites

- Ubuntu 20.04+ / Debian 11+ (or other Linux distribution)
- Docker and Docker Compose installed
- Git installed
- Minimum 4GB RAM, 20GB free space
- Open ports: 22 (SSH), 5173 (Frontend), 8000 (Backend API, optional)

### Step 1: Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose (use built-in version)
# Docker Compose v2 is included with Docker

# Install Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Git (if not installed)
sudo apt install git -y
```

### Step 2: Clone and Setup Project

```bash
# Clone repository
cd ~
mkdir -p projects
cd projects
git clone https://github.com/FaritSharafutdinov/Cryptify cryptify
cd cryptify
git checkout dev

# Fix permissions for scripts directory
chmod -R 755 scripts/
```

### Step 3: Start Backend Services

```bash
# Start PostgreSQL and FastAPI backend
docker-compose up -d

# Check status
docker-compose ps

# Verify backend is running
curl http://localhost:8000/health
```

### Step 4: Start Frontend

```bash
# Install dependencies
cd ~/projects/cryptify/frontend
npm install

# Start in background using screen
sudo apt install screen -y
screen -S frontend
npm run dev -- --host 0.0.0.0
# Press Ctrl+A, then D to detach

# Or use nohup
nohup npm run dev -- --host 0.0.0.0 > frontend.log 2>&1 &
```

### Step 5: Configure Firewall

```bash
# Allow required ports
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 5173/tcp  # Frontend
sudo ufw allow 8000/tcp  # Backend API (optional)

# Enable firewall
sudo ufw enable
sudo ufw status
```

### Step 6: Initial Data Collection and Training

```bash
# Collect historical data (10-30 minutes)
curl -X POST http://localhost:8000/ml/data-collector/run \
  -H "Content-Type: application/json" \
  -d '{"mode": "batch", "timeout": 3600}'

# Train models (30-60 minutes)
curl -X POST http://localhost:8000/ml/trainer/run \
  -H "Content-Type: application/json" \
  -d '{"mode": "batch", "timeout": 7200}'

# Generate predictions
curl -X POST http://localhost:8000/ml/predictor/run \
  -H "Content-Type: application/json" \
  -d '{"timeout": 300}'
```

### Step 7: Setup Automation (Cron Jobs)

```bash
# Setup automated tasks
./scripts/setup_cron.sh

# Verify cron jobs
crontab -l
```

**Automation Schedule:**
- **Data Collection**: Every hour (at minute 0)
- **Model Retraining**: Every Sunday at 2:00 AM

### Step 8: Access Application

After setup, the application will be available at:
- **Frontend**: `http://YOUR_SERVER_IP:5173`
- **Backend API**: `http://YOUR_SERVER_IP:8000`
- **API Documentation**: `http://YOUR_SERVER_IP:8000/docs`

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
  - Body: `{"mode": "batch" | "incremental", "timeout": 3600}`
- `POST /ml/trainer/run` - Train models
  - Body: `{"mode": "batch" | "retrain", "timeout": 7200}`
- `POST /ml/predictor/run` - Generate predictions
  - Body: `{"timeout": 300}`

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

## 🔄 Updating Project

```bash
# Pull latest changes
git pull origin dev

# Restart services
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Restart frontend (if needed)
cd frontend
npm install  # if package.json changed
# Restart using screen or nohup
```

## 📝 Useful Commands

### Monitoring

```bash
# Check container status
docker-compose ps

# View backend logs
docker-compose logs -f backend

# Check cron logs
tail -f logs/cron_data_collector.log
tail -f logs/cron_model_trainer.log

# Check resource usage
docker stats
```

### Troubleshooting

```bash
# Check backend health
curl http://localhost:8000/health

# Check script status
curl http://localhost:8000/ml/scripts/status/data_collector.py

# View recent logs
docker-compose logs --tail=50 backend

# Restart backend
docker-compose restart backend
```

## 📚 Additional Documentation

- **Backend Guide**: See `backend/BACKEND_GUIDE.md`
- **ML Scripts API**: See `backend/ML_SCRIPTS_API.md`
- **Automation**: See `scripts/README_AUTOMATION.md`

## 📝 License

See [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📧 Support

For issues and questions, please open an issue on GitHub.
