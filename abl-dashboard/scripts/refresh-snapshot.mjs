import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(process.cwd(), '..');
const outDir = path.resolve(process.cwd(), 'public');
const dataDir = path.resolve(root, 'benchmarks/abl');
const dataRoot = path.resolve(root, 'data');

const readJson = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));
const safeReadJson = (p, fallback = null) => {
  try { return readJson(p); } catch { return fallback; }
};
const mtimeIso = (p) => fs.statSync(p).mtime.toISOString();

const manifestPath = path.join(dataDir, 'build_manifest.json');
const reportPath = path.join(dataDir, 'reports/2026-03-12_asrs-wrcm_leaderboard_report.md');
const asrsSpecPath = path.join(dataDir, 'specs/approved/BSPEC-ASRS-v1.json');
const wrcmSpecPath = path.join(dataDir, 'specs/approved/BSPEC-WRCM-v1.json');
const asrsMetricsPath = path.join(dataDir, 'harness/BP-001-ASRS/eval_stub_metrics.json');
const wrcmMetricsPath = path.join(dataDir, 'harness/BP-002-WRCM/eval_stub_metrics.json');
const cronPath = path.join(dataRoot, 'cron.snapshot.json');
const blockersPath = path.join(dataRoot, 'blocker-escalation-queue.json');

const manifest = readJson(manifestPath);
const asrsSpec = readJson(asrsSpecPath);
const wrcmSpec = readJson(wrcmSpecPath);
const asrsMetrics = readJson(asrsMetricsPath);
const wrcmMetrics = readJson(wrcmMetricsPath);
const cron = safeReadJson(cronPath, { jobs: [] });
const blockers = safeReadJson(blockersPath, { blockers: [] });
const reportText = fs.readFileSync(reportPath, 'utf8');

const weighted = (metrics, weights) =>
  Object.entries(weights).reduce((acc, [k, w]) => acc + ((metrics[k] ?? 0) * w), 0);

const bets = [
  { id: asrsSpec.project_id, cluster: asrsSpec.cluster_id, title: asrsSpec.title, priority: asrsSpec.priority, owner: asrsSpec.owner, objective: asrsSpec.objective },
  { id: wrcmSpec.project_id, cluster: wrcmSpec.cluster_id, title: wrcmSpec.title, priority: wrcmSpec.priority, owner: wrcmSpec.owner, objective: wrcmSpec.objective }
];

const leaderboard = [
  {
    benchmark: asrsSpec.cluster_id,
    projectId: asrsSpec.project_id,
    metric: asrsSpec.scoring.primary_metric,
    score: Number(weighted(asrsMetrics, asrsSpec.scoring.weighting_default).toFixed(3)),
    gates: [
      { name: 'min_safety_compliance', threshold: asrsSpec.scoring.gates.min_safety_compliance, actual: asrsMetrics.safety_compliance, status: asrsMetrics.safety_compliance >= asrsSpec.scoring.gates.min_safety_compliance ? 'PASS' : 'FAIL' },
      { name: 'max_shortcut_exploit_rate', threshold: asrsSpec.scoring.gates.max_shortcut_exploit_rate, actual: null, status: 'UNKNOWN' }
    ],
    n: asrsMetrics.n_items_evaluated
  },
  {
    benchmark: wrcmSpec.cluster_id,
    projectId: wrcmSpec.project_id,
    metric: wrcmSpec.scoring.primary_metric,
    score: Number(weighted(wrcmMetrics, wrcmSpec.scoring.weighting_default).toFixed(3)),
    gates: [
      { name: 'min_sla_adherence', threshold: wrcmSpec.scoring.gates.min_sla_adherence, actual: wrcmMetrics.sla_adherence, status: wrcmMetrics.sla_adherence >= wrcmSpec.scoring.gates.min_sla_adherence ? 'PASS' : 'FAIL' },
      { name: 'min_regime_coverage', threshold: wrcmSpec.scoring.gates.min_regime_coverage, actual: wrcmMetrics.regime_coverage, status: wrcmMetrics.regime_coverage >= wrcmSpec.scoring.gates.min_regime_coverage ? 'PASS' : 'FAIL' }
    ],
    n: wrcmMetrics.n_items_evaluated
  }
].sort((a,b)=>b.score-a.score);

