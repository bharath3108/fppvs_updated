# Resume TODO (MAANG / Stripe target)

## Replace "Universal Sync" (Socket.io clipboard project)
Pick 1–2 (best: #1 or #2):
- [ ] Distributed KV store with Raft (Go/Rust/Java/C++): leader election, log replication, snapshots, fault-injection + consistency checker, benchmarks
- [ ] Stripe-style payments ledger: double-entry, idempotency keys, exactly-once webhooks, outbox pattern, reconciliation, concurrent-retry load test
- [ ] Distributed rate limiter / API gateway: token bucket + sliding window, Redis Lua, consistent hashing, benchmarks
- [ ] Mini database engine: B+Tree or LSM, WAL, buffer pool, crash recovery, basic SQL parser
- [ ] Open-source MCP server framework / agent eval + observability tool (extends Microsoft work)

## Resume fixes
- [ ] Remove the "sub-50ms latency" claim unless load-tested with a real number and stated setup
- [ ] VJ Fashions: lead with measured results (cache hit rate, p95 latency, load) instead of tech stack
- [ ] Microsoft: add scale (migrations/week, failure rate, number of engineers using it)
- [ ] Drop 10th-grade percentage; consider adding JEE Main rank if strong
- [ ] Remove "Coursework" line and generic tools (Postman)
- [ ] Skills: add Go, Docker, Kubernetes, Azure, Postgres, Kafka only if actually used
- [ ] Achievements: make LeetCode 1915 a one-line headline; collapse individual CodeChef ranks
- [ ] Keep to one page, single-column ATS-friendly layout
- [ ] Fix garbled characters (`�`) in the PDF (avoid special dashes/icons) so ATS parses it
- [ ] Optionally rewrite the whole resume in LaTeX/Word
