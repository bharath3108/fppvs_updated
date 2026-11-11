# FPPVS scenario results (synthetic)

Hold-out acceptance, mean ± std over seeds. Load = offered compute demand ÷ total DC capacity.
Training: 4 federated agents × 10 rounds × 50 episodes; 600 training / 600 hold-out requests per stream.

## Acceptance (%)

| Scenario | Updated FPPVS (ours) | FPPVS w/o sharing | FPPVS w/o fairness | FPPVS single agent | FPPVS w/o retry | Prior only (no DRL) | Shortest-path + sharing | Shortest-path first-fit | Greedy | Random | Original FPPVS | 2022 adaptation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Backbone load 0.5 | 99.6 ± 0.4 | 99.0 ± 1.0 | 99.4 ± 0.6 | 99.4 ± 0.6 | 99.5 ± 0.4 | 99.7 ± 0.3 | 98.6 ± 1.9 | 97.5 ± 2.6 | 72.1 ± 5.8 | 73.2 ± 4.5 | 58.1 ± 4.1 | 68.1 ± 5.4 |
| Backbone load 0.75 | 97.2 ± 2.1 | 87.5 ± 3.0 | 97.0 ± 1.8 | 96.5 ± 2.2 | 96.7 ± 2.4 | 96.9 ± 2.2 | 94.1 ± 3.5 | 85.8 ± 3.2 | 62.6 ± 5.7 | 61.8 ± 3.8 | 50.1 ± 3.7 | 48.6 ± 15.3 |
| Backbone load 1 | 86.4 ± 3.7 | 73.8 ± 3.1 | 85.6 ± 3.9 | 86.0 ± 3.4 | 85.4 ± 3.1 | 86.3 ± 2.8 | 83.1 ± 4.3 | 71.2 ± 4.2 | 53.4 ± 5.1 | 55.3 ± 3.4 | 43.6 ± 5.1 | 44.5 ± 6.5 |
| Backbone load 1.25 (overload) | 75.2 ± 2.9 | — | — | — | — | 73.4 ± 3.0 | 72.6 ± 2.9 | 61.8 ± 2.3 | 49.3 ± 3.8 | 50.9 ± 2.7 | 38.7 ± 3.9 | 41.1 ± 3.0 |
| Backbone load 1.5 (overload) | 65.2 ± 3.3 | — | — | — | — | 65.6 ± 2.7 | 65.1 ± 3.5 | 54.3 ± 2.0 | 43.4 ± 4.1 | 44.2 ± 2.1 | 35.0 ± 4.2 | 38.4 ± 4.3 |
| Metro load 0.5 | 99.0 ± 0.8 | 97.9 ± 1.1 | 99.1 ± 1.0 | 98.5 ± 1.3 | 98.8 ± 0.9 | 99.0 ± 0.6 | 97.6 ± 1.1 | 95.7 ± 1.1 | 71.4 ± 3.0 | 72.1 ± 2.9 | 64.6 ± 10.2 | 74.0 ± 9.7 |
| Metro load 0.75 | 93.0 ± 2.5 | 84.1 ± 2.3 | 93.4 ± 2.8 | 93.5 ± 3.2 | 93.5 ± 2.9 | 94.1 ± 2.2 | 88.8 ± 2.4 | 81.4 ± 2.1 | 59.5 ± 2.9 | 59.9 ± 2.3 | 58.5 ± 6.6 | 59.1 ± 5.3 |
| Metro load 1 | 81.3 ± 3.5 | 70.6 ± 3.2 | 81.1 ± 2.9 | 81.0 ± 3.2 | 81.9 ± 4.0 | 81.7 ± 3.2 | 78.5 ± 2.9 | 68.0 ± 2.8 | 51.8 ± 3.6 | 52.6 ± 3.0 | 49.7 ± 4.5 | 49.4 ± 9.7 |
| Metro load 1.25 (overload) | 69.2 ± 4.2 | — | — | — | — | 70.1 ± 3.2 | 68.5 ± 3.8 | 56.8 ± 3.4 | 47.2 ± 2.1 | 46.9 ± 2.3 | 44.0 ± 2.9 | 40.5 ± 7.8 |
| Metro load 1.5 (overload) | 60.6 ± 1.9 | — | — | — | — | 61.1 ± 2.8 | 58.2 ± 3.3 | 49.9 ± 3.3 | 42.2 ± 2.7 | 43.1 ± 1.3 | 36.7 ± 5.0 | 42.2 ± 3.9 |

## Resources per running SFC and per accepted SFC (lower is better)

