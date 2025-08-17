// src/Reviews.jsx

import React, { useState, useEffect } from 'react';
import { api } from './api';
import { Card, Button, Input } from './components';
import { CalendarClock, RefreshCw } from 'lucide-react';

export function Reviews({ keyProp }) {
    const [reviews, setReviews] = useState([]);
    const [loading, setLoading] = useState(true);
    const [range, setRange] = useState({ from: new Date().toISOString().split('T')[0], to: "" });

    const loadReviews = async () => {
        setLoading(true);
        const params = new URLSearchParams();
        if (range.from) params.set("from", range.from);
        if (range.to) params.set("to", range.to);
        try {
            const data = await api(`/reviews?${params.toString()}`);
            setReviews(data);
        } catch(e) { console.error(e) }
        finally { setLoading(false) }
    };

    useEffect(() => { loadReviews(); }, [keyProp]);

    return (
        <div className="flex-container-col">
        <Card title="Filtrar Revisões" icon={<CalendarClock />}>
            <div className="filter-container">
            <div><label>De:</label><Input type="date" value={range.from} onChange={(e) => setRange(r => ({ ...r, from: e.target.value }))} /></div>
            <div><label>Até:</label><Input type="date" value={range.to} onChange={(e) => setRange(r => ({ ...r, to: e.target.value }))} /></div>
            <Button variant="ghost" onClick={loadReviews}><RefreshCw />Atualizar</Button>
            </div>
        </Card>
        {loading ? <p>Carregando revisões...</p> : (
            <div className="grid-container tasks-grid">
            {reviews.map(r => (
                <Card key={r.id} title={`Revisão: ${r.discipline_name}`} icon={<CalendarClock />}>
                <div className="task-details">
                    <div><strong>Data:</strong> {r.scheduled_for}</div>
                    <div><strong>Tarefa:</strong> {r.task_title || "Geral"}</div>
                    <div><strong>Status:</strong> {r.status || "Pendente"}</div>
                </div>
                </Card>
            ))}
            </div>
        )}
        </div>
    );
}