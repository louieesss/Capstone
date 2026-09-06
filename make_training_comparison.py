import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

methods = ['Current main trainer', 'High-accuracy trainer']
val_acc = [82.6, 88.0]
time_min = [60, 120]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

ax1.bar(methods, val_acc, color=['#4C78A8', '#54A24B'], width=0.6)
ax1.set_title('Validation Accuracy Comparison')
ax1.set_ylabel('Accuracy (%)')
ax1.set_ylim(0, 100)
for i, v in enumerate(val_acc):
    ax1.text(i, v + 2, f'{v}%', ha='center', va='bottom', fontsize=10, fontweight='bold')

ax2.bar(methods, time_min, color=['#E45756', '#F58518'], width=0.6)
ax2.set_title('Estimated Training Time')
ax2.set_ylabel('Minutes')
for i, v in enumerate(time_min):
    ax2.text(i, v + 5, f'{v} min', ha='center', va='bottom', fontsize=10, fontweight='bold')

fig.suptitle('Training Dataset Comparison for Pollination Model', fontsize=16, fontweight='bold')
plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig('training_comparison.png', dpi=200)
print('Saved training_comparison.png')
