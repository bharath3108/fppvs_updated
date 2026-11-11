# Writing outline for the report (write each section in your own words)

Use this as notes. Each bullet is a fact you need to cover, not a sentence to copy.
Keep the LaTeX structure, figures and tables from `report.tex`; replace the prose.
Tip: split sections among the four of you, then have one person read the whole thing
once for consistency.

---

## Abstract (5-7 sentences)
- Paper studied: FPPVS (Zhu, Li, Rezaeipanah, Computer Networks 2026).
- What FPPVS combines: SFC parallelization, VNF sharing, fairness, federated DRL.
- Our first Python version: ~10% acceptance, worse than random (11.6%) and greedy (15.8%).
- What we changed (name 3-4 main ones): load-based Poisson arrivals, look-ahead mask,
  per-DC actor + prior, honest sharing model, retry admission.
- Result: 81.3-99.6% acceptance on both topologies at loads up to 1.0; less bandwidth per SFC.
- Plus: comparison with original FPPVS on the same scenarios (Section 6, part F).

## 1. Introduction
### 1.1 Problem
- NFV: middleboxes (FW, IDS, DPI, LB, NAT) become software VNFs.
- SFC = ordered list of VNFs; in MEC they run on small edge DCs.
- Placement = choose a DC per VNF + routes; limits: compute, bandwidth, latency.
- NP-hard, online (requests arrive and leave over time).
### 1.2 Motivation
- Latency grows with chain length if packets go through VNFs one by one.
- Many requests compete for small DCs; greedy per-request choices hurt later requests.
- Prior work handles parallelism OR reuse; fairness mostly ignored.
### 1.3 Paper's contributions (4 points)
- Algorithm 1: shapers vs monitors; monitors move to parallel branches; dependency
  matrix says where branches rejoin; latency = critical path (see Fig. 2).
- VNF sharing + SQN-LSTM demand forecasting.
- Fairness: alpha-fair utility, Jain's index.
- Federated actor-critic (CNN), FedAvg, adaptive epsilon-greedy.
- Paper reports 88.1% (backbone) and 75.9% (metro) acceptance.

## 2. Limitations (L1-L7) - say each in 2-3 sentences
- L1 arrival rate not given; 1 arrival/unit + lifetime 1000 means ~1000 active SFCs,
  network fits only ~70-100.
- L2 datasets, MATLAB code and baseline settings not public.
- L3 only compute is pruned; bandwidth/latency checked after the whole chain.
- L4 sharing capacity/release not defined; our first version overbooked (3x size, 1x reserved).
- L5 CNN + global pooling loses which column is which DC.
- L6 one request per episode; long-term effects invisible to the agent.
- L7 only utilization reported, not resources per served SFC over time.
- Table 1 (keep): which ones we addressed.
- Our own first-version bugs: missing class, crash on all-masked step, agents replaying
  the same 10 requests, shared ledger, state ignoring active requests -> 10.4%;
  diagnosis: 100% of rejections were link bandwidth.

## 3. System model and architecture
- Graph G=(V,E): DC capacity C_i, link latency L_ij, bandwidth B_ij; latency-shortest routes;
  same-DC traffic is free.
- Topologies: Backbone 24/47, Metro 17/29.
- Request fields: source, VNF list, destination, dependency matrix, arrival, TTL, rate, max latency.
- Supported request types: 5 VNF types; sequential, parallel-only and mixed chains; 4-10 VNFs.
- Output per request: accept/reject, DC per VNF, routes, latency split, resources, reuse info, reject reason.
- Explain Fig. 1 colours (blue = paper, orange = re-implemented, green = ours) and each block.
- Explain Fig. 2 example (IDS rejoins before NAT, DPI rejoins at destination).

## 4. Modified problem formulation
- Paper's objective (Eq. 1): weighted cost, latency, acceptance, utility.
- M1 offered load rho = lambda * 1000 * 4.9 / total capacity; loads 0.5/0.75/1.0 (+1.25, 1.5 stress).
- M2 instance overhead 0.25 per live instance; shared instance pays once, freed by last user (Eq. 3).
- M3 bandwidth per link on routed p-SFC edges (Eq. 4); latency = longest p-SFC path.
- M4 main objective still acceptance; second objective = resource-time per accepted SFC (Eq. 5).

