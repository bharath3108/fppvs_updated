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
| `tests/` | Unit tests |
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

## 1. Required software

| Software | Version used | Needed for |
|---|---|---|
| Python | 3.12.1 (3.11 or newer works) | experiments, tables, figures, tests |
| PyTorch | 2.10.0, CPU build (2.0 or newer) | neural networks and training |
| NetworkX | 3.6.1 (3.2 or newer) | network topologies and shortest paths |
| Matplotlib | 3.10.8 (3.8 or newer) | charts and report figures (installs NumPy, used 2.4.2) |
| pytest | 9.2.0 (8.0 or newer) | running the tests |
| Node.js + npm | Node 20.15.0 | building the slides |
| pptxgenjs | 3.12.0 (npm package) | building the slides |
| Tectonic **or** a LaTeX distribution (TeX Live / MiKTeX) **or** Overleaf | Tectonic 0.17.0 | compiling the report PDF |

The LaTeX report uses these packages (all included in TeX Live, MiKTeX and
Overleaf; Tectonic downloads them automatically on the first build):
geometry, fontenc, lmodern, amsmath, amssymb, graphicx, booktabs, tabularx,
array, float, needspace, caption, enumitem, xcolor, algorithm, algpseudocode,
hyperref.

A GPU is not needed. Everything runs on a CPU; the reported results were
produced on an Intel Core i5-12500H laptop with 16 GB RAM running Windows 11.

## 2. Installation

Run all commands from the project folder (the folder with this README).

Install the Python packages:

```bash
pip install torch networkx matplotlib pytest
```

For a smaller CPU-only PyTorch download you can install it from the PyTorch
CPU index instead:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

Install the slide builder's Node package (only needed to rebuild the slides):

```bash
cd presentation/build
npm install
```

To compile the report locally, install Tectonic (https://tectonic-typesetting.github.io)
or a LaTeX distribution. Alternatively, upload the whole `report/` folder to
Overleaf; it is self-contained.

No package installation of the project itself is needed: the scripts add the
project folder to Python's path, and the tests are run with `python -m pytest`.

## 3. Configuration

The experiments are configured with command-line options of
`scripts/run_scenarios.py`:

| Option | Default | Meaning |
|---|---|---|
| `--topologies` | `backbone metro` | Topologies to run |
| `--loads` | `0.9 1.0 1.1` | Main load levels (offered compute / total capacity) |
| `--stress-loads` | `0.5 1.25 1.5` | Extra load levels for the load sweep (fewer variants) |
| `--seeds` | `7 8 9` | Random seeds (the report uses `7 8 9 10 11`) |
| `--requests` | `600` | Requests per training stream and per hold-out stream |
| `--agents` | `4` | Federated agents |
| `--rounds` | `10` | FedAvg rounds |
| `--local-episodes` | `50` | Episodes per agent per round |
| `--workers` | `4` | Parallel worker processes |
| `--output` | `output/scenarios` | Output folder |
| `--replot` | off | Redraw charts and summary from an existing results file |
| `--merge-variants` | none | Re-run only the named methods and merge them into existing results |

Fixed model settings live in the code: training hyperparameters in
`TrainingConfig` (`fppvs/training.py`), experiment defaults in
`ExperimentConfig` (`fppvs/experiment.py`), the instance overhead in
`INSTANCE_OVERHEAD` (`fppvs/admission.py`) and the workload ranges in
`fppvs/workloads.py`.

## 4. Running the experiments

Full set of results used in the report (about 1 to 1.5 hours with 10 workers on
a 12-core laptop; use fewer workers on smaller machines):

```bash
python scripts/run_scenarios.py --seeds 7 8 9 10 11 --workers 10
```

The original-workload check (Table 9 of the report, under a minute):

```bash
python scripts/run_old_workload.py
```

A quick smoke test that finishes in a few minutes:

```bash
python scripts/run_scenarios.py --seeds 7 --requests 150 --rounds 1 --local-episodes 5 --workers 4 --output output/smoke
```

Results are written to `output/scenarios/`: `scenario-results.json` (all raw
numbers), `scenario-report.md` (summary tables), and the charts
`scenario-acceptance.png`, `scenario-resources.png` and `load-sweep.png`.

## 5. Building the report and slides

Generate the LaTeX tables and copy the charts, then draw the explanatory
figures:

```bash
python scripts/make_report_tables.py
```

```bash
python scripts/make_report_figures.py
```

Compile the report with Tectonic (or `pdflatex report.tex` twice with a LaTeX
distribution), from the `report/` folder:

```bash
cd report
tectonic -X compile report.tex
```

This produces `report/report.pdf`.

Rebuild the slides from the latest results, from the `presentation/build/`
folder:

```bash
cd presentation/build
node build_deck.js
```

This writes `presentation/FPPVS-final-presentation.pptx`.

## 6. Testing

Run the unit tests from the project folder:

```bash
python -m pytest
```

All 25 tests should pass in a few seconds. They cover Algorithm 1, the
placement evaluator, the resource ledger and sharing model, the feasibility
mask, the original-FPPVS neighbour rule, the network output shapes, FedAvg and
the SQN-LSTM queue.
