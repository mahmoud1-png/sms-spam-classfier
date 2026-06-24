import { useState, useMemo, useRef } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

// ── Design tokens ─────────────────────────────────────────────────────────────
const C = {
  bg: "#0D1117", card: "#161B22", card2: "#1C2128",
  border: "#30363D",
  spam: "#F85149", ham: "#3FB950", accent: "#7C3AED",
  text: "#E6EDF3", muted: "#8B949E", warn: "#E3B341",
};
const mono = { fontFamily: "'Courier New', monospace" };
const pct  = (n, d = 1) => `${(n * 100).toFixed(d)}%`;

// ── Primitives ────────────────────────────────────────────────────────────────
const Card = ({ children, style = {} }) => (
  <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 10, padding: 20, ...style }}>
    {children}
  </div>
);

const SL = ({ children }) => (
  <div style={{ color: C.muted, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.12em", marginBottom: 12, fontWeight: 600 }}>
    {children}
  </div>
);

const Badge = ({ label, color }) => (
  <span style={{ background: `${color}22`, color, border: `1px solid ${color}44`, borderRadius: 4, padding: "2px 8px", fontSize: 11, fontWeight: 700, ...mono }}>
    {label}
  </span>
);

// ── Metric card ───────────────────────────────────────────────────────────────
function MetricCard({ label, value, sub, accent }) {
  return (
    <Card style={{ padding: "22px 24px" }}>
      <SL>{label}</SL>
      <div style={{ color: accent || C.text, fontSize: 38, fontWeight: 700, lineHeight: 1, ...mono }}>
        {value}
      </div>
      {sub && <div style={{ color: C.muted, fontSize: 11, marginTop: 8 }}>{sub}</div>}
    </Card>
  );
}

// ── Confusion matrix ──────────────────────────────────────────────────────────
function CMCell({ v, label, sub, color, r, total }) {
  return (
    <td style={{ background: `${color}18`, border: `1px solid ${color}44`, borderRadius: r, padding: "14px 16px", textAlign: "center", minWidth: 118 }}>
      <div style={{ color, fontSize: 28, fontWeight: 700, ...mono }}>{v}</div>
      <div style={{ color: C.muted, fontSize: 10, marginTop: 4, fontWeight: 600 }}>{label}</div>
      <div style={{ color: C.muted, fontSize: 9, marginTop: 2 }}>{sub} · {pct(v / (total || 1))}</div>
    </td>
  );
}

function ConfusionMatrix({ m }) {
  const { true_positives: tp, true_negatives: tn, false_positives: fp, false_negatives: fn } = m;
  const total = tp + tn + fp + fn;
  return (
    <div>
      <SL>Confusion Matrix</SL>
      <div style={{ overflowX: "auto" }}>
        <table style={{ borderCollapse: "separate", borderSpacing: 4 }}>
          <thead>
            <tr>
              <td style={{ width: 90 }} />
              <th style={{ textAlign: "center", fontSize: 10, color: C.muted, fontWeight: 600, paddingBottom: 8 }}>Predicted SPAM</th>
              <th style={{ textAlign: "center", fontSize: 10, color: C.muted, fontWeight: 600, paddingBottom: 8 }}>Predicted HAM</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th style={{ textAlign: "right", fontSize: 10, color: C.muted, fontWeight: 600, paddingRight: 12, whiteSpace: "nowrap" }}>Actual SPAM</th>
              <CMCell v={tp} label="True Positive"  sub="Caught"      color={C.ham}  r="8px 0 0 0" total={total} />
              <CMCell v={fn} label="False Negative" sub="Spam missed" color={C.spam} r="0 8px 0 0" total={total} />
            </tr>
            <tr>
              <th style={{ textAlign: "right", fontSize: 10, color: C.muted, fontWeight: 600, paddingRight: 12, whiteSpace: "nowrap" }}>Actual HAM</th>
              <CMCell v={fp} label="False Positive" sub="False alarm" color={C.spam} r="0 0 0 8px" total={total} />
              <CMCell v={tn} label="True Negative"  sub="Passed"      color={C.ham}  r="0 0 8px 0" total={total} />
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ── Class breakdown bars ──────────────────────────────────────────────────────
function ClassBreakdown({ m }) {
  const { true_positives: tp, true_negatives: tn, false_positives: fp, false_negatives: fn } = m;
  const total = tp + tn + fp + fn;
  const rows = [
    { label: "Spam in dataset",       v: tp + fn, color: C.spam   },
    { label: "Ham in dataset",        v: tn + fp, color: C.ham    },
    { label: "Predicted as spam",     v: tp + fp, color: C.spam   },
    { label: "Predicted as ham",      v: tn + fn, color: C.ham    },
    { label: "Correctly classified",  v: tp + tn, color: C.accent },
    { label: "Misclassified",         v: fp + fn, color: C.warn   },
  ];
  return (
    <div>
      <SL>Class Breakdown</SL>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {rows.map(row => (
          <div key={row.label}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
              <span style={{ fontSize: 12, color: C.muted }}>{row.label}</span>
              <span style={{ fontSize: 12, color: C.text, ...mono }}>
                {row.v} <span style={{ color: C.muted }}>({pct(row.v / (total || 1))})</span>
              </span>
            </div>
            <div style={{ height: 5, background: C.border, borderRadius: 3 }}>
              <div style={{ height: 5, width: `${(row.v / (total || 1)) * 100}%`, background: row.color, borderRadius: 3 }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Probability histogram ─────────────────────────────────────────────────────
function ProbHistogram({ results }) {
  const BINS = 20;
  const data = useMemo(() => {
    const bins = Array.from({ length: BINS }, (_, i) => ({ name: `${i * 5}`, spam: 0, ham: 0 }));
    results.forEach(r => {
      const b = Math.min(Math.floor(r.spam_probability * BINS), BINS - 1);
      if (r.true_label === "spam") bins[b].spam++;
      else bins[b].ham++;
    });
    return bins;
  }, [results]);

  const Tip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    const spam = payload.find(p => p.dataKey === "spam")?.value || 0;
    const ham  = payload.find(p => p.dataKey === "ham")?.value  || 0;
    return (
      <div style={{ background: C.card2, border: `1px solid ${C.border}`, borderRadius: 6, padding: "10px 14px", fontSize: 12 }}>
        <div style={{ color: C.muted, marginBottom: 6 }}>Prob bucket: {label}%–{+label + 5}%</div>
        <div style={{ color: C.spam }}>True spam: {spam}</div>
        <div style={{ color: C.ham  }}>True ham: {ham}</div>
        <div style={{ color: C.muted, marginTop: 4 }}>Total: {spam + ham}</div>
      </div>
    );
  };

  return (
    <>
      <SL>Probability Distribution</SL>
      <p style={{ color: C.muted, fontSize: 11, margin: "0 0 12px" }}>
        Each bar = 5% probability bucket · stacked by true label · well-calibrated models show spam bunching right and ham bunching left
      </p>
      <ResponsiveContainer width="100%" height={190}>
        <BarChart data={data} barCategoryGap="8%">
          <XAxis dataKey="name" tick={{ fill: C.muted, fontSize: 10 }} interval={3} tickFormatter={v => `${v}%`} />
          <YAxis tick={{ fill: C.muted, fontSize: 10 }} width={28} />
          <Tooltip content={<Tip />} />
          <Bar dataKey="spam" stackId="a" fill={C.spam} />
          <Bar dataKey="ham"  stackId="a" fill={C.ham} radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <div style={{ display: "flex", gap: 20, justifyContent: "center", marginTop: 8 }}>
        {[["True spam", C.spam], ["True ham", C.ham]].map(([lbl, col]) => (
          <span key={lbl} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: C.muted }}>
            <span style={{ width: 10, height: 10, background: col, borderRadius: 2, display: "inline-block" }} />
            {lbl}
          </span>
        ))}
      </div>
    </>
  );
}

// ── Message browser ───────────────────────────────────────────────────────────
const FTABS = [
  { id: "all",     label: "All"             },
  { id: "correct", label: "✓ Correct"       },
  { id: "wrong",   label: "✗ Wrong"         },
  { id: "fp",      label: "False Positives" },
  { id: "fn",      label: "False Negatives" },
  { id: "spam",    label: "Spam"            },
  { id: "ham",     label: "Ham"             },
];

function applyFilter(results, fid, q) {
  let r = results;
  if      (fid === "correct") r = r.filter(x => x.correct);
  else if (fid === "wrong")   r = r.filter(x => !x.correct);
  else if (fid === "fp")      r = r.filter(x => x.true_label === "ham"  && x.predicted_label === "SPAM");
  else if (fid === "fn")      r = r.filter(x => x.true_label === "spam" && x.predicted_label === "HAM");
  else if (fid === "spam")    r = r.filter(x => x.true_label === "spam");
  else if (fid === "ham")     r = r.filter(x => x.true_label === "ham");
  if (q.trim()) {
    const lq = q.trim().toLowerCase();
    r = r.filter(x => x.text.toLowerCase().includes(lq));
  }
  return r;
}

function MessageBrowser({ results }) {
  const [fid,    setFid]    = useState("all");
  const [search, setSearch] = useState("");
  const [page,   setPage]   = useState(0);
  const PAGE = 15;

  const filtered = useMemo(() => applyFilter(results, fid, search), [results, fid, search]);
  const pages    = Math.ceil(filtered.length / PAGE) || 1;
  const visible  = filtered.slice(page * PAGE, (page + 1) * PAGE);

  const go  = (f) => { setFid(f); setPage(0); };
  const btn = (active) => ({
    background: active ? C.accent : "transparent",
    color: active ? "#fff" : C.muted,
    border: `1px solid ${active ? C.accent : C.border}`,
    borderRadius: 6, padding: "4px 11px", fontSize: 12, cursor: "pointer",
  });

  return (
    <>
      <SL>Message Browser — {filtered.length} of {results.length}</SL>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 10 }}>
        {FTABS.map(f => (
          <button key={f.id} onClick={() => go(f.id)} style={btn(fid === f.id)}>{f.label}</button>
        ))}
        <input
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(0); }}
          placeholder="Search messages…"
          style={{ flex: 1, minWidth: 160, background: C.card2, border: `1px solid ${C.border}`, borderRadius: 6, padding: "4px 11px", fontSize: 12, color: C.text, outline: "none" }}
        />
      </div>

      <div style={{ borderRadius: 8, overflow: "hidden", border: `1px solid ${C.border}` }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
          <thead>
            <tr style={{ background: C.card2 }}>
              {["#", "True", "Predicted", "Prob", "Rule", "Message text"].map(h => (
                <th key={h} style={{ padding: "8px 12px", textAlign: "left", color: C.muted, fontWeight: 600, fontSize: 10, textTransform: "uppercase", letterSpacing: "0.08em", borderBottom: `1px solid ${C.border}` }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.map(r => (
              <tr key={r.index ?? r.text} style={{ background: r.correct ? "transparent" : `${C.spam}08`, borderBottom: `1px solid ${C.border}` }}>
                <td style={{ padding: "7px 12px", color: C.muted, ...mono }}>{(r.index ?? 0) + 1}</td>
                <td style={{ padding: "7px 12px" }}>
                  <Badge label={r.true_label.toUpperCase()} color={r.true_label === "spam" ? C.spam : C.ham} />
                </td>
                <td style={{ padding: "7px 12px" }}>
                  <Badge label={r.predicted_label} color={r.predicted_label === "SPAM" ? C.spam : C.ham} />
                </td>
                <td style={{ padding: "7px 12px", color: r.spam_probability > 0.5 ? C.spam : C.ham, ...mono }}>
                  {pct(r.spam_probability)}
                </td>
                <td style={{ padding: "7px 12px", textAlign: "center", color: r.rule_triggered ? C.warn : C.muted }}>
                  {r.rule_triggered ? "⚡" : "·"}
                </td>
                <td style={{ padding: "7px 12px", color: C.text, maxWidth: 360, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={r.text}>
                  {!r.correct && <span style={{ color: C.spam, marginRight: 4 }}>⚠</span>}
                  {r.text}
                </td>
              </tr>
            ))}
            {visible.length === 0 && (
              <tr>
                <td colSpan={6} style={{ padding: 24, textAlign: "center", color: C.muted }}>No messages match</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {pages > 1 && (
        <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 8, marginTop: 12 }}>
          <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}
            style={{ ...btn(false), opacity: page === 0 ? 0.4 : 1, cursor: page === 0 ? "default" : "pointer" }}>← Prev</button>
          <span style={{ color: C.muted, fontSize: 12 }}>Page {page + 1} / {pages}</span>
          <button onClick={() => setPage(p => Math.min(pages - 1, p + 1))} disabled={page >= pages - 1}
            style={{ ...btn(false), opacity: page >= pages - 1 ? 0.4 : 1, cursor: page >= pages - 1 ? "default" : "pointer" }}>Next →</button>
        </div>
      )}
    </>
  );
}

// ── Load screen ───────────────────────────────────────────────────────────────
function LoadScreen({ onLoad }) {
  const [paste, setPaste] = useState("");
  const [err,   setErr]   = useState("");
  const ref = useRef();

  const parse = (text) => {
    try {
      const j = JSON.parse(text);
      if (!Array.isArray(j.results)) throw new Error("Missing 'results' array.");
      if (!j.metrics)                throw new Error("Missing 'metrics' object.");
      onLoad(j);
    } catch (e) { setErr(e.message); }
  };

  return (
    <div style={{ minHeight: "100vh", background: C.bg, display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
      <div style={{ width: "100%", maxWidth: 520 }}>
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <div style={{ fontSize: 44, marginBottom: 10 }}>🔬</div>
          <h1 style={{ color: C.text, fontSize: 24, fontWeight: 700, margin: 0 }}>Spam Classifier Dashboard</h1>
          <p style={{ color: C.muted, marginTop: 8, fontSize: 14 }}>
            Load test results to view accuracy metrics and message analysis
          </p>
        </div>

        <Card style={{ padding: 28 }}>
          <SL>Step 1 — run the test script</SL>
          <div style={{ background: "#010409", border: `1px solid ${C.border}`, borderRadius: 8, padding: "12px 16px", ...mono, fontSize: 12, color: "#58a6ff", marginBottom: 24, overflowX: "auto" }}>
            <span style={{ color: C.muted }}>$</span> python test_500.py --csv spam.csv
          </div>

          <SL>Step 2 — load the results JSON</SL>
          <div
            onClick={() => ref.current?.click()}
            onMouseEnter={e => e.currentTarget.style.borderColor = C.accent}
            onMouseLeave={e => e.currentTarget.style.borderColor = C.border}
            style={{ border: `2px dashed ${C.border}`, borderRadius: 8, padding: 20, textAlign: "center", cursor: "pointer", marginBottom: 14 }}
          >
            <input ref={ref} type="file" accept=".json" style={{ display: "none" }} onChange={e => {
              const f = e.target.files[0]; if (!f) return;
              const r = new FileReader(); r.onload = ev => parse(ev.target.result); r.readAsText(f);
            }} />
            <span style={{ color: C.muted, fontSize: 13 }}>📂  Click to upload results_*.json</span>
          </div>

          <div style={{ color: C.muted, fontSize: 12, textAlign: "center", marginBottom: 12 }}>— or paste JSON below —</div>

          <textarea
            value={paste}
            onChange={e => { setPaste(e.target.value); setErr(""); }}
            placeholder={'{\n  "results": [...],\n  "metrics": {...}\n}'}
            rows={5}
            style={{ width: "100%", background: "#010409", border: `1px solid ${C.border}`, borderRadius: 8, padding: 12, color: C.text, fontSize: 12, ...mono, resize: "vertical", boxSizing: "border-box", outline: "none" }}
          />

          {err && <div style={{ color: C.spam, fontSize: 12, marginTop: 6 }}>⚠ {err}</div>}

          <button
            onClick={() => parse(paste)}
            disabled={!paste.trim()}
            style={{
              width: "100%", marginTop: 12,
              background: paste.trim() ? C.accent : C.border,
              color: paste.trim() ? "#fff" : C.muted,
              border: "none", borderRadius: 8, padding: 12, fontSize: 14, fontWeight: 600,
              cursor: paste.trim() ? "pointer" : "default",
            }}
          >
            Load Results →
          </button>
        </Card>
      </div>
    </div>
  );
}

// ── Full dashboard ────────────────────────────────────────────────────────────
function FullDashboard({ data, onReset }) {
  const { metrics: m, results, tested_at, threshold, total } = data;
  const aColor = m.accuracy >= 0.95 ? C.ham : m.accuracy >= 0.85 ? C.warn : C.spam;

  return (
    <div style={{ minHeight: "100vh", background: C.bg, color: C.text, fontFamily: "system-ui, sans-serif", padding: 24 }}>
      <div style={{ maxWidth: 1140, margin: "0 auto" }}>

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
          <div>
            <h1 style={{ margin: 0, fontSize: 20, fontWeight: 700 }}>🔬 Spam Classifier · Test Report</h1>
            <div style={{ color: C.muted, fontSize: 12, marginTop: 4 }}>
              {total ?? results.length} messages · threshold {threshold ?? "—"}
              {tested_at ? ` · ${new Date(tested_at).toLocaleString()}` : ""}
            </div>
          </div>
          <button onClick={onReset} style={{ background: "transparent", border: `1px solid ${C.border}`, color: C.muted, borderRadius: 6, padding: "6px 14px", cursor: "pointer", fontSize: 12 }}>
            ↩ Load new file
          </button>
        </div>

        {/* Metric cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 16 }}>
          <MetricCard label="Accuracy"  value={pct(m.accuracy)}  sub={`${m.true_positives + m.true_negatives} of ${m.total} correct`} accent={aColor} />
          <MetricCard label="Precision" value={pct(m.precision)} sub={`${m.false_positives} false alarms`} />
          <MetricCard label="Recall"    value={pct(m.recall)}    sub={`${m.false_negatives} spam missed`} />
          <MetricCard label="F1 Score"  value={pct(m.f1)}        sub="Precision–Recall harmonic mean" />
        </div>

        {/* Confusion matrix + breakdown */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 16 }}>
          <Card><ConfusionMatrix m={m} /></Card>
          <Card><ClassBreakdown  m={m} /></Card>
        </div>

        {/* Probability histogram */}
        <Card style={{ marginBottom: 16 }}>
          <ProbHistogram results={results} />
        </Card>

        {/* Message browser */}
        <Card>
          <MessageBrowser results={results} />
        </Card>

      </div>
    </div>
  );
}

// ── Root ──────────────────────────────────────────────────────────────────────
export default function App() {
  const [data, setData] = useState(null);
  if (!data) return <LoadScreen onLoad={setData} />;
  return <FullDashboard data={data} onReset={() => setData(null)} />;
}
