import React, { useEffect, useRef, useState } from "react";
import { createChart, IChartApi, ISeriesApi, Time } from "lightweight-charts";
import { Box, Paper, CircularProgress, Typography, Chip } from "@mui/material";
import { BTCChartProps, ChartConfig } from "@/types";

const BTCChart: React.FC<BTCChartProps> = ({
	data,
	isLoading = false,
	isDarkMode = false,
	timeRange = "1d",
	selectedModel = "linear_regression",
}) => {
	const chartContainerRef = useRef<HTMLDivElement>(null);
	const chartRef = useRef<IChartApi | null>(null);
	const candlestickSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
	const predictionSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);

	const [chartReady, setChartReady] = useState(false);

	// Determine adaptive height (mobile smaller, desktop larger)
	const computeHeight = () => {
		if (typeof window === "undefined") return 500;
		const h = window.innerHeight;
		// Use a fraction of viewport, accounting for header and controls
		// More aggressive height calculation to fit better
		const base = Math.min(550, Math.max(300, Math.round(h * 0.5)));
		return base;
	};

	const [dynamicHeight, setDynamicHeight] = useState<number>(computeHeight());

	useEffect(() => {
		const onResize = () => setDynamicHeight(computeHeight());
		window.addEventListener("resize", onResize);
		return () => window.removeEventListener("resize", onResize);
	}, []);

	// Chart configuration based on theme + dynamic height
	const getChartConfig = (): ChartConfig => ({
		width: 0, // Will be set by resize observer
		height: dynamicHeight,
		layout: {
			backgroundColor: isDarkMode ? "#1a1a1a" : "#ffffff",
			textColor: isDarkMode ? "#ffffff" : "#333333",
		},
		grid: {
			vertLines: {
				color: isDarkMode ? "#2a2a2a" : "#e1e1e1",
			},
			horzLines: {
				color: isDarkMode ? "#2a2a2a" : "#e1e1e1",
			},
		},
		crosshair: {
			mode: 1, // CrosshairMode.Normal
		},
		timeScale: {
			borderColor: isDarkMode ? "#485c7b" : "#cccccc",
			timeVisible: true,
			secondsVisible: false,
		},
		rightPriceScale: {
			borderColor: isDarkMode ? "#485c7b" : "#cccccc",
		},
	});

	// Initialize chart after loading finished so container exists
	useEffect(() => {
		if (isLoading) return; // wait until data fetched once (container rendered)
		if (!chartContainerRef.current) return;
		if (chartRef.current) return; // already initialized
		if ((import.meta as any).env?.DEV) {
			// eslint-disable-next-line no-console
			console.log(
				"[BTCChart] initializing after load, width=",
				chartContainerRef.current.clientWidth
			);
		}
		const initialConfig = getChartConfig();
		const chart = createChart(chartContainerRef.current, initialConfig);
		const w = chartContainerRef.current.clientWidth;
		if (w > 0) chart.applyOptions({ width: w });
		chartRef.current = chart;
		const cs = chart.addCandlestickSeries({
			upColor: "#4caf50",
			downColor: "#f44336",
			borderVisible: false,
			wickUpColor: "#4caf50",
			wickDownColor: "#f44336",
			priceFormat: {
				type: "price",
				precision: 2,
				minMove: 0.01,
			},
		});
		candlestickSeriesRef.current = cs;
		const ls = chart.addLineSeries({
			color: "#ff9800",
			lineWidth: 3,
			priceLineVisible: true,
			lastValueVisible: true,
			title: "Prediction",
			priceFormat: {
				type: "price",
				precision: 2,
				minMove: 0.01,
			},
		});
		predictionSeriesRef.current = ls;
		setChartReady(true);
		const resizeObserver = new ResizeObserver((entries) => {
			if (!chartContainerRef.current || entries.length === 0) return;
			const { width, height } = entries[0].contentRect;
			chart.applyOptions({ width, height: height || dynamicHeight });
		});
		resizeObserver.observe(chartContainerRef.current);
		return () => {
			resizeObserver.disconnect();
			chart.remove();
			chartRef.current = null;
			candlestickSeriesRef.current = null;
			predictionSeriesRef.current = null;
			setChartReady(false);
		};
	}, [isLoading, dynamicHeight]);

	// Update theme options when isDarkMode changes
	useEffect(() => {
		if (!chartRef.current) return;
		chartRef.current.applyOptions({
			layout: {
				background: { color: isDarkMode ? "#1a1a1a" : "#ffffff" },
				textColor: isDarkMode ? "#ffffff" : "#333333",
			},
			grid: {
				vertLines: { color: isDarkMode ? "#2a2a2a" : "#e1e1e1" },
				horzLines: { color: isDarkMode ? "#2a2a2a" : "#e1e1e1" },
			},
			timeScale: {
				borderColor: isDarkMode ? "#485c7b" : "#cccccc",
				timeVisible: true,
				secondsVisible: false,
			},
			rightPriceScale: {
				borderColor: isDarkMode ? "#485c7b" : "#cccccc",
			},
		});
	}, [isDarkMode]);

	// Update chart data with simple smooth animation
	useEffect(() => {
		if (
			!chartReady ||
			!candlestickSeriesRef.current ||
			!predictionSeriesRef.current
		)
			return;

		if ((import.meta as any).env?.DEV) {
			// eslint-disable-next-line no-console
			console.log("[BTCChart] update", {
				bars: data.raw_bars.length,
				predictions: data.predictions.length,
			});
		}

		// Format historical data for candlestick chart
		// Remove duplicates by timestamp (keep last occurrence) and sort
		const candlestickDataMap = new Map<number, {
			time: Time;
			open: number;
			high: number;
			low: number;
			close: number;
		}>();
		
		data.raw_bars.forEach((bar) => {
			const time = Math.floor(new Date(bar.timestamp).getTime() / 1000) as Time;
			candlestickDataMap.set(time as number, {
				time,
				open: bar.open,
				high: bar.high,
				low: bar.low,
				close: bar.close,
			});
		});
		
		const candlestickData = Array.from(candlestickDataMap.values())
			.sort((a, b) => (a.time as number) - (b.time as number)); // Ensure ascending order

		// Format prediction data for line chart
		// Filter by selected model first, then remove duplicates by timestamp
		const filteredPredictions = data.predictions.filter(
			(prediction) => prediction.model === selectedModel
		);
		
		// Remove duplicates by timestamp (keep last occurrence) and sort
		const predictionDataMap = new Map<number, {
			time: Time;
			value: number;
		}>();
		
		filteredPredictions.forEach((prediction) => {
			const time = Math.floor(
				new Date(prediction.predicted_time).getTime() / 1000
			) as Time;
			predictionDataMap.set(time as number, {
				time,
				value: prediction.predicted_value,
			});
		});
		
		const predictionData = Array.from(predictionDataMap.values())
			.sort((a, b) => (a.time as number) - (b.time as number)); // Ensure ascending order

		// Set all data at once - no progressive reveal
		if (candlestickSeriesRef.current) {
			candlestickSeriesRef.current.setData(candlestickData);
		}
		if (predictionSeriesRef.current) {
			predictionSeriesRef.current.setData(predictionData);
		}

		// Add a marker for last prediction point
		if (predictionData.length > 0 && candlestickSeriesRef.current) {
			const last = predictionData[predictionData.length - 1];
			candlestickSeriesRef.current.setMarkers([
				{
					time: last.time,
					position: "aboveBar",
					color: "#ff9800",
					shape: "circle",
					text: "P",
				},
			]);
		}

		// Fit content smoothly after a brief delay to let data render
		if (chartRef.current) {
			// Use setTimeout to ensure data is set before fitting
			const timeoutId = setTimeout(() => {
				if (chartRef.current) {
					chartRef.current.timeScale().fitContent();
				}
			}, 50);

			return () => clearTimeout(timeoutId);
		}
	}, [data, chartReady, selectedModel]); // Add selectedModel to dependencies

	if (isLoading) {
		if ((import.meta as any).env?.DEV) {
			// eslint-disable-next-line no-console
			console.log("[BTCChart] render loading state");
		}
		return (
			<Paper
				elevation={3}
				sx={{
					height: dynamicHeight,
					display: "flex",
					alignItems: "center",
					justifyContent: "center",
					backgroundColor: isDarkMode ? "#1a1a1a" : "#ffffff",
				}}
			>
				<Box display="flex" flexDirection="column" alignItems="center" gap={2}>
					<CircularProgress size={60} />
					<Typography variant="h6" color={isDarkMode ? "#ffffff" : "#333333"}>
						Loading BTC Data...
					</Typography>
				</Box>
			</Paper>
		);
	}

	const getTimeRangeLabel = () => {
		const labels: Record<string, string> = {
			"1d": "1 Day",
			"1w": "1 Week",
			"1m": "1 Month",
		};
		return labels[timeRange] || timeRange;
	};

	const getModelLabel = () => {
		const labels: Record<string, string> = {
			linear_regression: "Linear Regression",
			xgboost: "XGBoost",
			lstm: "LSTM",
		};
		return labels[selectedModel] || selectedModel;
	};

	return (
		(import.meta as any).env?.DEV &&
			console.log("[BTCChart] render chart container"),
		(
			<Paper
				elevation={3}
				sx={{
					p: 0,
					backgroundColor: isDarkMode ? "#1a1a1a" : "#ffffff",
					overflow: "hidden",
					border: "1px solid rgba(0,0,0,0.12)",
					position: "relative",
					transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
					animation: "fadeInScale 0.6s ease-out",
					"@keyframes fadeInScale": {
						from: {
							opacity: 0,
							transform: "scale(0.98)",
						},
						to: {
							opacity: 1,
							transform: "scale(1)",
						},
					},
					"&:hover": {
						boxShadow: 6,
						transform: "translateY(-2px)",
					},
				}}
			>
				{/* Chart Header with Info */}
				<Box
					sx={{
						display: "flex",
						justifyContent: "space-between",
						alignItems: "center",
						p: { xs: 1, sm: 1.5 },
						borderBottom: "1px solid",
						borderColor: isDarkMode
							? "rgba(255,255,255,0.1)"
							: "rgba(0,0,0,0.1)",
						flexWrap: "wrap",
						gap: 1,
						transition: "border-color 0.3s ease",
					}}
				>
					<Typography
						variant="subtitle2"
						fontWeight="bold"
						color={isDarkMode ? "#ffffff" : "#333333"}
						sx={{ fontSize: { xs: "0.875rem", sm: "1rem" } }}
					>
						BTC/USD Price Chart
					</Typography>
					<Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
						<Chip
							label={`Period: ${getTimeRangeLabel()}`}
							size="small"
							variant="outlined"
							sx={{
								fontSize: { xs: "0.65rem", sm: "0.75rem" },
								height: { xs: "20px", sm: "24px" },
								transition: "all 0.2s ease",
								"&:hover": {
									transform: "scale(1.05)",
								},
							}}
						/>
						<Chip
							label={`Model: ${getModelLabel()}`}
							size="small"
							variant="outlined"
							color="primary"
							sx={{
								fontSize: { xs: "0.65rem", sm: "0.75rem" },
								height: { xs: "20px", sm: "24px" },
								transition: "all 0.2s ease",
								"&:hover": {
									transform: "scale(1.05)",
								},
							}}
						/>
					</Box>
				</Box>
				<Box
					ref={chartContainerRef}
					sx={{
						width: "100%",
						height: dynamicHeight,
						opacity: chartReady ? 1 : 0,
						transition: "opacity 0.6s ease-in-out",
						"& > div": {
							borderRadius: 1,
						},
					}}
				/>
				{!isLoading && chartReady && data.raw_bars.length === 0 && (
					<Box p={2}>
						<Typography variant="body2" color="text.secondary">
							No data to display.
						</Typography>
					</Box>
				)}
			</Paper>
		)
	);
};

export default BTCChart;
