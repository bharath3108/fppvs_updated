"""Performance metrics from Section 5."""
from math import log
def jains_fairness(values):
    values=list(values); return (sum(values)**2/(len(values)*sum(x*x for x in values))) if values and sum(x*x for x in values) else 0.0
def alpha_utility(values, delta=1.0):
    values=[max(float(x),1e-12) for x in values]
    return sum(log(x) if delta == 1 else x**(1-delta)/(1-delta) for x in values)/len(values) if values else 0.0
