import { useBrainStore } from '../../store/brainStore';

const PATTERN_ICONS: Record<string, string> = {
  sequential: '→',
  parallel: '⫙',
  recursive: '↻',
  interference: '~',
};

export function ThoughtPatternsPanel() {
  const { snapshot } = useBrainStore();

  if (!snapshot || !snapshot.patterns) return null;

  const { patterns } = snapshot;
  const recentPatterns = patterns.slice(-8);

  return (
    <div className="tahoe-panel p-6">
      <h2 className="text-lg font-semibold mb-4">Thought Patterns</h2>

      <div className="space-y-2 max-h-64 overflow-y-auto custom-scrollbar">
        {recentPatterns.length === 0 ? (
          <div className="text-sm text-tahoe-textMuted">No patterns detected</div>
        ) : (
          recentPatterns.map((pattern) => (
            <div 
              key={pattern.id}
              className="bg-black/20 rounded-tahoe-sm p-3 hover:bg-black/30 transition-colors"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-xl">{PATTERN_ICONS[pattern.type]}</span>
                  <span className="text-sm font-medium capitalize">{pattern.type}</span>
                </div>
                <span className="text-xs text-tahoe-textMuted">
                  {new Date(pattern.timestamp).toLocaleTimeString()}
                </span>
              </div>
              
              <div className="flex gap-4 text-xs">
                <div>
                  <span className="text-tahoe-textMuted">Hives: </span>
                  <span>{pattern.hive_ids.length}</span>
                </div>
                <div>
                  <span className="text-tahoe-textMuted">Stability: </span>
                  <span>{(pattern.stability * 100).toFixed(0)}%</span>
                </div>
                <div>
                  <span className="text-tahoe-textMuted">Complexity: </span>
                  <span>{pattern.complexity.toFixed(1)}</span>
                </div>
              </div>

              <div className="mt-2 text-xs font-mono text-tahoe-textMuted truncate">
                {pattern.signature.slice(0, 32)}...
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
