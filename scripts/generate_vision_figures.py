"""
Generate Vision Validation Figures for Publication

Creates 4 supplementary figures for vision validation:
1. Sparse Coding (4 layers: Lamina, Medulla, Lobula, Lobula Plate)
2. Contrast Invariance (Weber-Fechner law)
3. Chromatic Decorrelation (UV vs Visible opponency)
4. Motion Detection (Barlow-Levick mechanism)
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

# Publication settings
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica']
plt.rcParams['font.size'] = 9
plt.rcParams['axes.labelsize'] = 10
plt.rcParams['axes.titlesize'] = 11
plt.rcParams['xtick.labelsize'] = 8
plt.rcParams['ytick.labelsize'] = 8
plt.rcParams['legend.fontsize'] = 8
plt.rcParams['figure.titlesize'] = 12

# Colors
COLOR_PASS = '#2E7D32'  # Green
COLOR_FAIL = '#C62828'  # Red
COLOR_WARN = '#F57C00'  # Orange
COLOR_PRIMARY = '#1976D2'  # Blue
COLOR_SECONDARY = '#7B1FA2'  # Purple
COLOR_ACCENT = '#C2185B'  # Pink

def create_figure_1_sparse_coding():
    """Vision Sparse Coding: 4 layers validation"""
    
    # Data from VISION_VALIDATION_FINAL_RESULTS.md
    layers = ['Lamina', 'Medulla', 'Lobula', 'Lobula\nPlate']
    sparsity_mean = [18.68, 6.87, 20.62, 42.11]
    sparsity_std = [1.83, 1.43, 6.45, 12.09]
    target_min = [15, 3, 15, 15]
    target_max = [40, 15, 30, 50]
    
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    fig.suptitle('Vision Sparse Coding Validation — 4/4 Layers Pass', 
                 fontsize=14, fontweight='bold', y=0.98)
    
    for idx, (ax, layer, mean, std, t_min, t_max) in enumerate(
        zip(axes.flat, layers, sparsity_mean, sparsity_std, target_min, target_max)
    ):
        # Target range (biological)
        ax.axhspan(t_min, t_max, alpha=0.15, color=COLOR_PASS, label='Biological Target')
        
        # Measured value
        ax.errorbar([0], [mean], yerr=[std], fmt='o', markersize=12, 
                   color=COLOR_PRIMARY, ecolor=COLOR_PRIMARY, capsize=8, 
                   capthick=2, linewidth=2, label='Measured', zorder=10)
        
        # Determine pass/fail
        is_pass = t_min <= mean <= t_max
        status_color = COLOR_PASS if is_pass else COLOR_FAIL
        status_text = '✓ PASS' if is_pass else '✗ FAIL'
        
        # Styling
        ax.set_xlim(-0.5, 0.5)
        ax.set_ylim(0, max(t_max * 1.3, mean + 3*std))
        ax.set_xticks([])
        ax.set_ylabel('Active Neurons (%)', fontweight='bold')
        ax.set_title(f'{layer}\n{mean:.2f}% ± {std:.2f}%', 
                    fontweight='bold', fontsize=11)
        
        # Status badge
        ax.text(0, ax.get_ylim()[1] * 0.92, status_text,
               ha='center', va='top', fontsize=10, fontweight='bold',
               bbox=dict(boxstyle='round,pad=0.5', facecolor=status_color, 
                        edgecolor='none', alpha=0.9),
               color='white', zorder=20)
        
        # Target range text
        ax.text(0, t_min - (ax.get_ylim()[1] * 0.05), 
               f'Target: {t_min}-{t_max}%',
               ha='center', va='top', fontsize=8, style='italic',
               color='#555')
        
        if idx == 0:
            ax.legend(loc='upper left', framealpha=0.95)
        
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    # Overall summary
    fig.text(0.5, 0.02, 
            'All 4 visual layers exhibit biologically appropriate sparse coding patterns\n'
            'Lamina: retinotopic (18.7%) | Medulla: feature coding (6.9%) | '
            'Lobula: motion (20.6%) | LP: integration (42.1%)',
            ha='center', va='bottom', fontsize=9, style='italic', color='#333')
    
    plt.tight_layout(rect=[0, 0.05, 1, 0.97])
    return fig

def create_figure_2_contrast_invariance():
    """Vision Contrast Invariance: Weber-Fechner law"""
    
    # Data from validation results
    wavelengths = [450, 500, 600]
    correlations_mean = [0.913, 0.881, 0.757]
    correlations_std = [0.071, 0.050, 0.198]
    
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle('Vision Contrast Invariance — Weber-Fechner Logarithmic Encoding',
                 fontsize=14, fontweight='bold')
    
    # Panel A: Per-wavelength correlation
    ax1 = axes[0]
    x_pos = np.arange(len(wavelengths))
    bars = ax1.bar(x_pos, correlations_mean, yerr=correlations_std,
                   color=[COLOR_PRIMARY, COLOR_SECONDARY, COLOR_ACCENT],
                   capsize=8, alpha=0.8, edgecolor='black', linewidth=1.5)
    
    # Target line
    ax1.axhline(0.70, color=COLOR_PASS, linestyle='--', linewidth=2, 
               label='Target (r=0.70)', zorder=0)
    
    ax1.set_xticks(x_pos)
    ax1.set_xticklabels([f'{w}nm' for w in wavelengths])
    ax1.set_ylabel('Correlation (r)', fontweight='bold')
    ax1.set_xlabel('Wavelength', fontweight='bold')
    ax1.set_title('A. Per-Wavelength Pattern Correlation\n(10× intensity range)',
                 fontweight='bold')
    ax1.set_ylim(0, 1.0)
    ax1.legend(loc='lower right')
    ax1.grid(axis='y', alpha=0.3)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    
    # Add pass indicators
    for i, (mean, std) in enumerate(zip(correlations_mean, correlations_std)):
        if mean - std > 0.70:
            ax1.text(i, mean + std + 0.03, '✓', ha='center', fontsize=14,
                    color=COLOR_PASS, fontweight='bold')
    
    # Panel B: Overall performance summary
    ax2 = axes[1]
    overall_mean = 0.857
    overall_std = 0.140
    
    # Target box
    ax2.axhspan(0.70, 1.0, alpha=0.15, color=COLOR_PASS, label='Target Range')
    
    # Measured distribution
    ax2.errorbar([0], [overall_mean], yerr=[overall_std], fmt='o', 
                markersize=18, color=COLOR_PRIMARY, ecolor=COLOR_PRIMARY,
                capsize=12, capthick=3, linewidth=3, label='Measured', zorder=10)
    
    ax2.set_xlim(-0.5, 0.5)
    ax2.set_ylim(0, 1.0)
    ax2.set_xticks([])
    ax2.set_ylabel('Overall Correlation (r)', fontweight='bold')
    ax2.set_title(f'B. Overall Performance\nr = {overall_mean:.3f} ± {overall_std:.3f}\n'
                 f'(122% of target)', fontweight='bold')
    ax2.legend(loc='lower right')
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.grid(axis='y', alpha=0.3)
    
    # Pass badge
    ax2.text(0, 0.95, '✓ PASS', ha='center', va='top', fontsize=12, 
            fontweight='bold', color='white',
            bbox=dict(boxstyle='round,pad=0.6', facecolor=COLOR_PASS, alpha=0.9))
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    return fig

def create_figure_3_chromatic_decorrelation():
    """Vision Chromatic Decorrelation: UV vs Visible Opponency"""
    
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    fig.suptitle('Chromatic Decorrelation via Dm8/Tm5 Color Opponency',
                 fontsize=14, fontweight='bold')
    
    # Panel A: Opsin response profiles
    ax1 = axes[0]
    wavelengths = np.linspace(300, 600, 300)
    
    # Rh3 (R7, UV): peak 345nm, Gaussian approximation
    rh3_peak = 345
    rh3_width = 50
    rh3_response = np.exp(-((wavelengths - rh3_peak) / rh3_width) ** 2)
    
    # Rh6 (R8, visible): peak 508nm
    rh6_peak = 508
    rh6_width = 60
    rh6_response = np.exp(-((wavelengths - rh6_peak) / rh6_width) ** 2)
    
    ax1.fill_between(wavelengths, 0, rh3_response, alpha=0.4, 
                     color=COLOR_SECONDARY, label='R7 (Rh3, UV)')
    ax1.fill_between(wavelengths, 0, rh6_response, alpha=0.4,
                     color=COLOR_ACCENT, label='R8 (Rh6, Visible)')
    ax1.plot(wavelengths, rh3_response, color=COLOR_SECONDARY, linewidth=2)
    ax1.plot(wavelengths, rh6_response, color=COLOR_ACCENT, linewidth=2)
    
    # Mark test wavelengths
    ax1.axvline(350, color='purple', linestyle='--', alpha=0.6, linewidth=1.5)
    ax1.axvline(550, color='green', linestyle='--', alpha=0.6, linewidth=1.5)
    ax1.text(350, 0.95, '350nm\n(UV test)', ha='center', fontsize=8, 
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    ax1.text(550, 0.95, '550nm\n(Vis test)', ha='center', fontsize=8,
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    ax1.set_xlabel('Wavelength (nm)', fontweight='bold')
    ax1.set_ylabel('Normalized Response', fontweight='bold')
    ax1.set_title('A. Opsin Spectral Sensitivity\n(Gao et al. 2008)', 
                 fontweight='bold')
    ax1.legend(loc='upper right')
    ax1.set_xlim(300, 600)
    ax1.set_ylim(0, 1.1)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.grid(alpha=0.3)
    
    # Panel B: Medulla correlation comparison
    ax2 = axes[1]
    conditions = ['UV/Vis\nOpponent', 'Adjacent\nControl']
    correlations = [0.754, 0.815]
    colors_bar = [COLOR_PRIMARY, '#999']
    
    bars = ax2.bar(conditions, correlations, color=colors_bar, alpha=0.8,
                   edgecolor='black', linewidth=1.5)
    
    # Highlight the gap
    ax2.plot([0, 1], [correlations[0], correlations[1]], 'k--', 
            linewidth=2, alpha=0.5)
    gap = correlations[1] - correlations[0]
    ax2.text(0.5, np.mean(correlations), f'Gap = {gap:.3f}',
            ha='center', va='center', fontsize=10, fontweight='bold',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', 
                     edgecolor='black', linewidth=2, alpha=0.9))
    
    ax2.set_ylabel('Medulla Correlation (r)', fontweight='bold')
    ax2.set_title('B. Decorrelation Measurement\n(Target gap > 0.05)',
                 fontweight='bold')
    ax2.set_ylim(0, 1.0)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.grid(axis='y', alpha=0.3)
    
    # Target line
    ax2.axhline(0.85, color=COLOR_FAIL, linestyle=':', linewidth=2, 
               alpha=0.5, label='High corr limit')
    
    # Panel C: Circuit diagram (simplified)
    ax3 = axes[2]
    ax3.axis('off')
    ax3.set_xlim(0, 10)
    ax3.set_ylim(0, 10)
    ax3.set_title('C. Dm8/Tm5 Opponency Circuit\n(Behnia et al. 2021)',
                 fontweight='bold')
    
    # UV pathway
    ax3.add_patch(mpatches.FancyBboxPatch((1, 7), 2, 1.2, 
                 boxstyle="round,pad=0.1", facecolor=COLOR_SECONDARY, 
                 edgecolor='black', linewidth=2, alpha=0.7))
    ax3.text(2, 7.6, 'R7\n(Rh3)', ha='center', va='center', fontsize=9,
            fontweight='bold', color='white')
    
    ax3.add_patch(mpatches.FancyBboxPatch((1, 4.5), 2, 1.2,
                 boxstyle="round,pad=0.1", facecolor=COLOR_SECONDARY,
                 edgecolor='black', linewidth=1.5, alpha=0.5))
    ax3.text(2, 5.1, 'Dm8-UV\nTm5c', ha='center', va='center', fontsize=8,
            fontweight='bold')
    
    # Arrow UV
    ax3.annotate('', xy=(2, 4.5), xytext=(2, 7),
                arrowprops=dict(arrowstyle='->', lw=2, color=COLOR_SECONDARY))
    ax3.text(2.5, 5.8, 'UV ON', fontsize=7, color=COLOR_SECONDARY, 
            fontweight='bold')
    
    # Visible pathway
    ax3.add_patch(mpatches.FancyBboxPatch((7, 7), 2, 1.2,
                 boxstyle="round,pad=0.1", facecolor=COLOR_ACCENT,
                 edgecolor='black', linewidth=2, alpha=0.7))
    ax3.text(8, 7.6, 'R8\n(Rh6)', ha='center', va='center', fontsize=9,
            fontweight='bold', color='white')
    
    ax3.add_patch(mpatches.FancyBboxPatch((7, 4.5), 2, 1.2,
                 boxstyle="round,pad=0.1", facecolor=COLOR_ACCENT,
                 edgecolor='black', linewidth=1.5, alpha=0.5))
    ax3.text(8, 5.1, 'Dm8-Vis\nTm5a', ha='center', va='center', fontsize=8,
            fontweight='bold')
    
    # Arrow Visible
    ax3.annotate('', xy=(8, 4.5), xytext=(8, 7),
                arrowprops=dict(arrowstyle='->', lw=2, color=COLOR_ACCENT))
    ax3.text(7.3, 5.8, 'Vis ON', fontsize=7, color=COLOR_ACCENT,
            fontweight='bold')
    
    # Medulla output
    ax3.add_patch(mpatches.FancyBboxPatch((3.5, 2), 3, 1.2,
                 boxstyle="round,pad=0.1", facecolor='#FFD54F',
                 edgecolor='black', linewidth=2))
    ax3.text(5, 2.6, 'MEDULLA\nDecorrelated', ha='center', va='center',
            fontsize=9, fontweight='bold')
    
    # Converging arrows
    ax3.annotate('', xy=(4.5, 2.8), xytext=(2, 4.5),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='black', 
                              connectionstyle="arc3,rad=.3"))
    ax3.annotate('', xy=(5.5, 2.8), xytext=(8, 4.5),
                arrowprops=dict(arrowstyle='->', lw=1.5, color='black',
                              connectionstyle="arc3,rad=-.3"))
    
    # Result box
    ax3.text(5, 0.5, '✓ PASS: Gap = 0.061 > 0.05', ha='center', fontsize=10,
            fontweight='bold', color='white',
            bbox=dict(boxstyle='round,pad=0.5', facecolor=COLOR_PASS, alpha=0.9))
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    return fig

def create_figure_4_motion_detection():
    """Vision Motion Detection: Barlow-Levick Mechanism"""
    
    fig = plt.figure(figsize=(14, 10))
    gs = fig.add_gridspec(3, 2, hspace=0.35, wspace=0.3)
    fig.suptitle('Motion Detection via Barlow-Levick Null-Direction Suppression',
                 fontsize=14, fontweight='bold')
    
    # Panel A: Temporal filter kernels
    ax1 = fig.add_subplot(gs[0, 0])
    time = np.linspace(0, 100, 200)
    
    # Fast excitation (ACh, Mi1/Tm3, τ=10ms)
    tau_exc = 10
    exc_response = np.exp(-time / tau_exc)
    
    # Slow inhibition (GABA, Mi4/C3/CT1, τ=25ms)
    tau_inh = 25
    inh_response = 5.0 * np.exp(-time / tau_inh)  # 5× weight (Haag et al. 2017)
    
    ax1.plot(time, exc_response, color='#4CAF50', linewidth=2.5, 
            label='Fast Excitation (ACh, τ=10ms)')
    ax1.plot(time, inh_response, color='#F44336', linewidth=2.5,
            label='Slow Inhibition (GABA, 5×, τ=25ms)')
    ax1.fill_between(time, 0, exc_response, alpha=0.3, color='#4CAF50')
    ax1.fill_between(time, 0, inh_response, alpha=0.3, color='#F44336')
    
    ax1.set_xlabel('Time (ms)', fontweight='bold')
    ax1.set_ylabel('Response Amplitude', fontweight='bold')
    ax1.set_title('A. Temporal Filter Kernels (Haag et al. 2017)',
                 fontweight='bold')
    ax1.legend(loc='upper right')
    ax1.set_xlim(0, 100)
    ax1.set_ylim(0, 6)
    ax1.grid(alpha=0.3)
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    
    # Highlight 5× weight
    ax1.text(30, 4.5, 'GABA shunting:\n5× effective weight\n(~5nS vs ~1nS)',
            fontsize=8, bbox=dict(boxstyle='round', facecolor='#FFCCBC', 
                                 edgecolor='#F44336', linewidth=2),
            ha='center')
    
    # Panel B: Motion stimulus schematic
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.axis('off')
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 10)
    ax2.set_title('B. Moving Bar Stimulus\n(Spatial Luminance Contrast)',
                 fontweight='bold')
    
    # Draw ommatidia columns
    for i in range(5):
        x = 2 + i * 1.5
        ax2.add_patch(mpatches.Rectangle((x, 6), 0.8, 1.5,
                     facecolor='#E0E0E0', edgecolor='black', linewidth=1))
        ax2.text(x + 0.4, 6.75, f'O{i+1}', ha='center', va='center',
                fontsize=8, fontweight='bold')
    
    # Moving bar at different time points
    bar_positions = [3, 4.5, 6, 7.5]
    colors_time = ['#BBDEFB', '#90CAF9', '#42A5F5', '#1976D2']
    for t, (pos, col) in enumerate(zip(bar_positions, colors_time)):
        ax2.add_patch(mpatches.FancyBboxPatch((pos - 0.3, 3.5 - t*0.6), 0.8, 1.5,
                     boxstyle="round,pad=0.05", facecolor=col, 
                     edgecolor='black', linewidth=2, alpha=0.7))
        ax2.text(pos + 0.1, 4.2 - t*0.6, f't={t*10}ms', fontsize=7, 
                fontweight='bold')
    
    # Direction arrow
    ax2.annotate('', xy=(9, 4.5), xytext=(1.5, 4.5),
                arrowprops=dict(arrowstyle='->', lw=3, color='black'))
    ax2.text(5.2, 5.2, 'Preferred Direction →', ha='center', fontsize=10,
            fontweight='bold')
    
    # Panel C: Preferred direction response
    ax3 = fig.add_subplot(gs[1, 0])
    time_response = np.linspace(0, 100, 200)
    
    # Preferred: excitation arrives first, then weak inhibition
    exc_pref = 1.0 * np.exp(-(time_response - 20)**2 / 100)
    inh_pref = 0.3 * np.exp(-(time_response - 40)**2 / 150)
    output_pref = np.maximum(0, exc_pref - inh_pref)
    
    ax3.plot(time_response, exc_pref, '--', color='#4CAF50', linewidth=2,
            label='Excitation', alpha=0.7)
    ax3.plot(time_response, inh_pref, '--', color='#F44336', linewidth=2,
            label='Inhibition', alpha=0.7)
    ax3.plot(time_response, output_pref, color='black', linewidth=3,
            label='T4 Output = max(0, E - I)')
    ax3.fill_between(time_response, 0, output_pref, alpha=0.3, color='#4CAF50')
    
    ax3.set_xlabel('Time (ms)', fontweight='bold')
    ax3.set_ylabel('T4 Response', fontweight='bold')
    ax3.set_title('C. Preferred Direction: Strong Output\n(Excitation leads)',
                 fontweight='bold')
    ax3.legend(loc='upper right')
    ax3.set_xlim(0, 100)
    ax3.set_ylim(-0.2, 1.2)
    ax3.grid(alpha=0.3)
    ax3.spines['top'].set_visible(False)
    ax3.spines['right'].set_visible(False)
    
    # Highlight strong output
    ax3.text(50, 0.9, '✓ Strong Response\nMean = 1.19', ha='center',
            fontsize=9, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor=COLOR_PASS, alpha=0.7),
            color='white')
    
    # Panel D: Null direction response
    ax4 = fig.add_subplot(gs[1, 1])
    
    # Null: inhibition arrives first (5× weight), suppresses later excitation
    exc_null = 0.8 * np.exp(-(time_response - 40)**2 / 100)
    inh_null = 5.0 * 0.3 * np.exp(-(time_response - 20)**2 / 150)  # 5× weight!
    output_null = np.maximum(0, exc_null - inh_null)
    
    ax4.plot(time_response, exc_null, '--', color='#4CAF50', linewidth=2,
            label='Excitation', alpha=0.7)
    ax4.plot(time_response, inh_null, '--', color='#F44336', linewidth=2,
            label='Inhibition (5×)', alpha=0.7)
    ax4.plot(time_response, output_null, color='black', linewidth=3,
            label='T4 Output = max(0, E - I)')
    ax4.fill_between(time_response, 0, output_null, alpha=0.3, color='#FFCCBC')
    
    ax4.set_xlabel('Time (ms)', fontweight='bold')
    ax4.set_ylabel('T4 Response', fontweight='bold')
    ax4.set_title('D. Null Direction: Suppressed Output\n(Inhibition leads, 5× weight)',
                 fontweight='bold')
    ax4.legend(loc='upper right')
    ax4.set_xlim(0, 100)
    ax4.set_ylim(-0.2, 1.2)
    ax4.grid(alpha=0.3)
    ax4.spines['top'].set_visible(False)
    ax4.spines['right'].set_visible(False)
    
    # Highlight suppression
    ax4.text(50, 0.9, '✓ Suppressed (93.9%)\nMean = 0.073', ha='center',
            fontsize=9, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor=COLOR_FAIL, alpha=0.7),
            color='white')
    
    # Panel E: Direction selectivity index
    ax5 = fig.add_subplot(gs[2, :])
    
    # DSI values
    categories = ['Our Model', 'Biological\nTarget']
    dsi_values = [0.975, 0.30]
    colors_dsi = [COLOR_PRIMARY, '#999']
    
    bars = ax5.bar(categories, dsi_values, color=colors_dsi, alpha=0.8,
                   edgecolor='black', linewidth=2, width=0.4)
    
    # Target line
    ax5.axhline(0.30, color=COLOR_PASS, linestyle='--', linewidth=2,
               label='Biological Threshold', zorder=0)
    
    # Add value labels
    for i, (cat, val) in enumerate(zip(categories, dsi_values)):
        ax5.text(i, val + 0.05, f'{val:.3f}', ha='center', va='bottom',
                fontsize=12, fontweight='bold')
    
    ax5.set_ylabel('Direction Selectivity Index (DSI)', fontweight='bold')
    ax5.set_title('E. Direction Selectivity Performance\n'
                 'DSI = (Pref - Null) / (Pref + Null) = 0.975 (325% of target)',
                 fontweight='bold', fontsize=11)
    ax5.set_ylim(0, 1.1)
    ax5.legend(loc='upper right')
    ax5.grid(axis='y', alpha=0.3)
    ax5.spines['top'].set_visible(False)
    ax5.spines['right'].set_visible(False)
    
    # Pass badge
    ax5.text(0, 1.0, '✓ PASS\n(3.25× target)', ha='center', va='top',
            fontsize=11, fontweight='bold', color='white',
            bbox=dict(boxstyle='round,pad=0.6', facecolor=COLOR_PASS, alpha=0.9))
    
    # Mechanism summary
    fig.text(0.5, 0.01,
            'Barlow-Levick AND-NOT gate: Fast excitation (ACh, τ=10ms) + '
            'Slow inhibition (GABA, 5× weight, τ=25ms) → 93.9% null suppression',
            ha='center', va='bottom', fontsize=9, style='italic', color='#333')
    
    return fig

def main():
    """Generate all vision figures"""
    output_dir = Path(__file__).parent.parent / 'publication' / 'figures'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Generating vision validation figures...")
    
    # Figure 1: Sparse Coding
    print("  - Figure 1: Sparse Coding (4 layers)")
    fig1 = create_figure_1_sparse_coding()
    fig1.savefig(output_dir / 'supp_figure_vision_sparse_coding.png', 
                dpi=300, bbox_inches='tight')
    plt.close(fig1)
    
    # Figure 2: Contrast Invariance
    print("  - Figure 2: Contrast Invariance")
    fig2 = create_figure_2_contrast_invariance()
    fig2.savefig(output_dir / 'supp_figure_vision_contrast_invariance.png',
                dpi=300, bbox_inches='tight')
    plt.close(fig2)
    
    # Figure 3: Chromatic Decorrelation
    print("  - Figure 3: Chromatic Decorrelation")
    fig3 = create_figure_3_chromatic_decorrelation()
    fig3.savefig(output_dir / 'supp_figure_vision_chromatic_decorrelation.png',
                dpi=300, bbox_inches='tight')
    plt.close(fig3)
    
    # Figure 4: Motion Detection
    print("  - Figure 4: Motion Detection")
    fig4 = create_figure_4_motion_detection()
    fig4.savefig(output_dir / 'supp_figure_vision_motion_detection.png',
                dpi=300, bbox_inches='tight')
    plt.close(fig4)
    
    print(f"\n✓ All 4 vision figures saved to {output_dir}/")
    print("\nGenerated figures:")
    print("  1. supp_figure_vision_sparse_coding.png")
    print("  2. supp_figure_vision_contrast_invariance.png")
    print("  3. supp_figure_vision_chromatic_decorrelation.png")
    print("  4. supp_figure_vision_motion_detection.png")

if __name__ == '__main__':
    main()
