import { useState } from "react";
import type { State, Task, InventoryItem } from "./api";

export function InventoryView({
  state,
  act,
  busy,
  onEdit,
}: {
  state: State;
  act: (name: string, data?: unknown) => Promise<unknown>;
  busy: boolean;
  onEdit: (t: Task) => void;
}) {
  const [context, setContext] = useState("personal"),
    [kind, setKind] = useState("all"),
    [status, setStatus] = useState("unfinished"),
    [search, setSearch] = useState(""),
    [sort, setSort] = useState("review");
  const items = state.inventory || [];
  const finished = (r: InventoryItem) =>
    ["done", "delivered", "cancelled", "superseded"].includes(r.status);
  const counts = (ctx: string) =>
    items.filter((r) => r.context === ctx && !finished(r)).length;
  const rows = items
    .filter(
      (r) =>
        r.context === context &&
        (kind === "all" || kind === r.kind) &&
        (status === "all" ||
          (status === "finished" && finished(r)) ||
          (status === "unfinished" && !finished(r)) ||
          (status === "review" &&
            r.kind === "project" &&
            r.status === "needs_review") ||
          (status === "parked" && r.status === "parked")) &&
        `${r.title} ${r.source} ${r.detail}`
          .toLowerCase()
          .includes(search.toLowerCase()),
    )
    .sort((a, b) =>
      sort === "title"
        ? a.title.localeCompare(b.title)
        : sort === "date"
          ? (a.date || "9999").localeCompare(b.date || "9999")
          : sort === "priority"
            ? b.priority - a.priority
            : a.status === "needs_review" && b.status !== "needs_review"
              ? -1
              : b.status === "needs_review" && a.status !== "needs_review"
                ? 1
                : b.priority - a.priority || a.title.localeCompare(b.title),
    );
  const sources = (state.inventorySources || []).filter(
    (r) => r.context === context,
  );
  async function move(row: InventoryItem, value: string) {
    if (row.kind === "task")
      await act("taskContext", { id: row.id, context: value });
    else if (row.kind === "project")
      await act("reviewProject", { id: row.id, context: value });
    else await act("editEvent", { id: row.id, context: value });
  }
  return (
    <>
      <div className="section-heading">
        <div>
          <h2>Your complete picture, one area at a time.</h2>
          <p>
            Sort the known inventory here. Source gaps stay visible until
            checked. New project discoveries wait for your review before
            becoming scheduled tasks.
          </p>
        </div>
      </div>
      <div className="segmented" aria-label="Work or Home">
        {[
          ["personal", "Home"],
          ["work", "Work"],
        ].map(([key, label]) => (
          <button
            key={key}
            className={context === key ? "active" : ""}
            onClick={() => setContext(key)}
          >
            {label} · {counts(key)}
          </button>
        ))}
      </div>
      <div className="card">
        <h3>Source coverage</h3>
        <p className="muted">
          “Checked” covers the stated source and scope at that time. It does not
          establish that projects are finished.
        </p>
        {!sources.length && (
          <p>No source inventory has been verified for this area.</p>
        )}
        {sources.map((s) => (
          <div className="inventory-source" key={s.id}>
            <strong>{s.label}</strong>
            <span className="tag">
              {s.status === "checked"
                ? "Snapshot checked"
                : s.status === "partial"
                  ? "Incomplete"
                  : s.status === "unavailable"
                    ? "Unavailable"
                    : "Not connected"}{" "}
              · {s.count} items
            </span>
            <p>{s.note}</p>
            {s.checkedAt && (
              <small>
                Checked {new Date(s.checkedAt).toLocaleString("en-GB")}
              </small>
            )}
          </div>
        ))}
      </div>
      <div className="inventory-controls">
        <label>
          Find an item
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search titles and sources"
          />
        </label>
        <label>
          Show
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="all">Everything</option>
            <option value="project">Projects and Cowork sessions</option>
            <option value="task">Tasks</option>
            <option value="meeting">Meetings and events</option>
          </select>
        </label>
        <label>
          Status
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="unfinished">All outstanding</option>
            <option value="review">Projects to sort</option>
            <option value="parked">Parked</option>
            <option value="finished">Finished or retired</option>
            <option value="all">All records</option>
          </select>
        </label>
        <label>
          Order
          <select value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="review">Projects to sort first</option>
            <option value="priority">My priority</option>
            <option value="title">Name</option>
            <option value="date">Date</option>
          </select>
        </label>
      </div>
      <p>
        {rows.length} items in this view. Projects and their linked tasks are
        separate records, not separate promises to do more work.
      </p>
      {!rows.length && (
        <div className="card">
          <p>
            No matching items. Check source coverage above before assuming
            nothing is outstanding.
          </p>
        </div>
      )}
      {rows.map((row) => (
        <section className="card" key={row.kind + row.id}>
          <div className="section-heading">
            <div>
              <span className="tag">
                {row.kind === "meeting"
                  ? "Fixed event"
                  : row.kind === "project"
                    ? "Project / session"
                    : "Task"}{" "}
                · {row.status.replaceAll("_", " ")}
                {row.coverage ? " · " + row.coverage : ""}
              </span>
              <h3>{row.title}</h3>
            </div>
            <div className="inventory-controls">
              <label>
                Area
                <select
                  aria-label={`Area for ${row.title}`}
                  disabled={busy}
                  value={row.context}
                  onChange={(e) => move(row, e.target.value)}
                >
                  <option value="personal">Home</option>
                  <option value="work">Work</option>
                </select>
              </label>
              {row.kind !== "meeting" && (
                <label>
                  Priority
                  <select
                    aria-label={`Priority for ${row.title}`}
                    disabled={busy}
                    value={row.priority}
                    onChange={(e) =>
                      act(
                        row.kind === "task" ? "taskPriority" : "reviewProject",
                        { id: row.id, priority: Number(e.target.value) },
                      )
                    }
                  >
                    <option value={3}>High</option>
                    <option value={2}>Medium</option>
                    <option value={1}>Low</option>
                  </select>
                </label>
              )}
            </div>
          </div>
          {row.date && (
            <p>
              {row.date}
              {row.start !== undefined
                ? " · " +
                  String(Math.floor(row.start / 60)).padStart(2, "0") +
                  ":" +
                  String(row.start % 60).padStart(2, "0")
                : ""}
              {row.kind === "meeting" && !row.confirmed
                ? " · Attendance unconfirmed"
                : ""}
            </p>
          )}
          {row.detail && <p>{row.detail}</p>}
          {row.kind === "project" && (
            <p className="muted">
              {row.linkedTasks || 0} unfinished linked tasks
            </p>
          )}
          <details>
            <summary>Source and actions</summary>
            <p className="source">{row.source}</p>
            {row.kind === "task" && (
              <div className="card-actions">
                <button
                  onClick={() =>
                    onEdit(state.tasks.find((t) => t.id === row.id)!)
                  }
                >
                  Edit next step
                </button>
                <button
                  disabled={busy}
                  onClick={() =>
                    act("taskStatus", {
                      id: row.id,
                      status: row.status === "parked" ? "open" : "parked",
                    })
                  }
                >
                  {row.status === "parked" ? "Unpark" : "Park"}
                </button>
                <button
                  disabled={busy}
                  onClick={() =>
                    act("taskStatus", {
                      id: row.id,
                      status: row.status === "done" ? "open" : "done",
                    })
                  }
                >
                  {row.status === "done" ? "Reopen" : "Mark finished"}
                </button>
              </div>
            )}
            {row.kind === "project" && (
              <ProjectActions key={row.id} row={row} act={act} busy={busy} />
            )}
            {row.kind === "meeting" && (
              <p>
                Manage the time, confirmation and preparation in Meetings. This
                inventory does not infer attendance.
              </p>
            )}
          </details>
        </section>
      ))}
    </>
  );
}
function ProjectActions({
  row,
  act,
  busy,
}: {
  row: InventoryItem;
  act: (name: string, data?: unknown) => Promise<unknown>;
  busy: boolean;
}) {
  const [next, setNext] = useState(""),
    [finish, setFinish] = useState(""),
    [proof, setProof] = useState("");
  return (
    <>
      <div className="card-actions">
        <button
          disabled={busy}
          onClick={() =>
            act("reviewProject", {
              id: row.id,
              stage: row.status === "parked" ? "needs_review" : "parked",
            })
          }
        >
          {row.status === "parked" ? "Return to sorting" : "Park for now"}
        </button>
        <button
          disabled={busy}
          onClick={() =>
            act("reviewProject", { id: row.id, stage: "needs_review" })
          }
        >
          Needs review
        </button>
      </div>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          await act("commitProject", {
            id: row.id,
            outcome: finish,
            nextStep: next,
            doneWhen: finish,
            minutes: 25,
          });
          setNext("");
          setFinish("");
        }}
      >
        <h4>Make one next step ready to plan</h4>
        <label>
          Next action
          <input
            required
            maxLength={500}
            value={next}
            onChange={(e) => setNext(e.target.value)}
          />
        </label>
        <label>
          Useful finish line
          <input
            required
            maxLength={500}
            value={finish}
            onChange={(e) => setFinish(e.target.value)}
          />
        </label>
        <button disabled={busy || !next.trim() || !finish.trim()}>
          Add / update its next task
        </button>
      </form>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          await act("reviewProject", { id: row.id, stage: "delivered", proof });
          setProof("");
        }}
      >
        <label>
          Already finished? Record what you checked
          <input
            minLength={10}
            maxLength={1000}
            value={proof}
            onChange={(e) => setProof(e.target.value)}
          />
        </label>
        <button
          disabled={busy || proof.trim().length < 10 || !!row.linkedTasks}
        >
          Mark project finished
        </button>
      </form>
    </>
  );
}