| Scenario | Method | Compute/SFC | Bandwidth/SFC | Compute·time per accepted | Bandwidth·time per accepted | Instances per accepted | Latency | Decision ms |
|---|---|---|---|---|---|---|---|---|
| Backbone 0.5 | Updated FPPVS (ours) | 5.49 | 40.5 | 5491 | 40496 | 0.86 | 33.3 | 11.3 |
| Backbone 0.5 | Original FPPVS | 5.23 | 70.2 | 5260 | 70646 | 0.63 | 62.7 | 9.9 |
| Backbone 0.5 | 2022 adaptation | 5.31 | 57.6 | 5348 | 58001 | 0.60 | 64.7 | 4.1 |
| Backbone 0.5 | Greedy | 6.45 | 120.8 | 6456 | 120889 | 6.82 | 111.0 | 3.1 |
| Backbone 0.5 | Random | 6.44 | 122.0 | 6528 | 123677 | 6.77 | 111.6 | 2.9 |
| Backbone 0.75 | Updated FPPVS (ours) | 5.45 | 47.4 | 5429 | 47225 | 0.65 | 38.9 | 11.9 |
| Backbone 0.75 | Original FPPVS | 5.23 | 73.4 | 5303 | 74462 | 0.58 | 63.0 | 9.8 |
| Backbone 0.75 | 2022 adaptation | 5.11 | 58.7 | 5194 | 59755 | 0.62 | 68.1 | 4.2 |
| Backbone 0.75 | Greedy | 6.40 | 112.3 | 6496 | 114084 | 6.75 | 109.0 | 2.9 |
| Backbone 0.75 | Random | 6.31 | 115.9 | 6378 | 117266 | 6.64 | 109.8 | 2.8 |
| Backbone 1 | Updated FPPVS (ours) | 5.39 | 56.2 | 5418 | 56537 | 0.53 | 50.0 | 12.2 |
| Backbone 1 | Original FPPVS | 5.16 | 70.2 | 5204 | 70843 | 0.59 | 64.2 | 10.9 |
| Backbone 1 | 2022 adaptation | 5.19 | 56.5 | 5282 | 57413 | 0.61 | 67.2 | 4.4 |
| Backbone 1 | Greedy | 6.19 | 111.2 | 6397 | 115051 | 6.58 | 107.7 | 2.9 |
| Backbone 1 | Random | 6.24 | 109.4 | 6275 | 110073 | 6.58 | 108.1 | 3.1 |
| Metro 0.5 | Updated FPPVS (ours) | 5.46 | 41.0 | 5573 | 41874 | 0.85 | 33.7 | 8.9 |
| Metro 0.5 | Original FPPVS | 5.28 | 65.8 | 5313 | 66343 | 0.70 | 56.7 | 9.0 |
| Metro 0.5 | 2022 adaptation | 5.30 | 52.9 | 5396 | 53831 | 0.69 | 64.2 | 3.5 |
| Metro 0.5 | Greedy | 6.41 | 112.2 | 6436 | 112672 | 6.76 | 109.2 | 2.5 |
| Metro 0.5 | Random | 6.35 | 112.3 | 6503 | 115098 | 6.67 | 109.3 | 2.3 |
| Metro 0.75 | Updated FPPVS (ours) | 5.40 | 48.2 | 5524 | 49417 | 0.65 | 40.8 | 21.0 |
| Metro 0.75 | Original FPPVS | 5.27 | 67.9 | 5392 | 69528 | 0.65 | 62.5 | 7.9 |
| Metro 0.75 | 2022 adaptation | 5.23 | 55.0 | 5319 | 55939 | 0.63 | 67.4 | 3.6 |
| Metro 0.75 | Greedy | 6.25 | 104.5 | 6425 | 107605 | 6.63 | 105.8 | 2.4 |
| Metro 0.75 | Random | 6.23 | 104.5 | 6524 | 109487 | 6.61 | 107.2 | 2.7 |
| Metro 1 | Updated FPPVS (ours) | 5.35 | 51.6 | 5436 | 52519 | 0.55 | 48.6 | 19.2 |
| Metro 1 | Original FPPVS | 5.21 | 64.3 | 5284 | 65437 | 0.67 | 62.2 | 8.1 |
| Metro 1 | 2022 adaptation | 5.11 | 52.0 | 5350 | 54417 | 0.62 | 67.2 | 3.5 |
| Metro 1 | Greedy | 6.15 | 99.4 | 6460 | 104410 | 6.53 | 104.1 | 2.3 |
| Metro 1 | Random | 6.16 | 101.9 | 6377 | 105585 | 6.51 | 105.2 | 2.2 |
