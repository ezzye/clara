import { SourceContext } from "./SourceContext";
import { useState } from "react";
import { Sparkles, Check, ArrowUpRight } from "lucide-react";
import type { State, Suggestion } from "./api";
type Action = (action: string, data?: unknown) => Promise<unknown>;
const clock = (n: number) =>
  `${String(Math.floor(n / 60)).padStart(2, "0")}:${String(n % 60).padStart(2, "0")}`;
function DraftCard({
  draft,
  act,
  busy,
}: {
  draft: Suggestion;
  act: Action;
  busy: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [fields, setFields] = useState({
    category: draft.category || "personal",
    title: draft.title,
    nextStep: draft.nextStep,
    doneWhen: draft.doneWhen,
    date: draft.date,
    minutes: draft.minutes,
    start: clock(draft.start),
  });
  return (
    <section className="card draft-card">
      <div className="section-heading">
        <span className="tag">
          <Sparkles size={14} /> Proposed {draft.kind}
        </span>
        <small>
          {draft.source}
          {draft.sourceUrl ? ` · ${new URL(draft.sourceUrl).hostname}` : ""}
        </small>
      </div>
      <h3>{fields.title}</h3>
      <p>{draft.reason}</p>
      <details>
        <summary>Why Clara suggested this</summary>
        <blockquote>{draft.quote}</blockquote>
        <small>
          Passage from captured evidence ·{" "}
          {new Date(draft.observedAt).toLocaleString("en-GB")}
        </small>
        {draft.sourceUrl && (
          <p>
            <a href={draft.sourceUrl} target="_blank" rel="noreferrer">
              Open original source <ArrowUpRight size={14} />
            </a>
          </p>
        )}
      </details>
      <SourceContext context={draft.sourceContext} />
      <p className="muted">
        {draft.kind === "appointment"
          ? `${fields.date} at ${fields.start} · ${fields.minutes} minutes reserved`
          : `${fields.minutes} minute next step${fields.date ? ` · due ${fields.date}` : ""}`}
      </p>
      <p>{fields.nextStep}</p>
      <div className="definition">
        <strong>Enough for this step</strong>
        <p>{fields.doneWhen}</p>
      </div>
      {draft.kind === "appointment" && (
        <p className="notice">
          Check the date, time and duration against the source before adding. No
          booking or invitation will be sent.
        </p>
      )}
      {editing && (
        <div className="draft-fields">
          {draft.kind === "task" && (
            <label>
              Area
              <select
                value={fields.category}
                onChange={(e) =>
                  setFields({ ...fields, category: e.target.value })
                }
              >
                <option value="prep">Meeting preparation</option>
                <option value="project">Finish a project</option>
                <option value="development">Development goal</option>
                <option value="personal">Personal life</option>
              </select>
            </label>
          )}
          <label>
            Title
            <input
              value={fields.title}
              maxLength={180}
              onChange={(e) => setFields({ ...fields, title: e.target.value })}
            />
          </label>
          <label>
            First step
            <textarea
              value={fields.nextStep}
              maxLength={500}
              onChange={(e) =>
                setFields({ ...fields, nextStep: e.target.value })
              }
            />
          </label>
          <label>
            Finish line
            <textarea
              value={fields.doneWhen}
              maxLength={500}
              onChange={(e) =>
                setFields({ ...fields, doneWhen: e.target.value })
              }
            />
          </label>
          <div className="form-grid">
            <label>
              {draft.kind === "appointment" ? "Date" : "Due date (optional)"}
              <input
                type="date"
                value={fields.date}
                onChange={(e) => setFields({ ...fields, date: e.target.value })}
              />
            </label>
            {draft.kind === "appointment" && (
              <label>
                Start time
                <input
                  type="time"
                  value={fields.start}
                  onChange={(e) =>
                    setFields({ ...fields, start: e.target.value })
                  }
                />
              </label>
            )}
            <label>
              Estimated minutes
              <input
                type="number"
                min={5}
                max={480}
                value={fields.minutes}
                onChange={(e) =>
                  setFields({ ...fields, minutes: Number(e.target.value) })
                }
              />
            </label>
          </div>
        </div>
      )}
      <div className="card-actions">
        <button
          className="small-button"
          disabled={busy}
          onClick={() =>
            act("decideSuggestion", {
              id: draft.id,
              decision: "accept",
              ...fields,
              start:
                Number(fields.start.split(":")[0]) * 60 +
                Number(fields.start.split(":")[1]),
            })
          }
        >
          <Check size={16} />{" "}
          {draft.kind === "appointment" ? "Add appointment" : "Add to Backlog"}
        </button>
        <button className="text-button" onClick={() => setEditing(!editing)}>
          {editing ? "Close edits" : "Adjust"}
        </button>
        <button
          className="text-button"
          disabled={busy}
          onClick={() =>
            act("decideSuggestion", { id: draft.id, decision: "dismiss" })
          }
        >
          Set aside
        </button>
      </div>
    </section>
  );
}
export function SuggestionInbox({
  state,
  act,
  busy,
}: {
  state: State;
  act: Action;
  busy: boolean;
}) {
  const [showAll, setShowAll] = useState(false);
  const pending = (state.suggestions || []).filter(
    (s) => s.status === "pending",
  );
  return (
    <>
      <div className="section-heading">
        <div>
          <h2>A few decisions, when you’re ready</h2>
          <p className="muted">
            Add a useful task to Backlog or confirm an appointment. Tasks are
            not assigned a time here. Nothing is added until you choose.
          </p>
        </div>
        <span className="tag">
          {Math.min(pending.length, showAll ? pending.length : 3)} to consider
        </span>
      </div>
      <div className="card">
        <label className="toggle-row">
          <input
            type="checkbox"
            checked={state.settings.suggestFromMessages !== false}
            disabled={busy}
            onChange={(e) =>
              act("settings", { suggestFromMessages: e.target.checked })
            }
          />{" "}
          Let Clara draft next steps from captured Gmail, Chrome and WhatsApp
          evidence
        </label>
        <p className="muted">
          Uses the planning laptop while it is awake. NHS captures and file
          activity are excluded from drafting. Pausing Clara pauses drafting
          too.
        </p>
      </div>
      {pending.length ? (
        <div className="goals-grid">
          {(showAll ? pending : pending.slice(0, 3)).map((d) => (
            <DraftCard key={d.id} draft={d} act={act} busy={busy} />
          ))}
        </div>
      ) : (
        <div className="card empty">
          <Sparkles />
          <p>
            Nothing needs your decision right now. Your existing plan is ready
            to use; there is no activity checklist to clear.
          </p>
        </div>
      )}
      {pending.length > 3 && (
        <button className="text-button" onClick={() => setShowAll(!showAll)}>
          {showAll ? "Show just three" : "See other suggestions (optional)"}
        </button>
      )}
    </>
  );
}
