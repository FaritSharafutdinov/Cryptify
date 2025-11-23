import React, { useEffect, useMemo, useState } from 'react'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import { CssBaseline } from '@mui/material'
import { SnackbarProvider } from 'notistack'
import Dashboard from './components/Dashboard'

function App() {
	const [darkMode, setDarkMode] = useState(true)

	// Load persisted theme or default to dark mode
	useEffect(() => {
		const stored = localStorage.getItem('cryptify:darkMode')
		if (stored !== null) {
			setDarkMode(stored === 'true')
		} else {
			// Default to dark mode
			setDarkMode(true)
		}
	}, [])

	// Persist changes
	useEffect(() => {
		localStorage.setItem('cryptify:darkMode', String(darkMode))
	}, [darkMode])

	const theme = useMemo(
		() =>
			createTheme({
				palette: {
					mode: darkMode ? 'dark' : 'light',
					primary: { main: '#f57c00' },
					secondary: { main: '#1976d2' },
					background: darkMode
						? { default: '#0a0a0a', paper: '#121212' }
						: { default: '#f5f5f5', paper: '#ffffff' },
				},
				typography: {
					fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
					h1: { fontWeight: 700 },
					h2: { fontWeight: 600 },
					h3: { fontWeight: 600 },
				},
				transitions: {
					duration: {
						shortest: 150,
						shorter: 200,
						short: 250,
						standard: 300,
						complex: 375,
						enteringScreen: 225,
						leavingScreen: 195,
					},
					easing: {
						easeInOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
						easeOut: 'cubic-bezier(0.0, 0, 0.2, 1)',
						easeIn: 'cubic-bezier(0.4, 0, 1, 1)',
						sharp: 'cubic-bezier(0.4, 0, 0.6, 1)',
					},
				},
				components: {
					MuiCard: {
						styleOverrides: {
							root: {
								borderRadius: 12,
								transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
							},
						},
					},
					MuiPaper: {
						styleOverrides: {
							root: {
								borderRadius: 8,
								transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
							},
						},
					},
					MuiButton: {
						styleOverrides: {
							root: {
								transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
								'&:hover': {
									transform: 'translateY(-1px)',
								},
							},
						},
					},
					MuiIconButton: {
						styleOverrides: {
							root: {
								transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
								'&:hover': {
									transform: 'scale(1.1)',
								},
							},
						},
					},
					MuiChip: {
						styleOverrides: {
							root: {
								transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
							},
						},
					},
				},
			}),
		[darkMode]
	)

	// Dark mode state lifted; minimal logging only during development (removed verbose render logs)

	return (
		<ThemeProvider theme={theme}>
			<CssBaseline />
			<SnackbarProvider
				maxSnack={3}
				anchorOrigin={{
					vertical: 'bottom',
					horizontal: 'right',
				}}
				autoHideDuration={4000}
			>
				<Dashboard
					darkMode={darkMode}
					onToggleDarkMode={() => setDarkMode(d => !d)}
				/>
			</SnackbarProvider>
		</ThemeProvider>
	)
}

export default App
