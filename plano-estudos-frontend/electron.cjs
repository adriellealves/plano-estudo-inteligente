const { app, BrowserWindow, dialog, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs'); // ✅ Importe o módulo fs

let pythonProcess = null;
let mainWindow = null; // Referência global para a janela principal
const isDev = !app.isPackaged;
let isQuitting = false;

function createPythonProcess() {
  return new Promise((resolve, reject) => {
    if (isDev) {
      console.log("Modo de desenvolvimento. O backend deve ser iniciado separadamente.");
      resolve();
      return;
    }

    const resourcesPath = process.resourcesPath;
    const backendPath = path.join(resourcesPath, 'backend');
    const backendDistPath = path.join(backendPath, 'dist');

    // Caminhos corrigidos
    const executableName = process.platform === 'win32' ? 'app.exe' : 'app';
    const scriptPath = path.join(backendDistPath, executableName);

    console.log(`Iniciando backend: ${scriptPath}`);
    pythonProcess = spawn(scriptPath);

    // Buffer para acumular saída
    let outputBuffer = '';

    const handleBackendReady = () => {
      console.log("✅ Backend pronto!");
      resolve();
    };

    pythonProcess.stdout.on('data', (data) => {
      const output = data.toString();
      console.log(`Backend: ${output}`);
      outputBuffer += output;

      // Detecta quando o Flask está pronto
      if (output.includes('Running on') || output.includes('* Serving Flask app')) {
        handleBackendReady();
      }
    });

    pythonProcess.stderr.on('data', (data) => {
      const error = data.toString();
      console.error(`Backend ERROR: ${error}`);
      
      // Tratamento de erros críticos
      if (error.includes('Address already in use') || error.includes('port is already in use')) {
        reject(new Error("Porta 5000 já está em uso"));
      }
    });

    pythonProcess.on('error', (error) => {
      console.error(`Falha ao iniciar backend: ${error.message}`);
      reject(error);
    });

    pythonProcess.on('close', (code) => {
      if (code !== 0) {
        console.error(`Backend encerrado com código ${code}`);
        reject(new Error(`Backend encerrado com código ${code}`));
      }
    });

    // Timeout para segurança
    setTimeout(() => {
      if (!outputBuffer.includes('Running on')) {
        console.warn("Backend não sinalizou prontidão, mas continuando...");
        handleBackendReady();
      }
    }, 10000);
  });
}

function killBackendProcess() {
  if (pythonProcess) {
    console.log("Encerrando processo do backend...");
    isQuitting = true;
    
    // Métodos diferentes para diferentes sistemas operacionais
    if (process.platform === 'win32') {
      // Windows: usa taskkill para forçar o encerramento
      const { exec } = require('child_process');
      exec(`taskkill /pid ${pythonProcess.pid} /t /f`, (err) => {
        if (err) {
          console.error('Falha ao encerrar processo com taskkill:', err);
          // Fallback: encerramento normal
          pythonProcess.kill();
        }
      });
    } else {
      // Unix-like systems: envia SIGTERM primeiro, depois SIGKILL se necessário
      pythonProcess.kill('SIGTERM');
      
      setTimeout(() => {
        if (pythonProcess && !pythonProcess.killed) {
          console.log("Forçando encerramento do backend...");
          pythonProcess.kill('SIGKILL');
        }
      }, 3000);
    }
    
    pythonProcess = null;
  }
}


function createWindow() {
  // Use uma referência global
  mainWindow = new BrowserWindow({
    width: 1600,
    height: 800,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      webSecurity: false // Importante para permitir requisições locais
    },
    show: false // Não mostrar até estar pronto
  });

  mainWindow.once('ready-to-show', () => {
    console.log("Janela pronta para mostrar");
    mainWindow.show();
    mainWindow.focus();
  });

  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    console.error(`Falha no carregamento: ${errorCode} ${errorDescription}`);
    dialog.showErrorBox(
      "Erro de Carregamento", 
      `Não foi possível carregar o aplicativo:\n\n${errorDescription}`
    );
  });

  // Intercepta links externos para abrir no navegador padrão
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    // Abre URLs externas no navegador padrão do sistema
    shell.openExternal(url);
    return { action: 'deny' }; // Impede que o Electron abra uma nova janela
  });

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    // Caminho absoluto para o index.html
    const indexPath = path.join(__dirname, 'dist', 'renderer', 'index.html');
    console.log(`Carregando frontend: ${indexPath}`);
    
    if (fs.existsSync(indexPath)) {
      mainWindow.loadFile(indexPath).catch(err => {
        console.error("Erro ao carregar arquivo:", err);
      });
    } else {
      dialog.showErrorBox(
        "Arquivo não encontrado", 
        `O arquivo principal não foi encontrado:\n${indexPath}`
      );
      app.quit();
    }

    // // Intercepta requisições para redirecionar para a API
    // mainWindow.webContents.session.webRequest.onBeforeRequest((details, callback) => {
    //   if (details.url.startsWith('file:///C:/api/')) {
    //     const newUrl = details.url.replace('file:///C:/api/', 'http://localhost:5000/api/');
    //     callback({ cancel: false, redirectURL: newUrl });
    //   } else {
    //     callback({ cancel: false });
    //   }
    // });
  }
}

// Função para mostrar erros
function showStartupError(message) {
  if (mainWindow && !mainWindow.isDestroyed()) {
    dialog.showMessageBox(mainWindow, {
      type: 'error',
      title: 'Erro de Inicialização',
      message: message
    });
  } else {
    dialog.showErrorBox("Erro de Inicialização", message);
  }
}

app.whenReady().then(async () => {
  try {
    if (!isDev) {
      await createPythonProcess();
    }
    createWindow();
    
    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
  } catch (error) {
    console.error("Erro crítico na inicialização:", error);
    showStartupError(`Não foi possível iniciar o aplicativo:\n\n${error.message}`);
    app.quit();
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    // Encerra o backend antes de sair
    killBackendProcess();
    app.quit();
  }
});

app.on('before-quit', (event) => {
  // Previne o encerramento padrão para garantir que o backend seja encerrado primeiro
  if (!isQuitting) {
    event.preventDefault();
    isQuitting = true;
    killBackendProcess();
    
    // Dá tempo para o backend encerrar antes de sair
    setTimeout(() => {
      app.quit();
    }, 1000);
  }
});

app.on('will-quit', () => {
  // Garante que o backend seja encerrado
  killBackendProcess();
});