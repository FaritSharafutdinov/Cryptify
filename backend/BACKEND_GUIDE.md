# Backend Updates

## Architecture

### Components

1. **Model Service** (`services/model_service.py`)
   - Manages ML model lifecycle
   - Handles model loading and caching
   - Feature engineering
   - Prediction generation

2. **ML Models Registry** (Database table: `ml_models`)
   - Central registry for all trained models
   - Tracks model metadata and capabilities
   - Supports model versioning

3. **Trained Models Directory** (`trained_models/`)
   - Stores serialized model files (`.joblib`)
   - Mounted as Docker volume for persistence

## Key Features

### 1. Time Horizon Switcher

Models can now support multiple prediction horizons:

```python
# Example: Register a model with multiple horizons
{
    "model_name": "my_model",
    "prediction_horizons": [1, 3, 24, 168]  # 1h, 3h, 1d, 1w
}
```

**Implementation Details:**
- Horizon is passed as parameter to `make_prediction()`
- Feature engineering adapts based on horizon
- Validation ensures model supports requested horizon

### 2. Model Switcher

Switch between different trained models:

```python
# List all available models
GET /models

# Use specific model for prediction
POST /predict
{
    "model_name": "random_forest_v1",
    "prediction_horizon": 24
}
```

**Model Registration:**
```python
POST /models/register
{
    "model_name": "random_forest_v1",
    "model_type": "RandomForest",
    "prediction_horizons": [1, 3, 24],
    "file_path": "/app/trained_models/rf_model.joblib",
    "feature_config": {
        "features": ["lag_1h", "lag_2h", "lag_24h", "SMA_10h"]
    }
}
```

### 3. Predict Endpoint

Two ways to make predictions:

**POST Method (Recommended):**
```bash
POST /predict
{
    "model_name": "baseline",
    "prediction_horizon": 3,
    "save_to_db": true
}
```

**GET Method (Quick):**
```bash
GET /predict/baseline/3?save_to_db=true
```

## Database Schema Updates

### New Table: `ml_models`

```sql
CREATE TABLE ml_models (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL UNIQUE,
    model_type VARCHAR(50) NOT NULL,
    prediction_horizons JSONB NOT NULL,  -- [1, 3, 24, 168]
    file_path VARCHAR(255) NOT NULL,
    feature_config JSONB,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Updated Table: `predictions`

Added `model_name` field:

```sql
CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    model_name VARCHAR(100) NOT NULL DEFAULT 'baseline',  -- NEW
    prediction_horizon INTEGER NOT NULL DEFAULT 3,        -- Changed default
    predicted_value DECIMAL(20, 8) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Using the Model Service

### Initialize

```python
from services.model_service import ModelService

model_service = ModelService(models_directory="/app/trained_models")
```

### Load a Model

```python
# Automatic loading and caching
model_data = model_service.load_model("baseline", db)
```

### Make Prediction

```python
result = model_service.make_prediction(
    model_name="baseline",
    horizon=24,
    db=db,
    save_to_db=True
)

# Result contains:
# - model_name
# - base_timestamp
# - prediction_horizon
# - predicted_value
# - predicted_time
# - current_price
```

### Register New Model

```python
result = model_service.register_model(
    model_name="my_new_model",
    model_type="RandomForest",
    prediction_horizons=[1, 3, 24, 168],
    file_path="/app/trained_models/my_model.joblib",
    feature_config={"features": ["lag_1h", "lag_2h"]},
    db=db
)
```

## Feature Engineering

The model service handles feature engineering automatically:

```python
def create_features(df: pd.DataFrame, horizon: int):
    # Base features (always created)
    df['lag_1h'] = df['close_price'].shift(1)
    df['lag_2h'] = df['close_price'].shift(2)
    df['lag_24h'] = df['close_price'].shift(24)
    df['SMA_10h'] = df['close_price'].rolling(window=10).mean()
    df['price_change_1h'] = df['close_price'] - df['close_price'].shift(1)

    # Horizon-specific features
    if horizon >= 24:
        df['lag_48h'] = df['close_price'].shift(48)
        df['SMA_24h'] = df['close_price'].rolling(window=24).mean()
        df['price_change_24h'] = df['close_price'] - df['close_price'].shift(24)

    if horizon >= 168:
        df['lag_168h'] = df['close_price'].shift(168)
        df['SMA_168h'] = df['close_price'].rolling(window=168).mean()
```

