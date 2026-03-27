'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

import { loadM1, loadM2, loadPrecomputed } from '@/lib/api';
import { useAppStore } from '@/lib/store';

export default function HomePage() {
  const router = useRouter();
  const { sessionId, setSessionId, setScene, setStatusText, statusText } = useAppStore();
  const [scenePath, setScenePath] = useState('');
  const [m1SummaryPath, setM1SummaryPath] = useState('');
  const [m1AlignedPath, setM1AlignedPath] = useState('');
  const [m2ResultPath, setM2ResultPath] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [m1Info, setM1Info] = useState<string | null>(null);
  const [m2Info, setM2Info] = useState<string | null>(null);

  const onLoad = async () => {
    setBusy(true);
    setError(null);
    setStatusText('Loading precomputed SceneScript...');
    try {
      const scene = await loadPrecomputed(sessionId, scenePath || undefined);
      setScene(scene);
      setStatusText('Scene loaded. Ready for correction.');
      router.push('/correct');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load scene.';
      setError(message);
      setStatusText('Load failed');
    } finally {
      setBusy(false);
    }
  };

  const onLoadM1 = async () => {
    if (!m1SummaryPath || !m1AlignedPath) {
      setError('Provide both M1 summary and aligned payload paths.');
      return;
    }

    setBusy(true);
    setError(null);
    setM1Info(null);
    setM2Info(null);
    setStatusText('Loading Milestone 1 reconstruction output...');
    try {
      const result = await loadM1(sessionId, m1SummaryPath, m1AlignedPath);
      setScene(result.scene);
      const objectCount = result.scene.objects.length;
      const warnings = result.warnings;
      const quality = String(result.scene.metadata.confidence);
      const infoLine = `Imported tier=${quality}, objects=${objectCount}${warnings.length ? `, warnings=${warnings.length}` : ''}`;
      const statusLine = warnings.length
        ? `${infoLine}. ${warnings.join(' ')}`
        : `${infoLine}. M1 scene imported. Ready for correction.`;
      setM1Info([infoLine, ...warnings].join(' | '));
      setStatusText(statusLine);
      router.push('/correct');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load M1 output.';
      setError(message);
      setStatusText('M1 import failed');
    } finally {
      setBusy(false);
    }
  };

  const onLoadM2 = async () => {
    if (!m1SummaryPath || !m1AlignedPath || !m2ResultPath) {
      setError('Provide M1 summary path, aligned payload path, and m2_result path.');
      return;
    }

    setBusy(true);
    setError(null);
    setM2Info(null);
    setStatusText('Loading Milestone 2 output...');
    try {
      const result = await loadM2(sessionId, m1SummaryPath, m1AlignedPath, m2ResultPath);
      setScene(result.scene);
      const objectCount = result.scene.objects.length;
      const windowCount = result.scene.windows.length;
      const doorCount = result.scene.doors.length;
      const warnings = result.warnings;
      const quality = String(result.scene.metadata.confidence);
      const infoLine = `Imported tier=${quality}, objects=${objectCount}, windows=${windowCount}, doors=${doorCount}${warnings.length ? `, warnings=${warnings.length}` : ''}`;
      const statusLine = warnings.length
        ? `${infoLine}. ${warnings.join(' ')}`
        : `${infoLine}. M2 scene imported. Ready for correction.`;
      setM2Info([infoLine, ...warnings].join(' | '));
      setStatusText(statusLine);
      router.push('/correct');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load M2 output.';
      setError(message);
      setStatusText('M2 import failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="grid">
      <section className="card span-6">
        <h1>Phase A: Offline Scene Loader</h1>
        <p className="tiny">Use demo scene or provide a path to a precomputed scene.json file.</p>
        <label className="field">
          <span>Session ID</span>
          <input value={sessionId} onChange={(e) => setSessionId(e.target.value)} />
        </label>
        <label className="field">
          <span>Optional scene path</span>
          <input
            value={scenePath}
            onChange={(e) => setScenePath(e.target.value)}
            placeholder="C:/path/to/scene.json"
          />
        </label>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="button" type="button" onClick={onLoad} disabled={busy || !sessionId}>
            {busy ? 'Loading...' : 'Load Scene'}
          </button>
          <button className="button secondary" type="button" onClick={() => router.push('/scan')}>
            Open Scan Status
          </button>
        </div>
        {error ? <p style={{ color: 'var(--danger)' }}>{error}</p> : null}
      </section>

      <section className="card span-6">
        <h2>Load From M1 Outputs</h2>
        <p className="tiny">Import Colab output files: m1_summary.json and m1_aligned_payload.json.</p>
        <label className="field">
          <span>M1 summary path</span>
          <input
            value={m1SummaryPath}
            onChange={(e) => setM1SummaryPath(e.target.value)}
            placeholder="C:/path/to/m1_summary.json"
          />
        </label>
        <label className="field">
          <span>M1 aligned payload path</span>
          <input
            value={m1AlignedPath}
            onChange={(e) => setM1AlignedPath(e.target.value)}
            placeholder="C:/path/to/m1_aligned_payload.json"
          />
        </label>
        <label className="field">
          <span>M2 result path (optional for M2 import)</span>
          <input
            value={m2ResultPath}
            onChange={(e) => setM2ResultPath(e.target.value)}
            placeholder="C:/path/to/m2_result.json"
          />
        </label>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="button" type="button" onClick={onLoadM1} disabled={busy || !sessionId}>
            {busy ? 'Loading...' : 'Load M1 Output'}
          </button>
          <button className="button secondary" type="button" onClick={onLoadM2} disabled={busy || !sessionId}>
            {busy ? 'Loading...' : 'Load M2 Output'}
          </button>
        </div>
        {m1Info ? <p className="tiny" style={{ marginTop: 10 }}>{m1Info}</p> : null}
        {m2Info ? <p className="tiny" style={{ marginTop: 10 }}>{m2Info}</p> : null}
        <h3 style={{ marginTop: 18 }}>Execution Notes</h3>
        <ul>
          <li>Geometry-first build order is enforced.</li>
          <li>This phase runs on precomputed scene contracts.</li>
          <li>Agent and shop APIs are scaffolded for integration.</li>
          <li>Confidence fields drive correction workflow.</li>
        </ul>
        <p className="tiny">Status: {statusText}</p>
      </section>
    </div>
  );
}
