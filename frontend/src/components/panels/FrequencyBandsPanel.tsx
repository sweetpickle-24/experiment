import { useBrainStore } from '../../store/brainStore';

const BAND_COLORS: Record<string, string> = {
  'Delta': '#5E5CE6',
  'Theta': '#0A84FF',
  'Alpha': '#30D158',
  'Beta': '#FF9F0A',
  'Gamma': '#FF453A',
};

export function FrequencyBandsPanel() {
  const { snapshot } = useBrainStore();

  if (!snapshot || !snapshot.neurons) return null;

  const { neurons } = snapshot;

  const bandCounts = {
    Delta: 0,
    Theta: 0,
    Alpha: 0,
    Beta: 0,
    Gamma: 0,
  };

  neurons.forEach((neuron) => {
    const freq = neuron.frequency;
    if (freq < 4) bandCounts.Delta++;
    else if (freq < 8) bandCounts.Theta++;
    else if (freq < 13) bandCounts.Alpha++;
    else if (freq < 30) bandCounts.Beta++;
    else bandCounts.Gamma++;
  });

  const total = neurons.length;
  const bands = Object.entries(bandCounts).map(([name, count]) => ({
    name,
    count,
    percentage: (count / total) * 100,
    color: BAND_COLORS[name],
  }));

  return (
    <div className="tahoe-panel p-6">
      <h2 className="text-lg font-semibold mb-4">Frequency Bands</h2>

      <div className="space-y-3">
        {bands.map((band) => (
          <div key={band.name}>
            <div className="flex justify-between items-center mb-1">
              <div className="flex items-center gap-2">
                <div 
                  className="w-3 h-3 rounded-sm"
                  style={{ background: band.color }}
                />
                <span className="text-sm font-medium">{band.name}</span>
              </div>
              <div className="text-xs text-tahoe-textMuted">
                {band.count.toLocaleString()} ({band.percentage.toFixed(1)}%)
              </div>
            </div>
            <div className="w-full bg-black/30 rounded-full h-2 overflow-hidden">
              <div 
                className="h-full rounded-full transition-all duration-300"
                style={{ 
                  width: `${band.percentage}%`,
                  background: band.color,
                }}
              />
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 pt-4 border-t border-white/10 text-xs text-tahoe-textMuted">
        <div>Delta (0.5-4 Hz) • Theta (4-8 Hz) • Alpha (8-13 Hz)</div>
        <div>Beta (13-30 Hz) • Gamma (30-100 Hz)</div>
      </div>
    </div>
  );
}
