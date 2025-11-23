import React from 'react'

type ErrorBoundaryState = { hasError: boolean; error?: any }

export class ErrorBoundary extends React.Component<
	React.PropsWithChildren,
	ErrorBoundaryState
> {
	state: ErrorBoundaryState = { hasError: false }

	static getDerivedStateFromError(error: any): ErrorBoundaryState {
		return { hasError: true, error }
	}

	componentDidCatch(error: any, info: any) {
		// eslint-disable-next-line no-console
		console.error('[ErrorBoundary] Uncaught error:', error, info)
		;(window as any).__CRIPTIFY_LAST_ERROR__ = { error, info }
	}

	render() {
		if (this.state.hasError) {
			return (
				<div
					style={{
						padding: 32,
						maxWidth: 720,
						margin: '40px auto',
						fontFamily: 'Roboto, Arial, sans-serif',
					}}
				>
					<h1 style={{ color: '#f57c00' }}>⚠️ An error occurred in the interface</h1>
					<pre
						style={{
							background: '#1e1e1e',
							padding: 16,
							borderRadius: 8,
							color: '#ffb4b4',
							overflowX: 'auto',
						}}
					>
						{String(this.state.error)}
					</pre>
					<p style={{ opacity: 0.7 }}>
						Check the browser console (DevTools → Console) for details.
					</p>
				</div>
			)
		}
		return this.props.children
	}
}

export default ErrorBoundary
