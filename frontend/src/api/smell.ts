/**
 * Smell Synthesis API client
 * Typed wrappers for all /api/smell/* REST endpoints and WebSocket helper.
 */

import type {
  SmellEntry,
  SynthesisResult,
  SynthesisProgress,
  OdorCompareResult,
} from '../types/brain';

export type { SmellEntry, SynthesisResult, SynthesisProgress, OdorCompareResult };

const BASE = 'http://localhost:8000';

// ── helpers ────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init);
  if (!res.ok) {
    const body = await res.text().catch(() => res.statusText);
    throw new Error(`API ${path}: ${res.status} ${body}`);
  }
  return res.json() as Promise<T>;
}

// ── Odorant list ───────────────────────────────────────────────────────

export interface OdorantListItem {
  name: string;
  family: string;
  has_kc: boolean;
}

export interface OdorantListResponse {
  odorants: OdorantListItem[];
  total: number;
  with_kc: number;
}

export function fetchOdorantList(): Promise<OdorantListResponse> {
  return apiFetch<OdorantListResponse>('/api/smell/odorants');
}

// ── Full database ──────────────────────────────────────────────────────

export interface SmellDatabaseResponse {
  entries: SmellEntry[];
  stats: {
    total_odorants: number;
    odorants_with_kc: number;
    families: Record<string, number>;
    kc_matrix_shape: [number, number] | null;
  };
}

export function fetchSmellDatabase(includeKc = false): Promise<SmellDatabaseResponse> {
  return apiFetch<SmellDatabaseResponse>(
    `/api/smell/database?include_kc=${includeKc}`,
  );
}

// ── Encode single odor ─────────────────────────────────────────────────

export interface EncodeResponse extends SmellEntry {
  odor_name: string;
  cached: boolean;
}

export function encodeOdor(
  odorName: string,
  concentration = 1.0,
): Promise<EncodeResponse> {
  return apiFetch<EncodeResponse>('/api/smell/encode', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ odor_name: odorName, concentration }),
  });
}

// ── Compare two odors ──────────────────────────────────────────────────

export function compareOdors(
  odorA: string,
  odorB: string,
): Promise<OdorCompareResult> {
  return apiFetch<OdorCompareResult>('/api/smell/compare', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ odor_a: odorA, odor_b: odorB }),
  });
}

// ── Start synthesis ────────────────────────────────────────────────────

export type SynthesisMode = 'fast' | 'accurate';

export interface SynthesizeRequest {
  target_odor?: string;
  target_kc_pattern?: number[];
  mode?: SynthesisMode;
  num_steps?: number;
  region?: string;
}

export interface SynthesizeStartResponse {
  job_id: string;
  status: string;
}

export function startSynthesis(
  req: SynthesizeRequest,
): Promise<SynthesizeStartResponse> {
  return apiFetch<SynthesizeStartResponse>('/api/smell/synthesize', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
}

// ── Poll synthesis result ──────────────────────────────────────────────

export function getSynthesisResult(jobId: string): Promise<SynthesisResult> {
  return apiFetch<SynthesisResult>(`/api/smell/synthesize/${jobId}`);
}

// ── WebSocket subscription for live synthesis progress ─────────────────

export type ProgressCallback = (progress: SynthesisProgress) => void;
export type DoneCallback = (result: SynthesisResult) => void;
export type ErrorCallback = (err: string) => void;

export function subscribeSynthesis(
  jobId: string,
  onProgress: ProgressCallback,
  onDone: DoneCallback,
  onError: ErrorCallback,
): () => void {
  const wsUrl = `ws://localhost:8000/ws/synthesis/${jobId}`;
  let ws: WebSocket | null = new WebSocket(wsUrl);
  let closed = false;

  ws.onmessage = (evt) => {
    try {
      const data = JSON.parse(evt.data) as SynthesisProgress;
      if ('error' in data && (data as { error?: string }).error) {
        onError((data as { error?: string }).error ?? 'Unknown error');
        ws?.close();
        return;
      }
      onProgress(data);
      if (data.status === 'done' || data.status === 'error') {
        onDone(data as SynthesisResult);
        ws?.close();
      }
    } catch {
      // ignore parse errors
    }
  };

  ws.onerror = () => {
    if (!closed) onError('WebSocket connection error');
  };

  ws.onclose = () => {
    closed = true;
  };

  // Return unsubscribe fn
  return () => {
    closed = true;
    ws?.close();
    ws = null;
  };
}

// ── Family colour map (for UI) ─────────────────────────────────────────

export const FAMILY_COLORS: Record<string, string> = {
  ester:     '#4ade80',
  alcohol:   '#60a5fa',
  ketone:    '#f59e0b',
  aldehyde:  '#fb923c',
  acid:      '#f87171',
  terpene:   '#34d399',
  aromatic:  '#a78bfa',
  amine:     '#f472b6',
  aversive:  '#ef4444',
  pheromone: '#e879f9',
  lactone:   '#fbbf24',
  other:     '#94a3b8',
};

export const FAMILY_LABELS: Record<string, string> = {
  ester:     'Ester',
  alcohol:   'Alcohol',
  ketone:    'Ketone',
  aldehyde:  'Aldehyde',
  acid:      'Acid',
  terpene:   'Terpene',
  aromatic:  'Aromatic',
  amine:     'Amine',
  aversive:  'Aversive',
  pheromone: 'Pheromone',
  lactone:   'Lactone',
  other:     'Other',
};
