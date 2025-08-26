import React, { useState, useEffect, useMemo } from 'react';
import { api } from './api';
import { Card, Button, Input, Select } from './components';
import { ListChecks, PlusCircle, Edit, Trash2, Eye, ArrowLeft } from 'lucide-react';
import { AlertDialog } from './AlertDialog';

// --- Formulários para os Modais (AGORA EXPORTADOS) ---

export function DisciplineForm({ data, onSave, onCancel }) {
  const [name, setName] = useState(data?.name || "");
  const handleSubmit = (e) => { e.preventDefault(); onSave({ ...data, name }); };
  return (
    <form onSubmit={handleSubmit} className="form-container">
      <Input value={name} onChange={e => setName(e.target.value)} placeholder="Nome da Disciplina" required/>
      <div className="form-actions"><Button variant="ghost" type="button" onClick={onCancel}>Cancelar</Button><Button type="submit">Salvar</Button></div>
    </form>
  );
}

// --- Sub-componente para a visão de Tópicos (autônomo) ---
function TopicsForDisciplineView({ discipline, onBack, onOpenModal, handleDeleteTopic }) {
    const [topics, setTopics] = useState([]);
    const [loading, setLoading] = useState(true);
    const [alert, setAlert] = useState({ show: false, type: '', message: '', title: '', onConfirm: null });

    // Este useEffect busca os tópicos APENAS para a disciplina selecionada
    useEffect(() => {
        if (discipline?.id) {
            setLoading(true);
            api(`/disciplines/${discipline.id}/topics`)
                .then(data => setTopics(data || []))
                .catch(e => {
                    console.error("Falha ao buscar tópicos para a disciplina", e);
                    setTopics([]);
                })
                .finally(() => setLoading(false));
        }
    }, [discipline.id]);

    const confirmDelete = (topicId) => {
        setAlert({
            show: true,
            type: 'confirm',
            title: 'Confirmar Exclusão',
            message: 'Tem certeza que deseja deletar este item? A ação não pode ser desfeita e deletará todos os dados associados.',
            onConfirm: () => {
                handleDeleteTopic(topicId);
                setAlert({ ...alert, show: false });
            }
        });
    };

    return (
        <div className="flex-container-col">
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
            <Button variant="ghost" onClick={onBack} style={{ alignSelf: 'flex-start', marginBottom: '1rem' }}>
                <ArrowLeft /> Voltar para Todas as Disciplinas
            </Button>
            <Card 
                title={`Tópicos de: ${discipline.name}`} 
                icon={<ListChecks />} 
                action={
                    <Button onClick={() => onOpenModal('topic', { discipline_id: discipline.id })}>
                        <PlusCircle /> Adicionar Tópico
                    </Button>
                }
            >
                {loading ? <p>Carregando tópicos...</p> : (
                    <>
                        {topics.length > 0 ? (
                            <ul className="management-list">
                                {topics.map(t => (
                                    <li key={t.id}>
                                        <span>{t.name}</span>
                                        <div>
                                            <Button variant="ghost" onClick={() => onOpenModal('topic', t)}><Edit /></Button>
                                            <Button variant="danger" onClick={() => confirmDelete(t.id)}><Trash2 /></Button>
                                        </div>
                                    </li>
                                ))}
                            </ul>
                        ) : (
                          <p className="empty-list-message">Nenhum tópico cadastrado para esta disciplina.</p>
                        )}
                    </>
                )}
            </Card>
        </div>
    );
}


