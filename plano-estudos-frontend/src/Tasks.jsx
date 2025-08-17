// src/Tasks.jsx

import React, { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from "framer-motion";
import { api } from './api';
import { Card, Button, Select, TaskCard } from './components';
import { AddResultCard } from './AddResultCard';
import { ListChecks, RefreshCw } from 'lucide-react';

// CORREÇÃO: Recebe as novas props 'onTimerToggle' e 'activeSession'
export function Tasks({ keyProp, onEditTask, onDataChange, onTimerToggle, activeSession }) {
  const [tasks, setTasks] = useState([]);
  const [disciplines, setDisciplines] = useState([]);
  const [statusFilter, setStatusFilter] = useState("Pendente");
  const [loading, setLoading] = useState(true);
  
  const disciplineMap = useMemo(() => disciplines.reduce((acc, d) => ({...acc, [d.id]: d.name}), {}), [disciplines]);

  const loadTasks = async () => {
    setLoading(true);
    try {
      const data = await api(`/tasks?status=${statusFilter}`);
      setTasks(data);
    } catch (e) { console.error(e); } 
    finally { setLoading(false); }
  };

  useEffect(() => {
    api("/disciplines").then(setDisciplines);
  }, []);

  useEffect(() => {
    loadTasks();
  }, [statusFilter, keyProp]);

  const toggleStatus = async (task) => {
    const newStatus = task.status === "Concluída" ? "Pendente" : "Concluída";
    const newCompletionDate = newStatus === 'Concluída' ? new Date().toISOString().split('T')[0] : null;
    const updatedTaskPayload = { ...task, status: newStatus, completion_date: newCompletionDate, topic_ids: task.topics.map(t => t.id) };
    await api(`/tasks/${task.id}`, { method: "PUT", body: JSON.stringify(updatedTaskPayload) });
    loadTasks();
  };

  const handleDelete = async (taskId) => {
    if (window.confirm("Tem certeza que deseja deletar esta tarefa?")) {
      await api(`/tasks/${taskId}`, { method: 'DELETE' });
      loadTasks();
    }
  };

  if (loading) return <div style={{ padding: '1rem' }}>Carregando Tarefas...</div>;

  return (
    <div className="flex-container-col ">
      <div className="flex-container tasks-header">
        <AddResultCard onDataChange={onDataChange} />
        <Card title="Filtrar Tarefas" icon={<ListChecks />}>
          <div className="filter-container" style={{gridTemplateColumns: '200px auto'}}>
            <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} >
              <option value="Pendente">Pendentes</option>
              <option value="Concluída">Concluídas</option>
            </Select>
            <Button variant="ghost" onClick={loadTasks}><RefreshCw />Atualizar</Button>
          </div>
        </Card>
      </div>
      <div className="grid-container tasks-grid">
        <AnimatePresence>
          {tasks.map(t => (
            <motion.div key={t.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <TaskCard 
                task={t}
                disciplineMap={disciplineMap}
                onEdit={onEditTask}
                onDelete={handleDelete}
                onStatusChange={toggleStatus}
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