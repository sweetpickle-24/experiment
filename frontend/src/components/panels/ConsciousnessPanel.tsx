import { useBrainStore } from '../../store/brainStore';

const STATE_COLORS: Record<string, string> = {
  WAKE: '#0A84FF',
  SLEEP: '#5E5CE6',
  DREAM: '#BF5AF2',
  SHOCK: '#FF453A',
  MEDITATION: '#30D158',
};

export function ConsciousnessPanel() {
  const { snapshot } = useBrainStore();

  if (!snapshot || !snapshot.consciousness || !snapshot.metrics) return null;

  const { consciousness, metrics } = snapshot;
  const stateColor = STATE_COLORS[metrics.consciousness_state] || '#98989D';

  return (
    <div className="tahoe-panel p-6">
      <h2 className="text-lg font-semibold mb-4">Consciousness State</h2>

      <div className="flex items-center gap-4 mb-6">
        <div 
          className="w-16 h-16 rounded-full flex items-center justify-center text-2xl font-bold"
          style={{ 
            background: `radial-gradient(circle, ${stateColor}40, ${stateColor}10)`,
            border: `2px solid ${stateColor}`,
          }}
        >
          {metrics.consciousness_state[0]}
        </div>
        <div>
          <div className="text-2xl font-semibold">{metrics.consciousness_state}</div>
          <div className="text-sm text-tahoe-textMuted">Current State</div>
        </div>
      </div>

      <div className="space-y-3">
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-tahoe-textMuted">Global Coherence</span>
            <span>{(consciousness.global_coherence * 100).toFixed(1)}%</span>
          </div>
          <div className="w-full bg-black/30 rounded-full h-2 overflow-hidden">
            <div 
              className="h-full rounded-full transition-all duration-300"
              style={{ 
                width: `${consciousness.global_coherence * 100}%`,
                background: stateColor,
              }}
            />
          </div>
        </div>

        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-tahoe-textMuted">Dominant Frequency</span>
            <span>{consciousness.dominant_frequency.toFixed(1)} Hz</span>
          </div>
          <div className="text-xs text-tahoe-textMuted">
            {consciousness.dominant_frequency < 4 ? 'Delta' :
             consciousness.dominant_frequency < 8 ? 'Theta' :
             consciousness.dominant_frequency < 13 ? 'Alpha' :
             consciousness.dominant_frequency < 30 ? 'Beta' : 'Gamma'} wave
          </div>
        </div>

        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-tahoe-textMuted">Metastability</span>
            <span>{(consciousness.metastability * 100).toFixed(1)}%</span>
          </div>
          <div className="w-full bg-black/30 rounded-full h-2 overflow-hidden">
            <div 
              className="h-full bg-gradient-to-r from-purple-500 to-pink-500 rounded-full transition-all duration-300"
              style={{ width: `${consciousness.metastability * 100}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
