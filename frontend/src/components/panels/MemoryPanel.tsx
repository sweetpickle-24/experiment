import { useBrainStore } from '../../store/brainStore';

export function MemoryPanel() {
  const { snapshot } = useBrainStore();

  if (!snapshot || !snapshot.memories) return null;

  const { memories } = snapshot;
  const topMemories = [...memories]
    .sort((a, b) => b.strength - a.strength)
    .slice(0, 6);

  return (
    <div className="tahoe-panel p-6">
      <h2 className="text-lg font-semibold mb-4">Memory Patterns</h2>

      <div className="space-y-2">
        {topMemories.length === 0 ? (
          <div className="text-sm text-tahoe-textMuted">No memories stored</div>
        ) : (
          topMemories.map((memory) => (
            <div 
              key={memory.id}
              className="bg-black/20 rounded-tahoe-sm p-3 hover:bg-black/30 transition-colors"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium font-mono">{memory.id.slice(0, 12)}</span>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-tahoe-textMuted">
                    Recalled: {memory.recall_count}×
                  </span>
                </div>
              </div>
              
              <div className="flex items-center justify-between text-xs">
                <div>
                  <span className="text-tahoe-textMuted">Neurons: </span>
                  <span>{memory.neuron_ids.length}</span>
                </div>
                <div>
                  <span className="text-tahoe-textMuted">Age: </span>
                  <span>{memory.age}s</span>
                </div>
              </div>

              <div className="mt-2">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs text-tahoe-textMuted">Strength</span>
                  <span className="text-xs">{(memory.strength * 100).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-black/30 rounded-full h-1.5">
                  <div 
                    className="h-full bg-gradient-to-r from-amber-500 to-orange-500 rounded-full transition-all duration-300"
                    style={{ width: `${memory.strength * 100}%` }}
                  />
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