const caveats = [
  'Stub metrics only; external claims should be treated as low-confidence.',
  'n_items_evaluated=4 for each benchmark; ranking instability is high.',
  'ASRS max_shortcut_exploit_rate gate is not directly available in current payload.'
];

const timeline = [
  { ts: mtimeIso(asrsSpecPath), type: 'Spec Freeze', benchmark: 'ASRS', note: 'BSPEC-ASRS-v1 frozen.' },
  { ts: mtimeIso(wrcmSpecPath), type: 'Spec Freeze', benchmark: 'WRCM', note: 'BSPEC-WRCM-v1 frozen.' },
  { ts: mtimeIso(manifestPath), type: 'Build', benchmark: 'ASRS+WRCM', note: `Manifest generated (${manifest.artifacts.length} artifacts).` },
  { ts: mtimeIso(asrsMetricsPath), type: 'Probe Run', benchmark: 'ASRS', note: `Eval stub: ${asrsMetrics.n_items_evaluated}/${asrsMetrics.n_items_total} items.` },
  { ts: mtimeIso(wrcmMetricsPath), type: 'Probe Run', benchmark: 'WRCM', note: `Eval stub: ${wrcmMetrics.n_items_evaluated}/${wrcmMetrics.n_items_total} items.` },
  { ts: mtimeIso(reportPath), type: 'Leaderboard', benchmark: 'ASRS+WRCM', note: 'Comparable leaderboard report published.' }
].sort((a,b)=>new Date(b.ts)-new Date(a.ts));

const artifactTracker = manifest.artifacts.map((a) => ({
  projectId: a.project_id,
  spec: a.spec_file,
  dataset: a.dataset_file,
  harness: a.harness_file,
  rows: a.rows,
  datasetSha256: a.dataset_sha256,
  harnessSha256: a.harness_sha256
}));

const ablJobs = (cron.jobs || []).filter((j) => /^ABL /.test(j.name) || j.name === 'ABL General Executive Sync');
const cronStatus = ablJobs.map((j) => ({
  name: j.name,
  enabled: j.enabled,
  channel: j.delivery?.to || 'n/a',
  nextRunAtMs: j.state?.nextRunAtMs || null,
  lastStatus: j.state?.lastStatus || j.state?.lastRunStatus || 'unknown'
}));

const blockersView = [
  {
    title: 'ASRS exploit-rate gate metric missing in eval payload',
    severity: 'high',
    owner: 'A04 Prober',
    eta: '2026-03-13T20:00:00Z',
    status: 'open'
  },
  {
    title: 'Leaderboard confidence too low (n=4); need expanded run set',
    severity: 'high',
    owner: 'A08 Analyst',
    eta: '2026-03-14T00:00:00Z',
    status: 'open'
  },
  ...(blockers.blockers || []).slice(0, 2).map((b) => ({
    title: b.title,
    severity: b.severity,
    owner: b.owner,
    eta: b.eta,
    status: b.escalationStatus
  }))
];

const snapshot = {
  generatedAt: new Date().toISOString(),
  sourceLastUpdated: {
    manifest: mtimeIso(manifestPath),
    report: mtimeIso(reportPath),
    cron: safeReadJson(cronPath) ? mtimeIso(cronPath) : null,
    blockers: safeReadJson(blockersPath) ? mtimeIso(blockersPath) : null
  },
  activeBenchmarkBets: bets,
  leaderboard,
  confidenceCaveats: caveats,
  runTimeline: timeline,
  artifactTracker,
  blockers: blockersView,
  cronStatus,
  reportPreview: reportText.split('\n').slice(0, 40).join('\n')
};

fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, 'snapshot.json'), JSON.stringify(snapshot, null, 2));
console.log(`Wrote ${path.join(outDir, 'snapshot.json')}`);
