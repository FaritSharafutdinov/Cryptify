# Backend - Useful Commands

## Environment Setup

### Conda Environment
```bash
# Create conda environment
conda create -n criptify python=3.9 -y

# Activate environment
conda activate criptify

# Install dependencies
pip install -r backend/requirements.txt
```

## Development Commands

### Local Development (without Docker)
```bash
# Navigate to project
cd Cryptify/

# Activate environment
conda activate criptify

# Run backend locally (requires PostgreSQL)
cd backend
python run_dev.py
```

## Docker Commands

### Docker Operations
```bash
# Start all services
docker-compose up -d

# Start only PostgreSQL
docker-compose up -d postgres

# Start only backend
docker-compose up -d backend

# View logs
docker-compose logs -f
docker-compose logs -f backend
docker-compose logs -f postgres

# Stop services
docker-compose down

# Rebuild and start
docker-compose up --build -d

# Clean up
docker-compose down -v
docker system prune -a
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

## API Endpoints

### Health Check
```bash
GET /health
# Returns: {"status": "healthy", "timestamp": "...", "service": "criptify-backend"}
```

### Historical Data
```bash
GET /history?from_time=2024-01-01T00:00:00&to_time=2024-01-07T23:59:59
# Returns: Combined raw_bars and predictions data
```

### Latest Predictions
```bash
GET /predictions/latest?limit=10
# Returns: Latest ML predictions
```

### Model Metrics
```bash
GET /metrics/latest
# Returns: Latest model performance metrics
```

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
│   ├── requirements.txt    # Python dependencies
│   ├── Dockerfile         # Backend container configuration
│   ├── run_dev.py         # Development server runner
│   └── env.example        # Environment variables template
├── docker/                 # Docker configuration
│   └── init.sql           # Database initialization script
├── scripts/               # Utility scripts
│   └── start.sh           # Project startup script
├── docker-compose.yml     # Multi-container orchestration
├── README.md              # Main documentation
└── COMMANDS.md            # This file
```

## Environment Variables

Create a `.env` file in the backend directory:

```bash
# Copy template
cp backend/env.example backend/.env

# Edit with your settings
nano backend/.env
```

Required variables:
- `DATABASE_URL`: PostgreSQL connection string
- `API_HOST`: API server host (default: 0.0.0.0)
- `API_PORT`: API server port (default: 8000)


