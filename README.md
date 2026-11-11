# Implementation Status

## Running the scenario experiments

```bash
python scripts/run_scenarios.py --seeds 7 8 9 10 11 --workers 8
```

This trains and evaluates FPPVS on every scenario (Backbone 24/47 and Metro
17/29 topologies × offered load 0.9 / 1.0 / 1.1 (main), plus 0.5 / 1.25 / 1.5 for the load sweep
) and writes `output/scenarios/`: `scenario-results.json`,
`scenario-report.md`, `scenario-acceptance.png`, `scenario-resources.png` and
`load-sweep.png`. Tests: `python -m pytest`.

Project report (LaTeX): `report/report.tex`. Regenerate its tables and figures
after a new run with `python scripts/make_report_tables.py` and
`python scripts/make_report_figures.py`. The `report/` folder is
self-contained, so it can be uploaded to Overleaf as-is. A second check,
`python scripts/run_old_workload.py`, runs the new placement on the original
one-arrival-per-time-unit workload.

## Why acceptance used to be ~10% and what changed

Diagnosis: on the old hold-out stream, 100% of rejections were link
bandwidth exhaustion. Causes and fixes:

1. **Workload exceeded physical capacity.** Requests arrived 1 per time unit
   but live ~1000 units, so ~1000 SFCs would need to be active at once in a
   network that physically fits ~70-100. Arrivals are now a Poisson process
   whose rate is set from a target *offered load* = offered compute demand ÷
   total DC capacity (`fppvs.experiment.arrival_rate_for_load`). The paper
   fixes the lifetime (mean 1000) but not the arrival rate. Traffic demand now
   follows the paper's power-law 5-30 distribution.
2. **The action mask only checked compute**, so the agent walked into
   placements that failed bandwidth/latency at the very end. The mask now
   prunes DCs that would exceed compute (including instance overhead),
   bandwidth on every newly routed virtual link, or the latency budget
   (critical path so far + shortest route to egress).
3. **The actor could not tell DCs apart**: it globally pooled the CNN features
   before a fixed linear layer, so it could only learn fixed DC preferences.
   The actor now scores each DC column with shared weights (3x1 convolutions
   along features; still 3 × 64-filter conv + BN layers, 256-unit FC + dropout
   in the critic), adds a learnable-weight placement prior (short chains, few
   DCs, reuse, avoid saturated links), and is DC-permutation-equivariant.
4. **State ignored the active reservations** (residual compute only reflected
   the current episode). It now uses the ledger, plus bandwidth margin, reuse
   availability, distance to egress and the mask.
5. **Federated training replayed the same first 10 requests every round** and
   all agents shared one ledger. Each agent now has its own request stream and
   ledger, continues through it across rounds, and FedAvg is
   experience-weighted.
6. **Sharing overbooked capacity**: shared instances were 3× demand but only
   1× was reserved. Now every instance costs a fixed overhead
   (`INSTANCE_OVERHEAD = 0.25`) plus the demand of each flow it serves, all
   counted against physical capacity; a shared instance pays the overhead once
   and is released when its last user expires.
7. **Rollback-and-retry admission**: if a placement dead-ends, nothing has been
   committed, so FPPVS retries with the next-best first DCs before rejecting.
8. Bugs: `SFCQueueMemory` was missing (package failed to import), training
   crashed on an all-masked step, and resource-time integration miscounted
   expiring requests.

Baselines (`fppvs/baselines.py`) are transparent stand-ins, not RVNF /
DRL-SFCP / PVFP / DPC re-implementations: random, greedy load-balancing and
shortest-path first-fit (run without sharing, as in the original code) plus
shortest-path with sharing as the strongest fair comparator. All run in the
identical environment and feasibility mask.

Resource metrics (lower is better): compute and bandwidth held per running
SFC, compute·time and bandwidth·time per accepted SFC, and instances started
per accepted SFC.

## Done

- Algorithm 1: sequential SFC to parallel DAG conversion.
- MEC topology, data-center capacity, and physical-link bandwidth/latency.
- Placement routing, capacity/QoS validation, and critical-path latency.
- Online admission control with persistent compute/link reservations and TTL
  release across sequential SFC requests.
- Capacity-aware VNF instance sharing.
- SQN request memory.
- LSTM demand-prediction model.
- CNN actor-critic model and FedAvg helper.
- SQN-LSTM request-demand forecasting connected to the placement state.
- Federated local-agent training with FedAvg, adaptive epsilon/logit-noise
  exploration, GPU/CPU selection, and model checkpoints.
- Fairness/utility metrics and unit tests.
- Reproducible synthetic scenario generator, placement environment, masked
  actor-critic training loop, greedy/random baselines, and experiment runner.

## What Works Now

- Generate a connected synthetic MEC topology and SFC requests using the
  paper's Section 5 parameter ranges.
- Train the CNN actor-critic placement policy on those synthetic requests,
  either as one local agent or as multiple federated agents.
- Compare its service-acceptance ratio with greedy and random placement.
- Enable/disable VNF sharing and fairness for synthetic ablations using
  `--no-sharing` and `--no-fairness`.
- Run several seeds using `--runs` and report a mean plus every per-run value.
- Save a JSON result file and learning plot at `output/synthetic-results.json`
  and `output/synthetic-learning.png`.
- Report mean, standard deviation, and 95% confidence-interval half-width
  across repeated synthetic runs.
- Evaluate trained FPPVS deterministically on a separate synthetic test stream;
  greedy and random baselines use that same resource-constrained stream.

## Maximum We Can Complete Now (Without the Missing Datasets)

- Run larger local/cloud training jobs, seed-based evaluation, plots, and
  statistical summaries.
- Install CUDA-enabled PyTorch to use an NVIDIA GPU; the current installed
  PyTorch build is CPU-only.
- Add dataset loaders and validation checks that are ready to use as soon as
  the exact topology and traffic files are obtained.

These tasks can make the implementation complete and well-tested on synthetic
data. They cannot establish the paper's exact numerical results.

## Remaining

- Exact USANet and Italian mobile-operator topology/traffic datasets
  (not publicly provided by the paper or its cited source).
- Exact reimplementations/results for RVNF, DRL-SFCP, PVFP, and DPC, which
  are intentionally deferred until baseline comparison is requested.
- Reproducing the paper's experiments and numerical results after those
  datasets and their baseline configurations are available.
