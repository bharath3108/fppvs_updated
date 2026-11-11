# FPPVS scenario results (synthetic)

Hold-out acceptance, mean ± std over seeds. Load = offered compute demand ÷ total DC capacity.
Training: 4 federated agents × 10 rounds × 50 episodes; 600 training / 600 hold-out requests per stream.

## Acceptance (%)

| Scenario | Updated FPPVS (ours) | Prior only (no DRL) | Original FPPVS | 2022 adaptation | Shortest-path + sharing | Shortest-path first-fit | Greedy | Random |
|---|---|---|---|---|---|---|---|---|
| Backbone load 0.5 (light load) | 99.6 ± 0.4 | 99.7 ± 0.3 | 58.1 ± 4.1 | 68.1 ± 5.4 | 98.6 ± 1.9 | 97.5 ± 2.6 | 72.1 ± 5.8 | 73.2 ± 4.5 |
| Backbone load 0.9 | 91.0 ± 3.6 | 91.9 ± 3.1 | 45.0 ± 4.8 | 47.8 ± 7.6 | 86.8 ± 2.7 | 77.3 ± 3.3 | 58.7 ± 4.4 | 57.4 ± 4.0 |
| Backbone load 1 | 86.4 ± 3.7 | 86.3 ± 2.8 | 43.6 ± 5.1 | 44.5 ± 6.5 | 83.1 ± 4.3 | 71.2 ± 4.2 | 53.4 ± 5.1 | 55.3 ± 3.4 |
| Backbone load 1.1 | 80.8 ± 3.8 | 80.9 ± 3.0 | 40.9 ± 5.3 | 43.0 ± 10.4 | 77.5 ± 4.4 | 66.6 ± 3.7 | 51.9 ± 4.9 | 52.9 ± 3.3 |
| Backbone load 1.25 (overload) | 75.2 ± 2.9 | 73.4 ± 3.0 | 38.7 ± 3.9 | 41.1 ± 3.0 | 72.6 ± 2.9 | 61.8 ± 2.3 | 49.3 ± 3.8 | 50.9 ± 2.7 |
| Backbone load 1.5 (overload) | 65.2 ± 3.3 | 65.6 ± 2.7 | 35.0 ± 4.2 | 38.4 ± 4.3 | 65.1 ± 3.5 | 54.3 ± 2.0 | 43.4 ± 4.1 | 44.2 ± 2.1 |
| Metro load 0.5 (light load) | 99.0 ± 0.8 | 99.0 ± 0.6 | 64.6 ± 10.2 | 74.0 ± 9.7 | 97.6 ± 1.1 | 95.7 ± 1.1 | 71.4 ± 3.0 | 72.1 ± 2.9 |
| Metro load 0.9 | 86.1 ± 2.9 | 86.1 ± 3.1 | 50.2 ± 5.8 | 53.1 ± 9.3 | 82.8 ± 3.1 | 72.8 ± 2.4 | 56.3 ± 3.1 | 56.6 ± 3.0 |
| Metro load 1 | 81.3 ± 3.5 | 81.7 ± 3.2 | 49.7 ± 4.5 | 49.4 ± 9.7 | 78.5 ± 2.9 | 68.0 ± 2.8 | 51.8 ± 3.6 | 52.6 ± 3.0 |
| Metro load 1.1 | 76.6 ± 2.5 | 76.4 ± 2.9 | 47.2 ± 5.0 | 50.1 ± 5.2 | 73.8 ± 3.9 | 63.9 ± 2.5 | 48.8 ± 1.9 | 50.9 ± 3.1 |
| Metro load 1.25 (overload) | 69.2 ± 4.2 | 70.1 ± 3.2 | 44.0 ± 2.9 | 40.5 ± 7.8 | 68.5 ± 3.8 | 56.8 ± 3.4 | 47.2 ± 2.1 | 46.9 ± 2.3 |
| Metro load 1.5 (overload) | 60.6 ± 1.9 | 61.1 ± 2.8 | 36.7 ± 5.0 | 42.2 ± 3.9 | 58.2 ± 3.3 | 49.9 ± 3.3 | 42.2 ± 2.7 | 43.1 ± 1.3 |

## Resources per running SFC and per accepted SFC (lower is better)

