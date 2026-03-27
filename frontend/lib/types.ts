export type ConfidenceTier = 'metric' | 'partial' | 'approximate' | 'demo';

export interface SceneObject {
  id: string;
  type: string;
  type_confidence: number;
  position_confidence: number;
  size_confidence: number;
  rotation_confidence: number;
  label_confirmed: boolean;
  position: { x: number; y: number; z: number };
  size: { w: number; h: number; d: number };
  rotation_y: number;
  color?: string | null;
  product_url?: string | null;
  product_name?: string | null;
}

export interface SceneScript {
  version: number;
  session_id: string;
  source: string;
  pipeline_mode: string;
  room: {
    width: number;
    width_confidence: number;
    depth: number;
    depth_confidence: number;
    height: number;
    height_confidence: number;
    floor_plane: number[];
    floor_plane_inlier_ratio: number;
  };
  walls: Array<{ id: string; x1: number; z1: number; x2: number; z2: number; confidence: number }>;
  windows: Array<{
    id: string;
    wall: string;
    x: number;
    width: number;
    height: number;
    sill_height: number;
    confidence: number;
    user_confirmed: boolean;
  }>;
  doors: Array<{
    id: string;
    wall: string;
    x: number;
    width: number;
    height: number;
    sill_height: number;
    confidence: number;
    user_confirmed: boolean;
  }>;
  objects: SceneObject[];
  metadata: {
    room_type: string | null;
    room_type_confidence: number;
    pipeline_version: string;
    confidence: ConfidenceTier;
    created_at: string;
    last_edited: string;
  };
}

export interface AgentResult {
  action: Record<string, unknown>;
  scene: SceneScript;
  message: string;
}
