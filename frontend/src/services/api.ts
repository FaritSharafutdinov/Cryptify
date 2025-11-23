import {
	ApiResponse,
	DashboardData,
	TimeRange,
	PredictionModel,
} from "@/types";
import mockData from "@/data/mockData.json";

// Vite exposes env vars via import.meta.env; fallback to '/api'
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const viteEnv: any = (import.meta as any).env || {};
const API_BASE_URL = viteEnv.VITE_API_URL || "/api";

let backendHealthy: boolean | null = null;
let lastHealthCheck = 0;
const HEALTH_TTL = 30_000; // 30s cache

/**
 * Generate mock data based on time range
 */
function generateMockData(
	fromTime: string,
	toTime: string,
	timeRange?: TimeRange,
	model?: PredictionModel
): ApiResponse<DashboardData> {
	const from = new Date(fromTime).getTime();
	const to = new Date(toTime).getTime();

	// Determine how many bars to generate based on time range
	let barsCount = 24; // Default: 1 day, hourly
	if (timeRange === "1w") {
		barsCount = 168; // 7 days * 24 hours
	} else if (timeRange === "1m") {
		barsCount = 720; // 30 days * 24 hours
	}

	// Calculate interval between bars
	const interval = (to - from) / barsCount;

	// Generate bars
	const raw_bars = [];
	let currentPrice = 44890.45; // Starting price

	for (let i = 0; i < barsCount; i++) {
		const timestamp = new Date(from + i * interval);
		const change = (Math.random() - 0.5) * 200; // Random price change
		const open = currentPrice;
		const high = open + Math.abs(change) + Math.random() * 100;
		const low = open - Math.abs(change) - Math.random() * 100;
		const close = open + change;
		currentPrice = close;

		raw_bars.push({
			timestamp: timestamp.toISOString(),
			symbol: "BTCUSDT",
			open: Math.round(open * 100) / 100,
			high: Math.round(high * 100) / 100,
			low: Math.round(low * 100) / 100,
			close: Math.round(close * 100) / 100,
			volume: Math.round((50 + Math.random() * 100) * 100) / 100,
		});
	}

	// Generate predictions for the selected model (2 predictions: 3h and 12h)
	const predictions = [];
	const lastBar = raw_bars[raw_bars.length - 1];
	const predictionHorizons = [3, 12]; // 3 hours and 12 hours ahead

	for (const horizon of predictionHorizons) {
		const predictedTime =
			new Date(lastBar.timestamp).getTime() +
			horizon * 60 * 60 * 1000;
		const predictedValue = lastBar.close + (Math.random() - 0.5) * 500;

		predictions.push({
			timestamp: lastBar.timestamp,
			prediction_horizon: horizon,
			predicted_value: Math.round(predictedValue * 100) / 100,
			predicted_time: new Date(predictedTime).toISOString(),
			model: model || "linear_regression",
		});
	}

	return {
		status: "success",
		data: {
			raw_bars,
			predictions,
		},
		metadata: {
			bars_count: raw_bars.length,
			predictions_count: predictions.length,
		},
		time_range: {
			from: fromTime,
			to: toTime,
		},
	};
}

export class ApiService {
	static isBackendHealthy() {
		return backendHealthy === true;
	}

	static isUsingMock() {
		// Only return true if we're actually using mock data
		// This is determined by whether backend is healthy
		return backendHealthy === false && viteEnv.VITE_USE_MOCK_FALLBACK === "true";
	}
	/**
	 * Get historical BTC data and predictions
	 */
	static async getHistory(
		fromTime?: string,
		toTime?: string,
		forceReal = false,
		timeRange?: TimeRange,
		model?: PredictionModel
	): Promise<ApiResponse<DashboardData>> {
		// Always try to use real API first, fallback to mock only if explicitly enabled
		const useMockFallback = viteEnv.VITE_USE_MOCK_FALLBACK === "true";

		// Health check (cached) - but don't block on it
		const now = Date.now();
		if (backendHealthy === null || now - lastHealthCheck > HEALTH_TTL) {
			try {
				await this.healthCheck();
				backendHealthy = true;
			} catch {
				backendHealthy = false;
			} finally {
				lastHealthCheck = now;
			}
		}

		// Try to fetch real data first
		try {
			const params = new URLSearchParams();
			if (fromTime) params.append("from_time", fromTime);
			if (toTime) params.append("to_time", toTime);
			if (timeRange) params.append("time_range", timeRange);
			if (model) params.append("model", model);

			const response = await fetch(`${API_BASE_URL}/history?${params}`);

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			const data = await response.json();
			// Mark backend as healthy if we got data
			backendHealthy = true;
			return data;
		} catch (error) {
			console.error("Failed to fetch history data:", error);
			backendHealthy = false;
			
			// Only fallback to mock if explicitly enabled
			if (useMockFallback && !forceReal) {
				console.warn("Falling back to mock data");
				// Generate dynamic mock data based on time range
				if (fromTime && toTime) {
					return generateMockData(fromTime, toTime, timeRange, model);
				}
				// Fallback to static mock data if no time params provided
				return mockData as ApiResponse<DashboardData>;
			}
			
			// Otherwise, throw the error so UI can handle it
			throw error;
		}
	}

	/**
	 * Get latest predictions only
	 */
	static async getLatestPredictions(limit = 10): Promise<any> {
		try {
			const response = await fetch(
				`${API_BASE_URL}/predictions/latest?limit=${limit}`
			);

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			return await response.json();
		} catch (error) {
			console.error("Failed to fetch predictions:", error);
			throw error;
		}
	}

	/**
	 * Health check endpoint
	 */
	static async healthCheck(): Promise<any> {
		try {
			const response = await fetch(`${API_BASE_URL}/health`);

			if (!response.ok) {
				throw new Error(`HTTP error! status: ${response.status}`);
			}

			return await response.json();
		} catch (error) {
			console.error("Health check failed:", error);
			throw error;
		}
	}
}