| Scenario | Method | Compute/SFC | Bandwidth/SFC | Compute·time per accepted | Bandwidth·time per accepted | Instances per accepted | Latency | Decision ms |
|---|---|---|---|---|---|---|---|---|
| Backbone 0.9 | Updated FPPVS (ours) | 5.42 | 53.8 | 5429 | 53978 | 0.57 | 46.5 | 11.5 |
| Backbone 0.9 | Original FPPVS | 5.14 | 71.2 | 5081 | 70533 | 0.59 | 65.6 | 9.1 |
| Backbone 0.9 | 2022 adaptation | 5.23 | 58.4 | 5374 | 59977 | 0.59 | 66.2 | 4.5 |
| Backbone 0.9 | Greedy | 6.29 | 109.6 | 6308 | 109806 | 6.66 | 107.8 | 2.8 |
| Backbone 0.9 | Random | 6.22 | 110.7 | 6399 | 113978 | 6.57 | 108.8 | 2.7 |
| Backbone 1 | Updated FPPVS (ours) | 5.39 | 56.2 | 5418 | 56537 | 0.53 | 50.0 | 12.1 |
| Backbone 1 | Original FPPVS | 5.16 | 70.2 | 5204 | 70843 | 0.59 | 64.2 | 9.4 |
| Backbone 1 | 2022 adaptation | 5.19 | 56.5 | 5282 | 57413 | 0.61 | 67.2 | 4.4 |
| Backbone 1 | Greedy | 6.19 | 111.2 | 6397 | 115051 | 6.58 | 107.7 | 2.8 |
| Backbone 1 | Random | 6.24 | 109.4 | 6275 | 110073 | 6.58 | 108.1 | 2.6 |
| Backbone 1.1 | Updated FPPVS (ours) | 5.39 | 59.6 | 5402 | 59873 | 0.52 | 53.2 | 12.5 |
| Backbone 1.1 | Original FPPVS | 5.16 | 66.9 | 5169 | 67064 | 0.63 | 63.6 | 9.0 |
| Backbone 1.1 | 2022 adaptation | 5.15 | 57.0 | 5257 | 58160 | 0.63 | 70.2 | 4.5 |
| Backbone 1.1 | Greedy | 6.21 | 109.9 | 6298 | 111506 | 6.59 | 107.4 | 2.8 |
| Backbone 1.1 | Random | 6.23 | 106.7 | 6243 | 106956 | 6.56 | 108.8 | 2.7 |
| Metro 0.9 | Updated FPPVS (ours) | 5.38 | 51.1 | 5499 | 52280 | 0.55 | 45.8 | 9.4 |
| Metro 0.9 | Original FPPVS | 5.24 | 65.5 | 5417 | 67796 | 0.64 | 62.0 | 7.8 |
| Metro 0.9 | 2022 adaptation | 5.17 | 51.8 | 5279 | 53122 | 0.67 | 65.5 | 3.6 |
| Metro 0.9 | Greedy | 6.15 | 102.2 | 6270 | 104561 | 6.56 | 105.2 | 2.0 |
| Metro 0.9 | Random | 6.13 | 102.2 | 6219 | 103860 | 6.47 | 105.9 | 1.9 |
| Metro 1 | Updated FPPVS (ours) | 5.35 | 51.6 | 5436 | 52519 | 0.55 | 48.6 | 10.2 |
| Metro 1 | Original FPPVS | 5.21 | 64.3 | 5284 | 65437 | 0.67 | 62.2 | 8.1 |
| Metro 1 | 2022 adaptation | 5.11 | 52.0 | 5350 | 54417 | 0.62 | 67.2 | 3.6 |
| Metro 1 | Greedy | 6.15 | 99.4 | 6460 | 104410 | 6.53 | 104.1 | 2.0 |
| Metro 1 | Random | 6.16 | 101.9 | 6377 | 105585 | 6.51 | 105.2 | 2.0 |
| Metro 1.1 | Updated FPPVS (ours) | 5.33 | 52.6 | 5429 | 53567 | 0.51 | 50.2 | 10.2 |
| Metro 1.1 | Original FPPVS | 5.13 | 64.1 | 5118 | 63964 | 0.62 | 62.4 | 8.0 |
| Metro 1.1 | 2022 adaptation | 5.14 | 51.2 | 5324 | 53026 | 0.63 | 65.2 | 3.8 |
| Metro 1.1 | Greedy | 6.12 | 100.5 | 6335 | 104076 | 6.52 | 105.0 | 2.0 |
| Metro 1.1 | Random | 6.03 | 97.6 | 6137 | 99429 | 6.41 | 104.0 | 2.0 |
