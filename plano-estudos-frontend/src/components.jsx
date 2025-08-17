// src/components.jsx
import React, { useState, useMemo, useEffect } from 'react';
import { api } from './api';
import { useStudyTimer } from './TimerContext';
import { Edit, Trash2, Timer, Square } from 'lucide-react';

export const Card = ({ title, icon, action, children, footer }) => (
  <div className="card">
    {(title || icon || action) && (
      <div className="card-header">
        <div className="card-title">{icon}{title}</div>
        <div>{action}</div>
      </div>
    )}
    <div className="card-body">{children}</div>
    {footer && (<div className="card-footer">{footer}</div>)}
  </div>
);

export const Button = ({ children, onClick, variant = "primary", ...props }) => {
  const variantClass = {
    primary: 'button-primary',
    ghost: 'button-ghost',
    danger: 'button-danger'
  }[variant];
  return (<button onClick={onClick} className={`button ${variantClass}`} {...props}>{children}</button>);
};

export const Select = (props) => (<select {...props} className="select" />);
export const Input = (props) => (<input {...props} className="input" />);

export const Modal = ({ isOpen, onClose, title, children }) => {
  if (!isOpen) return null;
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header"><h3>{title}</h3><button onClick={onClose} className="modal-close-btn">&times;</button></div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
};

export function TaskCard({ task, disciplineMap, onEdit, onDelete, onStatusChange }) {
  const { session, startTimer, stopTimer } = useStudyTimer();
  const isTimerActiveForThisTask = session && session.task_id === task.id;

  const handleTimerToggle = () => {
    if (isTimerActiveForThisTask) {
      stopTimer();
    } else if (!session) {
      startTimer(task.id);
    } else {
      alert("Já existe outra sessão de estudo em andamento.");
    }
  };

  return (
    <div className="task-card">
      <div className="task-card-header">
        <span className="task-card-header-id">Tarefa #{task.spreadsheet_task_id || task.id}</span>
        <h3 className="task-card-header-title">{task.title || 'Tarefa sem título'}</h3>
      </div>
      <div className="task-card-body">
        <div className="task-card-details">
          <div><strong>Disciplina:</strong> {disciplineMap[task.discipline_id] || 'N/D'}</div>
          <div><strong>Tópicos:</strong> {task.topics?.map(topic => topic.name).join(', ') || "—"}</div>
          <div><strong>Concluída em:</strong> {task.completion_date ?? "—"}</div>
          <div><strong>Status:</strong> {task.status}</div>
        </div>
        <div></div>
      </div>
      <div className="task-card-footer">
        
        {/* --- LÓGICA DE CONDIÇÃO ADICIONADA AQUI --- */}
        {/* Mostra estes botões apenas se a tarefa NÃO estiver concluída */}
        {task.status !== 'Concluída' && (
          <>
            <Button onClick={handleTimerToggle} variant={isTimerActiveForThisTask ? "danger" : "ghost"} title={isTimerActiveForThisTask ? "Parar Cronômetro" : "Iniciar Cronômetro"}>
              {isTimerActiveForThisTask ? <Square size={16} /> : <Timer size={16} />}
            </Button>
            <Button onClick={() => onEdit(task)} variant="ghost" title="Editar"><Edit size={16} /></Button>
            <Button onClick={() => onDelete(task.id)} variant="danger" title="Deletar"><Trash2 size={16} /></Button>
          </>
        )}
        
        <div style={{ marginLeft: 'auto' }}>
          {/* O botão de Concluir/Reabrir sempre aparece */}
          <Button onClick={() => onStatusChange(task)} variant={task.status === "Concluída" ? "ghost" : "primary"}>
            {task.status === "Concluída" ? "Reabrir" : "Concluir"}
          </Button>
        </div>
      </div>
    </div>
  );
}