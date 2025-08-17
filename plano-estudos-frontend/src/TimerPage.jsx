// src/TimerPage.jsx

import React, { useState, useEffect } from 'react';
import { api } from './api';
import { Card, Button, Select } from './components';
import { Timer, Play, Square, ListChecks } from 'lucide-react';
import { useStudyTimer } from './TimerContext';

// Novo componente para exibir o histórico
function SessionHistory({ sessions }) {
  if (!sessions || sessions.length === 0) {
    return <p className="empty-list-message">Nenhuma sessão de estudo salva ainda.</p>;
  }

  return (
    <ul className="history-list">
      {sessions.map(s => (
        <li key={s.id}>
          <div className="history-item-main">
            <span className="history-item-title">{s.task_title || s.discipline_name || "Sessão Avulsa"}</span>
            <span className="history-item-duration">{s.duration_minutes} min</span>
          </div>
          <div className="history-item-meta">
            <span>Início: {new Date(s.start).toLocaleString()}</span>
            <span>Fim: {new Date(s.end).toLocaleString()}</span>
          </div>
        </li>
      ))}
    </ul>
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