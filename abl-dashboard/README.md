# ABL Dashboard (MVP)

Decision-centric dashboard for Autonomous Benchmark Discovery Lab status.

## Views
- Active benchmark bets (ASRS/WRCM)
- Latest leaderboard scores + confidence caveats
- Run history timeline (probe runs + failure-risk notes)
- Artifact tracker (specs/datasets/harness hashes)
- Blockers + owners + ETA
- ABL cron/agent status

## Refresh data snapshot
```bash
cd /home/node/.openclaw/workspace/mission-control/abl-dashboard
npm install
npm run refresh
```

This rebuilds `public/snapshot.json` from:
- `../benchmarks/abl/*`
- `../data/cron.snapshot.json`
- `../data/blocker-escalation-queue.json`

## Deploy
```bash
vercel --prod
```
