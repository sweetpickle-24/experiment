import { useBrainStore } from '../../store/brainStore';
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts';

export function WaveActivityChart() {
  const { history } = useBrainStore();

  if (history.length < 2) {
    return (
      <div className="tahoe-panel p-6">
        <h2 className="text-lg font-semibold mb-4">Wave Activity</h2>
        <div className="text-sm text-tahoe-textMuted">Collecting data...</div>
      </div>
    );
  }

  const data = history.slice(-50)
    .filter(s => s.consciousness && s.metrics)  // Filter out invalid snapshots
    .map((snapshot, idx) => ({
      index: idx,
      coherence: snapshot.consciousness.global_coherence * 100,
      frequency: snapshot.consciousness.dominant_frequency,
      energy: snapshot.metrics.energy / 1000,
    }));

  return (
    <div className="tahoe-panel p-6">
      <h2 className="text-lg font-semibold mb-4">Wave Activity</h2>
      
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data}>
          <XAxis 
            dataKey="index" 
            stroke="#98989D" 
            fontSize={10}
            hide
          />
          <YAxis 
            stroke="#98989D" 
            fontSize={10}
            width={30}
          />
          <Tooltip 
            contentStyle={{
              background: 'rgba(22, 22, 24, 0.95)',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              borderRadius: '12px',
              fontSize: '12px',
            }}
          />
          <Line 
            type="monotone" 
            dataKey="coherence" 
            stroke="#0A84FF" 
            strokeWidth={2}
            dot={false}
            name="Coherence %"
          />
          <Line 
            type="monotone" 
            dataKey="frequency" 
            stroke="#BF5AF2" 
            strokeWidth={2}
            dot={false}
            name="Frequency Hz"
          />
          <Line 
            type="monotone" 
            dataKey="energy" 
            stroke="#30D158" 
            strokeWidth={2}
            dot={false}
            name="Energy (k)"
          />
        </LineChart>
      </ResponsiveContainer>

      <div className="flex gap-4 mt-4 text-xs">
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-sm bg-[#0A84FF]"></div>
          <span className="text-tahoe-textMuted">Coherence</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-sm bg-[#BF5AF2]"></div>
          <span className="text-tahoe-textMuted">Frequency</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-3 h-3 rounded-sm bg-[#30D158]"></div>
          <span className="text-tahoe-textMuted">Energy</span>
        </div>
      </div>
    </div>
  );
}
