// src/PerformanceHistory.jsx
import React, { useState, useEffect } from 'react';
import { api } from './api';
import { Card, Button } from './components';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Timer, TrendingUp } from 'lucide-react';

export function PerformanceHistory() {
    const [performanceData, setPerformanceData] = useState([]);
    const [selectedDiscipline, setSelectedDiscipline] = useState(null);
    const [disciplines, setDisciplines] = useState([]);
    const [timeRange, setTimeRange] = useState(30); // dias
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const loadDisciplines = async () => {
            try {
                const data = await api('/disciplines');
                setDisciplines(data);
            } catch (e) {
                console.error("Erro ao carregar disciplinas:", e);
            }
        };
        loadDisciplines();
    }, []);

    useEffect(() => {
        const loadPerformanceData = async () => {
            setLoading(true);
            try {
                const params = new URLSearchParams();
                params.set('days', timeRange);
                if (selectedDiscipline) {
                    params.set('discipline_id', selectedDiscipline);
                }
                const data = await api(`/performance/history?${params.toString()}`);
                setPerformanceData(data);
            } catch (e) {
                console.error("Erro ao carregar dados de performance:", e);
            } finally {
                setLoading(false);
            }
        };
        loadPerformanceData();
    }, [selectedDiscipline, timeRange]);

    const formatDate = (date) => {
        return new Date(date).toLocaleDateString('pt-BR');
    };

    return (
        <div className="flex-container-col gap-4">
            <div className="filter-container">
                <select 
                    value={selectedDiscipline || ''} 
                    onChange={(e) => setSelectedDiscipline(e.target.value ? Number(e.target.value) : null)}
                    className="select"
                >
                    <option value="">Todas as Disciplinas</option>
                    {disciplines.map(d => (
                        <option key={d.id} value={d.id}>{d.name}</option>
                    ))}
                </select>
                <select 
                    value={timeRange} 
                    onChange={(e) => setTimeRange(Number(e.target.value))}
                    className="select"
                >
                    <option value={7}>Última Semana</option>
                    <option value={30}>Último Mês</option>
                    <option value={90}>Últimos 3 Meses</option>
                    <option value={180}>Últimos 6 Meses</option>
                </select>
            </div>

            <div className="grid-container grid-container-lg-2-cols">
                <Card title="Desempenho ao Longo do Tempo" icon={<TrendingUp />}>
                    <div className="chart-container">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={performanceData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="date" tickFormatter={formatDate} />
                                <YAxis yAxisId="left" domain={[0, 100]} tickFormatter={(value) => `${value}%`} />
                                <Tooltip
                                    formatter={(value, name) => [
                                        name === 'accuracy' ? `${value}%` : value,
                                        name === 'accuracy' ? 'Taxa de Acerto' : name
                                    ]}
                                    labelFormatter={formatDate}
                                />
                                <Legend />
                                <Line
                                    yAxisId="left"
                                    type="monotone"
                                    dataKey="accuracy"
                                    name="Taxa de Acerto"
                                    stroke="#8884d8"
                                    activeDot={{ r: 8 }}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </Card>

                <Card title="Tempo de Estudo Diário" icon={<Timer />}>
                    <div className="chart-container">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={performanceData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="date" tickFormatter={formatDate} />
                                <YAxis domain={[0, 'auto']} />
                                <Tooltip
                                    formatter={(value, name) => [
                                        `${Math.round(value / 60 * 100) / 100}h`,
                                        'Tempo de Estudo'
                                    ]}
                                    labelFormatter={formatDate}
                                />
                                <Legend />
                                <Line
                                    type="monotone"
                                    dataKey="study_time_minutes"
                                    name="Tempo de Estudo"
                                    stroke="#82ca9d"
                                    activeDot={{ r: 8 }}
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </Card>
            </div>
        </div>
    );
}
