import { VERDICT_ICON, IconCpu, IconScale } from "./Icons.jsx";

const LABEL_TEXT = { real: "Likely Real", fake: "Likely Fake", uncertain: "Uncertain" };

function Gauge({ pct, label }) {
  const r = 40;
  const c = 2 * Math.PI * r;
  const off = c * (1 - pct / 100);
  return (
    <div className="gauge" role="img" aria-label={`Confidence ${pct}%`}>
      <svg width="92" height="92" viewBox="0 0 92 92">
        <circle className="gauge-track" cx="46" cy="46" r={r} fill="none" strokeWidth="8" />
        <circle
          className={`gauge-${label}`}
          cx="46" cy="46" r={r} fill="none" strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={off}
        />
      </svg>
      <div className="gauge-val">
        <b className="num">{pct}%</b>
        <span>conf.</span>
      </div>
    </div>
  );
}

function Signal({ label, icon: Icon, score, available }) {
  const pct = Math.round((score ?? 0) * 100);
  return (
    <div className="signal-row">
      <span className="signal-label">
        <Icon /> {label}
      </span>
      {available ? (
        <span className="signal-track">
          <span className="signal-fill fakeish" style={{ width: `${pct}%` }} />
        </span>
      ) : (
        <span className="signal-na">not available</span>
      )}
      {available && <span className="signal-val num">{pct}%</span>}
    </div>
  );
}

export default function VerdictCard({ result }) {
  const label = result.label || "uncertain";
  const Icon = VERDICT_ICON[label];
  const conf = Math.round((result.confidence || 0) * 100);

  // Evidence signal = fake_probability fused; show share derived from claims.
  const checked = result.claims.filter((c) => c.verdict === "supported" || c.verdict === "refuted");
  const refuted = checked.filter((c) => c.verdict === "refuted").length;
  const evidenceScore = checked.length ? refuted / checked.length : null;

  return (
    <section className={`verdict ${label} fade-in`} aria-label="Verdict">
      <div className="verdict-top">
        <span className="verdict-badge">
          <Icon /> {LABEL_TEXT[label]}
        </span>
        <Gauge pct={conf} label={label} />
      </div>

      <p className="verdict-rationale">{result.rationale}</p>

      <div className="verdict-meta">
        {result.fake_probability != null && (
          <>
            <span>
              Fused P(fake): <b className="num">{Math.round(result.fake_probability * 100)}%</b>
            </span>
            <span className="dot">·</span>
          </>
        )}
        <span>{result.claims.length} claim{result.claims.length === 1 ? "" : "s"} checked</span>
        {result.article_title && (
          <>
            <span className="dot">·</span>
            <span>“{result.article_title}”</span>
          </>
        )}
      </div>

      <div className="signals">
        <Signal label="ML model" icon={IconCpu} score={result.ml?.score} available={result.ml?.available} />
        <Signal label="Evidence" icon={IconScale} score={evidenceScore} available={evidenceScore != null} />
      </div>
    </section>
  );
}
