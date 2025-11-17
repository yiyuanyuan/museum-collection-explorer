import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';
import posthog from 'posthog-js';

// Initialize PostHog
// Only initialize if API key is provided
if (process.env.REACT_APP_POSTHOG_KEY) {
  posthog.init(process.env.REACT_APP_POSTHOG_KEY, {
    api_host: 'https://app.posthog.com',
    autocapture: true, // Automatically captures clicks, form submissions, page views
    capture_pageview: true, // Capture initial page view
    capture_pageleave: true, // Capture when users leave
    session_recording: {
      enabled: true, // Enable session recordings
      recordCrossOriginIframes: true,
      maskAllInputs: false, // Don't mask inputs by default
      maskTextSelector: '.sensitive-data' // Only mask elements with this class
    },
    persistence: 'localStorage', // Store user data in localStorage
    loaded: (posthog) => {
      if (process.env.NODE_ENV === 'development') {
        posthog.debug(); // Enable debug mode in development
      }
    }
  });
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();