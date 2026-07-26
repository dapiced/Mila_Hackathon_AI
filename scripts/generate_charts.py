#!/usr/bin/env python3
"""Generate charts for the presentation."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

OUTPUT_DIR = "/home/dom/Documents/mila-hack/team_021/docs/images"

# Style
plt.rcParams['figure.facecolor'] = '#1a1a2e'
plt.rcParams['axes.facecolor'] = '#1a1a2e'
plt.rcParams['text.color'] = 'white'
plt.rcParams['axes.labelcolor'] = 'white'
plt.rcParams['xtick.color'] = 'white'
plt.rcParams['ytick.color'] = 'white'
plt.rcParams['font.size'] = 14

# ============================================================
# CHART 1: Performance Evolution
# ============================================================
fig, ax = plt.subplots(figsize=(12, 6))

milestones = ['mBERT\nonly', '+ Mistral\nfusion', '+ Prompt\ntweak', '+ Gate 12\nOVERRIDE']
f1_scores = [0.818, 0.872, 0.874, 0.876]
precision = [0.806, 0.853, 0.843, 0.833]
recall = [0.831, 0.892, 0.908, 0.923]

x = np.arange(len(milestones))
width = 0.25

bars1 = ax.bar(x - width, f1_scores, width, label='F1 Score', color='#0096d6', edgecolor='white', linewidth=0.5)
bars2 = ax.bar(x, precision, width, label='Precision', color='#4CAF50', edgecolor='white', linewidth=0.5)
bars3 = ax.bar(x + width, recall, width, label='Recall', color='#FF9800', edgecolor='white', linewidth=0.5)

# Add value labels on bars
for bars in [bars1, bars2, bars3]:
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.3f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=11, color='white', fontweight='bold')

ax.set_ylabel('Score', fontsize=16)
ax.set_title('Performance Evolution — From Baseline to Final System', fontsize=20, fontweight='bold', color='#0096d6')
ax.set_xticks(x)
ax.set_xticklabels(milestones, fontsize=13)
ax.set_ylim(0.75, 0.96)
ax.legend(loc='lower right', fontsize=13, facecolor='#2a2a4a', edgecolor='white')
ax.grid(axis='y', alpha=0.2, color='white')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('white')
ax.spines['bottom'].set_color('white')

# Add arrow showing improvement
ax.annotate('', xy=(3, 0.876), xytext=(0, 0.818),
            arrowprops=dict(arrowstyle='->', color='#FF5252', lw=2))
ax.text(1.5, 0.78, '+0.058 F1', fontsize=16, color='#FF5252', fontweight='bold', ha='center')

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/chart_performance_evolution.png', dpi=150, bbox_inches='tight')
print("Chart 1 saved: chart_performance_evolution.png")
plt.close()

# ============================================================
# CHART 2: Red Team Failures (Horizontal Bar)
# ============================================================
fig, ax = plt.subplots(figsize=(12, 7))

categories = [
    'Prompt Injection',
    'Indirect & Veiled Signals',
    'Very Young Users (5-12)',
    'Negation & Third-Party',
    'Youth Slang & Emoji',
    'Cultural & Linguistic'
]
missed = [6, 6, 7, 8, 9, 12]
total = [6, 7, 7, 9, 13, 15]
caught = [t - m for t, m in zip(total, missed)]

y = np.arange(len(categories))
height = 0.6

# Stacked horizontal bars
bars_missed = ax.barh(y, missed, height, label='Missed (no crisis resources)', color='#F44336', edgecolor='white', linewidth=0.5)
bars_caught = ax.barh(y, caught, height, left=missed, label='Caught', color='#4CAF50', edgecolor='white', linewidth=0.5)

# Add labels
for i, (m, t) in enumerate(zip(missed, total)):
    ax.text(t + 0.3, i, f'{m}/{t}', va='center', fontsize=13, color='white', fontweight='bold')
    pct = m / t * 100
    ax.text(m / 2, i, f'{pct:.0f}%', va='center', ha='center', fontsize=12, color='white', fontweight='bold')

ax.set_xlabel('Number of Test Cases', fontsize=16)
ax.set_title('KHP Chatbot Failure Patterns — Red Mission v3 (461 tests)', fontsize=20, fontweight='bold', color='#0096d6')
ax.set_yticks(y)
ax.set_yticklabels(categories, fontsize=13)
ax.legend(loc='lower right', fontsize=13, facecolor='#2a2a4a', edgecolor='white')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('white')
ax.spines['bottom'].set_color('white')
ax.set_xlim(0, 18)

# Overall stat
ax.text(9, -1, '319/411 CRITICAL+HIGH cases got NO crisis resources (77.6% failure rate)',
        fontsize=13, color='#FF9800', ha='center', fontweight='bold')

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/chart_redteam_failures.png', dpi=150, bbox_inches='tight')
print("Chart 2 saved: chart_redteam_failures.png")
plt.close()

# ============================================================
# CHART 3: Experiments Scatter (bonus)
# ============================================================
fig, ax = plt.subplots(figsize=(12, 7))

# All experiments (approximate P, R values)
experiments = {
    'mBERT only': (0.806, 0.831, 0.818, 'o'),
    'Mistral only': (0.821, 0.846, 0.833, 's'),
    'Cohere only': (0.847, 0.769, 0.806, 's'),
    'GPT-OSS only': (0.867, 0.800, 0.832, 's'),
    'Full prompt rewrite': (0.782, 0.938, 0.853, '^'),
    'Weight flip 0.6/0.4': (0.812, 0.862, 0.836, '^'),
    'Threshold 0.48': (0.819, 0.908, 0.861, '^'),
    'Threshold 0.46': (0.811, 0.923, 0.863, '^'),
    'mBERT v4 retrained': (0.838, 0.877, 0.857, 'D'),
    'mBERT v5 retrained': (0.792, 0.938, 0.859, 'D'),
    'Cohere fusion': (0.838, 0.877, 0.857, '^'),
    'Cascade': (0.814, 0.877, 0.844, '^'),
    'Gates 12+36+37+9': (0.803, 0.938, 0.865, 'v'),
    'Decisive scoring': (0.822, 0.923, 0.870, '^'),
    'Taxonomy prompt': (0.811, 0.923, 0.863, '^'),
}

for name, (p, r, f1, marker) in experiments.items():
    color = '#666666'
    size = 60
    ax.scatter(p, r, c=color, s=size, marker=marker, alpha=0.6, edgecolors='white', linewidth=0.5)

# Highlight key points
ax.scatter(0.853, 0.892, c='#FF9800', s=200, marker='*', edgecolors='white', linewidth=1, zorder=5, label='Baseline fusion (0.872)')
ax.scatter(0.833, 0.923, c='#4CAF50', s=300, marker='*', edgecolors='white', linewidth=1.5, zorder=5, label='FINAL (0.876)')

# Add F1 contour lines
for f1_val in [0.80, 0.85, 0.90]:
    p_range = np.linspace(0.70, 1.0, 100)
    r_from_f1 = (f1_val * p_range) / (2 * p_range - f1_val)
    mask = (r_from_f1 > 0) & (r_from_f1 <= 1)
    ax.plot(p_range[mask], r_from_f1[mask], '--', color='white', alpha=0.2, linewidth=1)
    # Label
    idx = np.argmin(np.abs(p_range[mask] - 0.95))
    if idx < len(r_from_f1[mask]):
        ax.text(0.95, r_from_f1[mask][idx], f'F1={f1_val}', fontsize=10, color='white', alpha=0.4)

ax.set_xlabel('Precision', fontsize=16)
ax.set_ylabel('Recall', fontsize=16)
ax.set_title('30+ Experiments — Precision vs Recall Trade-off', fontsize=20, fontweight='bold', color='#0096d6')
ax.set_xlim(0.75, 1.0)
ax.set_ylim(0.75, 1.0)
ax.legend(loc='lower left', fontsize=13, facecolor='#2a2a4a', edgecolor='white')
ax.grid(alpha=0.15, color='white')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('white')
ax.spines['bottom'].set_color('white')

plt.tight_layout()
plt.savefig(f'{OUTPUT_DIR}/chart_experiments_scatter.png', dpi=150, bbox_inches='tight')
print("Chart 3 saved: chart_experiments_scatter.png")
plt.close()

print("\nAll charts generated!")
