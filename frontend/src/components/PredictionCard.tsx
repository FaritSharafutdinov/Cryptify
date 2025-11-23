import React from "react";
import {
	Card,
	CardContent,
	Typography,
	Box,
	Chip,
	Divider,
	Tooltip,
} from "@mui/material";
import PredictionIcon from "@mui/icons-material/TrendingUp";
import { PredictionCardProps } from "@/types";

const PredictionCard: React.FC<PredictionCardProps> = ({
	prediction,
	confidence = 75,
	selectedModel = "linear_regression",
}) => {
	const formatPrice = (price: number) => {
		return new Intl.NumberFormat("en-US", {
			style: "currency",
			currency: "USD",
			minimumFractionDigits: 2,
		}).format(price);
	};

	const formatTime = (timestamp: string) => {
		const date = new Date(timestamp);
		return date.toLocaleString("en-US", {
			month: "short",
			day: "numeric",
			hour: "2-digit",
			minute: "2-digit",
		});
	};

	const getConfidenceColor = (confidence: number) => {
		if (confidence >= 80) return "success";
		if (confidence >= 60) return "warning";
		return "error";
	};

	const getModelLabel = () => {
		const model = prediction.model || selectedModel;
		const labels: Record<string, string> = {
			linear_regression: "Linear Regression",
			xgboost: "XGBoost",
			lstm: "LSTM",
		};
		return labels[model] || model;
	};

	return (
		<Card
			elevation={2}
			sx={{
				height: "calc(100% - 15px)",
				minHeight: 200,
				display: "flex",
				flexDirection: "column",
				transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
				animation: "fadeInScale 0.5s ease-out",
				"@keyframes fadeInScale": {
					from: {
						opacity: 0,
						transform: "scale(0.95)",
					},
					to: {
						opacity: 1,
						transform: "scale(1)",
					},
				},
				"&:hover": {
					transform: "translateY(-6px) scale(1.02)",
					boxShadow: 8,
				},
			}}
		>
			<CardContent
				sx={{
					p: { xs: 1, sm: 1.25 },
					pb: { xs: 0.75, sm: 1 },
					flex: 1,
					display: "flex",
					flexDirection: "column",
					overflow: "auto",
					minHeight: 0,
				}}
			>
				<Box
					display="flex"
					alignItems="center"
					justifyContent="space-between"
					mb={1.5}
				>
					<Box display="flex" alignItems="center" gap={1}>
						<PredictionIcon
							color="primary"
							sx={{
								fontSize: "1.25rem",
								transition: "transform 0.3s ease",
								"&:hover": {
									transform: "rotate(15deg) scale(1.1)",
								},
							}}
						/>
						<Typography
							variant="subtitle1"
							component="h3"
							fontWeight="bold"
							sx={{
								fontSize: { xs: "0.95rem", sm: "1rem" },
								transition: "color 0.3s ease",
							}}
						>
							Price Prediction
						</Typography>
					</Box>
					<Chip
						label={getModelLabel()}
						size="small"
						color="primary"
						variant="outlined"
						sx={{
							fontSize: "0.7rem",
							height: "22px",
							transition: "all 0.2s ease",
							"&:hover": {
								transform: "scale(1.05)",
							},
						}}
					/>
				</Box>

				<Box
					display="flex"
					flexDirection="column"
					gap={1.5}
					sx={{ flex: 1, justifyContent: "space-between", minHeight: 0 }}
				>
					{/* Predicted Price */}
					<Tooltip title="Predicted Bitcoin price after the specified time period based on the selected machine learning model">
						<Box
							sx={{
								transition: "transform 0.3s ease",
								"&:hover": {
									transform: "translateX(4px)",
								},
							}}
						>
							<Typography
								variant="body2"
								color="textSecondary"
								sx={{ fontSize: { xs: "0.75rem", sm: "0.875rem" }, mb: 0.5 }}
							>
								Predicted Price ({prediction.prediction_horizon}h)
							</Typography>
							<Typography
								variant="h4"
								fontWeight="bold"
								color="primary"
								sx={{
									fontSize: { xs: "1.5rem", sm: "1.75rem" },
									transition: "transform 0.3s ease, color 0.3s ease",
									"&:hover": {
										transform: "scale(1.05)",
									},
								}}
							>
								{formatPrice(prediction.predicted_value)}
							</Typography>
						</Box>
					</Tooltip>

					<Divider sx={{ my: 0.75 }} />

					{/* Prediction Details */}
					<Box
						display="flex"
						justifyContent="space-between"
						alignItems="flex-start"
						flexWrap="wrap"
						gap={1.5}
					>
						<Box>
							<Typography
								variant="body2"
								color="textSecondary"
								sx={{ fontSize: { xs: "0.75rem", sm: "0.875rem" }, mb: 0.5 }}
							>
								Target Time
							</Typography>
							<Typography
								variant="body1"
								fontWeight="medium"
								sx={{ fontSize: { xs: "0.875rem", sm: "1rem" } }}
							>
								{formatTime(prediction.predicted_time)}
							</Typography>
						</Box>

						<Tooltip title="Model confidence level in the prediction. Above 80% - high confidence, 60-80% - medium, below 60% - low">
							<Box display="flex" flexDirection="column" alignItems="flex-end">
								<Typography
									variant="body2"
									color="textSecondary"
									sx={{ fontSize: { xs: "0.75rem", sm: "0.875rem" }, mb: 0.5 }}
								>
									Confidence
								</Typography>
								<Chip
									label={`${confidence}%`}
									color={getConfidenceColor(confidence)}
									variant="filled"
									size="small"
									sx={{
										height: "24px",
										fontSize: "0.75rem",
										fontWeight: "bold",
									}}
								/>
							</Box>
						</Tooltip>
					</Box>
				</Box>
			</CardContent>
		</Card>
	);
};

export default PredictionCard;
