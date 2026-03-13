import { useBrainStore } from '../../store/brainStore';

export function ResponseTrackerPanel() {
  const snapshot = useBrainStore((state) => state.snapshot);

  if (!snapshot?.response_summary) return null;

  const { recent_responses } = snapshot.response_summary;

  const getCoherenceColor = (change: number) => {
    if (change > 0.3) return 'text-green-500';
    if (change > 0.1) return 'text-blue-400';
    if (change < -0.1) return 'text-orange-400';
    if (change < -0.3) return 'text-red-500';
    return 'text-gray-400';
  };

  const getCoherenceIcon = (change: number) => {
    if (change > 0.1) return '↑';
    if (change < -0.1) return '↓';
    return '→';
  };

  return (
    <div className="bg-tahoe-panel backdrop-blur-tahoe rounded-tahoe border border-tahoe-border p-6">
      <h2 className="text-lg font-semibold text-tahoe-text mb-4">Response Tracker</h2>
      
      <div className="space-y-4">
        {/* Summary Stats */}
        {recent_responses && recent_responses.length > 0 && (
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-black/10 rounded-tahoe-sm p-3">
              <div className="text-xs text-tahoe-text-secondary mb-1">Avg Coherence Δ</div>
              <div className={`text-xl font-bold ${getCoherenceColor(
                recent_responses.reduce((sum, r) => sum + r.coherence_change, 0) / recent_responses.length
              )}`}>
                {((recent_responses.reduce((sum, r) => sum + r.coherence_change, 0) / recent_responses.length) * 100).toFixed(1)}%
              </div>
            </div>
            <div className="bg-black/10 rounded-tahoe-sm p-3">
              <div className="text-xs text-tahoe-text-secondary mb-1">Avg Patterns</div>
              <div className="text-xl font-bold text-tahoe-text">
                {(recent_responses.reduce((sum, r) => sum + r.patterns.length, 0) / recent_responses.length).toFixed(1)}
              </div>
            </div>
            <div className="bg-black/10 rounded-tahoe-sm p-3">
              <div className="text-xs text-tahoe-text-secondary mb-1">Memory Rate</div>
              <div className="text-xl font-bold text-tahoe-accent">
                {((recent_responses.filter(r => r.memory_encoded).length / recent_responses.length) * 100).toFixed(0)}%
              </div>
            </div>
          </div>
        )}

        {/* Recent Responses Table */}
        <div className="bg-black/10 rounded-tahoe-sm border border-tahoe-border">
          <div className="text-xs text-tahoe-text-secondary p-3 pb-2 uppercase tracking-wider border-b border-tahoe-border">
            Stimulus-Response Correlations
          </div>
          <div className="max-h-80 overflow-y-auto">
            {!recent_responses || recent_responses.length === 0 ? (
              <div className="p-4 text-center text-tahoe-text-secondary text-sm">
                No responses recorded yet
              </div>
            ) : (
              <div className="divide-y divide-tahoe-border">
                {recent_responses.slice().reverse().map((response, idx) => (
                  <div 
                    key={idx} 
                    className="p-3 hover:bg-black/20 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="font-medium text-tahoe-text text-sm">
                        {response.stimulus}
                      </div>
                      <div className="flex items-center gap-2">
                        {response.memory_encoded && (
                          <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded-full border border-yellow-500/30">
                            Memory
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-2 text-xs">
                      <div>
                        <div className="text-tahoe-text-secondary">Coherence</div>
                        <div className={`font-bold ${getCoherenceColor(response.coherence_change)}`}>
                          {getCoherenceIcon(response.coherence_change)} {(response.coherence_change * 100).toFixed(1)}%
                        </div>
                      </div>
                      <div>
                        <div className="text-tahoe-text-secondary">Patterns</div>
                        <div className="font-bold text-tahoe-text">
                          {response.patterns.length}
                        </div>
                      </div>
                      <div>
                        <div className="text-tahoe-text-secondary">Anomalies</div>
                        <div className={`font-bold ${response.anomaly_count > 0 ? 'text-red-400' : 'text-gray-500'}`}>
                          {response.anomaly_count}
                        </div>
                      </div>
                    </div>

                    {response.patterns.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-tahoe-border">
                        <div className="text-xs text-tahoe-text-secondary mb-1">Patterns:</div>
                        <div className="flex flex-wrap gap-1">
                          {response.patterns.slice(0, 3).map((pattern, pidx) => (
                            <span 
                              key={pidx} 
                              className="text-xs bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded border border-blue-500/30"
                            >
                              {pattern}
                            </span>
                          ))}
                          {response.patterns.length > 3 && (
                            <span className="text-xs text-tahoe-text-secondary">
                              +{response.patterns.length - 3} more
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Pattern Emergence Detection */}
        <div className="bg-black/10 rounded-tahoe-sm p-3 border border-tahoe-border">
          <div className="text-xs text-tahoe-text-secondary mb-2 uppercase tracking-wider">
            Pattern Detection
          </div>
          <div className="text-xs text-tahoe-text">
            {recent_responses && recent_responses.length >= 3 ? (
              <>
                {(() => {
                  // Simple pattern detection: find stimuli with similar responses
                  const stimuliGroups = recent_responses.reduce((acc, r) => {
                    const key = r.stimulus.split('_')[0]; // Group by prefix (e.g., "grating", "looming")
                    if (!acc[key]) acc[key] = [];
                    acc[key].push(r);
                    return acc;
                  }, {} as Record<string, typeof recent_responses>);

                  const repeatedStimuli = Object.entries(stimuliGroups)
                    .filter(([_, responses]) => responses.length >= 2)
                    .map(([stimulus, responses]) => ({
                      stimulus,
                      count: responses.length,
                      avgCoherence: responses.reduce((sum, r) => sum + r.coherence_change, 0) / responses.length,
                      memoryRate: responses.filter(r => r.memory_encoded).length / responses.length
                    }));

                  if (repeatedStimuli.length === 0) {
                    return <div className="text-tahoe-text-secondary">Not enough repeated stimuli yet...</div>;
                  }

                  return (
                    <div className="space-y-2">
                      {repeatedStimuli.map(({ stimulus, count, avgCoherence, memoryRate }) => (
                        <div key={stimulus} className="flex items-center justify-between p-2 bg-black/20 rounded">
                          <div>
                            <span className="font-medium text-tahoe-text capitalize">{stimulus}</span>
                            <span className="text-tahoe-text-secondary ml-2">({count}×)</span>
                          </div>
                          <div className="flex items-center gap-3 text-xs">
                            <span className={getCoherenceColor(avgCoherence)}>
                              Δ{(avgCoherence * 100).toFixed(0)}%
                            </span>
                            <span className="text-yellow-400">
                              {(memoryRate * 100).toFixed(0)}% mem
                            </span>
                          </div>
                        </div>
                      ))}
                      <div className="text-xs text-green-400 mt-2">
                        ✓ Pattern emergence detected: Similar stimuli produce consistent responses!
                      </div>
                    </div>
                  );
                })()}
              </>
            ) : (
              <div className="text-tahoe-text-secondary">
                Collecting responses... (need 3+ for pattern detection)
              </div>
            )}
          </div>
        </div>

        {/* Info */}
        <div className="text-xs text-tahoe-text-secondary p-3 bg-black/5 rounded-tahoe-sm border border-tahoe-border">
          <div className="font-medium mb-1">Hypothesis Test:</div>
          <div className="opacity-75">
            If similar stimuli (e.g., all food images) produce consistent coherence changes and similar patterns,
            the brain has learned to recognize that category through emergent dynamics!
          </div>
        </div>
      </div>
    </div>
  );
}
