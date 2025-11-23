import React, { useState, useEffect, useRef, useCallback } from "react";
import {
	Container,
	Grid,
	Box,
	IconButton,
	Tooltip,
	AppBar,
	Toolbar,
	Typography,
	Switch,
	FormControlLabel,
	Skeleton,
	Chip,
	Select,
	MenuItem,
	FormControl,
	InputLabel,
	Paper,
	Fade,
	Zoom,
	LinearProgress,
	Card,
	CardContent,
	Alert,
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import { useSnackbar } from "notistack";
import { ApiService } from "@/services/api";
import {
	DashboardData,
	TimeRange,
	PredictionModel,
	TimeRangeOption,
	ModelOption,
} from "@/types";
import BTCChart from "./BTCChart";
import DashboardHeader from "./DashboardHeader";
import PredictionCard from "./PredictionCard";

interface DashboardProps {
	darkMode?: boolean;
	onToggleDarkMode?: () => void;
}

const Dashboard: React.FC<DashboardProps> = ({
	darkMode = false,
	onToggleDarkMode,
}) => {
	const { enqueueSnackbar } = useSnackbar();
	const [data, setData] = useState<DashboardData | null>(null);
	const [isLoading, setIsLoading] = useState(true);
	const [isRefreshing, setIsRefreshing] = useState(false);
	const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
	const [forceRealNext, setForceRealNext] = useState(false);
	const [usingMock, setUsingMock] = useState(false);
	const [isOnline, setIsOnline] = useState(navigator.onLine);
	const [retryCount, setRetryCount] = useState(0);
	const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);

	// Load saved settings from localStorage
	const [timeRange, setTimeRange] = useState<TimeRange>(() => {
		const saved = localStorage.getItem("cryptify:timeRange");
		return (saved as TimeRange) || "1d";
	});
	const [selectedModel, setSelectedModel] = useState<PredictionModel>(() => {
		const saved = localStorage.getItem("cryptify:selectedModel");
		return (saved as PredictionModel) || "linear_regression";
	});

	// Time range options
	const timeRangeOptions: TimeRangeOption[] = [
		{ value: "1d", label: "1 Day", hours: 24 },
		{ value: "1w", label: "1 Week", hours: 168 },
		{ value: "1m", label: "1 Month", hours: 720 },
	];

	// Model options
	const modelOptions: ModelOption[] = [
		{
			value: "linear_regression",
			label: "Linear Regression",
			description: "Basic linear regression",
		},
		{ value: "xgboost", label: "XGBoost", description: "Gradient boosting" },
		{
			value: "lstm",
			label: "LSTM",
			description: "Recurrent neural network",
		},
	];

	// Calculate time range for API
	const getTimeRangeParams = (range: TimeRange) => {
		const now = new Date();
		const hoursAgo =
			timeRangeOptions.find((opt) => opt.value === range)?.hours || 24;
		const fromTime = new Date(now.getTime() - hoursAgo * 60 * 60 * 1000);
		return {
			fromTime: fromTime.toISOString(),
			toTime: now.toISOString(),
		};
	};

	// Load data from API with retry logic and optimistic updates
	const loadData = useCallback(
		async (showToast = true, isRetry = false) => {
			// Optimistic UI: keep showing old data while loading
			setData((prevData) => {
				// Store previous data for potential restore
				if (prevData) {
					(window as any).__previousData = prevData;
				}
				return prevData;
			});

			if (!isRetry) {
				setIsRefreshing(true);
				setIsLoading(true);
			}

			try {
				if (!isOnline) {
					throw new Error("No internet connection");
				}

				const { fromTime, toTime } = getTimeRangeParams(timeRange);
				const response = await ApiService.getHistory(
					fromTime,
					toTime,
					forceRealNext,
					timeRange,
					selectedModel
				);

				setData(response.data);
				setLastRefresh(new Date());
				setForceRealNext(false);
				setUsingMock(ApiService.isUsingMock());
				setRetryCount(0);

				if (showToast && !isRetry) {
					enqueueSnackbar("Data updated successfully", { variant: "success" });
				}
			} catch (err) {
				const errorMessage =
					err instanceof Error ? err.message : "Failed to load data";

				// Retry logic with exponential backoff
				const currentRetryCount = retryCount;
				if (currentRetryCount < 3 && isOnline) {
					const delay = Math.min(1000 * Math.pow(2, currentRetryCount), 10000);
					setRetryCount((prev) => prev + 1);

					if (retryTimeoutRef.current) {
						clearTimeout(retryTimeoutRef.current);
					}

					retryTimeoutRef.current = setTimeout(() => {
						loadData(false, true);
					}, delay);

					if (showToast) {
						enqueueSnackbar(
							`Loading error. Retrying ${currentRetryCount + 1}/3...`,
							{ variant: "warning", autoHideDuration: delay }
						);
					}
				} else {
					// Show error toast
					enqueueSnackbar(errorMessage, {
						variant: "error",
						action: (
							<IconButton
								size="small"
								color="inherit"
								onClick={() => {
									setRetryCount(0);
									loadData(true, false);
								}}
							>
								<RefreshIcon fontSize="small" />
							</IconButton>
						),
					});

					// Restore previous data on error (optimistic UI)
					const previousData = (window as any).__previousData;
					if (previousData) {
						setData(previousData);
					}
				}
			} finally {
				setIsLoading(false);
				setIsRefreshing(false);
			}
		},
		[
			isOnline,
			timeRange,
			selectedModel,
			forceRealNext,
			retryCount,
			enqueueSnackbar,
		]
	);

	// Save settings to localStorage
	useEffect(() => {
		localStorage.setItem("cryptify:timeRange", timeRange);
	}, [timeRange]);

	useEffect(() => {
		localStorage.setItem("cryptify:selectedModel", selectedModel);
	}, [selectedModel]);

	// Online/Offline detection
	useEffect(() => {
		const handleOnline = () => {
			setIsOnline(true);
			enqueueSnackbar("Connection restored", { variant: "success" });
			loadData(false, false);
		};
		const handleOffline = () => {
			setIsOnline(false);
			enqueueSnackbar("No internet connection", { variant: "warning" });
		};

		window.addEventListener("online", handleOnline);
		window.addEventListener("offline", handleOffline);

		return () => {
			window.removeEventListener("online", handleOnline);
			window.removeEventListener("offline", handleOffline);
		};
	}, [enqueueSnackbar, loadData]);

	// Keyboard shortcuts
	useEffect(() => {
		const handleKeyPress = (e: KeyboardEvent) => {
			// Ignore if typing in input/select
			if (
				e.target instanceof HTMLInputElement ||
				e.target instanceof HTMLTextAreaElement ||
				(e.target as HTMLElement).isContentEditable
			) {
				return;
			}

			// R - Refresh
			if (e.key === "r" || e.key === "R") {
				e.preventDefault();
				loadData(true, false);
			}
			// D - Toggle dark mode
			if (e.key === "d" || e.key === "D") {
				e.preventDefault();
				onToggleDarkMode?.();
			}
			// 1, 2, 3 - Time ranges
			if (e.key === "1") {
				e.preventDefault();
				setTimeRange("1d");
			}
			if (e.key === "2") {
				e.preventDefault();
				setTimeRange("1w");
			}
			if (e.key === "3") {
				e.preventDefault();
				setTimeRange("1m");
			}
		};

		window.addEventListener("keydown", handleKeyPress);
		return () => window.removeEventListener("keydown", handleKeyPress);
	}, [loadData, onToggleDarkMode]);

	// Initial data load and reload when range/model changes
	useEffect(() => {
		loadData(false, false);
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [timeRange, selectedModel]);

	// Auto-refresh every 5 minutes
	useEffect(() => {
		if (!isOnline) return;
		const interval = setInterval(() => loadData(false, false), 5 * 60 * 1000);
		return () => clearInterval(interval);
	}, [loadData, isOnline]);

	// Cleanup retry timeout
	useEffect(() => {
		return () => {
			if (retryTimeoutRef.current) {
				clearTimeout(retryTimeoutRef.current);
			}
		};
	}, []);

	const getCurrentPrice = () => {
		if (!data || data.raw_bars.length === 0) return undefined;
		return data.raw_bars[data.raw_bars.length - 1].close;
	};

	const get24hChange = () => {
		if (!data || data.raw_bars.length < 2) return 0;
		const current = data.raw_bars[data.raw_bars.length - 1].close;
		const previous =
			data.raw_bars[data.raw_bars.length - 24]?.close || data.raw_bars[0].close;
		return ((current - previous) / previous) * 100;
	};

	const getMinPrice = () => {
		if (!data || data.raw_bars.length === 0) return undefined;
		return Math.min(...data.raw_bars.map((bar) => bar.low));
	};

	const getMaxPrice = () => {
		if (!data || data.raw_bars.length === 0) return undefined;
		return Math.max(...data.raw_bars.map((bar) => bar.high));
	};

	const getTotalVolume = () => {
		if (!data || data.raw_bars.length === 0) return undefined;
		return data.raw_bars.reduce((sum, bar) => sum + bar.volume, 0);
	};

	const getVolatility = () => {
		if (!data || data.raw_bars.length < 2) return undefined;
		// Calculate volatility as the standard deviation of returns
		const returns = [];
		for (let i = 1; i < data.raw_bars.length; i++) {
			const prevClose = data.raw_bars[i - 1].close;
			const currentClose = data.raw_bars[i].close;
			const returnValue = (currentClose - prevClose) / prevClose;
			returns.push(returnValue);
		}

		// Calculate mean return
		const meanReturn = returns.reduce((sum, r) => sum + r, 0) / returns.length;

		// Calculate variance
		const variance =
			returns.reduce((sum, r) => sum + Math.pow(r - meanReturn, 2), 0) /
			returns.length;

		// Calculate standard deviation (volatility) as percentage
		const volatility = Math.sqrt(variance) * 100;

		return volatility;
	};

	return (
		<Box
			sx={{
				minHeight: "100vh",
				backgroundColor: darkMode ? "#0a0a0a" : "#f5f5f5",
				width: "100%",
				overflowX: "hidden",
			}}
		>
			{/* App Bar */}
			<AppBar position="static" elevation={0}>
				<Toolbar sx={{ flexWrap: "wrap", gap: 1 }}>
					<Typography
						variant="h6"
						component="div"
						sx={{
							flexGrow: 1,
							fontSize: { xs: "1rem", sm: "1.25rem" },
						}}
					>
						🪙 Criptify - BTC Price Prediction
					</Typography>

					<Tooltip title="Toggle dark theme (D)">
						<FormControlLabel
							control={
								<Switch
									checked={darkMode}
									onChange={() => onToggleDarkMode && onToggleDarkMode()}
									color="default"
									size="small"
								/>
							}
							label={
								<Typography
									variant="body2"
									sx={{ fontSize: { xs: "0.75rem", sm: "0.875rem" } }}
								>
									Dark
								</Typography>
							}
							sx={{ mr: { xs: 0.5, sm: 2 } }}
						/>
					</Tooltip>

					{!isLoading && (
						<Chip
							label={usingMock ? "Mock" : "Real"}
							color={usingMock ? "warning" : "success"}
							size="small"
							variant="outlined"
							sx={{
								mr: { xs: 0.5, sm: 2 },
								fontSize: { xs: "0.7rem", sm: "0.75rem" },
								color: "inherit",
								borderColor: "currentColor",
								"& .MuiChip-label": {
									color: "inherit",
								},
							}}
						/>
					)}
					<Tooltip title="Refresh data (R) - Automatic fallback to mock data on error">
						<span style={{ display: "inline-flex" }}>
							<IconButton
								color="inherit"
								onClick={() => loadData(true, false)}
								disabled={isLoading || !isOnline}
								size="small"
								sx={{
									padding: { xs: "8px", sm: "12px" },
									transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
									"&:hover:not(:disabled)": {
										transform: "rotate(180deg) scale(1.1)",
									},
									"&:disabled": {
										opacity: 0.5,
									},
								}}
							>
								<RefreshIcon
									sx={{
										fontSize: { xs: "1.2rem", sm: "1.5rem" },
										transition: "transform 0.3s ease",
										animation: isRefreshing
											? "spin 1s linear infinite"
											: "none",
										"@keyframes spin": {
											from: { transform: "rotate(0deg)" },
											to: { transform: "rotate(360deg)" },
										},
									}}
								/>
							</IconButton>
						</span>
					</Tooltip>
				</Toolbar>
			</AppBar>

			{/* Progress Bar */}
			{isRefreshing && (
				<LinearProgress
					sx={{
						position: "fixed",
						top: 0,
						left: 0,
						right: 0,
						zIndex: 1301,
						height: 3,
					}}
				/>
			)}

			{/* Offline Indicator */}
			{!isOnline && (
				<Box
					sx={{
						position: "fixed",
						top: 64,
						left: 0,
						right: 0,
						backgroundColor: "warning.main",
						color: "warning.contrastText",
						textAlign: "center",
						py: 1,
						zIndex: 1300,
					}}
				>
					<Typography variant="caption">
						⚠️ No internet connection. Working in offline mode.
					</Typography>
				</Box>
			)}

			<Container
				maxWidth="xl"
				sx={{
					py: { xs: 1.5, sm: 2 },
					pt: { xs: !isOnline ? 7 : 1.5, sm: !isOnline ? 8 : 2 },
					animation: "fadeIn 0.6s ease-out",
					"@keyframes fadeIn": {
						from: { opacity: 0 },
						to: { opacity: 1 },
					},
				}}
			>
				{/* Dashboard Header */}
				<DashboardHeader
					currentPrice={getCurrentPrice()}
					change24h={get24hChange()}
					lastUpdate={lastRefresh.toISOString()}
					minPrice={getMinPrice()}
					maxPrice={getMaxPrice()}
					totalVolume={getTotalVolume()}
					volatility={getVolatility()}
				/>

				{/* Controls: Time Range and Model Selection */}
				<Paper
					elevation={2}
					sx={{
						mb: 1.5,
						p: { xs: 1, sm: 1.5 },
						display: "flex",
						flexWrap: "wrap",
						gap: 1.5,
						alignItems: "center",
						justifyContent: { xs: "stretch", sm: "flex-start" },
						transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
						animation: "fadeInUp 0.5s ease-out 0.2s both",
						"@keyframes fadeInUp": {
							from: {
								opacity: 0,
								transform: "translateY(20px)",
							},
							to: {
								opacity: 1,
								transform: "translateY(0)",
							},
						},
						"&:hover": {
							boxShadow: 4,
							transform: "translateY(-2px)",
						},
					}}
				>
					<FormControl sx={{ minWidth: { xs: "100%", sm: 160 } }} size="small">
						<InputLabel id="time-range-label">Time Range</InputLabel>
						<Select
							labelId="time-range-label"
							value={timeRange}
							label="Time Range"
							onChange={(e) => setTimeRange(e.target.value as TimeRange)}
							disabled={isLoading}
						>
							{timeRangeOptions.map((option) => (
								<MenuItem key={option.value} value={option.value}>
									{option.label}
								</MenuItem>
							))}
						</Select>
					</FormControl>

					<FormControl sx={{ minWidth: { xs: "100%", sm: 180 } }} size="small">
						<InputLabel id="model-label">Prediction Model</InputLabel>
						<Select
							labelId="model-label"
							value={selectedModel}
							label="Prediction Model"
							onChange={(e) =>
								setSelectedModel(e.target.value as PredictionModel)
							}
							disabled={isLoading}
						>
							{modelOptions.map((option) => (
								<MenuItem key={option.value} value={option.value}>
									{option.label}
								</MenuItem>
							))}
						</Select>
					</FormControl>
				</Paper>

				<Grid container spacing={3}>
					{/* Main Chart */}
					<Grid item xs={12} lg={8}>
						{isLoading ? (
							<Zoom in={isLoading}>
								<Skeleton
									variant="rectangular"
									height={500}
									animation="wave"
									sx={{ borderRadius: 1, mb: 2 }}
								/>
							</Zoom>
						) : (
							<Fade in={!isLoading} timeout={500}>
								<Box>
									<BTCChart
										data={data || { raw_bars: [], predictions: [] }}
										isLoading={false}
										isDarkMode={darkMode}
										timeRange={timeRange}
										selectedModel={selectedModel}
									/>
								</Box>
							</Fade>
						)}
					</Grid>

					{/* Prediction Cards */}
					<Grid item xs={12} lg={4}>
						{(() => {
							const filteredPredictions =
								!isLoading && data?.predictions
									? data.predictions.filter(
											(p) =>
												!selectedModel || p.model === selectedModel || !p.model
									  )
									: [];
							const cardCount = filteredPredictions.length || 1;

							// Calculate chart height same way as BTCChart does
							const computeChartHeight = () => {
								if (typeof window === "undefined") return 500;
								const h = window.innerHeight;
								const base = Math.min(550, Math.max(300, Math.round(h * 0.5)));
								return base;
							};

							// Chart height: header (~60px) + chart body height
							const chartHeaderHeight = 60;
							const chartBodyHeight = computeChartHeight();
							const totalChartHeight = chartHeaderHeight + chartBodyHeight;

							// Each card should be exactly half of the chart height
							const cardHeight = totalChartHeight / 2;
							// Small gap between cards
							const gapBetweenCards = 1;
							// Container height: 2 cards + gap, slightly less than chart to lift bottom boundary
							const cardsContainerHeight = cardHeight * 2 + gapBetweenCards;

							return (
								<Box
									sx={{
										height: cardsContainerHeight,
										display: "flex",
										flexDirection: "column",
										gap: gapBetweenCards,
									}}
								>
									{!isLoading &&
										filteredPredictions.map((prediction, index) => {
											// Calculate confidence from CI if available
											let confidence = 75; // Default fallback
											if (prediction.ci_low !== undefined && prediction.ci_high !== undefined && prediction.predicted_value) {
												// Confidence based on CI width relative to prediction
												// Narrower CI = higher confidence
												const ciWidth = Math.abs(prediction.ci_high - prediction.ci_low);
												const relativeWidth = ciWidth / Math.abs(prediction.predicted_value);
												
												// Adjust confidence based on prediction horizon
												// Longer horizons should have lower confidence (more uncertainty)
												const horizon = prediction.prediction_horizon || 6;
												// Penalty increases with horizon: 0% for 6h, 1.5% for 12h, 3% for 24h
												const horizonPenalty = (horizon - 6) / 6 * 3; // Linear scaling: 0, 1, 3
												
												// Base confidence from CI width
												const baseConfidence = Math.max(50, Math.min(95, 95 - (relativeWidth * 450)));
												// Apply horizon penalty (reduce confidence for longer horizons)
												confidence = Math.max(50, baseConfidence - horizonPenalty);
											}
											
											return (
												<Fade
													key={index}
													in={!isLoading}
													timeout={300}
													style={{ transitionDelay: `${index * 100}ms` }}
												>
													<Box sx={{ height: cardHeight, flexShrink: 0 }}>
														<PredictionCard
															prediction={prediction}
															confidence={Math.round(confidence)}
															selectedModel={selectedModel}
														/>
													</Box>
												</Fade>
											);
										})}

									{/* No predictions placeholder */}
									{(!data || data.predictions.length === 0) && !isLoading && (
										<Alert severity="info">
											No predictions available. The ML model is currently
											training or updating.
										</Alert>
									)}
									{isLoading &&
										Array.from({ length: 2 }).map((_, i) => {
											const skeletonCardHeight = totalChartHeight / 2;
											return (
												<Box
													key={i}
													sx={{ height: skeletonCardHeight, flexShrink: 0 }}
												>
													<Zoom
														in={isLoading}
														timeout={300}
														style={{ transitionDelay: `${i * 100}ms` }}
													>
														<Card elevation={2} sx={{ height: "100%" }}>
															<CardContent>
																<Skeleton
																	variant="text"
																	width="60%"
																	height={24}
																	sx={{ mb: 2 }}
																/>
																<Skeleton
																	variant="rectangular"
																	width="100%"
																	height={40}
																	sx={{ mb: 2, borderRadius: 1 }}
																/>
																<Skeleton
																	variant="text"
																	width="40%"
																	height={20}
																/>
																<Box
																	display="flex"
																	justifyContent="space-between"
																	mt={2}
																>
																	<Skeleton
																		variant="text"
																		width="30%"
																		height={20}
																	/>
																	<Skeleton
																		variant="circular"
																		width={60}
																		height={24}
																	/>
																</Box>
															</CardContent>
														</Card>
													</Zoom>
												</Box>
											);
										})}
								</Box>
							);
						})()}
					</Grid>
				</Grid>

				{/* Footer */}
				<LastUpdateIndicator lastRefresh={lastRefresh} />
			</Container>
		</Box>
	);
};

// Component for displaying last update time with auto-update
const LastUpdateIndicator: React.FC<{ lastRefresh: Date }> = ({
	lastRefresh,
}) => {
	const [timeAgo, setTimeAgo] = useState("");

	useEffect(() => {
		const updateTimeAgo = () => {
			const now = new Date();
			const diff = now.getTime() - lastRefresh.getTime();
			const seconds = Math.floor(diff / 1000);
			const minutes = Math.floor(seconds / 60);
			const hours = Math.floor(minutes / 60);

			if (seconds < 60) {
				setTimeAgo("just now");
			} else if (minutes < 60) {
				setTimeAgo(`${minutes} ${minutes === 1 ? "minute" : "minutes"} ago`);
			} else if (hours < 24) {
				setTimeAgo(`${hours} ${hours === 1 ? "hour" : "hours"} ago`);
			} else {
				setTimeAgo(lastRefresh.toLocaleString());
			}
		};

		updateTimeAgo();
		const interval = setInterval(updateTimeAgo, 10000); // Update every 10 seconds

		return () => clearInterval(interval);
	}, [lastRefresh]);

	return (
		<Box sx={{ mt: 6, py: 3, textAlign: "center" }}>
			<Typography variant="body2" color="textSecondary">
				© 2024 Criptify Team - BTC Price Prediction Dashboard
			</Typography>
			<Tooltip title={`Exact time: ${lastRefresh.toLocaleString()}`}>
				<Typography
					variant="caption"
					color="textSecondary"
					sx={{ cursor: "help" }}
				>
					Updated: {timeAgo}
				</Typography>
			</Tooltip>
		</Box>
	);
};

export default Dashboard;
