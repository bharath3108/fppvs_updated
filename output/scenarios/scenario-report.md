# FPPVS scenario results (synthetic)

Hold-out acceptance, mean ± std over seeds. Load = offered compute demand ÷ total DC capacity.
Training: 4 federated agents × 10 rounds × 50 episodes; 600 training / 600 hold-out requests per stream.

## Acceptance (%)

| Scenario | Updated FPPVS (ours) | Prior only (no DRL) | Original FPPVS | 2022 adaptation | Greedy | Random |
|---|---|---|---|---|---|---|
| Backbone load 0.5 (light load) | 99.6 ± 0.4 | 99.7 ± 0.3 | 91.2 ± 2.3 | 68.1 ± 5.4 | 72.1 ± 5.8 | 73.2 ± 4.5 |
| Backbone load 0.9 | 91.0 ± 3.6 | 91.9 ± 3.1 | 77.0 ± 2.1 | 47.8 ± 7.6 | 58.7 ± 4.4 | 57.4 ± 4.0 |
| Backbone load 1 | 86.4 ± 3.7 | 86.3 ± 2.8 | 72.9 ± 2.4 | 44.5 ± 6.5 | 53.4 ± 5.1 | 55.3 ± 3.4 |
| Backbone load 1.1 | 80.8 ± 3.8 | 80.9 ± 3.0 | 67.7 ± 3.1 | 43.0 ± 10.4 | 51.9 ± 4.9 | 52.9 ± 3.3 |
| Backbone load 1.25 (overload) | 75.2 ± 2.9 | 73.4 ± 3.0 | 65.5 ± 2.7 | 41.1 ± 3.0 | 49.3 ± 3.8 | 50.9 ± 2.7 |
| Backbone load 1.5 (overload) | 65.2 ± 3.3 | 65.6 ± 2.7 | 58.2 ± 3.2 | 38.4 ± 4.3 | 43.4 ± 4.1 | 44.2 ± 2.1 |
| Metro load 0.5 (light load) | 99.0 ± 0.8 | 99.0 ± 0.6 | 89.2 ± 3.7 | 74.0 ± 9.7 | 71.4 ± 3.0 | 72.1 ± 2.9 |
| Metro load 0.9 | 86.1 ± 2.9 | 86.1 ± 3.1 | 73.6 ± 3.6 | 53.1 ± 9.3 | 56.3 ± 3.1 | 56.6 ± 3.0 |
| Metro load 1 | 81.3 ± 3.5 | 81.7 ± 3.2 | 69.6 ± 3.6 | 49.4 ± 9.7 | 51.8 ± 3.6 | 52.6 ± 3.0 |
| Metro load 1.1 | 76.6 ± 2.5 | 76.4 ± 2.9 | 65.6 ± 3.2 | 50.1 ± 5.2 | 48.8 ± 1.9 | 50.9 ± 3.1 |
| Metro load 1.25 (overload) | 69.2 ± 4.2 | 70.1 ± 3.2 | 61.1 ± 3.7 | 40.5 ± 7.8 | 47.2 ± 2.1 | 46.9 ± 2.3 |
| Metro load 1.5 (overload) | 60.6 ± 1.9 | 61.1 ± 2.8 | 53.3 ± 5.2 | 42.2 ± 3.9 | 42.2 ± 2.7 | 43.1 ± 1.3 |

## Resources per running SFC and per accepted SFC (lower is better)

