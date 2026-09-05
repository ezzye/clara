import { SourceContext } from "./SourceContext";
import { useEffect, useState } from "react";
import type { Meeting, State } from "./api";

const time = (n: number) =>
  `${String(Math.floor(n / 60)).padStart(2, "0")}:${String(n % 60).padStart(2, "0")}`;
const minute = (s: string) => Number(s.slice(0, 2)) * 60 + Number(s.slice(3));
type Action = (name: string, data?: unknown) => Promise<unknown>;

export function MeetingPrep({
  state,
  act,
  busy,
  today,
}: {
  state: State;
  act: Action;
  busy: boolean;
  today: string;
}) {
  const [filter, setFilter] = useState("upcoming");
  const events = state.events
    .filter(
      (e) =>
        filter === "all" ||
        (e.date >= today &&
          !["cancelled", "superseded"].includes(e.status || "")),
    )
    .sort((a, b) => a.date.localeCompare(b.date) || a.start - b.start);
  return (
    <>
      <div className="section-heading">
        <p className="muted">
          Preparation time, checked details and feeling ready are separate
          steps.
        </p>
        <label>
          Show appointments
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="upcoming">Upcoming</option>
            <option value="all">All, including removed</option>
          </select>
        </label>
      </div>
      {!events.length && (
        <div className="card empty">
          <h2>No appointments in this view.</h2>
          <p>Bring in a calendar entry or add your next appointment.</p>
        </div>
      )}
      <div className="goals-grid">
        {events.map((e) => (
          <MeetingCard
            key={e.id}
            meeting={e}
            act={act}
            busy={busy}
            paused={state.settings.paused}
            today={today}
          />
        ))}
      </div>
    </>
  );
}

function MeetingCard({
  meeting: e,
  act,
  busy,
  paused,
  today,
}: {
  meeting: Meeting;
  act: Action;
  busy: boolean;
  paused: boolean;
  today: string;
}) {
  const [notes, setNotes] = useState(e.notes);
  const [confirmed, setConfirmed] = useState(e.confirmed);
  const [prepared, setPrepared] = useState(e.prepared || false);
  const [editing, setEditing] = useState(false);
  useEffect(() => {
    setNotes(e.notes);
    setConfirmed(e.confirmed);
    setPrepared(e.prepared || false);
  }, [e.notes, e.confirmed, e.prepared]);
  const prep = e.preparation;
  const cancelled = e.status === "cancelled" || e.status === "superseded";
  const unresolved = e.status === "needs_confirmation";
  const before = new Date(e.date + "T12:00:00Z");
  before.setUTCDate(before.getUTCDate() - 6);
  const planStart = [today, before.toISOString().slice(0, 10)].sort().at(-1)!;
  const days = Math.max(
    1,
    Math.min(
      7,
      Math.round((Date.parse(e.date) - Date.parse(planStart)) / 86400000) + 1,
    ),
  );
  return (
    <section className="card meeting-card">
      <span className="tag">
        {unresolved
          ? "Date awaiting confirmation"
          : `${e.date} · ${time(e.start)} · ${e.minutes} min · London time`}
      </span>
      <h2>{e.title}</h2>
      <SourceContext context={e.sourceContext} />
      <p className="muted">
        {e.confirmed
          ? "Appointment details checked by you."
          : "Please check the date, time and duration against the original source."}
      </p>
      <div className="definition" role="status">
        <strong>
          {
            {
              "needs-confirmation": "Check replacement letter",
              superseded: "Superseded",
              review: "Review readiness",
              ready: "Ready",
              reserved: "Time reserved",
              "needs-time": "Needs preparation time",
              none: "No preparation requested",
              cancelled: "Removed from plan",
              past: "Past appointment",
            }[prep?.status || "needs-time"]
          }
        </strong>
        <p>
          {prep?.message ||
            "Plan the days before this appointment to find preparation time."}
        </p>
        {prep?.date && (
          <p>
            {prep.date} at {time(prep.start!)} · {prep.minutes} minutes
          </p>
        )}
      </div>
      {!cancelled && !unresolved && e.date >= today && (
        <button
          className="small-button"
          disabled={busy || paused}
          onClick={() => act("plan", { date: planStart, days })}
        >
          Plan preparation & nearby days
        </button>
      )}
      {!cancelled && (
        <small>
          Planning may update unprotected task blocks in those days. Your locked
          blocks stay in place.
        </small>
      )}
      {!cancelled && (
        <form
          onSubmit={(ev) => {
            ev.preventDefault();
            act("saveMeeting", { id: e.id, notes, confirmed, prepared });
          }}
        >
          <ol className="prep-checklist">
            <li>
              What is the purpose, and what contribution is needed from me?
            </li>
            <li>Read the relevant material; note what remains unclear.</li>
            <li>
              Write two questions and the decision or next step to capture.
            </li>
          </ol>
          <label>
            Briefing, reading links & questions
            <textarea
              rows={5}
              maxLength={2000}
              value={notes}
              onChange={(ev) => setNotes(ev.target.value)}
              placeholder="What I know, what I need to read, what I want to ask…"
            />
          </label>
          <label className="meeting-check">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(ev) => setConfirmed(ev.target.checked)}
            />
            I checked the appointment details
          </label>
          <label className="meeting-check">
            <input
              type="checkbox"
              checked={prepared}
              onChange={(ev) => setPrepared(ev.target.checked)}
            />
            I have prepared enough to take part
          </label>
          <button className="small-button" disabled={busy}>
            Save preparation review
          </button>
        </form>
      )}
      <small className="source">Source: {e.source}</small>
      <div className="section-heading">
        {!cancelled && (
          <button
            className="text-button"
            disabled={busy}
            onClick={() => setEditing(!editing)}
          >
            {editing ? "Close details" : "Edit appointment"}
          </button>
        )}
        <button
          className="text-button"
          disabled={busy}
          onClick={() =>
            act("eventStatus", {
              id: e.id,
              status: cancelled ? "scheduled" : "cancelled",
            })
          }
        >
          {cancelled ? "Restore to Clara" : "Remove from Clara’s plan"}
        </button>
      </div>
      <small>
        Changes here affect Clara only. They do not change invitations or send
        messages.
      </small>
      {editing && !cancelled && (
        <form
          onSubmit={async (ev) => {
            ev.preventDefault();
            const d = Object.fromEntries(new FormData(ev.currentTarget));
            const result = await act("editEvent", {
              ...d,
              id: e.id,
              start: minute(String(d.start)),
              minutes: Number(d.minutes),
              prepMinutes: Number(d.prepMinutes),
            });
            if (result) setEditing(false);
          }}
        >
          <label>
            Appointment name
            <input
              name="title"
              required
              maxLength={180}
              defaultValue={e.title}
            />
          </label>
          <div className="form-row">
            <label>
              Date
              <input type="date" name="date" required defaultValue={e.date} />
            </label>
            <label>
              Time in London
              <input
                type="time"
                name="start"
                required
                defaultValue={time(e.start)}
              />
            </label>
          </div>
          <div className="form-row">
            <label>
              Duration in minutes
              <input
                type="number"
                name="minutes"
                required
                min={5}
                max={720}
                defaultValue={e.minutes}
              />
            </label>
            <label>
              Preparation in minutes
              <input
                type="number"
                name="prepMinutes"
                required
                min={0}
                max={120}
                defaultValue={e.prepMinutes}
              />
            </label>
          </div>
          <button className="small-button" disabled={busy}>
            Save appointment details
          </button>
        </form>
      )}
    </section>
  );
}
