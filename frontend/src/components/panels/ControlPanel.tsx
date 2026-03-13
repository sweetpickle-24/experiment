import { useBrainStore } from '../../store/brainStore';
import { useState } from 'react';

interface ControlPanelProps {
  onStart: () => void;
  onStop: () => void;
  onReset: () => void;
}

export function ControlPanel({ onStart, onStop, onReset }: ControlPanelProps) {
  const { isConnected, snapshot } = useBrainStore();
  const [isRunning, setIsRunning] = useState(false);

  const handleStart = () => {
    setIsRunning(true);
    onStart();
  };

  const handleStop = () => {
    setIsRunning(false);
    onStop();
  };

  return (
    <div className="tahoe-panel p-6">
      <h2 className="text-lg font-semibold mb-4">System Control</h2>

      <div className="space-y-4">
        <div className="flex gap-2">
          <button
            onClick={handleStart}
            disabled={!isConnected || isRunning}
            className="tahoe-button flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            ▶ Start
          </button>
          <button
            onClick={handleStop}
            disabled={!isConnected || !isRunning}
            className="tahoe-button flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ background: '#FF453A' }}
          >
            ⏸ Pause
          </button>
          <button
            onClick={onReset}
            disabled={!isConnected}
            className="tahoe-button flex-1 disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ background: '#98989D' }}
          >
            ↻ Reset
          </button>
        </div>

        <div className="bg-black/20 rounded-tahoe-sm p-4 space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-tahoe-textMuted">Connection</span>
            <span className={isConnected ? 'text-green-500' : 'text-red-500'}>
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          
          {snapshot && snapshot.metrics && (
            <>
              <div className="flex justify-between text-sm">
                <span className="text-tahoe-textMuted">Simulation Time</span>
                <span>{(snapshot.metrics.timestamp / 1000).toFixed(1)}s</span>
              </div>
              
              <div className="flex justify-between text-sm">
                <span className="text-tahoe-textMuted">Status</span>
                <span className={isRunning ? 'text-green-500' : 'text-yellow-500'}>
                  {isRunning ? 'Running' : 'Paused'}
                </span>
              </div>
            </>
          )}
        </div>

        <div className="bg-black/20 rounded-tahoe-sm p-4">
          <div className="text-xs text-tahoe-textMuted mb-2">Quick Actions</div>
          <div className="grid grid-cols-2 gap-2">
            <button className="text-xs py-2 px-3 bg-black/30 rounded-tahoe-sm hover:bg-black/40 transition-colors">
              Inject Stimulus
            </button>
            <button className="text-xs py-2 px-3 bg-black/30 rounded-tahoe-sm hover:bg-black/40 transition-colors">
              Force State
            </button>
            <button className="text-xs py-2 px-3 bg-black/30 rounded-tahoe-sm hover:bg-black/40 transition-colors">
              Save Snapshot
            </button>
            <button className="text-xs py-2 px-3 bg-black/30 rounded-tahoe-sm hover:bg-black/40 transition-colors">
              Export Data
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
