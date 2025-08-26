// src/App.jsx
import React, { useState, useEffect } from 'react';
import CoursesPage from './CoursesPage';
import { api } from './api';
import { Button, Modal } from './components'; 
import { DisciplineForm, TopicForm, TaskForm } from './ManagePage'; // Os forms agora vivem em ManagePage
import { AlertDialog } from './AlertDialog';
import { Dashboard } from './Dashboard';
import { Tasks } from './Tasks';
import { TimerPage } from './TimerPage';
import { Reviews } from './Reviews';
import { ManagePage } from './ManagePage';
import { Importer } from './Importer';
import { TrailsPage } from './TrailsPage';
import { PerformanceHistory } from './PerformanceHistory';
import { GoalsPage } from './GoalsPage';
import { Timer, ListChecks, PieChart as PieChartIcon, Edit, CalendarClock, GitMerge, TrendingUp, Target, BookOpen } from "lucide-react";
import { useStudyTimer } from './TimerContext';

export default function App() {
  const [tab, setTab] = useState("dashboard");
  const [refreshKey, setRefreshKey] = useState(0);
  const [modal, setModal] = useState({ isOpen: false, type: null, data: null });
  const [disciplines, setDisciplines] = useState([]);
  const [alert, setAlert] = useState({ show: false, type: '', message: '', title: '' });
  
  // Apenas a função stopTimer é necessária aqui para o alerta
  const { session } = useStudyTimer(); 

  // Carrega apenas os dados realmente globais necessários para os Modais
  useEffect(() => {
    const loadGlobalData = async () => {
      try {
        const d = await api('/disciplines');
        setDisciplines(d);
      } catch(e) { console.error("Falha ao carregar disciplinas", e) }
    };
    loadGlobalData();
  }, [refreshKey]);

  const handleSync = () => setRefreshKey(prevKey => prevKey + 1);
  const handleOpenModal = (type, data = null) => setModal({ isOpen: true, type, data });

  const handleSave = async (type, data) => {
    try {
      const endpoint = `${type}s`;
      if (data.id) {
        await api(`/${endpoint}/${data.id}`, { method: 'PUT', body: JSON.stringify(data) });
      } else {
        const url = type === 'topic' ? `/disciplines/${data.discipline_id}/topics` : `/${endpoint}`;
        await api(url, { method: 'POST', body: JSON.stringify(data) });
      }
      setModal({ isOpen: false });
      handleSync();
    } catch(e) {
      setAlert({
        show: true,
        type: 'error',
        title: 'Erro ao Salvar',
        message: e.message
      });
    }
  };

  const tabs = [
    { id: "dashboard", label: "Dashboard", icon: <PieChartIcon /> },
    { id: "performance", label: "Desempenho", icon: <TrendingUp /> },
    { id: "goals", label: "Metas", icon: <Target /> },
    { id: "trilhas", label: "Trilhas", icon: <GitMerge /> },
    { id: "tasks", label: "Tarefas", icon: <ListChecks /> },
    { id: "timer", label: "Sessões", icon: <Timer /> },
    { id: "courses", label: "Cursos", icon: <BookOpen /> },
    { id: "manage", label: "Gerenciar", icon: <Edit /> },
  ];

  return (
    <div className="app-container">
      <header className="header">
        <div className="header-content">
            <div className="header-title">
                <span className={`logo-icon ${session ? 'timer-active-glow' : ''}`}><Timer /></span>
                <h1 className="app-title">Plano de Estudos Auditor TCU</h1>
            </div>
            <div className="header-actions">
              <nav className="header-nav">
                {tabs.map(t => (
                    <Button key={t.id} variant={tab === t.id ? "primary" : "ghost"} onClick={() => setTab(t.id)}>{t.icon}{t.label}</Button>
                ))}
            </nav>
            <Importer onSync={handleSync} />
            </div>
        </div>
       
      </header>
      <main className="main-content">
        
        {tab === "dashboard" && <Dashboard key={refreshKey} />}
        {tab === "performance" && <PerformanceHistory key={refreshKey} />}
        {tab === "goals" && <GoalsPage key={refreshKey} />}
        {tab === "trilhas" && <TrailsPage key={refreshKey} onEditTask={(task) => handleOpenModal('task', task)} />}
        {tab === "tasks" && <Tasks key={refreshKey} onEditTask={(task) => handleOpenModal('task', task)} onDataChange={handleSync} />}
        {tab === "timer" && <TimerPage key={refreshKey} />}
        {tab === "courses" && <CoursesPage key={refreshKey} />}
        {tab === "manage" && <ManagePage key={refreshKey} onOpenModal={handleOpenModal} />}
      </main>
      <footer className="footer">API Conectada</footer>

      <AlertDialog
        isOpen={alert.show}
        onClose={() => setAlert({ ...alert, show: false })}
        title={alert.title}
        message={alert.message}
        type={alert.type}
        confirmLabel="OK"
      />

      <Modal isOpen={modal.isOpen} onClose={() => setModal({ isOpen: false })} title={`${modal.data?.id ? 'Editar' : 'Adicionar'} ${modal.type}`}>
          {modal.type === 'discipline' && <DisciplineForm data={modal.data} onSave={(d) => handleSave('discipline', d)} onCancel={() => setModal({isOpen: false})} />}
          {modal.type === 'topic' && <TopicForm data={modal.data} disciplines={disciplines} onSave={(d) => handleSave('topic', d)} onCancel={() => setModal({isOpen: false})} />}
          {/* O TaskForm agora busca seus próprios tópicos e não precisa mais da prop 'topics' */}
          {modal.type === 'task' && <TaskForm data={modal.data} disciplines={disciplines} onSave={(d) => handleSave('task', d)} onCancel={() => setModal({isOpen: false})} />}
      </Modal>
    </div>
  );
}