# Frontend Visual Guide

## Dashboard Layout

The dashboard uses a 3-column responsive grid layout with macOS Tahoe styling.

### Layout Structure

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Fly Brain Wave Consciousness                                             │
│  Real-time visualization of wave-based consciousness architecture         │
└──────────────────────────────────────────────────────────────────────────┘

┌────────────────────┬────────────────────┬────────────────────┐
│  COLUMN 1          │  COLUMN 2          │  COLUMN 3          │
├────────────────────┼────────────────────┼────────────────────┤
│ ┌────────────────┐ │ ┌────────────────┐ │ ┌────────────────┐ │
│ │ System Status  │ │ │  3D Brain Viz  │ │ │ Thought Pattern│ │
│ │                │ │ │                │ │ │                │ │
│ │ • 139K neurons │ │ │   [3D SCENE]   │ │ │ → Sequential   │ │
│ │ • 24 hives     │ │ │                │ │ │ ⫙ Parallel     │ │
│ │ • 87% coherence│ │ │  [Colored      │ │ │ ↻ Recursive    │ │
│ │ • 42k energy   │ │ │   particles    │ │ │ ~ Interference │ │
│ │                │ │ │   represent    │ │ │                │ │
│ │ [Live • ]      │ │ │   neurons]     │ │ │ Latest 8       │ │
│ └────────────────┘ │ │                │ │ │ patterns shown │ │
│                    │ └────────────────┘ │ └────────────────┘ │
│ ┌────────────────┐ │                    │                    │
│ │ Consciousness  │ │ ┌────────────────┐ │ ┌────────────────┐ │
│ │ State          │ │ │ Wave Activity  │ │ │ Active Hives   │ │
│ │                │ │ │                │ │ │                │ │
│ │    ⦿ W         │ │ │  [Line chart   │ │ │ • Hive a3f2    │ │
│ │   WAKE         │ │ │   showing      │ │ │   95% coherent │ │
│ │                │ │ │   coherence,   │ │ │                │ │
│ │ Coherence ████ │ │ │   frequency,   │ │ │ • Hive 7c8e    │ │
│ │ Frequency 18Hz │ │ │   energy over  │ │ │   89% coherent │ │
│ │ Metastable ███ │ │ │   last 50      │ │ │                │ │
│ └────────────────┘ │ │   snapshots]   │ │ │ Top 8 by       │ │
│                    │ │                │ │ │ coherence      │ │
│ ┌────────────────┐ │ └────────────────┘ │ └────────────────┘ │
│ │ Control Panel  │ │                    │                    │
│ │                │ │                    │ ┌────────────────┐ │
│ │ [▶ Start]      │ │                    │ │ Memory Pattern │ │
│ │ [⏸ Pause]      │ │                    │ │                │ │
│ │ [↻ Reset]      │ │                    │ │ • mem_a8f3     │ │
│ │                │ │                    │ │   92% strength │ │
│ │ Connection: ✓  │ │                    │ │   Recalled 5×  │ │
│ │ Time: 42.3s    │ │                    │ │                │ │
│ │ Status: Run    │ │                    │ │ • mem_f2d1     │ │
│ │                │ │                    │ │   87% strength │ │
│ │ Quick Actions: │ │                    │ │   Recalled 3×  │ │
│ │ [Stimulus]     │ │                    │ │                │ │
│ │ [Force State]  │ │                    │ │ Top 6 by       │ │
│ │ [Snapshot]     │ │                    │ │ strength       │ │
│ │ [Export]       │ │                    │ │                │ │
│ └────────────────┘ │                    │ └────────────────┘ │
└────────────────────┴────────────────────┴────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  FULL WIDTH ROW                                              │
├──────────────────────────┬───────────────────────────────────┤
│ ┌──────────────────────┐ │ ┌───────────────────────────────┐│
│ │ Frequency Bands      │ │ │ Phase Coherence Map           ││
│ │                      │ │ │                               ││
│ │ Delta  ████ 15%      │ │ │   [20×20 heatmap grid]        ││
│ │ Theta  ████ 22%      │ │ │   showing spatial activity    ││
│ │ Alpha  ████████ 35%  │ │ │   patterns across brain       ││
│ │ Beta   ███ 18%       │ │ │                               ││
│ │ Gamma  ██ 10%        │ │ │   Low Activity ← → High       ││
│ │                      │ │ │   [Blue gradient bar]         ││
│ └──────────────────────┘ │ └───────────────────────────────┘│
└──────────────────────────┴───────────────────────────────────┘
```

## Color Scheme (Tahoe)

### Panel Colors
- **Background**: `#0B0B0C` (very dark)
- **Panel**: `rgba(22, 22, 24, 0.8)` with 20px blur
- **Border**: `rgba(255, 255, 255, 0.12)` (subtle white)
- **Text**: `#F5F5F7` (off-white)
- **Muted Text**: `#98989D` (gray)

