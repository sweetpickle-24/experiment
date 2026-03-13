import { useBrainStore } from '../../store/brainStore';
import { useMemo } from 'react';

export function PhaseCoherenceMap() {
  const { snapshot } = useBrainStore();

  const heatmapData = useMemo(() => {
    if (!snapshot || !snapshot.neurons) return [];

    const gridSize = 20;
    const grid: number[][] = Array(gridSize).fill(0).map(() => Array(gridSize).fill(0));
    const counts: number[][] = Array(gridSize).fill(0).map(() => Array(gridSize).fill(0));

    const bounds = {
      minX: Math.min(...snapshot.neurons.map(n => n.position[0])),
      maxX: Math.max(...snapshot.neurons.map(n => n.position[0])),
      minY: Math.min(...snapshot.neurons.map(n => n.position[1])),
      maxY: Math.max(...snapshot.neurons.map(n => n.position[1])),
    };

    snapshot.neurons.forEach((neuron) => {
      const x = Math.floor(((neuron.position[0] - bounds.minX) / (bounds.maxX - bounds.minX)) * (gridSize - 1));
      const y = Math.floor(((neuron.position[1] - bounds.minY) / (bounds.maxY - bounds.minY)) * (gridSize - 1));
      
      if (x >= 0 && x < gridSize && y >= 0 && y < gridSize) {
        grid[y][x] += neuron.amplitude;
        counts[y][x]++;
      }
    });

    for (let y = 0; y < gridSize; y++) {
      for (let x = 0; x < gridSize; x++) {
        if (counts[y][x] > 0) {
          grid[y][x] /= counts[y][x];
        }
      }
    }

    return grid;
  }, [snapshot]);

  const maxValue = Math.max(...heatmapData.flat());

  return (
    <div className="tahoe-panel p-6">
      <h2 className="text-lg font-semibold mb-4">Phase Coherence Map</h2>

      <div className="grid grid-cols-20 gap-0.5 w-full aspect-square max-w-sm mx-auto">
        {heatmapData.map((row, y) =>
          row.map((value, x) => {
            const intensity = maxValue > 0 ? value / maxValue : 0;
            const hue = intensity * 240;
            return (
              <div
                key={`${x}-${y}`}
                className="aspect-square rounded-sm transition-colors duration-200"
                style={{
                  background: `hsl(${hue}, 70%, ${40 + intensity * 30}%)`,
                }}
              />
            );
          })
        )}
      </div>

      <div className="mt-4 flex justify-between text-xs text-tahoe-textMuted">
        <span>Low Activity</span>
        <span>High Activity</span>
      </div>
      
      <div className="mt-2 h-2 rounded-full bg-gradient-to-r from-blue-900 via-blue-500 to-cyan-300" />
    </div>
  );
}
