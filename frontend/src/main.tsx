import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

// Optional custom API base URL for external deployments (e.g. Vercel)
const rawBase = (import.meta.env.VITE_API_BASE_URL as string | undefined) || '';
const API_BASE = rawBase.trim().replace(/\/+$/, '');

// Automatically bypass ngrok free interstitial warning page & rewrite API endpoints if deployed
const originalFetch = window.fetch;
window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
  try {
    let resolvedInput = input;
    if (API_BASE) {
      if (typeof input === 'string' && input.startsWith('/api')) {
        resolvedInput = `${API_BASE}${input}`;
      } else if (input instanceof URL && input.pathname.startsWith('/api')) {
        resolvedInput = `${API_BASE}${input.pathname}${input.search}`;
      } else if (input instanceof Request && input.url.startsWith('/api')) {
        resolvedInput = new Request(`${API_BASE}${input.url}`, input);
      }
    }

    let headers: Headers;
    if (init?.headers) {
      headers = new Headers(init.headers);
    } else if (resolvedInput instanceof Request) {
      headers = new Headers(resolvedInput.headers);
    } else {
      headers = new Headers();
    }
    if (!headers.has('ngrok-skip-browser-warning')) {
      headers.set('ngrok-skip-browser-warning', 'true');
    }
    return originalFetch(resolvedInput, { ...init, headers });
  } catch {
    return originalFetch(input, init);
  }
};

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
