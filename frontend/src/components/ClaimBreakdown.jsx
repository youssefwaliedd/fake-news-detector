import { VERDICT_ICON, IconLink, IconSearch } from "./Icons.jsx";

const VERDICT_TEXT = {
  supported: "Supported",
  refuted: "Refuted",
  unverified: "Unverified",
};

function hostOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export default function ClaimBreakdown({ claims }) {
  if (!claims || claims.length === 0) return null;

  return (
    <section className="panel" aria-label="Claim-by-claim breakdown">
      <h2 className="panel-title">
        <IconSearch /> Claim-by-claim
      </h2>
      <div className="claims">
        {claims.map((c, i) => {
          const Icon = VERDICT_ICON[c.verdict] || VERDICT_ICON.unverified;
          return (
            <article className="claim fade-in" key={i}>
              <div className="claim-head">
                <span className={`claim-pill ${c.verdict}`}>
                  <Icon /> {VERDICT_TEXT[c.verdict] || "Unverified"}
                </span>
                <p className="claim-text">{c.claim}</p>
              </div>
              {c.rationale && <p className="claim-rationale">{c.rationale}</p>}
              {c.sources && c.sources.length > 0 && (
                <div className="claim-sources">
                  {c.sources.map((s, j) => (
                    <a
                      key={j}
                      className="claim-src"
                      href={s.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      title={s.title || s.url}
                    >
                      <IconLink />
                      <span>{hostOf(s.url)}</span>
                    </a>
                  ))}
                </div>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
