import React, { useEffect, useState } from 'react';

export function PdfList({ disciplina }) {
  const [pdfs, setPdfs] = useState([]);

  useEffect(() => {
    if (!disciplina) return;
    fetch(`/api/pdf/list/${disciplina}`)
      .then(res => res.json())
      .then(setPdfs);
  }, [disciplina]);

  return (
    <div>
      <h3>PDFs da disciplina: {disciplina}</h3>
      <ul>
        {pdfs.map(pdf => (
          <li key={pdf}>
            <a href={`/api/pdf/view/${disciplina}/${pdf}`} target="_blank" rel="noopener noreferrer">{pdf}</a>
          </li>
        ))}
      </ul>
    </div>
  );
}
