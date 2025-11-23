import React from "react";
import { Box, Typography, Card, CardContent, Chip, Grid, Divider, Tooltip } from "@mui/material";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import ShowChartIcon from "@mui/icons-material/ShowChart";
import BarChartIcon from "@mui/icons-material/BarChart";
import { DashboardHeaderProps } from "@/types";

const DashboardHeader: React.FC<DashboardHeaderProps> = ({
	currentPrice = 44890.45,
	change24h = 2.5,
	lastUpdate = "2024-01-07T12:00:00Z",
	minPrice,
	maxPrice,
	totalVolume,
	volatility,
}) => {
	const isPositive = change24h >= 0;
	const formattedPrice = new Intl.NumberFormat("en-US", {
		style: "currency",
		currency: "USD",
		minimumFractionDigits: 2,
	}).format(currentPrice);

	const formatTimestamp = (timestamp: string) => {
		return new Date(timestamp).toLocaleString();
	};

	const formatPrice = (price: number) => {
		return new Intl.NumberFormat("en-US", {
			style: "currency",
			currency: "USD",
			minimumFractionDigits: 2,
			maximumFractionDigits: 2,
		}).format(price);
	};

	const formatVolume = (volume: number) => {
		if (volume >= 1000) {
			return `${(volume / 1000).toFixed(2)}K BTC`;
		}
		return `${volume.toFixed(2)} BTC`;
	};

	return (
		<Card
			elevation={3}
			sx={{
				mb: 2,
				transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
				animation: "fadeInUp 0.6s ease-out",
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
					boxShadow: 6,
					transform: "translateY(-2px)",
				},
			}}
		>
			<CardContent sx={{ py: { xs: 1.5, sm: 2 }, px: { xs: 1.5, sm: 2 } }}>
				<Grid container spacing={2} alignItems="center">
					{/* BTC Price */}
					<Grid item xs={12} sm={6} md={4}>
						<Box
							display="flex"
							flexDirection="column"
							sx={{
								animation: "fadeIn 0.8s ease-out 0.1s both",
								"@keyframes fadeIn": {
									from: { opacity: 0 },
									to: { opacity: 1 },
								},
							}}
						>
							<Typography
								variant="h5"
								component="h1"
								fontWeight="bold"
								color="primary"
								sx={{
									fontSize: { xs: "1.25rem", sm: "1.5rem" },
									transition: "color 0.3s ease",
								}}
							>
								Bitcoin (BTC)
							</Typography>
							<Typography
								variant="h4"
								component="h2"
								fontWeight="bold"
								sx={{
									mt: 0.5,
									fontSize: { xs: "1.5rem", sm: "2rem", md: "2.5rem" },
									transition: "transform 0.3s ease, color 0.3s ease",
									"&:hover": {
										transform: "scale(1.02)",
									},
								}}
							>
								{formattedPrice}
							</Typography>
						</Box>
					</Grid>

					{/* 24h Change */}
					<Grid item xs={12} sm={6} md={4}>
						<Box
							display="flex"
							alignItems="center"
							gap={1}
							flexWrap="wrap"
							justifyContent={{
								xs: "flex-start",
								sm: "center",
								md: "flex-start",
							}}
							sx={{
								animation: "fadeIn 0.8s ease-out 0.2s both",
								"@keyframes fadeIn": {
									from: { opacity: 0 },
									to: { opacity: 1 },
								},
							}}
						>
							{isPositive ? (
								<TrendingUpIcon
									color="success"
									sx={{
										fontSize: { xs: "1.5rem", sm: "2rem" },
										transition: "transform 0.3s ease",
										animation: "pulse 2s ease-in-out infinite",
										"@keyframes pulse": {
											"0%, 100%": { transform: "scale(1)" },
											"50%": { transform: "scale(1.1)" },
										},
									}}
								/>
							) : (
								<TrendingDownIcon
									color="error"
									sx={{
										fontSize: { xs: "1.5rem", sm: "2rem" },
										transition: "transform 0.3s ease",
										animation: "pulse 2s ease-in-out infinite",
										"@keyframes pulse": {
											"0%, 100%": { transform: "scale(1)" },
											"50%": { transform: "scale(1.1)" },
										},
									}}
								/>
							)}
							<Chip
								label={`${isPositive ? "+" : ""}${change24h.toFixed(2)}%`}
								color={isPositive ? "success" : "error"}
								variant="filled"
								size="medium"
								sx={{
									fontSize: { xs: "0.75rem", sm: "0.875rem" },
									transition: "transform 0.2s ease",
									"&:hover": {
										transform: "scale(1.05)",
									},
								}}
							/>
							<Typography
								variant="body2"
								color="textSecondary"
								sx={{ fontSize: { xs: "0.75rem", sm: "0.875rem" } }}
							>
								24h Change
							</Typography>
						</Box>
					</Grid>

					{/* Last Update */}
					<Grid item xs={12} md={4}>
						<Box
							display="flex"
							flexDirection="column"
							alignItems={{ xs: "flex-start", sm: "center", md: "flex-end" }}
						>
							<Typography
								variant="body2"
								color="textSecondary"
								sx={{ fontSize: { xs: "0.75rem", sm: "0.875rem" } }}
							>
								Last Updated
							</Typography>
							<Typography
								variant="body1"
								fontWeight="medium"
								sx={{ fontSize: { xs: "0.875rem", sm: "1rem" } }}
							>
								{formatTimestamp(lastUpdate)}
							</Typography>
						</Box>
					</Grid>
				</Grid>

				{/* Statistics Row */}
				{(minPrice !== undefined || maxPrice !== undefined || totalVolume !== undefined || volatility !== undefined) && (
					<>
						<Divider sx={{ my: 1.5 }} />
						<Grid container spacing={1.5}>
							{/* Min/Max Prices */}
							{(minPrice !== undefined || maxPrice !== undefined) && (
								<Grid item xs={6} sm={3}>
									<Tooltip title="Minimum and maximum Bitcoin price for the selected time period">
										<Box
											display="flex"
											flexDirection="column"
											sx={{
												animation: "fadeIn 0.8s ease-out 0.3s both",
												"@keyframes fadeIn": {
													from: { opacity: 0 },
													to: { opacity: 1 },
												},
												cursor: "help",
											}}
										>
										<Box display="flex" alignItems="center" gap={0.5} mb={0.25}>
											<ShowChartIcon
												sx={{
													fontSize: "0.875rem",
													color: "text.secondary",
												}}
											/>
											<Typography
												variant="caption"
												color="textSecondary"
												sx={{ fontSize: { xs: "0.6rem", sm: "0.7rem" } }}
											>
												Min / Max
											</Typography>
										</Box>
										{minPrice !== undefined && (
											<Typography
												variant="body2"
												fontWeight="medium"
												color="error"
												sx={{ fontSize: { xs: "0.7rem", sm: "0.8rem" }, lineHeight: 1.2 }}
											>
												{formatPrice(minPrice)}
											</Typography>
										)}
										{maxPrice !== undefined && (
											<Typography
												variant="body2"
												fontWeight="medium"
												color="success.main"
												sx={{ fontSize: { xs: "0.7rem", sm: "0.8rem" }, lineHeight: 1.2 }}
											>
												{formatPrice(maxPrice)}
											</Typography>
										)}
										</Box>
									</Tooltip>
								</Grid>
							)}

							{/* Total Volume */}
							{totalVolume !== undefined && (
								<Grid item xs={6} sm={3}>
									<Tooltip title="Total Bitcoin trading volume for the selected period. Shows market activity">
										<Box
											display="flex"
											flexDirection="column"
											sx={{
												animation: "fadeIn 0.8s ease-out 0.4s both",
												"@keyframes fadeIn": {
													from: { opacity: 0 },
													to: { opacity: 1 },
												},
												cursor: "help",
											}}
										>
										<Box display="flex" alignItems="center" gap={0.5} mb={0.25}>
											<BarChartIcon
												sx={{
													fontSize: "0.875rem",
													color: "text.secondary",
												}}
											/>
											<Typography
												variant="caption"
												color="textSecondary"
												sx={{ fontSize: { xs: "0.6rem", sm: "0.7rem" } }}
											>
												Volume
											</Typography>
										</Box>
										<Typography
											variant="body2"
											fontWeight="medium"
											sx={{ fontSize: { xs: "0.7rem", sm: "0.8rem" }, lineHeight: 1.2 }}
										>
											{formatVolume(totalVolume)}
										</Typography>
										</Box>
									</Tooltip>
								</Grid>
							)}

							{/* Volatility */}
							{volatility !== undefined && (
								<Grid item xs={6} sm={3}>
									<Tooltip title="Volatility shows price variability. Low (<2%) - stable market, Medium (2-5%) - normal activity, High (>5%) - unstable market">
										<Box
											display="flex"
											flexDirection="column"
											sx={{
												animation: "fadeIn 0.8s ease-out 0.5s both",
												"@keyframes fadeIn": {
													from: { opacity: 0 },
													to: { opacity: 1 },
												},
												cursor: "help",
											}}
										>
										<Typography
											variant="caption"
											color="textSecondary"
											sx={{ fontSize: { xs: "0.6rem", sm: "0.7rem" }, mb: 0.25 }}
										>
											Volatility
										</Typography>
										<Typography
											variant="body2"
											fontWeight="medium"
											color={volatility > 5 ? "error.main" : volatility > 2 ? "warning.main" : "success.main"}
											sx={{ fontSize: { xs: "0.7rem", sm: "0.8rem" }, lineHeight: 1.2 }}
										>
											{volatility.toFixed(2)}%
										</Typography>
										</Box>
									</Tooltip>
								</Grid>
							)}
						</Grid>
					</>
				)}
			</CardContent>
		</Card>
	);
};

export default DashboardHeader;
