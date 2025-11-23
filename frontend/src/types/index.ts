// API Response Types
export interface ApiResponse<T> {
	status: "success" | "error";
	data: T;
	metadata?: {
		bars_count: number;
		predictions_count: number;
	};
	time_range?: {
		from: string;
		to: string;
	};
}

// BTC Price Data Types
export interface RawBar {
	timestamp: string;
	symbol: string;
	open: number;
	high: number;
	low: number;
	close: number;
	volume: number;
}

export interface Prediction {
	timestamp: string;
	prediction_horizon: number;
	predicted_value: number;
	predicted_time: string;
	model?: string; // Model name (e.g., 'linear_regression', 'xgboost', 'lstm')
}

// Chart Data Types
export interface ChartDataPoint {
	time: string;
	value: number;
}

export interface CandlestickData {
	time: string;
	open: number;
	high: number;
	low: number;
	close: number;
}

// Dashboard State Types
export interface DashboardData {
	raw_bars: RawBar[];
	predictions: Prediction[];
}

// Chart Configuration
export interface ChartConfig {
	width: number;
	height: number;
	layout: {
		backgroundColor: string;
		textColor: string;
	};
	grid: {
		vertLines: {
			color: string;
		};
		horzLines: {
			color: string;
		};
	};
	crosshair: {
		mode: number;
	};
	timeScale: {
		borderColor: string;
	};
}

// Component Props
export interface BTCChartProps {
	data: DashboardData;
	isLoading?: boolean;
	isDarkMode?: boolean;
	timeRange?: TimeRange;
	selectedModel?: PredictionModel;
}

export interface DashboardHeaderProps {
	currentPrice?: number;
	change24h?: number;
	lastUpdate?: string;
	minPrice?: number;
	maxPrice?: number;
	totalVolume?: number;
	volatility?: number;
}

export interface PredictionCardProps {
	prediction: Prediction;
	confidence?: number;
	selectedModel?: PredictionModel;
}

// Time Range Types
export type TimeRange = "1d" | "1w" | "1m";

// Model Types
export type PredictionModel = "linear_regression" | "xgboost" | "lstm";

export interface TimeRangeOption {
	value: TimeRange;
	label: string;
	hours: number;
}

export interface ModelOption {
	value: PredictionModel;
	label: string;
	description?: string;
}
