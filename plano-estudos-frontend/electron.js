// frontend/electron.js

const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let pythonProcess = null;

function createPythonProcess() {
  // Inicia o servidor Python a partir do venv do backend
  const scriptPath = path.join(__dirname, '..', 'backend', 'app.py');
  const pythonExecutable = path.join(__dirname, '..', 'backend', 'venv', 'bin', 'python');
  
  pythonProcess = spawn(pythonExecutable, [scriptPath]);

  pythonProcess.stdout.on('data', (data) => {
    console.log(`Backend: ${data}`);
  });
  pythonProcess.stderr.on('data', (data) => {
    console.error(`Backend Error: ${data}`);
  });
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
  });

  // Em desenvolvimento, carrega o servidor do Vite.
  // Em produção, carregaria o arquivo buildado.
  win.loadURL('http://localhost:5173');
}

app.whenReady().then(() => {
  createPythonProcess();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Garante que o processo Python seja encerrado ao fechar o app
app.on('will-quit', () => {
  if (pythonProcess) {
    pythonProcess.kill();
  }
});