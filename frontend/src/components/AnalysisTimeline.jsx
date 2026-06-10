import { NODE_ICON, IconCheck, IconSpinner, IconScale } from "./Icons.jsx";

// Ordered pipeline nodes — must match backend graph.PIPELINE.
const STEPS = [
  { id: "ingest", label: "Reading input" },
  { id: "ml_classify", label: "ML first-pass" },
  { id: "extract_claims", label: "Extracting claims" },
  { id: "retrieve_evidence", label: "Gathering evidence" },
  { id: "assess_claims", label: "Checking claims" },
  { id: "fuse", label: "Final verdict" },
];

export default function AnalysisTimeline({ statuses, summaries }) {
  return (
    <section className="panel" aria-label="Analysis pipeline">
      <h2 className="panel-title">
        <IconScale /> Pipeline
      </h2>
      <ol className="timeline" aria-live="polite">
        {STEPS.map((step) => {
          const status = statuses[step.id] || "waiting";
          const Icon = NODE_ICON[step.id];
          return (
            <li key={step.id} className={`tl-step ${status}`}>
              <div className="tl-rail">
                <span className="tl-dot">
                  {status === "running" ? (
                    <IconSpinner />
                  ) : status === "done" ? (
                    <IconCheck />
                  ) : (
                    <Icon />
                  )}
                </span>
                <span className="tl-line" />
              </div>
              <div className="tl-body">
                <div className="tl-name">{step.label}</div>
                {summaries[step.id] && (
                  <div className="tl-summary">{summaries[step.id]}</div>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

export { STEPS };