export function TopicForm({ data, disciplines, onSave, onCancel }) {
  const [name, setName] = useState(data?.name || "");
  const [disciplineId, setDisciplineId] = useState(data?.discipline_id || "");

  if (!disciplines || disciplines.length === 0) {
      return <div>Carregando disciplinas...</div>;
  }

  const handleSubmit = (e) => { 
    e.preventDefault();
    if (!disciplineId) {
        setAlert({
            show: true,
            type: 'error',
            title: 'Erro de Validação',
            message: 'Por favor, selecione uma disciplina.'
        });
        return;
    }
    onSave({ ...data, name, discipline_id: Number(disciplineId) }); 
  };
  
  return (
    <form onSubmit={handleSubmit} className="form-container">
        <label>Nome do Tópico</label>
        <Input value={name} onChange={e => setName(e.target.value)} placeholder="Nome do Tópico" required/>
        <label>Disciplina</label>
        <Select value={disciplineId} onChange={e => setDisciplineId(e.target.value)} required>
            <option value="" disabled>Selecione uma disciplina</option>
            {disciplines.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
        </Select>
        <div className="form-actions"><Button variant="ghost" type="button" onClick={onCancel}>Cancelar</Button><Button type="submit">Salvar</Button></div>
    </form>
  );
}

export function TaskForm({ data, disciplines, onSave, onCancel }) {
    const [title, setTitle] = useState(data?.title || "");
    const [disciplineId, setDisciplineId] = useState(data?.discipline_id || "");
    const [completionDate, setCompletionDate] = useState(data?.completion_date || "");
    const [status, setStatus] = useState(data?.status || "Pendente");
    const [selectedTopics, setSelectedTopics] = useState(data?.topics?.map(t => t.id) || []);
    const [availableTopics, setAvailableTopics] = useState([]);
    const [topicsLoading, setTopicsLoading] = useState(false);

    useEffect(() => {
        if (disciplineId) {
            setTopicsLoading(true);
            api(`/disciplines/${disciplineId}/topics`)
                .then(data => {
                    setAvailableTopics(data || []);
                    if(data?.id) { // Should be data from parent task
                        const existingTopicIds = data.topics.map(t => t.id);
                        const availableTopicIdsOnLoad = (data || []).map(t => t.id);
                        setSelectedTopics(existingTopicIds.filter(id => availableTopicIdsOnLoad.includes(id)));
                    }
                })
                .catch(e => console.error("Falha ao buscar tópicos", e))
                .finally(() => setTopicsLoading(false));
        } else {
            setAvailableTopics([]);
        }
    }, [disciplineId]);

    const handleSubmit = (e) => {
        e.preventDefault();
        onSave({ ...data, title, discipline_id: Number(disciplineId), completion_date: completionDate || null, status, topic_ids: selectedTopics });
    };
    
    const handleTopicChange = (topicId) => {
        setSelectedTopics(prev => prev.includes(topicId) ? prev.filter(id => id !== topicId) : [...prev, topicId]);
    };
    
    if (!disciplines || disciplines.length === 0) {
        return <div>Carregando dados do formulário...</div>;
    }

    return (
        <form onSubmit={handleSubmit} className="form-container">
            <label>Título da Tarefa</label>
            <Input value={title} onChange={e => setTitle(e.target.value)} required />
            <label>Disciplina</label>
            <Select value={disciplineId} onChange={e => { setDisciplineId(e.target.value); setSelectedTopics([]); }} required>
                <option value="" disabled>Selecione...</option>
                {disciplines.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
            </Select>
            <label>Tópicos</label>
            <div className="topics-checkbox-container">
                {topicsLoading && <small>Carregando tópicos...</small>}
                {!topicsLoading && availableTopics.length > 0 && availableTopics.map(t => (
                    <div key={t.id}><label><input type="checkbox" checked={selectedTopics.includes(t.id)} onChange={() => handleTopicChange(t.id)} /> {t.name}</label></div>
                ))}
                {!topicsLoading && !disciplineId && <small>Selecione uma disciplina para ver os tópicos.</small>}
                {!topicsLoading && disciplineId && availableTopics.length === 0 && <small>Nenhum tópico encontrado.</small>}
            </div>
            <label>Data de Conclusão</label>
            <Input type="date" value={completionDate || ""} onChange={e => setCompletionDate(e.target.value)} />
            <label>Status</label>
            <Select value={status} onChange={e => setStatus(e.target.value)}>
                <option value="Pendente">Pendente</option>
                <option value="Concluída">Concluída</option>
            </Select>
            <div className="form-actions">
                <Button variant="ghost" type="button" onClick={onCancel}>Cancelar</Button>
                <Button type="submit">Salvar</Button>
            </div>
        </form>
    );
}

// --- Componente Principal da Página ---
export function ManagePage({ keyProp, onOpenModal }) {
    const [disciplines, setDisciplines] = useState([]);
    const [tasks, setTasks] = useState([]);
    const [loading, setLoading] = useState(true);
    const [selectedDisciplineId, setSelectedDisciplineId] = useState(null);
    const [alert, setAlert] = useState({ show: false, type: '', message: '', title: '', onConfirm: null });

    // A função de carregamento agora busca apenas o necessário para a tela principal
    const loadData = async () => {
        setLoading(true);
        try {
            const [d, ta] = await Promise.all([api('/disciplines'), api('/tasks')]);
            setDisciplines(d || []);
            setTasks(ta || []);
        } catch (e) { 
            console.error("Erro em loadData no ManagePage:", e);
            setDisciplines([]); setTasks([]);
        } finally { 
            setLoading(false);
        }
    };

    useEffect(() => { loadData(); }, [keyProp]);

      const handleDelete = async (type, id) => {
        setAlert({
            show: true,
            type: 'confirm',
            title: 'Confirmar Exclusão',
            message: 'Tem certeza que deseja deletar este item? A ação não pode ser desfeita e deletará todos os dados associados.',
            onConfirm: async () => {
                try {
                    const endpoint = `${type}s`;
                    await api(`/${endpoint}/${id}`, { method: 'DELETE' });
                    // Se um tópico for deletado na visão de tópicos, precisamos recarregar os dados aqui também
                    if (type === 'topic') {
                        // Esta chamada não é ideal, mas para manter simples, vamos recarregar tudo
                        loadData(); 
                    } else {
                        loadData();
                    }
                } catch(e) {
                    setAlert({
                        show: true,
                        type: 'error',
                        title: 'Erro ao Excluir',
                        message: e.message
                    });
                }
            }
        });
    };
    
    // Encontra o objeto completo da disciplina selecionada
    const selectedDiscipline = useMemo(() => 
        (disciplines || []).find(d => d.id === selectedDisciplineId), 
    [disciplines, selectedDisciplineId]);

    if (loading) return <p>Carregando dados de gerenciamento...</p>

    // Se uma disciplina foi selecionada, mostra a view de tópicos
    if (selectedDiscipline) {
        return (
            <TopicsForDisciplineView 
                discipline={selectedDiscipline}
                onBack={() => setSelectedDisciplineId(null)}
                onOpenModal={onOpenModal}
                handleDeleteTopic={(topicId) => handleDelete('topic', topicId)}
            />
        );
    }
    
    return (
        <div className="flex-container-col">
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
            <Card title="Disciplinas" icon={<ListChecks />} action={<Button onClick={() => onOpenModal('discipline')}><PlusCircle /> Adicionar Disciplina</Button>}>
                {disciplines.length > 0 ? (
                    <ul className="management-list">
                        {disciplines.map(d => (
                            <li key={d.id}>
                                <span>{d.name}</span>
                                <div>
                                    <Button variant="ghost" onClick={() => setSelectedDisciplineId(d.id)} title="Ver Tópicos"><Eye /></Button>
                                    <Button variant="ghost" onClick={() => onOpenModal('discipline', d)}><Edit /></Button>
                                    <Button variant="danger" onClick={() => handleDelete('discipline', d.id)}><Trash2 /></Button>
                                </div>
                            </li>
                        ))}
                    </ul>
                ) : <p className="empty-list-message">Nenhuma disciplina cadastrada.</p> }
            </Card>
            <Card title="Últimas 10 Tarefas" icon={<ListChecks />} action={<Button onClick={() => onOpenModal('task')}><PlusCircle /> Adicionar Tarefa</Button>}>
                {tasks.length > 0 ? (
                    <ul className="management-list">
                        {tasks.slice(0, 10).map(t => (
                            <li key={t.id}>
                                <span>{t.title || `Tarefa #${t.id}`}</span>
                                <div>
                                    <Button variant="ghost" onClick={() => onOpenModal('task', t)}><Edit /></Button>
                                    <Button variant="danger" onClick={() => handleDelete('task', t.id)}><Trash2 /></Button>
                                </div>
                            </li>
                        ))}
                    </ul>
                ) : <p className="empty-list-message">Nenhuma tarefa cadastrada.</p>}
            </Card>
        </div>
    );
}