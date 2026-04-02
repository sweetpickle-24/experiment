import { useWebSocket } from '../hooks/useWebSocket';
import { useBrainStore } from '../store/brainStore';
import { SystemStatus } from './panels/SystemStatus';
import { ConsciousnessPanel } from './panels/ConsciousnessPanel';
import { ThoughtPatternsPanel } from './panels/ThoughtPatternsPanel';
import { WaveActivityChart } from './panels/WaveActivityChart';
import { HiveActivityPanel } from './panels/HiveActivityPanel';
import { MemoryPanel } from './panels/MemoryPanel';
import { BrainVisualization3D } from './panels/BrainVisualization3D';
import { FrequencyBandsPanel } from './panels/FrequencyBandsPanel';
import { PhaseCoherenceMap } from './panels/PhaseCoherenceMap';
import { ControlPanel } from './panels/ControlPanel';
import { VisualInputPanel } from './panels/VisualInputPanel';
import { AnomalyMonitorPanel } from './panels/AnomalyMonitorPanel';
import { ResponseTrackerPanel } from './panels/ResponseTrackerPanel';
import { SmellSynthesisPanel } from './panels/SmellSynthesisPanel';

export function Dashboard() {
  useWebSocket();
  const { snapshot, isConnected } = useBrainStore();

  // Show loading screen if no valid data yet
  if (!snapshot || !snapshot.metrics) {
    return (
      <div className="min-h-screen bg-tahoe-bg flex items-center justify-center">
        <div className="tahoe-panel p-12 max-w-md text-center">
          <div className="mb-6">
            <div className="w-16 h-16 mx-auto border-4 border-tahoe-accent border-t-transparent rounded-full animate-spin"></div>
          </div>
          <h2 className="text-2xl font-semibold mb-3">
            {isConnected ? 'Loading Fly Brain System' : 'Connecting to Backend'}
          </h2>
          <p className="text-tahoe-textMuted mb-4">
            {snapshot?.status === 'loading' 
              ? snapshot.message || 'Building neural connections...'
              : isConnected 
                ? 'Initializing 139,255 neurons and 5.3M synapses...'
                : 'Establishing WebSocket connection...'}
          </p>
          {snapshot?.status === 'loading' && (
            <p className="text-xs text-tahoe-textMuted">
              This may take 2-3 minutes on first load
            </p>
          )}
        </div>
      </div>
    );
  }

  const handleStart = async () => {
    try {
      await fetch('http://localhost:8000/api/control/start', { method: 'POST' });
    } catch (err) {
      console.error('Failed to start:', err);
    }
  };

  const handleStop = async () => {
    try {
      await fetch('http://localhost:8000/api/control/stop', { method: 'POST' });
    } catch (err) {
      console.error('Failed to stop:', err);
    }
  };

  const handleReset = async () => {
    try {
      await fetch('http://localhost:8000/api/control/reset', { method: 'POST' });
    } catch (err) {
      console.error('Failed to reset:', err);
    }
  };

  return (
    <div className="min-h-screen bg-tahoe-bg p-6">
      <header className="mb-8">
        <h1 className="text-3xl font-semibold mb-2">Fly Brain Wave Consciousness</h1>
        <p className="text-tahoe-textMuted text-sm">
          Real-time visualization of wave-based consciousness architecture with vision & monitoring
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="space-y-6">
          <SystemStatus />
          <ConsciousnessPanel />
          <ControlPanel 
            onStart={handleStart}
            onStop={handleStop}
            onReset={handleReset}
          />
          <VisualInputPanel />
        </div>

        <div className="space-y-6">
          <BrainVisualization3D />
          <WaveActivityChart />
          <AnomalyMonitorPanel />
        </div>

        <div className="space-y-6">
          <ThoughtPatternsPanel />
          <HiveActivityPanel />
          <MemoryPanel />
          <ResponseTrackerPanel />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        <FrequencyBandsPanel />
        <PhaseCoherenceMap />
      </div>

      {/* Smell Synthesis — full width */}
      <div className="mt-6">
        <SmellSynthesisPanel />
      </div>
    </div>
  );
}