| Scenario | Method | Compute/SFC | Bandwidth/SFC | Compute·time per accepted | Bandwidth·time per accepted | Instances per accepted | Latency | Decision ms |
|---|---|---|---|---|---|---|---|---|
| Backbone 0.9 | Updated FPPVS (ours) | 5.42 | 53.8 | 5429 | 53978 | 0.57 | 46.5 | 11.5 |
| Backbone 0.9 | Original FPPVS | 5.39 | 63.7 | 5323 | 62911 | 0.78 | 56.0 | 28.0 |
| Backbone 0.9 | 2022 adaptation | 5.23 | 58.4 | 5374 | 59977 | 0.59 | 66.2 | 4.5 |
| Backbone 0.9 | Greedy | 6.29 | 109.6 | 6308 | 109806 | 6.66 | 107.8 | 2.8 |
| Backbone 0.9 | Random | 6.22 | 110.7 | 6399 | 113978 | 6.57 | 108.8 | 2.7 |
| Backbone 1 | Updated FPPVS (ours) | 5.39 | 56.2 | 5418 | 56537 | 0.53 | 50.0 | 12.1 |
| Backbone 1 | Original FPPVS | 5.35 | 62.3 | 5400 | 62896 | 0.73 | 56.2 | 27.9 |
| Backbone 1 | 2022 adaptation | 5.19 | 56.5 | 5282 | 57413 | 0.61 | 67.2 | 4.4 |
| Backbone 1 | Greedy | 6.19 | 111.2 | 6397 | 115051 | 6.58 | 107.7 | 2.8 |
| Backbone 1 | Random | 6.24 | 109.4 | 6275 | 110073 | 6.58 | 108.1 | 2.6 |
| Backbone 1.1 | Updated FPPVS (ours) | 5.39 | 59.6 | 5402 | 59873 | 0.52 | 53.2 | 12.5 |
| Backbone 1.1 | Original FPPVS | 5.33 | 61.7 | 5366 | 62188 | 0.74 | 54.7 | 23.7 |
| Backbone 1.1 | 2022 adaptation | 5.15 | 57.0 | 5257 | 58160 | 0.63 | 70.2 | 4.5 |
| Backbone 1.1 | Greedy | 6.21 | 109.9 | 6298 | 111506 | 6.59 | 107.4 | 2.8 |
| Backbone 1.1 | Random | 6.23 | 106.7 | 6243 | 106956 | 6.56 | 108.8 | 2.7 |
| Metro 0.9 | Updated FPPVS (ours) | 5.38 | 51.1 | 5499 | 52280 | 0.55 | 45.8 | 9.4 |
| Metro 0.9 | Original FPPVS | 5.35 | 60.0 | 5442 | 61129 | 0.74 | 54.5 | 19.5 |
| Metro 0.9 | 2022 adaptation | 5.17 | 51.8 | 5279 | 53122 | 0.67 | 65.5 | 3.6 |
| Metro 0.9 | Greedy | 6.15 | 102.2 | 6270 | 104561 | 6.56 | 105.2 | 2.0 |
| Metro 0.9 | Random | 6.13 | 102.2 | 6219 | 103860 | 6.47 | 105.9 | 1.9 |
| Metro 1 | Updated FPPVS (ours) | 5.35 | 51.6 | 5436 | 52519 | 0.55 | 48.6 | 10.2 |
| Metro 1 | Original FPPVS | 5.28 | 58.7 | 5463 | 60730 | 0.71 | 54.1 | 16.8 |
| Metro 1 | 2022 adaptation | 5.11 | 52.0 | 5350 | 54417 | 0.62 | 67.2 | 3.6 |
| Metro 1 | Greedy | 6.15 | 99.4 | 6460 | 104410 | 6.53 | 104.1 | 2.0 |
| Metro 1 | Random | 6.16 | 101.9 | 6377 | 105585 | 6.51 | 105.2 | 2.0 |
| Metro 1.1 | Updated FPPVS (ours) | 5.33 | 52.6 | 5429 | 53567 | 0.51 | 50.2 | 10.2 |
| Metro 1.1 | Original FPPVS | 5.28 | 58.3 | 5366 | 59312 | 0.71 | 54.2 | 16.8 |
| Metro 1.1 | 2022 adaptation | 5.14 | 51.2 | 5324 | 53026 | 0.63 | 65.2 | 3.8 |
| Metro 1.1 | Greedy | 6.12 | 100.5 | 6335 | 104076 | 6.52 | 105.0 | 2.0 |
| Metro 1.1 | Random | 6.03 | 97.6 | 6137 | 99429 | 6.41 | 104.0 | 2.0 |
