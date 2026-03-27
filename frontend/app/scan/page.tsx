'use client';

import { useEffect, useState } from 'react';

import { useAppStore } from '@/lib/store';

type ScanStatus = {
  status: string;
  stage: string;
  pipeline_tier_so_far: string;
  elapsed_seconds: number;
};

export default function ScanPage() {
  const { sessionId } = useAppStore();
  const [status, setStatus] = useState<ScanStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const run = async () => {
      try {
        const base = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
        const response = await fetch(`${base}/api/scan/status/${sessionId}`, { cache: 'no-store' });
        if (!response.ok) {
          throw new Error(`Failed with ${response.status}`);
        }
        setStatus((await response.json()) as ScanStatus);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown scan status error');
      }
    };

    run();
  }, [sessionId]);

  return (
    <div className="card">
      <h1>Scan Status</h1>
      <p className="tiny">Session: {sessionId}</p>
      {error ? <p style={{ color: 'var(--danger)' }}>{error}</p> : null}
      {status ? (
        <div style={{ display: 'grid', gap: 8 }}>
          <div><strong>Status:</strong> {status.status}</div>
          <div><strong>Stage:</strong> {status.stage}</div>
          <div><strong>Tier:</strong> {status.pipeline_tier_so_far}</div>
          <div><strong>Elapsed:</strong> {status.elapsed_seconds}s</div>
        </div>
      ) : (
        <p>Loading status...</p>
      )}
    </div>
  );
}
