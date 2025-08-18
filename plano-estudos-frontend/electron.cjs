const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let pythonProcess = null;
const isDev = !app.isPackaged; // Verifica se estamos em modo de desenvolvimento

function createPythonProcess() {
  if (isDev) {
    // --- MODO DE DESENVOLVIMENTO ---
    // O backend já é iniciado pelo "concurrently"
    console.log("Modo de desenvolvimento. O backend deve ser iniciado separadamente.");
    return;
  }

  // --- MODO DE PRODUÇÃO ---
  // O caminho para os 'extraResources' onde o backend foi empacotado
  const resourcesPath = process.resourcesPath;
  const backendPath = path.join(resourcesPath, 'backend');

  // Determina o nome do executável baseado no sistema operacional
  const executableName = process.platform === 'win64' ? 'app.exe' : 'app';
  const scriptPath = path.join(backendPath, executableName);
  
  console.log(`Iniciando backend de produção em: ${scriptPath}`);

  pythonProcess = spawn(scriptPath);

  pythonProcess.stdout.on('data', (data) => console.log(`Backend Prod: ${data}`));
  pythonProcess.stderr.on('data', (data) => console.error(`Backend Prod Error: ${data}`));
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1600,
    height: 800,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
  });

  if (isDev) {
    // Carrega a URL do servidor Vite
    win.loadURL('http://localhost:5173');
    win.webContents.openDevTools();
  } else {
    // Carrega o index.html da nova pasta 'dist/renderer'
    win.loadFile(path.join(__dirname, 'dist/renderer', 'index.html'));
  }
}

app.whenReady().then(() => {
  // Em produção, precisamos iniciar o backend empacotado
  if (!isDev) {
    createPythonProcess();
  }
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('will-quit', () => {
  if (pythonProcess) {
    console.log("Encerrando processo do backend...");
    pythonProcess.kill();
  }
});
