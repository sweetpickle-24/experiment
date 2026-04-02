import { useState, useEffect, useRef, useCallback } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import {
  fetchOdorantList,
  startSynthesis,
  subscribeSynthesis,
  FAMILY_COLORS,
  FAMILY_LABELS,
  type OdorantListItem,
  type SynthesisMode,
} from '../../api/smell';
import type { OdorMatch, SynthesisProgress } from '../../types/brain';

// ── Glom barcode ────────────────────────────────────────────────────────

function GlomBarcode({ pattern }: { pattern: number[] }) {
  if (!pattern || pattern.length === 0) return null;
  const max = Math.max(...pattern, 0.001);

  return (
    <div className="flex gap-0.5 mt-2">
      {pattern.map((v, i) => (
        <div
          key={i}
          title={`Ch${i}: ${v.toFixed(3)}`}
          style={{
            flex: 1,
            height: 20,
            borderRadius: 2,
            backgroundColor: `rgba(10, 132, 255, ${v / max})`,
            outline: '1px solid rgba(10,132,255,0.15)',
          }}
        />
      ))}
    </div>
  );
}

// ── Family badge ────────────────────────────────────────────────────────

function FamilyBadge({ family }: { family: string }) {
  const color = FAMILY_COLORS[family] ?? '#94a3b8';
  const label = FAMILY_LABELS[family] ?? family;
  return (
    <span
      className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
      style={{ background: `${color}22`, color, border: `1px solid ${color}44` }}
    >
      {label}
    </span>
  );
}

// ── Match card ──────────────────────────────────────────────────────────

function MatchCard({ match, rank }: { match: OdorMatch; rank: number }) {
  const color  = FAMILY_COLORS[match.family] ?? '#94a3b8';
  const simPct = Math.max(0, Math.min(100, match.similarity * 100));

  return (
    <div className="tahoe-panel p-3 space-y-1.5">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs text-tahoe-textMuted font-mono">#{rank}</span>
        <FamilyBadge family={match.family} />
      </div>
      <p
        className="text-sm font-medium truncate"
        title={match.name.replace(/_/g, ' ')}
      >
        {match.name.replace(/_/g, ' ')}
      </p>
      {/* Similarity bar */}
      <div className="h-1.5 bg-tahoe-border rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${simPct}%`, backgroundColor: color }}
        />
      </div>
      <p className="text-[10px] text-tahoe-textMuted">
        Similarity: {simPct.toFixed(1)}%
      </p>
      {match.glom_pattern && (
        <GlomBarcode pattern={match.glom_pattern} />
      )}
    </div>
  );
}

// ── Searchable odor selector ────────────────────────────────────────────

interface OdorSelectorProps {
  odorants: OdorantListItem[];
  value: string;
  onChange: (name: string) => void;
  disabled: boolean;
}

