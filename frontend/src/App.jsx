import { useRef, useState } from "react";
import InputForm from "./components/InputForm.jsx";
import AnalysisTimeline, { STEPS } from "./components/AnalysisTimeline.jsx";
import VerdictCard from "./components/VerdictCard.jsx";
import ClaimBreakdown from "./components/ClaimBreakdown.jsx";
import SourcesPanel from "./components/SourcesPanel.jsx";
import { IconLogo, IconWarning, IconScale } from "./components/Icons.jsx";
import { streamAnalyze } from "./lib/api.js";

const NODE_IDS = STEPS.map((s) => s.id);
const freshStatuses = () => Object.fromEntries(NODE_IDS.map((id) => [id, "waiting"]));

export default function App() {
  const [running, setRunning] = useState(false);
  const [started, setStarted] = useState(false);
  const [statuses, setStatuses] = useState(freshStatuses());
  const [summaries, setSummaries] = useState({});
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const abortRef = useRef(null);

  const doneCount = Object.values(statuses).filter((s) => s === "done").length;
  const progress = started ? Math.round((doneCount / NODE_IDS.length) * 100) : 0;

  function reset() {
    setStatuses(freshStatuses());
    setSummaries({});
    setResult(null);
    setError("");
  }

  async function run(input) {
    reset();
    setRunning(true);
    setStarted(true);
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      await streamAnalyze(input, handleEvent, controller.signal);
    } catch (e) {
      if (e.name !== "AbortError") setError(e.message || String(e));
    } finally {
      setRunning(false);
      // Any node still "running" at the end is promoted to done.
      setStatuses((s) =>
        Object.fromEntries(Object.entries(s).map(([k, v]) => [k, v === "running" ? "done" : v]))
      );
    }
  }

  function handleEvent({ event, data }) {
    if (event === "node_start") {
      setStatuses((s) => ({ ...s, [data.node]: "running" }));
    } else if (event === "node_output") {
      setStatuses((s) => ({ ...s, [data.node]: "done" }));
      if (data.summary) setSummaries((m) => ({ ...m, [data.node]: data.summary }));
    } else if (event === "final") {
      setResult(data.result);
    } else if (event === "error") {
      setError(data.message || "Analysis failed.");
    }
  }

  return (
    <div className="app">
      <div className="bg-grid" aria-hidden="true" />

      <header className="app-header">
        <div className="brand">
          <span className="brand-mark">
            <IconLogo />
          </span>
          <div className="brand-text">
            <h1>
              Fake News <span className="grad">Detector</span>
            </h1>
            <p className="subtitle">
              A hybrid check: a machine-learning first pass fused with an LLM that extracts the
              article’s claims and weighs them against live web evidence.
            </p>
          </div>
        </div>
      </header>

      <InputForm onSubmit={run} running={running} />

      {started && (
        <div className="pipeline" role="status" aria-live="polite">
          <div className="pipeline-bar">
            <div className={`pipeline-fill ${running ? "active" : ""}`} style={{ width: `${progress}%` }} />
          </div>
          <span className="pipeline-label">
            {running ? `Analyzing… ${doneCount}/${NODE_IDS.length} steps` : `${progress}% complete`}
          </span>
        </div>
      )}

      {error && (
        <div className="error-banner" role="alert">
          <IconWarning />
          <span>{error}</span>
        </div>
      )}

      {started && (
        <div className="grid">
          <div className="col-left">
            <AnalysisTimeline statuses={statuses} summaries={summaries} />
            {result && <SourcesPanel sources={result.sources} />}
          </div>

          <div className="col-right">
            {result ? (
              <>
                <VerdictCard result={result} />
                <ClaimBreakdown claims={result.claims} />
              </>
            ) : (
              <section className="panel">
                <div className="empty">
                  <IconScale />
                  <h3>Weighing the evidence…</h3>
                  <p>Reading the input, scoring it, pulling claims, and checking each against the web.</p>
                </div>
              </section>
            )}
          </div>
        </div>
      )}

      <div className="disclaimer">
        <IconWarning />
        <span>
          This is a decision-support tool, not a verdict of truth. Verdicts are probabilistic and
          depend on available evidence — always check the cited sources yourself.
        </span>
      </div>
    </div>
  );
}
