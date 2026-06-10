import { IconLink } from "./Icons.jsx";

function hostOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export default function SourcesPanel({ sources }) {
  if (!sources || sources.length === 0) return null;

  return (
    <section className="panel" aria-label="Evidence sources">
      <h2 className="panel-title">
        <IconLink /> Evidence sources ({sources.length})
      </h2>
      <ul className="source-list">
        {sources.map((s, i) => (
          <li key={i}>
            <a className="source-item" href={s.url} target="_blank" rel="noopener noreferrer">
              <span className="source-idx num">{String(i + 1).padStart(2, "0")}</span>
              <span className="source-meta">
                <span className="source-title">{s.title || hostOf(s.url)}</span>
                <span className="source-host">
                  <IconLink /> {hostOf(s.url)}
                </span>
              </span>
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}