function OdorSelector({ odorants, value, onChange, disabled }: OdorSelectorProps) {
  const [query, setQuery]     = useState('');
  const [open, setOpen]       = useState(false);
  const containerRef          = useRef<HTMLDivElement>(null);

  const filtered = query.trim()
    ? odorants.filter(o =>
        o.name.toLowerCase().includes(query.toLowerCase()) ||
        o.family.toLowerCase().includes(query.toLowerCase()),
      ).slice(0, 40)
    : odorants.slice(0, 40);

  useEffect(() => {
    function handleOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleOutside);
    return () => document.removeEventListener('mousedown', handleOutside);
  }, []);

  return (
    <div className="relative" ref={containerRef}>
      <div
        className="flex items-center gap-2 px-3 py-2 rounded-xl border border-tahoe-border bg-tahoe-panel cursor-pointer"
        onClick={() => !disabled && setOpen(o => !o)}
      >
        {value ? (
          <span className="text-sm flex-1 truncate">{value.replace(/_/g, ' ')}</span>
        ) : (
          <span className="text-sm flex-1 text-tahoe-textMuted">Select odorant…</span>
        )}
        <svg className="w-4 h-4 text-tahoe-textMuted" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>

      {open && (
        <div className="absolute z-50 mt-1 w-full rounded-xl border border-tahoe-border bg-tahoe-panel shadow-2xl overflow-hidden">
          <div className="p-2 border-b border-tahoe-border">
            <input
              autoFocus
              className="w-full text-sm bg-transparent outline-none placeholder-tahoe-textMuted"
              placeholder="Search odorants or families…"
              value={query}
              onChange={e => setQuery(e.target.value)}
            />
          </div>
          <ul className="max-h-52 overflow-y-auto">
            {filtered.map(o => (
              <li
                key={o.name}
                className="flex items-center justify-between px-3 py-2 cursor-pointer hover:bg-tahoe-accent/10 transition-colors"
                onClick={() => { onChange(o.name); setOpen(false); setQuery(''); }}
              >
                <span className="text-sm truncate">{o.name.replace(/_/g, ' ')}</span>
                <FamilyBadge family={o.family} />
              </li>
            ))}
            {filtered.length === 0 && (
              <li className="px-3 py-4 text-sm text-tahoe-textMuted text-center">No results</li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}

// ── Main panel ──────────────────────────────────────────────────────────

type PanelStatus = 'idle' | 'loading_db' | 'running' | 'done' | 'error';

export function SmellSynthesisPanel() {
  const [odorants, setOdorants]       = useState<OdorantListItem[]>([]);
  const [selected, setSelected]       = useState<string>('');
  const [mode, setMode]               = useState<SynthesisMode>('fast');
  const [panelStatus, setPanelStatus] = useState<PanelStatus>('idle');
  const [progress, setProgress]       = useState<SynthesisProgress | null>(null);
  const [matches, setMatches]         = useState<OdorMatch[]>([]);
  const [lossHistory, setLossHistory] = useState<{ step: number; loss: number }[]>([]);
  const [statusMsg, setStatusMsg]     = useState('');
  const unsubRef = useRef<(() => void) | null>(null);

  // Load odorant list on mount
  useEffect(() => {
    setPanelStatus('loading_db');
    fetchOdorantList()
      .then(res => {
        setOdorants(res.odorants);
        setPanelStatus('idle');
      })
      .catch(err => {
        setStatusMsg(`Failed to load database: ${err.message}`);
        setPanelStatus('error');
      });
  }, []);

  const handleSynthesize = useCallback(async () => {
    if (!selected) return;
    unsubRef.current?.();

    setPanelStatus('running');
    setProgress(null);
    setMatches([]);
    setLossHistory([]);
    setStatusMsg('Starting synthesis…');

    try {
      const { job_id } = await startSynthesis({
        target_odor: selected,
        mode,
        num_steps: mode === 'accurate' ? 100 : 1,
      });

      const unsub = subscribeSynthesis(
        job_id,
        (prog) => {
          setProgress(prog);
          if (prog.top_matches.length > 0) setMatches(prog.top_matches);
          setLossHistory(prev => {
            const pts = prog.history_loss.map((l, i) => ({ step: i + 1, loss: l }));
            return pts.length > 0 ? pts : prev;
          });
          setStatusMsg(
            prog.status === 'running'
              ? `Step ${prog.step} — loss ${prog.loss.toFixed(4)}`
              : prog.status === 'done'
              ? prog.converged
                ? `Converged at step ${prog.step}`
                : `Completed ${prog.step} steps`
              : `Status: ${prog.status}`,
          );
        },
        (result) => {
          if (result.top_matches.length > 0) setMatches(result.top_matches);
          setPanelStatus('done');
          setStatusMsg(
            result.converged
              ? `Converged — ${result.top_matches[0]?.name ?? 'unknown'} is nearest match`
              : `Done — ${result.top_matches[0]?.name ?? 'unknown'} is nearest match`,
          );
        },
        (err) => {
          setPanelStatus('error');
          setStatusMsg(`Error: ${err}`);
        },
      );

      unsubRef.current = unsub;
    } catch (err: unknown) {
      setPanelStatus('error');
      setStatusMsg(`Failed: ${err instanceof Error ? err.message : String(err)}`);
    }
  }, [selected, mode]);

  // Cleanup on unmount
  useEffect(() => () => { unsubRef.current?.(); }, []);

  const isRunning  = panelStatus === 'running';
  const isLoading  = panelStatus === 'loading_db';

  return (
    <div className="tahoe-panel p-6 space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-semibold">Smell Synthesis</h2>
          <p className="text-xs text-tahoe-textMuted mt-0.5">
            Inverse problem solver — KC pattern → nearest molecular match
          </p>
        </div>
        <div className="flex items-center gap-2">
          {odorants.length > 0 && (
            <span className="text-[10px] font-mono text-tahoe-textMuted">
              {odorants.length} odorants
            </span>
          )}
          <div
            className="w-2 h-2 rounded-full"
            style={{
              backgroundColor:
                panelStatus === 'running'  ? '#f59e0b' :
                panelStatus === 'done'     ? '#30D158' :
                panelStatus === 'error'    ? '#FF453A' :
                '#94a3b8',
              boxShadow: panelStatus === 'running' ? '0 0 6px #f59e0b' : undefined,
            }}
          />
        </div>
      </div>

      {/* Input zone */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-end">
        {/* Odorant selector */}
        <div className="md:col-span-2 space-y-1">
          <label className="text-xs font-medium text-tahoe-textMuted uppercase tracking-wider">
            Target odorant
          </label>
          <OdorSelector
            odorants={odorants}
            value={selected}
            onChange={setSelected}
            disabled={isRunning || isLoading}
          />
        </div>

        {/* Mode toggle + run button */}
        <div className="space-y-2">
          <label className="text-xs font-medium text-tahoe-textMuted uppercase tracking-wider">
            Mode
          </label>
          <div className="flex rounded-xl overflow-hidden border border-tahoe-border">
            {(['fast', 'accurate'] as SynthesisMode[]).map(m => (
              <button
                key={m}
                disabled={isRunning}
                onClick={() => setMode(m)}
                className="flex-1 text-xs py-2 font-medium transition-colors"
                style={{
                  background: mode === m ? 'var(--tahoe-accent)' : 'transparent',
                  color: mode === m ? '#fff' : 'var(--tahoe-textMuted)',
                }}
              >
                {m === 'fast' ? 'Fast' : 'Accurate'}
              </button>
            ))}
          </div>
          <button
            disabled={!selected || isRunning || isLoading}
            onClick={handleSynthesize}
            className="w-full py-2 rounded-xl text-sm font-semibold transition-all"
            style={{
              background: (!selected || isRunning || isLoading)
                ? 'rgba(10,132,255,0.3)'
                : '#0A84FF',
              color: '#fff',
              cursor: (!selected || isRunning || isLoading) ? 'not-allowed' : 'pointer',
            }}
          >
            {isRunning ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Synthesising…
              </span>
            ) : 'Synthesize'}
          </button>
        </div>
      </div>

      {/* Status message */}
      {statusMsg && (
        <p
          className="text-xs px-3 py-1.5 rounded-lg font-mono"
          style={{
            background: panelStatus === 'error'
              ? 'rgba(239,68,68,0.12)'
              : 'rgba(10,132,255,0.08)',
            color: panelStatus === 'error' ? '#f87171' : '#60a5fa',
          }}
        >
          {statusMsg}
        </p>
      )}

      {/* Convergence chart — only in accurate mode with history */}
      {mode === 'accurate' && lossHistory.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-tahoe-textMuted uppercase tracking-wider mb-2">
            Optimisation Convergence
          </h3>
          <div className="h-32">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={lossHistory}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis
                  dataKey="step"
                  tick={{ fontSize: 10, fill: '#94a3b8' }}
                  label={{ value: 'Step', position: 'insideBottom', offset: -2, fill: '#94a3b8', fontSize: 10 }}
                />
                <YAxis
                  tick={{ fontSize: 10, fill: '#94a3b8' }}
                  domain={['auto', 'auto']}
                />
                <Tooltip
                  contentStyle={{ background: '#1c1c1e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8 }}
                  labelStyle={{ color: '#94a3b8', fontSize: 11 }}
                  itemStyle={{ color: '#60a5fa', fontSize: 11 }}
                />
                <Line
                  type="monotone"
                  dataKey="loss"
                  stroke="#0A84FF"
                  strokeWidth={1.5}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
          {progress?.converged && (
            <p className="text-xs text-center mt-1" style={{ color: '#30D158' }}>
              Converged at step {progress.step}
            </p>
          )}
        </div>
      )}

      {/* Top matches */}
      {matches.length > 0 && (
        <div>
          <h3 className="text-xs font-semibold text-tahoe-textMuted uppercase tracking-wider mb-3">
            Nearest Molecular Matches
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            {matches.map((m, i) => (
              <MatchCard key={m.name} match={m} rank={i + 1} />
            ))}
          </div>
        </div>
      )}

      {/* Idle placeholder */}
      {panelStatus === 'idle' && matches.length === 0 && odorants.length > 0 && (
        <div className="text-center py-8 text-tahoe-textMuted text-sm border border-dashed border-tahoe-border rounded-xl">
          Select an odorant above and click <strong>Synthesize</strong> to find its nearest molecular matches
          via KC pattern similarity search across {odorants.length} DoOR odorants.
        </div>
      )}

      {isLoading && (
        <div className="text-center py-8 text-tahoe-textMuted text-sm">
          <div className="w-5 h-5 border-2 border-tahoe-accent border-t-transparent rounded-full animate-spin mx-auto mb-2" />
          Loading chemical database…
        </div>
      )}
    </div>
  );
}
