import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import ErrorBoundary from './ErrorBoundary'

// Dev-only runtime diagnostics
if ((import.meta as any).env?.DEV) {
	// eslint-disable-next-line no-console
	console.log('[Cryptify] Bootstrapping application...')
	console.log('[Cryptify] App version marker:', {
		buildTime: new Date().toISOString(),
		entry: 'main.tsx',
		appFile: 'App.tsx',
	})
	// eslint-disable-next-line @typescript-eslint/no-explicit-any, no-console
	console.log('[Cryptify] Vite env snapshot:', (import.meta as any).env)
}

function mount() {
	const rootEl = document.getElementById('root')
	if (!rootEl) {
		console.error('[Cryptify] #root element not found in DOM')
		return
	}
	try {
		ReactDOM.createRoot(rootEl).render(
			<React.StrictMode>
				<ErrorBoundary>
					<App />
				</ErrorBoundary>
			</React.StrictMode>
		)
		if ((import.meta as any).env?.DEV)
			console.log('[Cryptify] React mounted successfully')
	} catch (e) {
		console.error('[Cryptify] Mount failed:', e)
		;(window as any).__CRIPTIFY_MOUNT_ERROR__ = e
	}
}

// Capture global errors
if ((import.meta as any).env?.DEV) {
	window.addEventListener('error', ev => {
		// eslint-disable-next-line no-console
		console.error('[Cryptify] Global error event:', ev.error || ev.message)
	})
	window.addEventListener('unhandledrejection', ev => {
		// eslint-disable-next-line no-console
		console.error('[Cryptify] Unhandled promise rejection:', ev.reason)
	})
}

mount()
