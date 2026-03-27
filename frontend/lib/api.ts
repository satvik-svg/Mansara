import type { AgentResult, SceneScript } from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

async function callApi<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {})
    },
    cache: 'no-store'
  });

  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status}: ${detail}`);
  }

  return (await res.json()) as T;
}

export async function loadPrecomputed(sessionId: string, scenePath?: string): Promise<SceneScript> {
  const response = await callApi<{ scene: SceneScript }>('/api/load_precomputed', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, scene_path: scenePath || null })
  });
  return response.scene;
}

export async function loadM1(
  sessionId: string,
  summaryPath: string,
  alignedPayloadPath: string
): Promise<{ scene: SceneScript; warnings: string[]; diagnostics: Record<string, unknown> }> {
  const response = await callApi<{
    scene: SceneScript;
    warnings?: string[];
    diagnostics?: Record<string, unknown>;
  }>('/api/load_m1', {
    method: 'POST',
    body: JSON.stringify({
      session_id: sessionId,
      summary_path: summaryPath,
      aligned_payload_path: alignedPayloadPath
    })
  });
  return {
    scene: response.scene,
    warnings: response.warnings || [],
    diagnostics: response.diagnostics || {}
  };
}

export async function loadM2(
  sessionId: string,
  summaryPath: string,
  alignedPayloadPath: string,
  m2ResultPath: string
): Promise<{ scene: SceneScript; warnings: string[]; diagnostics: Record<string, unknown> }> {
  const response = await callApi<{
    scene: SceneScript;
    warnings?: string[];
    diagnostics?: Record<string, unknown>;
  }>('/api/load_m2', {
    method: 'POST',
    body: JSON.stringify({
      session_id: sessionId,
      summary_path: summaryPath,
      aligned_payload_path: alignedPayloadPath,
      m2_result_path: m2ResultPath
    })
  });
  return {
    scene: response.scene,
    warnings: response.warnings || [],
    diagnostics: response.diagnostics || {}
  };
}

export async function getScene(sessionId: string): Promise<SceneScript> {
  const response = await callApi<{ scene: SceneScript }>(`/api/scene/${sessionId}`);
  return response.scene;
}

export async function correctScene(sessionId: string, scene: SceneScript): Promise<SceneScript> {
  const response = await callApi<{ scene: SceneScript }>('/api/scene/correct', {
    method: 'PUT',
    body: JSON.stringify({ session_id: sessionId, scene })
  });
  return response.scene;
}

export async function runAgent(
  sessionId: string,
  instruction: string,
  selectedObjectId?: string
): Promise<AgentResult> {
  return await callApi<AgentResult>('/api/agent', {
    method: 'POST',
    body: JSON.stringify({
      session_id: sessionId,
      instruction,
      selected_object_id: selectedObjectId || null
    })
  });
}

export async function undoScene(sessionId: string): Promise<SceneScript> {
  const response = await callApi<{ scene: SceneScript }>('/api/scene/undo', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId })
  });
  return response.scene;
}
