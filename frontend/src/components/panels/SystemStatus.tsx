import { useBrainStore } from '../../store/brainStore';

export function SystemStatus() {
  const { snapshot, isConnected } = useBrainStore();

  if (!snapshot || !snapshot.metrics) {
    return (
      <div className="tahoe-panel p-6">
        <h2 className="text-lg font-semibold mb-4">System Status</h2>
        <div className="text-tahoe-textMuted">
          {snapshot?.status === 'loading' ? 'Loading brain system...' : 'Waiting for data...'}
        </div>
      </div>
    );
  }

  const { metrics } = snapshot;

  return (
    <div className="tahoe-panel p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">System Status</h2>
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'} animate-pulse`}></div>
          <span className="text-xs text-tahoe-textMuted">{isConnected ? 'Live' : 'Disconnected'}</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-black/20 rounded-tahoe-sm p-4">
          <div className="text-xs text-tahoe-textMuted mb-1">Active Neurons</div>
          <div className="text-2xl font-semibold">{metrics.active_neurons.toLocaleString()}</div>
        </div>

        <div className="bg-black/20 rounded-tahoe-sm p-4">
          <div className="text-xs text-tahoe-textMuted mb-1">Active Hives</div>
          <div className="text-2xl font-semibold">{metrics.active_hives}</div>
        </div>

        <div className="bg-black/20 rounded-tahoe-sm p-4">
          <div className="text-xs text-tahoe-textMuted mb-1">Coherence</div>
          <div className="text-2xl font-semibold">{(metrics.coherence * 100).toFixed(1)}%</div>
        </div>

        <div className="bg-black/20 rounded-tahoe-sm p-4">
          <div className="text-xs text-tahoe-textMuted mb-1">Energy</div>
          <div className="text-2xl font-semibold">{metrics.energy.toFixed(0)}</div>
        </div>
      </div>
    </div>
  );
}
