export interface Neuron {
  id: number;
  position: [number, number, number];
  phase: number;
  amplitude: number;
  frequency: number;
  group: string;
}

export interface Hive {
  id: string;
  neuron_ids: number[];
  centroid: [number, number, number];
  coherence: number;
  size: number;
  age: number;
}

export interface ThoughtPattern {
  id: string;
  type: 'sequential' | 'parallel' | 'recursive' | 'interference';
  hive_ids: string[];
  signature: string;
  stability: number;
  complexity: number;
  timestamp: number;
}

export interface ConsciousnessState {
  name: string;
  global_coherence: number;
  dominant_frequency: number;
  metastability: number;
  energy: number;
}

export interface MemoryPattern {
  id: string;
  neuron_ids: number[];
  strength: number;
  age: number;
  recall_count: number;
}

export interface SystemMetrics {
  timestamp: number;
  active_neurons: number;
  active_hives: number;
  coherence: number;
  energy: number;
  consciousness_state: string;
}

export interface VisualInfo {
  current_stimulus: string;
  compound_eye_active: boolean;
  stimulus_gen_stats: Record<string, any>;
}

export interface AnomalyEvent {
  timestamp: number;
  type: 'neuron' | 'hive' | 'pattern' | 'memory' | 'global';
  subtype: string;
  severity: number;
  description: string;
  stimulus_context: string;
}

export interface StimulusResponseSummary {
  recent_responses: {
    stimulus: string;
    coherence_change: number;
    patterns: string[];
    anomaly_count: number;
    memory_encoded: boolean;
  }[];
}

export interface WaveSnapshot {
  neurons: Neuron[];
  hives: Hive[];
  patterns: ThoughtPattern[];
  consciousness: ConsciousnessState;
  memories: MemoryPattern[];
  metrics: SystemMetrics;
  visual: VisualInfo;
  anomalies: AnomalyEvent[];
  response_summary: StimulusResponseSummary;
  // Loading / error states sent before brain is ready
  status?: string;
  message?: string;
}

// ── Smell Synthesis types ──────────────────────────────────────────────

export interface SmellEntry {
  name: string;
  family: string;
  glom_pattern: number[];
  kc_pattern?: number[];
  kc_sparsity: number;
  kc_active: number;
  has_kc?: boolean;
}

export interface OdorMatch {
  name: string;
  family: string;
  similarity: number;
  glom_pattern?: number[];
}

export interface SynthesisProgress {
  job_id: string;
  status: 'queued' | 'running' | 'done' | 'error';
  step: number;
  loss: number;
  gradient_norm: number;
  converged: boolean;
  top_matches: OdorMatch[];
  history_loss: number[];
}

export interface SynthesisResult extends SynthesisProgress {
  glom_pattern: number[];
  error?: string;
}

export interface OdorCompareResult {
  odor_a: string;
  odor_b: string;
  glom_similarity: number;
  kc_similarity: number | null;
  decorrelation: number | null;
}