### Accent Colors
- **Primary**: `#0A84FF` (blue) - buttons, coherence
- **Delta**: `#5E5CE6` (purple) - 0.5-4 Hz
- **Theta**: `#0A84FF` (blue) - 4-8 Hz
- **Alpha**: `#30D158` (green) - 8-13 Hz
- **Beta**: `#FF9F0A` (orange) - 13-30 Hz
- **Gamma**: `#FF453A` (red) - 30-100 Hz

### State Colors
- **WAKE**: `#0A84FF` (blue)
- **SLEEP**: `#5E5CE6` (purple)
- **DREAM**: `#BF5AF2` (magenta)
- **SHOCK**: `#FF453A` (red)
- **MEDITATION**: `#30D158` (green)

## Typography

- **Font**: SF Pro Text (system font stack)
- **Title**: 22-24px, medium/semibold
- **Section**: 16-18px, semibold
- **Body**: 13-14px, regular
- **Labels**: 11-12px, medium

## Panel Details

### 1. System Status
Shows 4 key metrics in 2×2 grid:
- Active Neurons (count)
- Active Hives (count)
- Coherence (percentage)
- Energy (value)

Live indicator (green pulsing dot) in header.

### 2. Consciousness State
Large circular state indicator with letter.
Current state name prominently displayed.
3 metrics with progress bars:
- Global Coherence (%)
- Dominant Frequency (Hz + band name)
- Metastability (%)

### 3. 3D Brain Visualization
Full WebGL Three.js scene:
- Neurons as colored particles (phase-based HSL color)
- Hive boundaries as wireframe spheres
- Grid helper for spatial reference
- Orbit controls (drag to rotate, scroll to zoom)
- Instructions at bottom

### 4. Wave Activity Chart
Line chart with 3 traces:
- Coherence % (blue line)
- Frequency Hz (purple line)
- Energy k (green line)
Shows last 50 snapshots.
Legend with colored squares.

### 5. Thought Patterns Panel
List of recent patterns (last 8):
- Icon for type (→ ⫙ ↻ ~)
- Type name (Sequential/Parallel/Recursive/Interference)
- Timestamp
- Hive count, stability %, complexity
- Signature hash preview

### 6. Active Hives Panel
Top 8 hives by coherence:
- Hive ID (8-char hash)
- Size and neuron count
- Age
- Coherence progress bar (blue-cyan gradient)

### 7. Memory Patterns Panel
Top 6 memories by strength:
- Memory ID (12-char hash)
- Neuron count
- Age in seconds
- Recall count
- Strength progress bar (amber-orange gradient)

### 8. Frequency Bands Panel
5 frequency bands with distribution:
- Delta, Theta, Alpha, Beta, Gamma
- Count and percentage for each
- Color-coded progress bars
- Band ranges shown at bottom

### 9. Phase Coherence Map
20×20 heatmap grid:
- Each cell = spatial region
- Color = average amplitude in region
- Blue (low) to cyan (high) gradient
- Gradient scale at bottom

### 10. Control Panel
3 main buttons (Start, Pause, Reset).
Status display:
- Connection status (green/red)
- Simulation time (seconds)
- Running status

Quick action buttons (4 placeholders):
- Inject Stimulus
- Force State
- Save Snapshot
- Export Data

## Animations

All transitions use:
- **Duration**: 150-220ms
- **Easing**: `cubic-bezier(0.25, 0.8, 0.25, 1)`

Animations applied to:
- Panel hover (border glow, shadow)
- Button hover (lift, shadow)
- Button active (press down)
- Progress bar updates (smooth width change)
- State indicator glow
- Live dot pulse
- Chart line drawing
- 3D particle colors (every frame)

## Responsive Behavior

- **≥1280px**: 3-column grid + 2-column bottom row
- **768-1279px**: 2-column grid, stacked panels
- **<768px**: Single column, full stack

All panels maintain same styling at all breakpoints.

## Performance

- **React renders**: 20/sec (WebSocket rate)
- **3D scene**: 60 FPS (requestAnimationFrame)
- **Chart updates**: Smooth (Recharts handles animation)
- **History buffer**: Last 100 snapshots (~5 seconds)
- **Neuron sample**: 1000 particles (configurable in server.py)

## Accessibility

- Clear contrast ratios (WCAG AA)
- Focus states on all buttons
- Readable font sizes (13px minimum)
- Color not sole indicator (icons + text)
- Keyboard navigation supported

---

**Design Philosophy**: Clean, minimal, soft, glassy. Like a macOS app, not a web dashboard. Every element intentional, every animation purposeful, zero "corporate stock dashboard" vibes.
