// src/TrailsPage.jsx

import React, { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from "framer-motion";
import { api } from './api';
import { Card, Button, TaskCard } from './components'; // TaskCard já está importado
import { ListChecks, ArrowLeft, GitMerge, CheckCircle2, Edit, RefreshCw, Trash2, Timer, Play, Square } from 'lucide-react';

export function TrailsPage({ keyProp, onEditTask, onTimerToggle, activeSession }) { // Recebe as props
  const [trilhas, setTrilhas] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [selectedTrilha, setSelectedTrilha] = useState(null);
  const [disciplines, setDisciplines] = useState([]);
  const [loading, setLoading] = useState(true);
  
  const disciplineMap = useMemo(() => disciplines.reduce((acc, d) => ({...acc, [d.id]: d.name}), {}), [disciplines]);

  const loadTrilhas = async () => {
    setLoading(true);
    try {
      const [trilhasData, disciplinesData] = await Promise.all([
        api('/trilhas'),
        api('/disciplines')
      ]);
      setTrilhas(trilhasData || []);
      setDisciplines(disciplinesData || []);
    } catch (e) { console.error("Falha ao carregar trilhas", e); }
    finally { setLoading(false); }
  };

  const loadTasksForTrilha = async (trilhaId) => {
    setLoading(true);
    try {
      const tasksData = await api(`/trilhas/${trilhaId}/tasks`);
      setTasks(tasksData || []);
    } catch (e) { console.error("Falha ao carregar tarefas da trilha", e); }
    finally { setLoading(false); }
  };

  useEffect(() => {
    loadTrilhas();
  }, [keyProp]);

  const handleSelectTrilha = (trilha) => {
    setSelectedTrilha(trilha);
    loadTasksForTrilha(trilha.id);
  };

  const handleStatusChange = async (task) => {
    const newStatus = task.status === "Concluída" ? "Pendente" : "Concluída";
    const newCompletionDate = newStatus === 'Concluída' ? new Date().toISOString().split('T')[0] : null;
    const updatedTaskPayload = { ...task, status: newStatus, completion_date: newCompletionDate, topic_ids: task.topics.map(t => t.id) };
    await api(`/tasks/${task.id}`, { method: "PUT", body: JSON.stringify(updatedTaskPayload) });
    loadTasksForTrilha(selectedTrilha.id);
    loadTrilhas();
  };

  const handleDelete = async (taskId) => {
    if (window.confirm("Tem certeza que deseja deletar esta tarefa?")) {
      await api(`/tasks/${taskId}`, { method: 'DELETE' });
      loadTasksForTrilha(selectedTrilha.id);
    }
  };

  if (loading) return <div>Carregando...</div>;

  if (selectedTrilha) {
    return (
      <div className="flex-container-col">
        <Button variant="ghost" onClick={() => { setSelectedTrilha(null); loadTrilhas(); }} style={{ alignSelf: 'flex-start' }}>
          <ArrowLeft /> Voltar para Todas as Trilhas
        </Button>
        <h2 style={{textAlign: 'center', fontSize: '1.5rem', fontWeight: 600}}>{selectedTrilha.name}</h2>
        <div className="grid-container tasks-grid">
          <AnimatePresence>
            {tasks.map(t => (
              <motion.div key={t.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <TaskCard 
                  task={t} 
                  disciplineMap={disciplineMap}
                  onEdit={onEditTask}
                  onDelete={handleDelete}
                  onStatusChange={handleStatusChange}
                  // CORREÇÃO: Passa a funcionalidade real do timer para o card
                  onTimerToggle={onTimerToggle}
                  activeSession={activeSession}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>
    );
  }

  return (
   <div className="trilhas-grid">
      {trilhas.map(trilha => (
        <Card
          key={trilha.id}
          title={trilha.name}
          icon={<GitMerge />}
          action={<span className={`status-badge status-${trilha.status.toLowerCase()}`}>{trilha.status}</span>}
        >
          <p style={{ minHeight: '40px' }}>Verifique o andamento das tarefas desta trilha.</p>
          <div className="card-footer">
            <Button onClick={() => handleSelectTrilha(trilha)}>Ver Tarefas</Button>
          </div>
        </Card>
      ))}
    </div>
  );
}