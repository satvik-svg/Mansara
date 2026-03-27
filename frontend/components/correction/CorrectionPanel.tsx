'use client';

import type { SceneObject } from '@/lib/types';

function confidenceBadge(obj: SceneObject): { label: string; className: string } {
  if (obj.type_confidence < 0.6) {
    return { label: 'Check label', className: 'pill danger' };
  }
  if (obj.position_confidence < 0.5) {
    return { label: 'Position uncertain', className: 'pill warn' };
  }
  if (obj.size_confidence < 0.5) {
    return { label: 'Size estimated', className: 'pill warn' };
  }
  return { label: 'Good', className: 'pill ok' };
}

export function CorrectionPanel({
  objects,
  selectedId,
  onSelect
}: {
  objects: SceneObject[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="card">
      <h2>Object Confidence Review</h2>
      <p className="tiny">Review low-confidence labels and positions before design actions.</p>
      <div style={{ display: 'grid', gap: 10, marginTop: 10 }}>
        {objects.map((obj) => {
          const badge = confidenceBadge(obj);
          const selected = selectedId === obj.id;
          return (
            <button
              type="button"
              key={obj.id}
              onClick={() => onSelect(obj.id)}
              style={{
                textAlign: 'left',
                border: selected ? '1px solid var(--primary)' : '1px solid var(--border)',
                borderRadius: 12,
                padding: 12,
                background: selected ? 'rgba(0,109,119,0.08)' : '#fff'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <strong>{obj.id} - {obj.type}</strong>
                <span className={badge.className}>{badge.label}</span>
              </div>
              <div className="tiny" style={{ marginTop: 6 }}>
                pos ({obj.position.x.toFixed(2)}, {obj.position.z.toFixed(2)}) m, size {obj.size.w.toFixed(2)} x {obj.size.h.toFixed(2)} x {obj.size.d.toFixed(2)} m
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
