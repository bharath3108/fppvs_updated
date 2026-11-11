"""Fairness metric used in the reward (Jain's fairness index)."""


def jains_fairness(values):
    values = list(values)
    squares = sum(x * x for x in values)
    return (sum(values) ** 2 / (len(values) * squares)) if values and squares else 0.0