## 5. Proposed approach
- One request = one episode; VNFs in topological order -> early routing possible.
- Walk through Algorithm 1 (ours) and Fig. 3 in your words.
- State: 9 rows per DC (Table 2) - say which 5 are ours.
- Mask: compute (+overhead), bandwidth on new links, latency lower bound; why it never
  removes a DC that could still work (triangle inequality).
- Prior (Eq. 6): short chains, few DCs, reuse, avoid full DCs/links.
- Network: 3 conv layers kept, 3x1 kernels; per-DC actor; learnable prior weight; critic as paper.
- Reward: +1 valid, -1 new instance, -10 reject, -0.2 per hop, final 5*(1+slack) + 5*dJFI;
  we dropped the +5 reuse bonus (prior already covers reuse).
- Training: A2C, adaptive epsilon + logit noise, 4 agents x 10 rounds x 50 episodes,
  weighted FedAvg; Table 3 hyperparameters.

## 6. Performance evaluation
- Setup: i5-12500H, 16 GB RAM, Windows 11, CPU only; Python 3.12, PyTorch 2.10, NetworkX 3.6.
- 5 seeds; per seed: new network, 4 training streams, 1 hold-out stream.
  Training: ~60 s per updated model, ~200-400 s per original model.
- Table 4 parameters (paper values + ours marked).
- Main scenarios = heavy load 0.9 / 1.0 / 1.1 (why: light load is too easy, any compact
  method gets ~99%); 0.5, 1.25, 1.5 shown in the load sweep.
- Metrics: acceptance, compute/bandwidth per running SFC, resource-time per accepted SFC,
  instances per accepted, latency, decision time.
- Compared methods (5): Updated FPPVS (ours); Original FPPVS implemented closely from
  paper Sec. 4.3 (compute + bandwidth pruning, current/neighbour node, history signal,
  fixed-length CNN, Eq. 28 reward, federated, same budget); 2022 adaptation (Zhang et al.:
  sequential, reuse, TD=20 SQN-LSTM, actor-critic, rollback, LTCR reward; our
  implementation from the description); Greedy; Random. Greedy/random use our mask.
- A. Acceptance: Updated best everywhere; all six main scenarios > 70% (76.6-91.0%,
  mean 83.7, lowest seed 73.5%). Original clearly second: 65.6-77.0% (mean 71.1),
  beats 2022/greedy/random in all 30 main runs (15-18 points per scenario).
  2022 43.0-53.1% (mean 48.0, unstable, seed std up to 10). Greedy/random 49-59%.
  At rho=1: Updated 86.4/81.3, original 72.9/69.6, 2022 44.5/49.4. Metro harder.
- Load sweep: at 0.5 updated 99.6/99.0, original 91.2/89.2; at 1.25 updated 75.2/69.2,
  at 1.5 65.2/60.6; original 7-10 points lower; others <= 51%.
- B. Ablation: sharing matters most (-10 to -13 points); fairness/agents/retry ~1 point;
  prior-only ~ same as full -> gains come from problem changes, not RL (be honest).
- C. Resources: bandwidth per running SFC ~49% less than greedy/random, 11% less than
  original, about equal to 2022. Instances 0.51-0.57 per accepted: 27% fewer than
  original, 14% fewer than 2022, ~92% fewer than greedy/random. Compute: 13% less than
  greedy/random, ~equal to original, ~4% more than 2022. Latency 46-53 ms (updated),
  54-56 (original), 65-70 (2022), 104-108 (greedy/random). Decision 9-13 ms (updated),
  17-28 (original), 4-5 (2022), 2-3 (greedy/random).
- D. Old workload: updated placement 70.4% vs original implementation 10.4%.
- E. Learning methods: updated 11-14 points above original (main), 7-10 elsewhere;
  original 16-29 points above 2022. Original's rejections: 96-98% dead ends (no
  neighbour fits), 2-4% latency. 2022: 63-70% bandwidth / 30-37% latency, found at the end.
  Looser reading of the original (compute-only pruning, any DC, global pooling) got only
  41-50% -> following the paper closely matters.
  Paper's 88.1/75.9 vs our original run 72.9/69.6: close on Metro, ~15 lower on Backbone.
  Reasons: workload, data, training budget (~400k vs 2k placements), unstated details.
  Latency/utilization defined differently.

## Conclusion
- 2-3 sentences: what was wrong, what we changed.
- 2 sentences: results (acceptance + resources).
- Future work: real datasets, real baselines, multi-request episodes, VNF migration.
