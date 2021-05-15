from hdroller import Die
import numpy
import matplotlib as mpl
import matplotlib.pyplot as plt

figsize = (8, 4.5)
dpi = 120

def opposed_keep_highest(x, half_life=3):
    attack_ratio = numpy.power(0.5, x / half_life)
    ccdf = attack_ratio / (attack_ratio + 1.0)
    return Die.from_ccdf(ccdf, x[0])

left = -20
right = 20
x = numpy.arange(left * 2, right * 2+1)
okh = opposed_keep_highest(x)
laplace = Die.laplace(half_life=3)  - Die.coin(0.5)
opposed_simple = Die.d(10).explode(3) - Die.d(10).explode(3) - Die.coin(0.5)
exploding = Die.d(10).explode(3) + Die.d(1, 12)
opposed_exploding = exploding - exploding - Die.coin(0.5)

legend = [
    'Logistic, half-life = 3',
    'Opposed d10! + d12',
    'Laplace, half-life = 3',
    'Opposed d10!',
]

# ccdf

fig = plt.figure(figsize=figsize)
ax = plt.subplot(111)

ax.set_xlabel('Difference in modifiers')
ax.set_ylabel('Chance to hit (%)')
ax.grid()

ax.plot(okh.outcomes(), 100.0 * okh.ccdf())
ax.plot(opposed_exploding.outcomes(), 100.0 * opposed_exploding.ccdf())
ax.plot(laplace.outcomes(), 100.0 * laplace.ccdf())
ax.plot(opposed_simple.outcomes(), 100.0 * opposed_simple.ccdf())


ax.set_xlim(left=left, right=right)
ax.set_ylim(bottom=0.0,top=100.0)
ax.legend(legend, loc = 'upper right')
plt.savefig('output/opposed_keep_highest_ccdf.png', dpi = dpi, bbox_inches = "tight")

# pdf

fig = plt.figure(figsize=figsize)
ax = plt.subplot(111)

ax.set_xlabel('Difference in rolls')
ax.set_ylabel('Chance (%)')
ax.grid()

ax.plot(okh.outcomes() + 0.5, 100.0 * okh.pmf())
ax.plot(opposed_exploding.outcomes() + 0.5, 100.0 * opposed_exploding.pmf())
ax.plot(laplace.outcomes() + 0.5, 100.0 * laplace.pmf())
ax.plot(opposed_simple.outcomes() + 0.5, 100.0 * opposed_simple.pmf())


ax.set_xlim(left=left, right=right)
ax.set_ylim(bottom=0.0)
ax.legend(legend, loc = 'upper right')
plt.savefig('output/opposed_keep_highest_pmf.png', dpi = dpi, bbox_inches = "tight")