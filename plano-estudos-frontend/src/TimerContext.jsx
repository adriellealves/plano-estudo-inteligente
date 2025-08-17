// src/TimerContext.jsx
import React, { createContext, useState, useEffect, useRef, useContext } from 'react';
import { api } from './api';

const SESSION_STORAGE_KEY = 'activeStudySession';
const TimerContext = createContext();

export function TimerProvider({ children, onDataChange }) {
  const [session, setSession] = useState(null);
  const [elapsed, setElapsed] = useState("00:00:00");
  const timerRef = useRef(null);

  useEffect(() => {
    const savedSession = sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (savedSession) {
      setSession(JSON.parse(savedSession));
    }
  }, []);

  useEffect(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (session && session.start) {
      timerRef.current = setInterval(() => {
        const sec = Math.floor((Date.now() - new Date(session.start).getTime()) / 1000);
        if (sec >= 0) {
          const h = String(Math.floor(sec / 3600)).padStart(2, "0");
          const m = String(Math.floor((sec % 3600) / 60)).padStart(2, "0");
          const s = String(sec % 60).padStart(2, "0");
          setElapsed(`${h}:${m}:${s}`);
        }
      }, 1000);
    }
    return () => clearInterval(timerRef.current);
  }, [session]);

  const startTimer = (taskId = null) => {
    if (session) {
      alert("Já existe uma sessão de estudo em andamento.");
      return;
    }
    const newSession = {
      start: new Date().toISOString(),
      task_id: taskId ? Number(taskId) : null
    };
    sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(newSession));
    setSession(newSession);
  };

  const stopTimer = async () => {
    if (!session) return;
    const startTime = new Date(session.start);
    const endTime = new Date();
    const duration = Math.round((endTime - startTime) / 60000);
    const payload = { ...session, end: endTime.toISOString(), duration_minutes: duration };

    try {
      await api("/sessions/save", { method: "POST", body: JSON.stringify(payload) });
      alert(`Sessão salva: ${duration} minutos`);
      if (onDataChange) onDataChange();
    } catch (e) {
      alert(`Erro ao salvar sessão: ${e.message}`);
    } finally {
      if (timerRef.current) clearInterval(timerRef.current);
      sessionStorage.removeItem(SESSION_STORAGE_KEY);
      setSession(null);
      setElapsed("00:00:00");
    }
  };

  const value = { session, elapsed, startTimer, stopTimer };

  return (
    <TimerContext.Provider value={value}>
      {children}
    </TimerContext.Provider>
  );
}

export function useStudyTimer() {
  return useContext(TimerContext);
}