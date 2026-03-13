import { useBrainStore } from '../../store/brainStore';

export function AnomalyMonitorPanel() {
  const snapshot = useBrainStore((state) => state.snapshot);

  if (!snapshot?.anomalies) return null;

  const anomalies = snapshot.anomalies;

  // Count by type
  const typeCounts = anomalies.reduce((acc, a) => {
    acc[a.type] = (acc[a.type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  // Get severity distribution
  const criticalCount = anomalies.filter(a => a.severity >= 0.8).length;
  const highCount = anomalies.filter(a => a.severity >= 0.5 && a.severity < 0.8).length;
  const mediumCount = anomalies.filter(a => a.severity >= 0.3 && a.severity < 0.5).length;
  const lowCount = anomalies.filter(a => a.severity < 0.3).length;

  const getSeverityColor = (severity: number) => {
    if (severity >= 0.8) return 'text-red-500 bg-red-500/10 border-red-500/30';
    if (severity >= 0.5) return 'text-orange-500 bg-orange-500/10 border-orange-500/30';
    if (severity >= 0.3) return 'text-yellow-500 bg-yellow-500/10 border-yellow-500/30';
    return 'text-blue-500 bg-blue-500/10 border-blue-500/30';
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'neuron': return 'text-purple-400';
      case 'hive': return 'text-cyan-400';
      case 'pattern': return 'text-green-400';
      case 'memory': return 'text-yellow-400';
      case 'global': return 'text-red-400';
      default: return 'text-gray-400';
    }
  };

  return (
    <div className="bg-tahoe-panel backdrop-blur-tahoe rounded-tahoe border border-tahoe-border p-6">
      <h2 className="text-lg font-semibold text-tahoe-text mb-4">Anomaly Monitor</h2>
      
      <div className="space-y-4">
        {/* Severity Summary */}
        <div className="grid grid-cols-4 gap-2">
          <div className="bg-red-500/10 border border-red-500/30 rounded-tahoe-sm p-2">
            <div className="text-xs text-red-400 mb-1">Critical</div>
            <div className="text-2xl font-bold text-red-500">{criticalCount}</div>
          </div>
          <div className="bg-orange-500/10 border border-orange-500/30 rounded-tahoe-sm p-2">
            <div className="text-xs text-orange-400 mb-1">High</div>
            <div className="text-2xl font-bold text-orange-500">{highCount}</div>
          </div>
          <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-tahoe-sm p-2">
            <div className="text-xs text-yellow-400 mb-1">Medium</div>
            <div className="text-2xl font-bold text-yellow-500">{mediumCount}</div>
          </div>
          <div className="bg-blue-500/10 border border-blue-500/30 rounded-tahoe-sm p-2">
            <div className="text-xs text-blue-400 mb-1">Low</div>
            <div className="text-2xl font-bold text-blue-500">{lowCount}</div>
          </div>
        </div>

        {/* Type Distribution */}
        <div className="bg-black/10 rounded-tahoe-sm p-3">
          <div className="text-xs text-tahoe-text-secondary mb-2 uppercase tracking-wider">
            By Level
          </div>
          <div className="grid grid-cols-5 gap-2 text-xs">
            {['neuron', 'hive', 'pattern', 'memory', 'global'].map(type => (
              <div key={type} className="text-center">
                <div className={`font-bold text-lg ${getTypeColor(type)}`}>
                  {typeCounts[type] || 0}
                </div>
                <div className="text-tahoe-text-secondary capitalize">{type}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Anomalies (scrollable) */}
        <div className="bg-black/10 rounded-tahoe-sm border border-tahoe-border">
          <div className="text-xs text-tahoe-text-secondary p-3 pb-2 uppercase tracking-wider border-b border-tahoe-border">
            Recent Events (last 20)
          </div>
          <div className="max-h-64 overflow-y-auto">
            {anomalies.length === 0 ? (
              <div className="p-4 text-center text-tahoe-text-secondary text-sm">
                No anomalies detected
              </div>
            ) : (
              <div className="divide-y divide-tahoe-border">
                {anomalies.slice().reverse().map((anomaly, idx) => (
                  <div 
                    key={idx} 
                    className={`p-3 hover:bg-black/20 transition-colors ${getSeverityColor(anomaly.severity)} border-l-2`}
                  >
                    <div className="flex items-start justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className={`text-xs font-bold uppercase ${getTypeColor(anomaly.type)}`}>
                          {anomaly.type}
                        </span>
                        <span className="text-xs text-tahoe-text-secondary">
                          {anomaly.subtype}
                        </span>
                      </div>
                      <span className="text-xs font-mono text-tahoe-text-secondary">
                        {anomaly.timestamp.toFixed(2)}s
                      </span>
                    </div>
                    <div className="text-xs text-tahoe-text mb-1">
                      {anomaly.description}
                    </div>
                    {anomaly.stimulus_context && (
                      <div className="text-xs text-tahoe-text-secondary">
                        Stimulus: <span className="text-tahoe-accent">{anomaly.stimulus_context}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Info */}
        <div className="text-xs text-tahoe-text-secondary p-3 bg-black/5 rounded-tahoe-sm border border-tahoe-border">
          <div className="font-medium mb-1">5-Level Monitoring:</div>
          <div className="opacity-75">
            Neuron (spikes, silence) → Hive (formation, collapse) → Pattern (novelty, cascade) 
            → Memory (rapid encoding) → Global (coherence jumps, state transitions)
          </div>
        </div>
      </div>
    </div>
  );
}
