'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

import { CorrectionPanel } from '@/components/correction/CorrectionPanel';
import { correctScene } from '@/lib/api';
import { useAppStore } from '@/lib/store';

export default function CorrectPage() {
  const router = useRouter();
  const { sessionId, scene, selectedObjectId, setSelectedObjectId, setScene, setStatusText, statusText } = useAppStore();
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  if (!scene) {
    return (
      <div className="card">
        <h1>No scene loaded</h1>
        <p className="tiny">Load a precomputed scene first from the upload page.</p>
      </div>
    );
  }

  const onConfirm = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const updated = await correctScene(sessionId, scene);
      setScene(updated);
      setMessage('Scene confirmed and saved.');
      setStatusText('Scene confirmed. Opening design view...');
      router.push('/design');
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to save scene.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="grid">
      {statusText ? (
        <section className="card span-12">
          <p className="tiny">Pipeline status: {statusText}</p>
        </section>
      ) : null}
      <section className="span-12">
        <CorrectionPanel
          objects={scene.objects}
          selectedId={selectedObjectId}
          onSelect={setSelectedObjectId}
        />
      </section>
      <section className="card span-12" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <button className="button" type="button" onClick={onConfirm} disabled={saving}>
          {saving ? 'Saving...' : 'Confirm Scene'}
        </button>
        <button className="button secondary" type="button" onClick={() => router.push('/design')} disabled={saving}>
          Go To Design
        </button>
        {message ? <span className="tiny">{message}</span> : null}
      </section>
      {scene.objects.length === 0 ? (
        <section className="card span-12">
          <p className="tiny">
            No objects were detected yet. This is expected for Milestone 1 import. You can still proceed, and object
            detection will appear after Milestone 2 integration.
          </p>
        </section>
      ) : null}
    </div>
  );
}
