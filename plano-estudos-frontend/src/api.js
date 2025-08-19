// src/api.js

// Detecta se está rodando no Electron
const isElectron = window && window.process && window.process.type;

// Define a URL base da API conforme o ambiente
const API_BASE_URL = isElectron 
  ? 'http://localhost:5000'  // No Electron, usa localhost:5000
  : '';                      // No navegador, usa URL relativa (/api)

export async function api(path, opts = {}) {
  const res = await fetch(`${API_BASE_URL}/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  
  if (!res.ok) throw new Error(await res.text());
  const text = await res.text();
  return text ? JSON.parse(text) : {};
}