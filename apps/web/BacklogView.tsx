import { useState } from "react";
import { ArrowUpRight, ListTodo } from "lucide-react";
import type { State, Task } from "./api";
export function BacklogView({
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
  const [filter, setFilter] = useState("unscheduled"),
    [sort, setSort] = useState("consideration");
  const backlog = state.backlog || [];
  const tasks = new Map(state.tasks.map((t) => [t.id, t]));
  const count = (value: string) =>
    backlog.filter((r) =>
      value === "unscheduled"
        ? ["unscheduled", "partial"].includes(r.coverage)
        : r.coverage === value,
    ).length;
  const rows = backlog
    .filter(
      (r) =>
        filter === "all" ||
        (filter === "unscheduled"
          ? ["unscheduled", "partial"].includes(r.coverage)
          : r.coverage === filter),
    )
    .slice()
    .sort((a, b) =>
      sort === "priority"
        ? tasks.get(b.id)!.priority - tasks.get(a.id)!.priority ||
          b.score - a.score
        : sort === "due"
          ? (tasks.get(a.id)!.due || "9999").localeCompare(
              tasks.get(b.id)!.due || "9999",
            )
          : b.score - a.score,
    );
  const last = state.planner.lastConsidered;
  return (
    <>
      <div className="stats">
        <div className="card">
          <p>Known unfinished tasks</p>
          <strong>{backlog.length}</strong>
        </div>
        <div className="card">
          <p>Need more scheduled time</p>
          <strong>{count("unscheduled")}</strong>
        </div>
        <div className="card">
          <p>Parked by you</p>
          <strong>{count("parked")}</strong>
        </div>
      </div>
      <div className="card">
        <h2>See what went into the plan.</h2>
        <p>
          Your priority is one factor, alongside deadlines, preparation, project
          finishing and Clara’s recommendation. Available time, protected
          appointments, energy and the daily task limit decide what fits.
        </p>
        <p className="muted">
          This list is complete for tasks Clara currently knows about.
          Unconnected accounts and uncaptured commitments can still be missing.
        </p>
        {last ? (
          <p>
            Last planning pass: {new Date(last.at).toLocaleString("en-GB")} ·{" "}
            {last.openCount} open tasks considered · {last.days} day window from{" "}
            {last.date}.
          </p>
        ) : (
          <p>
            No recorded planning pass yet. Use “Plan my day” to produce a trace
            of what was considered.
          </p>
        )}
      </div>
      <div className="section-heading">
        <div className="segmented">
          {[
            ["unscheduled", "Needs time"],
            ["scheduled", "Scheduled"],
            ["parked", "Parked"],
            ["all", "All unfinished"],
          ].map(([key, label]) => (
            <button
              key={key}
              className={filter === key ? "active" : ""}
              onClick={() => setFilter(key)}
            >
              {label}
            </button>
          ))}
        </div>
        <label>
          Sort by{" "}
          <select value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="consideration">Planner factors</option>
            <option value="priority">My priority</option>
            <option value="due">Due date</option>
          </select>
        </label>
      </div>
      {!rows.length && (
        <div className="card empty">
          <ListTodo />
          <p>No tasks in this view.</p>
        </div>
      )}
      {rows.map((row) => {
        const task = tasks.get(row.id)!;
        return (
          <section className="card backlog-row" key={row.id}>
            <div className="section-heading">
              <div>
                <span className="tag">
                  {row.coverage === "partial"
                    ? "Partly scheduled"
                    : row.coverage === "unscheduled"
                      ? "No future time reserved"
                      : row.coverage === "parked"
                        ? "Parked"
                        : "Time reserved"}
                </span>
                <h3>{task.title}</h3>
              </div>
              <label>
                Your priority
                <select
                  aria-label={`Priority for ${task.title}`}
                  value={task.priority}
                  disabled={busy}
                  onChange={(e) =>
                    act("taskPriority", {
                      id: task.id,
                      priority: Number(e.target.value),
                    })
                  }
                >
                  <option value={3}>High</option>
                  <option value={2}>Medium</option>
                  <option value={1}>Low</option>
                </select>
              </label>
            </div>
            <p>{task.nextStep}</p>
            <p className="muted">
              {task.minutes} estimated minutes · {row.reservedMinutes} reserved
              {task.due ? ` · due ${task.due}` : ""}
            </p>
            <details>
              <summary>Why it is here</summary>
              <p>{row.lastDecision}</p>
              <small>
                {row.consideredAt
                  ? "Decision recorded " +
                    new Date(row.consideredAt).toLocaleString("en-GB")
                  : "New or not yet assessed in a recorded planning pass."}{" "}
                Current priority edits apply on the next planning pass.
              </small>
              <ul>
                {row.factors.map((f) => (
                  <li key={f.label}>
                    {f.label}: {f.points} points
                  </li>
                ))}
              </ul>
              <p className="muted">
                {row.modelConsidered === null
                  ? "Model coverage has not yet been recorded."
                  : row.modelConsidered
                    ? "Included in the latest model context."
                    : "Not in the latest model context; the scheduler still considers it using the other factors."}
              </p>
              <p className="source">Source: {task.source}</p>
            </details>
            <div className="card-actions">
              <button className="text-button" onClick={() => onEdit(task)}>
                Adjust task <ArrowUpRight size={15} />
              </button>
              <button
                className="text-button"
                disabled={busy}
                onClick={() =>
                  act("taskStatus", {
                    id: task.id,
                    status: task.status === "parked" ? "open" : "parked",
                  })
                }
              >
                {task.status === "parked"
                  ? "Return to consideration"
                  : "Park for now"}
              </button>
            </div>
          </section>
        );
      })}
    </>
  );
}
