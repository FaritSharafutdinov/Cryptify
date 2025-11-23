# Criptify Frontend

Modern React dashboard for Bitcoin price prediction with TradingView-style charts.

> Updated: Time range selection, ML model selection, enhanced UI/UX with animations, improved mobile responsiveness, dynamic mock data generation.

## 🚀 Features

### Core Features

- **Candlesticks + Predictions**: TradingView Lightweight Charts integration
- **Time Range Selection**: Choose between 1 day, 1 week, or 1 month views
- **ML Model Selection**: Switch between Linear Regression, XGBoost, and LSTM models
- **Adaptive Height**: Chart uses ~45% of viewport height (bounded 320–600px)
- **Dark Mode Persistence**: LocalStorage + system preference detection
- **Auto Mock Fallback**: Seamless switch to mock data if backend is down (dev)
- **Dynamic Mock Data**: Mock data generates based on selected time range
- **Health Check Cache**: `/health` ping cached for 30s to reduce load
- **Prediction Marker**: Last forecast point marked with a highlighted circle (P)
- **Loading Skeletons**: Chart & prediction cards skeleton UI
- **Status Chip**: Shows current data source (Real API / Mock Data)
- **Type Safety**: Strict TypeScript models and service layer
- **Docker Ready**: Optimized Nginx production image

### UI/UX Enhancements

- **Smooth Animations**: Fade and Zoom transitions for loading states
- **Chart Labels**: Clear period and model indicators on chart header
- **Mobile Responsive**: Fully adaptive layout for all screen sizes
- **Hover Effects**: Interactive card animations on hover
- **Time Labels**: Visible time scale on chart for better readability

## 🛠️ Tech Stack

- **React 18** + **TypeScript**
- **Material-UI (MUI)** components
- **TradingView Lightweight Charts**
- **Vite** dev/build tooling
- **Nginx** production serving
- **Docker** containerization

## 📦 Installation

### Development Setup

1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```
2. (Optional) Copy env file:
   ```bash
   cp config/.env.example .env
   ```
3. Start dev server:
   ```bash
   npm run dev
   ```
4. Open: http://localhost:3000

### Production with Docker

```bash
# From project root
docker-compose up --build frontend
# or
docker build -t criptify-frontend ./frontend
docker run -p 3000:3000 criptify-frontend
```

## 🎨 Components

### BTCChart

- Lightweight Charts candlesticks + prediction line
- Adaptive height + theme sync
- Last prediction marker (circle + P)

### Dashboard

- Data loading / refresh cycle
- Auto-refresh every 5m
- Data source chip
- Error & loading management

### PredictionCard

- Individual prediction values
- Confidence mock display
- Skeleton during load

## 🔧 Configuration

### Environment Variables

| Variable       | Description                          | Default       |
| -------------- | ------------------------------------ | ------------- |
| `VITE_API_URL` | Backend API base path / proxy target | `/api`        |
| `NODE_ENV`     | Environment mode                     | `development` |

If backend health check fails (development only), the app transparently falls back to mock data (`src/data/mockData.json`) and displays a yellow "Mock Data" chip.

### API Integration & Fallback Logic

Endpoints:

- `GET /api/health` — backend availability probe (30s TTL cache)
- `GET /api/history?time_range=1d|1w|1m&model=linear_regression|xgboost|lstm&from_time=...&to_time=...` — historical bars + predictions
- `GET /api/predictions/latest` — latest predictions (future use)

Query Parameters:

- `time_range`: `1d` (1 day), `1w` (1 week), `1m` (1 month)
- `model`: `linear_regression`, `xgboost`, `lstm`
- `from_time`: ISO 8601 timestamp (start of range)
- `to_time`: ISO 8601 timestamp (end of range)

Fallback decision (development mode):

1. Health check determines backend state (cached for 30s)
2. If unhealthy → dynamic mock data generated based on time range (with slight delay)
3. Mock data includes appropriate number of bars for selected period
4. Status chip: Mock Data / Real API
5. Force-real pattern scaffolded via `forceRealNext`

## 📱 Features

### Chart Features

- Candlesticks (OHLC) + prediction overlay
- **Time Range Selection**: 1 day (24 bars), 1 week (168 bars), 1 month (720 bars)
- **Chart Header**: Shows current period and selected model
- **Time Scale Labels**: Visible timestamps on X-axis
- Adaptive height (viewport based)
- Last prediction marker (P)
- Auto fitContent after data load
- Dark/light theme sync

### Dashboard Features

- **Time Range Selector**: Dropdown to choose viewing period (1d/1w/1m)
- **Model Selector**: Dropdown to switch between ML models
- Auto refresh (5m) - respects selected time range and model
- Source chip (Real API / Mock Data)
- Skeleton loading placeholders with animations
- Dismissible error alerts with fade transitions
- Persistent dark mode
- **Responsive Controls**: Mobile-optimized selectors and layout

### Data Features

- Auto mock fallback (dev only)
- **Dynamic Mock Data**: Generates data based on selected time range
- **Model-Aware Predictions**: Predictions filtered/displayed by selected model
- Health check TTL cache (30s)
- Typed `ApiService` abstraction
- Extendable force-real flag
- API parameters: `time_range`, `model`, `from_time`, `to_time`

## 🚢 Deployment

### Docker Production Build

```bash
docker build -t criptify-frontend ./frontend
docker run -p 3000:3000 criptify-frontend
```

Nginx image includes SPA routing + static caching.

### Performance Optimizations

- Code splitting by Vite
- Lightweight Charts (small footprint)
- Skeletons minimize layout shift
- Dev logging gated by `import.meta.env.DEV`

## 🎯 Development Workflow

### Scripts

```bash
npm run dev        # dev server
npm run build      # production build
npm run preview    # local preview of prod build
npm run lint       # lint
npm run lint:fix   # auto-fix
npm run type-check # TS type checking
```

## 🔗 Integration

### Backend Response Shape (history)

```ts
interface ApiResponse<T> {
	status: "success" | "error";
	data: T;
}
interface RawBar {
	timestamp: string;
	open: number;
	high: number;
	low: number;
	close: number;
	volume: number;
	symbol: string;
}
interface Prediction {
	predicted_time: string;
	predicted_value: number;
	prediction_horizon: number;
	timestamp: string;
	model?: string; // Model name: 'linear_regression', 'xgboost', 'lstm'
}
interface DashboardData {
	raw_bars: RawBar[];
	predictions: Prediction[];
}
```

## 🎨 Theming

### Material-UI Theme

- Primary: Bitcoin Orange `#f57c00`
- Secondary: Blue `#1976d2`
- Dark backgrounds: `#0a0a0a` / `#121212`
- Light backgrounds: `#f5f5f5` / `#ffffff`

### Dark Mode Support

- LocalStorage persistence (`cryptify:darkMode`)
- Initial system preference detection
- Synchronized chart + MUI palette

## 📈 Future Enhancements

- WebSocket streaming
- Volume & indicators (MACD, RSI, EMA)
- Multi-asset (ETH, SOL ...)
- Notifications / alerts
- Extended historical ranges & pagination
- Export (PNG / CSV)
- Progressive prefetch & performance audits

### Production Notes

- Gate dev-only logs with `import.meta.env.DEV`
- Configure reverse proxy for `VITE_API_URL`
- Add CSP + security headers as needed
- Consider Sentry / LogRocket for monitoring

## 🤝 Contributing

1. Follow TypeScript & MUI patterns
2. Keep components accessible & responsive
3. Provide loading & error states
4. Avoid unnecessary re-renders
5. Keep API layer pure and typed

## 📄 License

MIT License - see LICENSE file for details.
