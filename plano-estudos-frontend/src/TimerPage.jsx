// src/TimerPage.jsx

import React, { useState, useEffect } from 'react';
import { api } from './api';
import { Card, Button, Select } from './components';
import { Timer, Play, Square, ListChecks, Trash2 } from 'lucide-react';
import { useStudyTimer } from './TimerContext';
import { AlertDialog } from './AlertDialog';

// Novo componente para exibir o histórico
function SessionHistory({ sessions }) {
  const { deleteSession } = useStudyTimer();
  const [alert, setAlert] = useState({ show: false, type: '', message: '', title: '', onConfirm: null });

  if (!sessions || sessions.length === 0) {
    return <p className="empty-list-message">Nenhuma sessão de estudo salva ainda.</p>;
  }

  const handleDelete = (sessionId) => {
    setAlert({
      show: true,
      type: 'confirm',
      title: 'Confirmar Exclusão',
      message: 'Tem certeza que deseja excluir esta sessão de estudo?',
      onConfirm: () => {
        deleteSession(sessionId);
        setAlert({ ...alert, show: false });
      }
    });
  };

  return (
    <>
      <AlertDialog
        isOpen={alert.show}
        onClose={() => setAlert({ ...alert, show: false })}
        title={alert.title}
        message={alert.message}
        type={alert.type}
        confirmLabel={alert.type === 'confirm' ? 'Excluir' : 'OK'}
        cancelLabel={alert.type === 'confirm' ? 'Cancelar' : undefined}
        onConfirm={alert.onConfirm}
      />
      <ul className="history-list">
        {sessions.map(s => (
          <li key={s.id}>
            <div className="history-item-main">
              <span className="history-item-title">{s.task_title || s.discipline_name || "Sessão Avulsa"}</span>
              <div className="history-item-actions">
                <span className="history-item-duration">{s.duration_minutes} min</span>
                <Button variant="ghost" onClick={() => handleDelete(s.id)} title="Excluir sessão">
                  <Trash2 size={16} />
                </Button>
              </div>
            </div>
            <div className="history-item-meta">
              <span>Início: {new Date(s.start).toLocaleString()}</span>
              <span>Fim: {new Date(s.end).toLocaleString()}</span>
            </div>
          </li>
        ))}
      </ul>
    </>
  );
}


export function TimerPage({ keyProp }) {
  const { session, elapsed, startTimer, stopTimer } = useStudyTimer();
  const [tasks, setTasks] = useState([]);
  const [selectedTaskId, setSelectedTaskId] = useState("");
  const [history, setHistory] = useState([]); // Novo estado para o histórico
  const [loading, setLoading] = useState(true);

  const loadPageData = async () => {
    setLoading(true);
    try {
      // Busca tarefas pendentes e o histórico em paralelo
      const [tasksData, historyData] = await Promise.all([
        api("/tasks?status=Pendente"),
        api("/sessions/history")
      ]);
      setTasks(tasksData || []);
      setHistory(historyData || []);
    } catch(e) {
      console.error("Erro ao carregar dados da página de sessões:", e);
    } finally {
      setLoading(false);
    }
  };
  
  // Recarrega os dados quando a chave de refresh mudar ou quando uma sessão terminar
  useEffect(() => {
    loadPageData();
  }, [keyProp, session]);

  const handleStart = () => {
    startTimer(selectedTaskId || null);
  };
  
  return (
    <div className="flex-container-col">
      <Card title="Cronômetro" icon={<Timer />}>
        <div className="timer-display">{elapsed}</div>
        <div className="timer-controls">
          <Select value={selectedTaskId} onChange={(e) => setSelectedTaskId(e.target.value)} disabled={!!session}>
            <option value="">— Sessão avulsa —</option>
            {tasks.map(t => <option key={t.id} value={t.id}>{t.title || `Tarefa #${t.id}`}</option>)}
          </Select>
          {!session ? (
            <Button onClick={handleStart}><Play/>Iniciar</Button>
          ) : (
            <Button onClick={stopTimer} variant="danger"><Square/>Parar & Salvar</Button>
          )}
        </div>
      </Card>

      <Card title="Últimas Sessões Salvas" icon={<ListChecks />}>
        {loading ? <p>Carregando histórico...</p> : <SessionHistory sessions={history} />}
      </Card>
    </div>
  );
}