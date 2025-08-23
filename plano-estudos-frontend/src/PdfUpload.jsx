import React, { useState } from 'react';

export function PdfUpload({ disciplinas, onUpload }) {
  const [disciplina, setDisciplina] = useState('');
  const [file, setFile] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!disciplina || !file) return alert('Selecione disciplina e arquivo!');
    const formData = new FormData();
    formData.append('disciplina', disciplina);
    formData.append('file', file);

    const res = await fetch('/api/pdf/upload', {
      method: 'POST',
      body: formData,
    });
    if (res.ok) {
      alert('Upload realizado!');
      onUpload && onUpload();
    } else {
      alert('Erro no upload');
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <select value={disciplina} onChange={e => setDisciplina(e.target.value)}>
        <option value="">Selecione a disciplina</option>
        {disciplinas.map(d => (
          <option key={d.id} value={d.name}>{d.name}</option>
        ))}
      </select>
      <input type="file" accept="application/pdf" onChange={e => setFile(e.target.files[0])} />
      <button type="submit">Enviar PDF</button>
    </form>
  );
}

