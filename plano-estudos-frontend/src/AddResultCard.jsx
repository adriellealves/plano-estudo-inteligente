import React, { useState, useEffect } from 'react';
import { api } from './api';
import { Card, Button, Select, Input } from './components';
import { PlusCircle, CheckCircle2 } from 'lucide-react';

export function AddResultCard({ onDataChange }) {
  const [taskId, setTaskId] = useState("");
  const [tasks, setTasks] = useState([]);
  const [correct, setCorrect] = useState("");
  const [total, setTotal] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    // Carrega tarefas pendentes para o seletor
    api("/tasks?status=Pendente").then(setTasks);
  }, []);

  const handleSave = async () => {
    if (!total || !correct) {
      alert("Por favor, preencha os acertos e o total de questões.");
      return;
    }
    setSaving(true);
    try {
      const payload = {
        task_id: taskId ? Number(taskId) : null,
        correct: Number(correct),
        total: Number(total)
      };
      // No backend, a coluna `discipline_id` na tabela `result` não é NOT NULL,
      // então podemos omiti-la e o backend a pegará da tarefa, se vinculada.
      const res = await api("/results", { method: "POST", body: JSON.stringify(payload) });
      alert(`Resultado salvo com sucesso: ${res.percent.toFixed(1)}%`);
      // Limpa o formulário e avisa o app principal para recarregar os dados
      setTaskId("");
      setCorrect("");
      setTotal("");
      if (onDataChange) {
        onDataChange();
      }
    } catch (e) {
      alert(`Erro ao salvar resultado: ${e.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card title="Adicionar Resultado de Questões" icon={<PlusCircle />}>
      {/* Usando a classe .result-form-grid que você já tem */}
      <div className="result-form-grid">
        {/* Cada item é envolvido por .form-group para ter o label e o espaçamento correto */}
        <div className="form-group">
          <label>Vincular a uma tarefa (opcional)</label>
          <Select value={taskId} onChange={(e) => setTaskId(e.target.value)}>
            <option value="">— Sem tarefa específica —</option>
            {tasks.map(t => <option key={t.id} value={t.id}>{t.title || `Tarefa #${t.id}`}</option>)}
          </Select>
        </div>

        <div className="form-group">
          <label>Acertos</label>
          <Input type="number" value={correct} onChange={(e) => setCorrect(e.target.value)} placeholder="Ex: 25" />
        </div>
        
        <div className="form-group">
          <label>Total de Questões</label>
          <Input type="number" value={total} onChange={(e) => setTotal(e.target.value)} placeholder="Ex: 30" />
        </div>
        
        <div className="form-group">
          <label>&nbsp;</label> {/* Label vazio para alinhar o botão */}
          <Button onClick={handleSave} disabled={saving}>
            <CheckCircle2 /> Salvar
          </Button>
        </div>
      </div>
    </Card>
  );
}