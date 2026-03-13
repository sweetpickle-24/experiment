import { useBrainStore } from '../../store/brainStore';

export function VisualInputPanel() {
  const snapshot = useBrainStore((state) => state.snapshot);

  if (!snapshot?.visual) return null;

  const { current_stimulus, compound_eye_active, stimulus_gen_stats } = snapshot.visual;

  const stimulusType = current_stimulus.includes('grating') ? 'Grating'
    : current_stimulus.includes('looming') ? 'Looming'
    : current_stimulus.includes('flicker') ? 'Flicker'
    : current_stimulus === 'blank' ? 'Blank'
    : current_stimulus === 'ISI' ? 'Inter-stimulus'
    : 'Image';

  const stimulusColor = stimulusType === 'Grating' ? 'text-blue-400'
    : stimulusType === 'Looming' ? 'text-red-400'
    : stimulusType === 'Flicker' ? 'text-yellow-400'
    : stimulusType === 'Blank' || stimulusType === 'Inter-stimulus' ? 'text-gray-500'
    : 'text-green-400';

  return (
    <div className="bg-tahoe-panel backdrop-blur-tahoe rounded-tahoe border border-tahoe-border p-6">
      <h2 className="text-lg font-semibold text-tahoe-text mb-4">Visual Input</h2>
      
      <div className="space-y-4">
        {/* Current Stimulus */}
        <div className="bg-black/20 rounded-tahoe-sm p-4 border border-tahoe-border">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-tahoe-text-secondary uppercase tracking-wider">
              Current Stimulus
            </span>
            <div className={`w-3 h-3 rounded-full ${compound_eye_active ? 'bg-green-500' : 'bg-gray-500'} 
                            ${compound_eye_active ? 'animate-pulse' : ''}`} 
                 title={compound_eye_active ? 'Compound eye active' : 'Compound eye inactive'}
            />
          </div>
          <div className="flex items-center gap-3">
            <div className={`text-2xl font-bold ${stimulusColor}`}>
              {current_stimulus}
            </div>
            <div className="text-sm text-tahoe-text-secondary">
              ({stimulusType})
            </div>
          </div>
        </div>

        {/* Compound Eye Status */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-black/10 rounded-tahoe-sm p-3">
            <div className="text-xs text-tahoe-text-secondary mb-1">Ommatidia</div>
            <div className="text-xl font-bold text-tahoe-text">
              {compound_eye_active ? '800' : '—'}
            </div>
          </div>
          <div className="bg-black/10 rounded-tahoe-sm p-3">
            <div className="text-xs text-tahoe-text-secondary mb-1">Field of View</div>
            <div className="text-xl font-bold text-tahoe-text">
              {compound_eye_active ? '270°' : '—'}
            </div>
          </div>
        </div>

        {/* Stimulus Statistics */}
        {stimulus_gen_stats && Object.keys(stimulus_gen_stats).length > 0 && (
          <div className="bg-black/10 rounded-tahoe-sm p-3">
            <div className="text-xs text-tahoe-text-secondary mb-2 uppercase tracking-wider">
              Stimulus Statistics
            </div>
            <div className="space-y-1 text-sm">
              {Object.entries(stimulus_gen_stats).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                  <span className="text-tahoe-text-secondary">{key}:</span>
                  <span className="text-tahoe-text font-medium">
                    {typeof value === 'number' ? value.toFixed(1) : String(value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Visual Processing Info */}
        <div className="text-xs text-tahoe-text-secondary mt-4 p-3 bg-black/5 rounded-tahoe-sm border border-tahoe-border">
          <div className="font-medium mb-1">Processing Pipeline:</div>
          <div className="opacity-75">
            Image → 800 Ommatidia → Optical Flow → T4/T5 Neurons → Wave Propagation
          </div>
        </div>
      </div>
    </div>
  );
}
