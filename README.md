# FPPVS: implementation, limitations and modifications

Python implementation of FPPVS (Zhu, Li and Rezaeipanah, *Computer Networks*,
2026; `paper.pdf`), an updated version of it, and the experiments behind the
project report (`report/`) and slides (`presentation/`). All data is synthetic.

## Project layout

| Path | What it is |
|---|---|
| `fppvs/` | The library: substrate, request model, Algorithm 1, placement evaluation, resource ledger, environment, networks, training, baselines, experiment runner |
| `scripts/run_scenarios.py` | Runs every scenario and method, writes `output/scenarios/` (results JSON, charts, summary) |
| `scripts/run_old_workload.py` | Runs the updated placement on the original one-arrival-per-time-unit workload (report Table 9) |
| `scripts/make_report_tables.py` | Turns the results into the LaTeX tables in `report/tables/` and copies the charts |
| `scripts/make_report_figures.py` | Draws the architecture, p-SFC and placement-flow figures in `report/figures/` |
| `presentation/build/build_deck.js` | Builds `presentation/FPPVS-final-presentation.pptx` from the results |
| `tests/` | Unit tests (`python -m pytest`) |
| `output/fppvs-final-corrected.json` | Results of our first implementation (the 10.4% acceptance quoted in the report) |
| `backup/` | Earlier versions of the results, report and slides |

## Compared methods

All run in the same simulator, on the same networks and test requests:

- **Updated FPPVS (ours)**: look-ahead feasibility mask (compute, bandwidth,
  latency), per-DC actor with a learnable placement prior, instance-overhead
  sharing model, rollback-and-retry admission, federated actor-critic.
- **Original FPPVS**: implemented closely from Section 4.3 of the paper
  (compute and bandwidth pruning, current or neighbouring node, history signal,
  fixed-length CNN, Eq. 28 reward, federated training).
- **2022 adaptation** (Zhang et al., JKSUCIS 2022): sequential placement, VNF
  reuse, SQN-LSTM with TD = 20, actor-critic, rollback, LTCR reward.
- **Greedy** (most free compute) and **Random**, both using the feasibility mask.

Main scenarios: Backbone (24 DCs, 47 links) and Metro (17 DCs, 29 links) at
offered load 0.9, 1.0 and 1.1 (offered compute demand / total capacity), plus
0.5, 1.25 and 1.5 for the load sweep; 5 seeds each.

## Reproducing everything

```bash
python scripts/run_scenarios.py --seeds 7 8 9 10 11 --workers 8
```

```bash
python scripts/run_old_workload.py
```

```bash
python scripts/make_report_tables.py
```

```bash
python scripts/make_report_figures.py
```

Then compile `report/report.tex` (for example with Tectonic or on Overleaf; the
`report/` folder is self-contained) and rebuild the slides from
`presentation/build` with `node build_deck.js`.

To redraw the charts and summary from existing results without re-running:
`python scripts/run_scenarios.py --replot`. To add or re-run one method on all
existing runs: `python scripts/run_scenarios.py --merge-variants original`.

Requirements: Python 3.11+, PyTorch, NetworkX, Matplotlib (see
`pyproject.toml`); Node.js with `pptxgenjs` for the slides.
