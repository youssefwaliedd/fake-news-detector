import { useState } from "react";
import { IconDoc, IconSpinner, IconScale, IconArrow } from "./Icons.jsx";

const URL_RE = /^https?:\/\/\S+$/i;

const EXAMPLES = [
  {
    label: "Sample claim",
    value:
      "Scientists have confirmed that drinking celery juice every morning cures all forms of cancer within two weeks, according to a leaked government study.",
  },
  {
    label: "News URL",
    value: "https://www.reuters.com/world/",
  },
];

export default function InputForm({ onSubmit, running }) {
  const [value, setValue] = useState("");
  const isUrl = URL_RE.test(value.trim()) && !value.trim().includes(" ");

  function submit(e) {
    e.preventDefault();
    const text = value.trim();
    if (text.length < 3 || running) return;
    onSubmit(text);
  }

  return (
    <form className="input-card" onSubmit={submit}>
      <div className="input-head">
        <IconScale />
        Analyze a claim or article
        <span className={`kind-chip ${isUrl ? "url" : ""}`}>
          {isUrl ? "URL detected" : "Text"}
        </span>
      </div>

      <textarea
        className="input-field"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Paste an article, a headline, a single claim — or drop in an article URL to fetch and check it."
        aria-label="Claim, article text, or URL to analyze"
        rows={5}
      />

      <div className="input-row">
        <div className="examples" aria-label="Examples">
          {EXAMPLES.map((ex) => (
            <button
              key={ex.label}
              type="button"
              className="example-btn"
              onClick={() => setValue(ex.value)}
              disabled={running}
            >
              {ex.label}
            </button>
          ))}
        </div>

        <button type="submit" className="run-btn" disabled={running || value.trim().length < 3}>
          {running ? (
            <>
              <IconSpinner /> Analyzing…
            </>
          ) : (
            <>
              <IconDoc /> Check credibility <IconArrow />
            </>
          )}
        </button>
      </div>
    </form>
  );
}
