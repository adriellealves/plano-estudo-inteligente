import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import './App.css';
import { TimerProvider } from './TimerContext'; // Importa o Provedor

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    {/* Envolve o App com o TimerProvider */}
    <TimerProvider>
      <App />
    </TimerProvider>
  </React.StrictMode>,
);