// src/Dashboard.jsx

import React, { useState, useEffect, useMemo } from 'react';
import { api } from './api';
import { Card } from './components';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { Timer, PieChart as PieChartIcon } from "lucide-react";

export function Dashboard({ keyProp }) {
  const [evolutionData, setEvolutionData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const res = await api("/evolution");
        setEvolutionData(res);
      } catch (e) { setError(String(e)); } 
      finally { setLoading(false); }
    })();
  }, [keyProp]);
  
  const hoursData = useMemo(() => evolutionData.map(item => ({ name: item.discipline_name, Horas: parseFloat((item.total_minutos_estudados / 60).toFixed(2)) })), [evolutionData]);
  const percentData = useMemo(() => evolutionData.map(item => ({ name: item.discipline_name, '% Acerto': parseFloat(Number(item.desempenho_medio).toFixed(1)) })), [evolutionData]);

  if (loading) return <div>Carregando Dashboard...</div>;
  if (error) return <div style={{ color: 'red' }}>Erro no Dashboard: {String(error)}</div>;

  return (
    <div className="grid-container grid-container-lg-2-cols dashboard">
      <Card title="Horas por Disciplina" icon={<Timer />}>
        <div className="chart-container"><ResponsiveContainer width="100%" height="100%"><BarChart data={hoursData} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" hide /><YAxis /> <Tooltip /> <Legend /><Bar dataKey="Horas" fill="#3b82f6" /></BarChart></ResponsiveContainer></div>
      </Card>
      <Card title="% Médio de Acertos" icon={<PieChartIcon />}>
        <div className="chart-container"><ResponsiveContainer width="100%" height="100%"><BarChart data={percentData} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="name" hide /><YAxis domain={[0, 100]} tickFormatter={(v) => `${v}%`} /><Tooltip formatter={(v) => `${v.toFixed(1)}%`} /> <Legend /><Bar dataKey="% Acerto" fill="#8884d8" /></BarChart></ResponsiveContainer></div>
      </Card>
    </div>
  );
}