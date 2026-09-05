import type { SourceContext as Context } from "./api";
export function SourceContext({ context }: { context?: Context | null }) {
  if (!context) return null;
  if (context.status !== "available")
    return (
      <p className="muted">
        {context.status === "removed"
          ? "The source capture has been removed. Your chosen task or appointment remains."
          : context.status === "changed"
            ? "The captured source changed. Check the original before relying on these details."
            : "This source was set aside. Check whether the next step is still useful."}
      </p>
    );
  return (
    <details className="source-context">
      <summary>Source context & preparation details</summary>
      <p style={{ whiteSpace: "pre-wrap" }}>{context.summary}</p>
      <small>
        Captured{" "}
        {context.observedAt
          ? new Date(context.observedAt).toLocaleString("en-GB", {
              timeZone: "Europe/London",
            })
          : "at an unknown time"}{" "}
        · London time. This is a snapshot, not a live calendar check.
      </small>
      {context.sourceUrl && (
        <p>
          <a href={context.sourceUrl} target="_blank" rel="noreferrer">
            Open original source
          </a>
        </p>
      )}
    </details>
  );
}
