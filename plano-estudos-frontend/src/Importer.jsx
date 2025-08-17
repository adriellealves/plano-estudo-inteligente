// src/Importer.jsx
import React, { useState } from 'react';
import { api } from './api';
import { Card, Button } from './components';
import { UploadCloud, CalendarClock } from 'lucide-react';

export function Importer({ onSync }) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const doImport = async () => {
    setBusy(true); setMsg("Sincronizando...");
    try {
      await api("/sync", { method: "POST" });
      setMsg(`Sincronização concluída!`);
      if (onSync) onSync();
    } catch (e) { 
      setMsg(`Erro: ${String(e)}`); 
    } finally { 
      setBusy(false); 
    }
  };

  return (
    <Card title="Sincronização" icon={<UploadCloud />}>
      <div className="importer-controls">
        <Button onClick={doImport} disabled={busy}><UploadCloud />Sincronizar com Planilha</Button>
      </div>
       {msg && <p className="sync-message">{msg}</p>}
    </Card>
  );
}