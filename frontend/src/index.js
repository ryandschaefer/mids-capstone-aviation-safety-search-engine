import React from 'react';
import ReactDOM from 'react-dom/client';
import {App} from './components/App.jsx';
import 'bootstrap';
import 'bootstrap/dist/css/bootstrap.min.css';

// Suppress errors from browser extensions to prevent error screen
window.addEventListener('error', function(event) {
  const filename = event.filename || '';
  const isExtensionError =
    filename.includes('chrome-extension://') ||
    filename.includes('moz-extension://') ||
    filename.includes('safari-extension://') ||
    filename.includes('safari-web-extension://');

  if (isExtensionError) {
    event.preventDefault();
    // Log for monitoring purposes
    console.debug('Extension error suppressed:', filename);
    return true;
  }
}, true);

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  // <React.StrictMode>
    <App />
  // </React.StrictMode>
);