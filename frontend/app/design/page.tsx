'use client';

import { useState } from 'react';

import { runAgent, undoScene } from '@/lib/api';
import { useAppStore } from '@/lib/store';

export default function DesignPage() {
  const { sessionId, scene, selectedObjectId, setScene } = useAppStore();
  const [instruction, setInstruction] = useState('Add sofa near center');
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!scene) {
    return (
      <div className="card">
        <h1>No scene loaded</h1>
        <p className="tiny">Load and confirm a scene before using the design agent.</p>
      </div>
    );
  }

  const onRunAgent = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const result = await runAgent(sessionId, instruction, selectedObjectId || undefined);
      setScene(result.scene);
      setMessage(result.message);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Agent failed');
    } finally {
      setBusy(false);
    }
  };

  const onUndo = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const restored = await undoScene(sessionId);
      setScene(restored);
      setMessage('Undo complete.');
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Undo failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid">
      <section className="card span-6">
        <h1>Design Agent</h1>
        <p className="tiny">Current selection: {selectedObjectId || 'none'}</p>
        {scene.objects.length === 0 ? (
          <p className="tiny">
            No detected objects yet from M1 scan. Use an instruction like "Add sofa" or "Add coffee table".
          </p>
        ) : null}
        <label className="field">
          <span>Instruction</span>
          <input value={instruction} onChange={(e) => setInstruction(e.target.value)} />
        </label>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
          <button className="button secondary" type="button" onClick={() => setInstruction('Add sofa')} disabled={busy}>
            Add Sofa
          </button>
          <button className="button secondary" type="button" onClick={() => setInstruction('Add coffee table')} disabled={busy}>
            Add Coffee Table
          </button>
          <button className="button secondary" type="button" onClick={() => setInstruction('Add chair')} disabled={busy}>
            Add Chair
          </button>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="button" type="button" onClick={onRunAgent} disabled={busy}>
            Run Agent
          </button>
          <button className="button secondary" type="button" onClick={onUndo} disabled={busy}>
            Undo
          </button>
        </div>
        {message ? <p className="tiny">{message}</p> : null}
      </section>

      <section className="card span-6">
        <h2>Scene Objects</h2>
        <div style={{ display: 'grid', gap: 8 }}>
          {scene.objects.map((obj) => (
            <div key={obj.id} style={{ border: '1px solid var(--border)', borderRadius: 10, padding: 10 }}>
              <strong>{obj.id}</strong> - {obj.type}
              <div className="tiny">{obj.position.x.toFixed(2)}, {obj.position.z.toFixed(2)} m</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
