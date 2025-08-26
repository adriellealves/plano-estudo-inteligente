// src/GoalsPage.jsx
import React, { useState, useEffect } from 'react';
import { api } from './api';
import { Card, Button } from './components';
import { Target, Plus, Check, X, AlertTriangle, Edit } from 'lucide-react';
import { AlertDialog } from './AlertDialog';

export function GoalsPage() {
    const [goals, setGoals] = useState([]);
    const [progress, setProgress] = useState([]);
    const [disciplines, setDisciplines] = useState([]);
    const [showForm, setShowForm] = useState(false);
    const [loading, setLoading] = useState(true);
    const [editingGoal, setEditingGoal] = useState(null);
    const [alert, setAlert] = useState({ show: false, type: '', message: '', title: '', onConfirm: null });
    const [formData, setFormData] = useState({
        discipline_id: '',
        type: 'study_time',
        target_value: '',
        period: 'weekly',
        start_date: new Date().toISOString().split('T')[0],  // Formato YYYY-MM-DD sem conversão de timezone
        end_date: ''
    });

    useEffect(() => {
        loadData();
        loadDisciplines();
    }, []);

    const loadData = async () => {
        setLoading(true);
        try {
            const [goalsData, progressData] = await Promise.all([
                api('/goals'),
                api('/goals/progress')
            ]);
            setGoals(goalsData);
            setProgress(progressData);
        } catch (e) {
            console.error('Erro ao carregar metas:', e);
            setAlert({
                show: true,
                type: 'error',
                title: 'Erro',
                message: 'Erro ao carregar metas. Tente novamente.'
            });
        } finally {
            setLoading(false);
        }
    };

    const loadDisciplines = async () => {
        try {
            const data = await api('/disciplines');
            setDisciplines(data);
        } catch (e) {
            console.error('Erro ao carregar disciplinas:', e);
        }
    };

    const handleEdit = (goal) => {
        setEditingGoal(goal);
        setFormData({
            discipline_id: goal.discipline_id,
            type: goal.type,
            target_value: goal.target_value,
            period: goal.period,
            start_date: goal.start_date,
            end_date: goal.end_date
        });
        setShowForm(true);
    };

    const resetForm = () => {
        setEditingGoal(null);
        setFormData({
            discipline_id: '',
            type: 'study_time',
            target_value: '',
            period: 'weekly',
            start_date: new Date().toISOString().split('T')[0],  // Formato YYYY-MM-DD sem conversão de timezone
            end_date: ''
        });
        setShowForm(false);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        // Enviar os dados diretamente sem conversão
        const adjustedData = {
            ...formData,
            start_date: formData.start_date,
            end_date: formData.end_date
        };

        try {
            if (editingGoal) {
                await api(`/goals/${editingGoal.id}`, {
                    method: 'PUT',
                    body: JSON.stringify(adjustedData)
                });
            } else {
                await api('/goals', {
                    method: 'POST',
                    body: JSON.stringify(adjustedData)
                });
            }
            resetForm();
            loadData();
        } catch (e) {
            console.error('Erro ao salvar meta:', e);
            alert('Erro ao salvar meta. Tente novamente.');
        }
    };

    const handleUpdateStatus = async (goalId, newStatus) => {
        try {
            await api(`/goals/${goalId}`, {
                method: 'PUT',
                body: JSON.stringify({ status: newStatus })
            });
            loadData();
        } catch (e) {
            console.error('Erro ao atualizar meta:', e);
        }
    };

    const formatValue = (type, value) => {
        switch (type) {
            case 'study_time':
                return `${Math.round(value / 60 * 100) / 100}h`;
            case 'performance':
                return `${Math.round(value)}%`;
            case 'exercises_completed':
                return Math.round(value);
            default:
                return value;
        }
    };

    const getGoalLabel = (type) => {
        switch (type) {
            case 'study_time':
                return 'Tempo de Estudo';
            case 'performance':
                return 'Desempenho';
            case 'exercises_completed':
                return 'Exercícios Concluídos';
            default:
                return type;
        }
    };

    const getPeriodLabel = (period) => {
        switch (period) {
            case 'daily':
                return 'Diária';
            case 'weekly':
                return 'Semanal';
            case 'monthly':
                return 'Mensal';
            case 'custom':
                return 'Personalizada';
            default:
                return period;
        }
    };

    return (
        <div className="flex-container-col">
            <div className="goals-header">
                <Button onClick={() => {
                    resetForm();
                    setShowForm(true);
                }}><Plus />Nova Meta</Button>
            </div>

            {showForm && (
                <Card title={editingGoal ? "Editar Meta" : "Nova Meta"} icon={<Target />}>
                    <form onSubmit={handleSubmit} className="goals-form">
                        <div className="form-group">
                            <label>Disciplina</label>
                            <select
                                required
                                value={formData.discipline_id}
                                onChange={e => setFormData({ ...formData, discipline_id: e.target.value })}
                            >
                                <option value="">Selecione uma disciplina</option>
                                {disciplines.map(d => (
                                    <option key={d.id} value={d.id}>{d.name}</option>
                                ))}
                            </select>
                        </div>

                        <div className="form-group">
                            <label>Tipo de Meta</label>
                            <select
                                required
                                value={formData.type}
                                onChange={e => setFormData({ ...formData, type: e.target.value })}
                            >
                                <option value="study_time">Tempo de Estudo</option>
                                <option value="performance">Desempenho</option>
                                <option value="exercises_completed">Exercícios Concluídos</option>
                            </select>
                        </div>

                        <div className="form-group">
                            <label>Valor Alvo ({formData.type === 'study_time' ? 'minutos' : formData.type === 'performance' ? '%' : 'quantidade'})</label>
                            <input
                                type="number"
                                required
                                value={formData.target_value}
                                onChange={e => setFormData({ ...formData, target_value: e.target.value })}
                                min="0"
                                max={formData.type === 'performance' ? "100" : undefined}
                            />
                        </div>

                        <div className="form-group">
                            <label>Período</label>
                            <select
                                required
                                value={formData.period}
                                onChange={e => setFormData({ ...formData, period: e.target.value })}
                            >
                                <option value="daily">Diária</option>
                                <option value="weekly">Semanal</option>
                                <option value="monthly">Mensal</option>
                                <option value="custom">Personalizada</option>
                            </select>
                        </div>

                        <div className='form-dates'>
                            <div className="form-group">
                                <label>Data Inicial</label>
                                <input
                                    type="date"
                                    required
                                    value={formData.start_date}
                                    onChange={e => setFormData({ ...formData, start_date: e.target.value })}
                                />
                            </div>

                            <div className="form-group">
                                <label>Data Final</label>
                                <input
                                    type="date"
                                    required
                                    value={formData.end_date}
                                    onChange={e => setFormData({ ...formData, end_date: e.target.value })}
                                    min={formData.start_date}
                                />
                            </div>

                        </div>
                        <div className="form-actions">
                            <Button variant="ghost" onClick={() => setShowForm(false)}>Cancelar</Button>
                            <Button type="submit">Criar Meta</Button>
                        </div>
                    </form>
                </Card>
            )}

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

            <div className="goals-grid">
                {loading ? (
                    <p>Carregando metas...</p>
                ) : (
                    progress.map(goal => {
                        const progressPercent = Math.min(100, Math.round(goal.progress_percent));
                        const isCompleted = progressPercent >= 100;
                        const isAtRisk = !isCompleted && new Date(goal.end_date) < new Date();

                        return (
                            <Card
                                key={goal.id}
                                title={`Meta: ${goal.discipline_name}`}
                                icon={<Target />}
                            >
                                <div className="goal-content">
                                    <div className="goal-info">
                                        <div><strong>Tipo:</strong> {getGoalLabel(goal.type)}</div>
                                        <div><strong>Meta:</strong> {formatValue(goal.type, goal.target_value)}</div>
                                        <div><strong>Atual:</strong> {formatValue(goal.type, goal.current_value)}</div>
                                        <div><strong>Período:</strong> {getPeriodLabel(goal.period)}</div>
                                        <div><strong>Início:</strong> {goal.start_date.split('-').reverse().join('/')}</div>
                                        <div><strong>Fim:</strong> {goal.end_date.split('-').reverse().join('/')}</div>
                                    </div>

                                    <div className="goal-progress">
                                        <div className="progress-bar-container">
                                            <div
                                                className={`progress-bar ${isCompleted ? 'completed' : isAtRisk ? 'at-risk' : ''}`}
                                                style={{ width: `${progressPercent}%` }}
                                            />
                                        </div>
                                        <div className="progress-label">{progressPercent}%</div>
                                    </div>

                                    <div className="goal-actions">
                                        <Button onClick={() => handleEdit(goal)} variant="ghost">
                                            <Edit size={16} />Editar
                                        </Button>
                                        <Button
                                            onClick={() => {
                                                setAlert({
                                                    show: true,
                                                    type: 'confirm',
                                                    title: 'Excluir Meta',
                                                    message: 'Tem certeza que deseja excluir esta meta?',
                                                    onConfirm: async () => {
                                                        try {
                                                            await api(`/goals/${goal.id}`, {
                                                                method: 'DELETE'
                                                            });
                                                            loadData();
                                                        } catch (e) {
                                                            console.error('Erro ao excluir meta:', e);
                                                            setAlert({
                                                                show: true,
                                                                type: 'error',
                                                                title: 'Erro',
                                                                message: 'Erro ao excluir meta. Tente novamente.'
                                                            });
                                                        }
                                                    }
                                                });
                                            }}
                                            variant="ghost"
                                            style={{ color: 'var(--red-9)' }}
                                        >
                                            <X size={16} />Excluir
                                        </Button>
                                        {goal.status === 'active' && (
                                            <>
                                                {isCompleted && (
                                                    <Button onClick={() => handleUpdateStatus(goal.id, 'completed')} variant="ghost">
                                                        <Check />Marcar como Concluída
                                                    </Button>
                                                )}
                                                {isAtRisk && (
                                                    <Button onClick={() => handleUpdateStatus(goal.id, 'failed')} variant="ghost">
                                                        <X />Marcar como Não Atingida
                                                    </Button>
                                                )}
                                            </>
                                        )}
                                    </div>
                                </div>
                            </Card>
                        );
                    })
                )}
            </div>
        </div>
    );
}