## Training New Models

### Step 1: Train Your Model

```python
from sklearn.ensemble import RandomForestRegressor
import joblib

# Train your model
model = RandomForestRegressor()
model.fit(X_train, y_train)

# Save to trained_models directory
joblib.dump(model, '/app/trained_models/my_model.joblib')
```

### Step 2: Register the Model

```bash
curl -X POST http://localhost:8000/models/register \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "random_forest_v1",
    "model_type": "RandomForest",
    "prediction_horizons": [1, 3, 24, 168],
    "file_path": "/app/trained_models/my_model.joblib"
  }'
```

### Step 3: Use the Model

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "random_forest_v1",
    "prediction_horizon": 24,
    "save_to_db": true
  }'
```

## Filtering Predictions

Enhanced `/predictions/latest` endpoint now supports filtering:

```python
# Filter by model
GET /predictions/latest?model_name=baseline

# Filter by horizon
GET /predictions/latest?horizon=24

# Combine filters
GET /predictions/latest?model_name=baseline&horizon=3&limit=5
```

## Error Handling

### Common Errors

1. **Model Not Found**
```python
raise ValueError(f"Model '{model_name}' not found or inactive")
# HTTP 400
```

2. **Unsupported Horizon**
```python
raise ValueError(
    f"Horizon {horizon}h not supported by model '{model_name}'. "
    f"Supported horizons: {model_info.prediction_horizons}"
)
# HTTP 400
```

3. **Model File Not Found**
```python
raise FileNotFoundError(f"Model file not found: {model_path}")
# HTTP 404
```

4. **No Historical Data**
```python
raise ValueError("No historical data available for prediction")
# HTTP 400
```

## Testing

### Test Model Registration

```bash
curl -X POST http://localhost:8000/models/register \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "test_model",
    "model_type": "LinearRegression",
    "prediction_horizons": [1, 3],
    "file_path": "/app/trained_models/baseline_model.joblib"
  }'
```

### Test Prediction

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "baseline",
    "prediction_horizon": 3,
    "save_to_db": false
  }'
```

### Test Model Listing

```bash
curl http://localhost:8000/models
```

## Best Practices

### 1. Model Naming
- Use descriptive names: `random_forest_v1`, `lstm_24h_v2`
- Include version numbers for tracking
- Use lowercase with underscores

### 2. Horizon Support
- Always specify all supported horizons
- Document horizon limitations
- Test each horizon before deployment

### 3. Feature Configuration
- Store feature configs in model metadata
- Version your feature engineering code
- Document feature requirements

### 4. Model Files
- Use consistent file naming
- Store in `/app/trained_models/`
- Use `.joblib` for sklearn models
- Consider compression for large models

### 5. Database Persistence
- Set `save_to_db=True` for production predictions
- Set `save_to_db=False` for testing/debugging
- Monitor database size with many predictions

## Development Workflow

### 1. Local Development

```bash
# Start PostgreSQL
docker-compose up -d postgres

# Run backend locally
cd backend
python run_dev.py
```

### 2. Access Interactive Docs

Visit http://localhost:8000/docs for Swagger UI

### 3. Test Endpoints

Use the interactive UI or curl commands

### 4. Check Logs

```bash
# Docker logs
docker-compose logs -f backend

# Or local logs (stdout)
```

## Dependencies

New dependencies added in `requirements.txt`:

```
pandas==2.1.4
numpy==1.26.3
scikit-learn==1.4.0
joblib==1.3.2
```

## Docker Volume Mapping

Ensure `trained_models` directory is accessible:

```yaml
# docker-compose.yml
volumes:
  - ./backend:/app
  - ./backend/trained_models:/app/trained_models
```

## Next Steps

1. **Add fetching and inserting new data**
2. **Add model evaluation metrics** tracking
3. **Add prediction confidence intervals**
4. **Create automated retraining pipeline**
5. **Add model performance monitoring**

