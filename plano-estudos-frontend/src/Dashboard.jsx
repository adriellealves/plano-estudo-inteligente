// src/Dashboard.jsx

import React, { useState, useEffect, useMemo } from 'react';
import { api } from './api';
import { Card } from './components';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { Timer, PieChart as PieChartIcon, ListChecks, AlertTriangle } from "lucide-react";

export function Dashboard({ keyProp }) {
  const [evolutionData, setEvolutionData] = useState([]);
  const [topicsData, setTopicsData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedDiscipline, setSelectedDiscipline] = useState(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const [evolutionRes, topicsRes] = await Promise.all([
          api("/evolution"),
          api("/topics/performance")
        ]);
        setEvolutionData(evolutionRes);
        setTopicsData(topicsRes);
      } catch (e) { setError(String(e)); } 
      finally { setLoading(false); }
    })();
  }, [keyProp]);
  
  const hoursData = useMemo(() => evolutionData.map(item => ({ name: item.discipline_name, Horas: parseFloat((item.total_minutos_estudados / 60).toFixed(2)) })), [evolutionData]);
  const percentData = useMemo(() => evolutionData.map(item => ({ name: item.discipline_name, '% Acerto': parseFloat(Number(item.desempenho_medio).toFixed(1)) })), [evolutionData]);

  if (loading) return <div>Carregando Dashboard...</div>;
  if (error) return <div style={{ color: 'red' }}>Erro no Dashboard: {String(error)}</div>;

  const filteredTopicsData = selectedDiscipline
    ? topicsData.filter(d => d.discipline_id === selectedDiscipline)
    : topicsData;

  return (
    <div className="dashboard">
      <div className="grid-container grid-container-lg-2-cols">
        <Card title="Horas por Disciplina" icon={<Timer />}>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={hoursData} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" hide />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="Horas" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="% Médio de Acertos" icon={<PieChartIcon />}>
          <div className="chart-container">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={percentData} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" hide />
                <YAxis domain={[0, 100]} tickFormatter={(v) => `${v}%`} />
                <Tooltip formatter={(v) => `${v.toFixed(1)}%`} />
                <Legend />
                <Bar dataKey="% Acerto" fill="#8884d8" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <Card title="Análise por Tópicos" icon={<ListChecks />}>
        <div className="topics-analysis">
          <div className="topics-header">
            <select 
              value={selectedDiscipline || ''} 
              onChange={(e) => setSelectedDiscipline(e.target.value ? Number(e.target.value) : null)}
              className="select"
            >
              <option value="">Todas as Disciplinas</option>
              {evolutionData.map(d => (
                <option key={d.discipline_id} value={d.discipline_id}>{d.discipline_name}</option>
              ))}
            </select>
          </div>

          <div className="topics-grid">
            {filteredTopicsData.map(discipline => (
              <div key={discipline.discipline_id} className="discipline-topics">
                {!selectedDiscipline && (
                  <h3 className="discipline-name">{discipline.discipline_name}</h3>
                )}
                <div className="topics-list">
                  {discipline.topics.map(topic => (
                    <div 
                      key={topic.id} 
                      className={`topic-card performance-${topic.performanceLevel}`}
                    >
                      <div className="topic-header">
                        <h4>{topic.name}</h4>
                        <span className="topic-performance">
                          {topic.avgPerformance ? `${topic.avgPerformance.toFixed(1)}%` : 'N/A'}
                        </span>
                      </div>
                      <div className="topic-stats">
                        <div className="topic-stat">
                          <span>Questões:</span>
                          <span>{topic.totalQuestions}</span>
                        </div>
                        <div className="topic-stat">
                          <span>Acertos:</span>
                          <span>{topic.totalCorrect}</span>
                        </div>
                        <div className="topic-stat">
                          <span>Tarefas:</span>
                          <span>{topic.totalTasks}</span>
                        </div>
                      </div>
                      {topic.performanceLevel === 'weak' && (
                        <div className="topic-alert">
                          <AlertTriangle size={16} />
                          Precisa de atenção
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </Card>
    </div>
  );
}