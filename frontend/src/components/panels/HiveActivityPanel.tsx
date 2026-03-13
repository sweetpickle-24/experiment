import { useBrainStore } from '../../store/brainStore';

export function HiveActivityPanel() {
  const { snapshot } = useBrainStore();

  if (!snapshot || !snapshot.hives) return null;

  const { hives } = snapshot;
  const topHives = [...hives]
    .sort((a, b) => b.coherence - a.coherence)
    .slice(0, 8);

  return (
    <div className="tahoe-panel p-6">
      <h2 className="text-lg font-semibold mb-4">Active Hives</h2>

      <div className="space-y-2 max-h-64 overflow-y-auto custom-scrollbar">
        {topHives.length === 0 ? (
          <div className="text-sm text-tahoe-textMuted">No active hives</div>
        ) : (
          topHives.map((hive) => (
            <div 
              key={hive.id}
              className="bg-black/20 rounded-tahoe-sm p-3 hover:bg-black/30 transition-colors"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium font-mono">{hive.id.slice(0, 8)}</span>
                <span className="text-xs text-tahoe-textMuted">Age: {hive.age}</span>
              </div>
              
              <div className="flex gap-4 text-xs mb-2">
                <div>
                  <span className="text-tahoe-textMuted">Size: </span>
                  <span>{hive.size}</span>
                </div>
                <div>
                  <span className="text-tahoe-textMuted">Neurons: </span>
                  <span>{hive.neuron_ids.length}</span>
                </div>
              </div>

              <div className="flex justify-between items-center">
                <span className="text-xs text-tahoe-textMuted">Coherence</span>
                <span className="text-xs">{(hive.coherence * 100).toFixed(1)}%</span>
              </div>
              <div className="w-full bg-black/30 rounded-full h-1.5 mt-1">
                <div 
                  className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full transition-all duration-300"
                  style={{ width: `${hive.coherence * 100}%` }}
                />
              </div>
            </div>
          ))
        )}
      </div>

      <style>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: rgba(0, 0, 0, 0.2);
          border-radius: 3px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.2);
          border-radius: 3px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(255, 255, 255, 0.3);
        }
      `}</style>
    </div>
  );
}
