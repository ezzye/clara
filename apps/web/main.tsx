import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  Sun,
  CalendarDays,
  Target,
  BookOpen,
  Layers,
  BarChart3,
  Link2,
  Settings,
  ArrowUpRight,
  ArrowRight,
  Plus,
  Play,
  Pause,
  Check,
  Lock,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Leaf,
  X,
  Clock,
  RefreshCw,
  ShieldCheck,
  Monitor,
  Download,
  Heart,
} from "lucide-react";
import {
  api,
  initialize,
  config,
  signIn,
  signOut,
  type State,
  type Task,
  type Block,
  type Meeting,
} from "./api";
import "./style.css";
import { LifeView } from "./LifeView";
const today = () =>
  new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/London",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
const time = (n: number) =>
  `${Math.floor(n / 60)
    .toString()
    .padStart(2, "0")}:${(n % 60).toString().padStart(2, "0")}`;
const mins = (s: string) =>
  Number(s.split(":")[0]) * 60 + Number(s.split(":")[1]);
const addDays = (d: string, n: number) => {
  const v = new Date(d + "T12:00:00");
  v.setDate(v.getDate() + n);
  return `${v.getFullYear()}-${String(v.getMonth() + 1).padStart(2, "0")}-${String(v.getDate()).padStart(2, "0")}`;
};
const niceDate = (d: string) =>
  new Date(d + "T12:00:00").toLocaleDateString("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
const nav = [
  ["Now", Sun],
  ["Plan", CalendarDays],
  ["Meeting prep", BookOpen],
  ["Projects", Layers],
  ["Life", Heart],
  ["Review", BarChart3],
  ["Connections", Link2],
  ["Preferences", Settings],
] as const;
function App() {
  const [state, setState] = useState<State | null>(null),
    [error, setError] = useState(""),
    [view, setView] = useState("Now"),
    [horizon, setHorizon] = useState("Day"),
    [date, setDate] = useState(today()),
    [busy, setBusy] = useState(false),
    [modal, setModal] = useState(""),
    [editing, setEditing] = useState<Task | null>(null),
    [message, setMessage] = useState(""),
    [tick, setTick] = useState(Date.now()),
    [deviceToken, setDeviceToken] = useState("");
  useEffect(() => {
    initialize()
      .then(setState)
      .catch((e) => setError(e.message));
    const t = setInterval(() => setTick(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  useEffect(() => {
    if (!state) return;
    const t = setInterval(
      () =>
        api("/api/state")
          .then(setState)
          .catch(() => {}),
      30000,
    );
    return () => clearInterval(t);
  }, [!!state]);
  useEffect(() => {
    if (!modal) return;
    const previous = document.activeElement as HTMLElement;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setModal("");
      if (e.key === "Tab") {
        const elements = Array.from(
          document.querySelectorAll<HTMLElement>(
            ".modal button:not(:disabled),.modal input,.modal textarea,.modal select",
          ),
        );
        const first = elements[0],
          last = elements[elements.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey);
    document
      .querySelector<HTMLElement>(".modal input,.modal textarea,.modal button")
      ?.focus();
    return () => {
      document.removeEventListener("keydown", onKey);
      previous?.focus();
    };
  }, [modal]);
  async function act(action: string, data: unknown = {}) {
    if (!state || busy) return;
    setBusy(true);
    setError("");
    try {
      const res = await api("/api/action", {
        revision: state.revision,
        action,
        data,
      });
      setState(res.state);
      if (res.deviceToken) setDeviceToken(res.deviceToken);
      return res;
    } catch (e) {
      setError((e as Error).message);
      await api("/api/state")
        .then(setState)
        .catch(() => {});
    } finally {
      setBusy(false);
    }
  }
  async function save(
    e: React.FormEvent<HTMLFormElement>,
    action: string,
    convert: (d: Record<string, FormDataEntryValue>) => unknown,
  ) {
    e.preventDefault();
    const d = Object.fromEntries(new FormData(e.currentTarget));
    if (await act(action, convert(d))) {
      setModal("");
      setEditing(null);
    }
  }
  if (!state)
    return (
      <main className="signin">
        <div className="wordmark">
          <span className="logo">
            <Leaf />
          </span>
          clara<span className="dot">.</span>
        </div>
        <h1>A little more headspace.</h1>
        <p>Your private place to prepare, focus and finish.</p>
        {error && <p className="notice">{error}</p>}
        {config.mode === "aws" ? (
          <button className="primary" onClick={signIn}>
            Open my private space <ArrowRight size={18} />
          </button>
        ) : (
          <p>
            Open the private launch link from the Clara companion on this
            laptop.
          </p>
        )}
        <small>
          <Lock size={14} /> Only the owner can access plans and activity.
        </small>
      </main>
    );
  const blocks = state.plan.filter((b) => b.date === date),
    openTasks = state.tasks.filter((t) => t.status === "open");
  const active = state.plan.find((b) => b.status === "active");
  const next =
    active ||
    blocks.find(
      (b) =>
        !["done", "skipped"].includes(b.status) &&
        b.kind !== "break" &&
        b.kind !== "event",
    );
  const nextTask = state.tasks.find((t) => t.id === next?.taskId);
  const elapsed = active?.startedAt
    ? Math.max(
        0,
        Math.floor((tick - new Date(active.startedAt).getTime()) / 1000),
      )
    : 0;
  const remaining = active
    ? Math.max(0, active.minutes * 60 - elapsed)
    : state.settings.focusMinutes * 60;
  const evidence = state.evidence.filter((e) => e.status === "unreviewed");
  const done = blocks.filter((b) => b.status === "done" && b.kind !== "break");
  const totalMinutes = blocks
    .filter((b) => b.kind !== "break")
    .reduce((a, b) => a + b.minutes, 0);
  const makePlan = (days = 1) => act("plan", { date, days });
  const showTask = (task?: Task) => {
    setEditing(task || null);
    setModal("task");
  };
  const exportData = () => {
    const blob = new Blob([JSON.stringify(state, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "clara-private-export.json";
    a.click();
    URL.revokeObjectURL(url);
  };
  const row = (b: Block) => (
    <article key={b.id} className={`plan-row ${b.kind} ${b.status}`}>
      <div className="row-time">
        {time(b.start)}
        <small>{b.minutes} min</small>
      </div>
      <div className="row-marker" />
      <div className="row-main">
        <div className="row-title">
          {b.title}
          {b.locked && <Lock size={13} />}
        </div>
        <small>
          {b.kind === "event"
            ? "Appointment · attendance unconfirmed"
            : b.status === "done"
              ? "Session complete"
              : b.reason}
        </small>
      </div>
      <button
        className="icon-button"
        aria-label={`Edit ${b.title}`}
        onClick={() => {
          setMessage(b.id);
          setModal("block");
        }}
      >
        <ArrowUpRight size={18} />
      </button>
    </article>
  );
  return (
    <div className="app">
      <aside className="sidebar">
        <a
          className="wordmark"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setView("Now");
          }}
        >
          <span className="logo">
            <Leaf size={23} />
          </span>
          clara<span className="dot">.</span>
        </a>
        <div className="workspace">
          <span className="avatar">E</span>
          <div>
            Your space<small>Private by design</small>
          </div>
          <Lock size={13} />
        </div>
        <p className="eyebrow nav-label">A LITTLE MORE HEADSPACE</p>
        <nav>
          {nav.map(([name, Icon]) => (
            <button
              key={name}
              className={view === name ? "selected" : ""}
              onClick={() => setView(name)}
            >
              <Icon size={19} />
              {name}
              {name === "Review" && evidence.length > 0 && (
                <span className="badge">{evidence.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="companion">
            <span
              className={`status-light ${state.settings.paused ? "paused" : ""}`}
            />
            <strong>
              {state.settings.paused ? "Taking a pause" : "Your plan is here"}
            </strong>
            <p>
              {state.settings.paused
                ? "New collection and planning are paused."
                : "One useful next step at a time."}
            </p>
            <button
              onClick={() =>
                act("settings", { paused: !state.settings.paused })
              }
            >
              {state.settings.paused ? <Play size={14} /> : <Pause size={14} />}{" "}
              {state.settings.paused ? "Resume" : "Pause collection"}
            </button>
          </div>
          <button className="quiet" onClick={signOut}>
            <ShieldCheck size={15} />{" "}
            {config.mode === "aws" ? "Sign out" : "This laptop only"}
          </button>
        </div>
      </aside>
      <div className="page">
        <header className="topbar">
          <div>
            <span className="crumb">Your space</span>
            <ChevronRight size={14} />
            <span>{view}</span>
          </div>
          <div>
            <span className="private-label">
              <Lock size={13} /> Only you
            </span>
            <button className="small-button" onClick={() => showTask()}>
              <Plus size={16} /> Capture a thought
            </button>
          </div>
        </header>
        <main className="content">
          {error && (
            <div className="notice" role="alert">
              {error}
              <button aria-label="Dismiss error" onClick={() => setError("")}>
                <X size={15} />
              </button>
            </div>
          )}
          <div className="page-heading">
            <div>
              <p className="eyebrow">
                {view === "Now"
                  ? niceDate(date).toUpperCase()
                  : "YOUR SPACE, AT YOUR PACE"}
              </p>
              <h1>
                {view === "Now"
                  ? "Make room for what matters."
                  : view === "Plan"
                    ? "A plan you can change."
                    : view === "Meeting prep"
                      ? "Walk in prepared."
                      : view === "Life"
                        ? "Make space for a fuller life."
                        : view === "Projects"
                          ? "Less starting. More finishing."
                          : view === "Review"
                            ? "Notice what actually helped."
                            : view === "Connections"
                              ? "Your world, brought together."
                              : "Make Clara work for you."}
              </h1>
              <p>
                {view === "Now"
                  ? "A manageable day. A clear next step. Space to be a person."
                  : view === "Plan"
                    ? "Keep the important things close and leave room for life."
                    : view === "Meeting prep"
                      ? "Know the purpose, read what matters, and bring your questions."
                      : view === "Life"
                        ? "Sleep, health, connection and a more secure future count as progress."
                        : view === "Projects"
                          ? "Turn active ideas into a small number of useful outcomes."
                          : view === "Review"
                            ? "Activity is a clue. You decide what it means."
                            : view === "Connections"
                              ? "Connect deliberately. See what arrived. Pause whenever you need."
                              : "Choose a rhythm that feels sustainable."}
              </p>
            </div>
            {["Now", "Plan"].includes(view) && (
              <button
                className="primary"
                disabled={busy || state.settings.paused}
                onClick={() => makePlan(horizon === "Week" ? 7 : 1)}
              >
                <Sparkles size={17} /> {busy ? "Planning…" : "Plan for me"}
              </button>
            )}
          </div>
          {view === "Now" && (
            <>
              <div className="day-strip">
                <div>
                  <Sun size={19} />
                  <strong>How much room do you have today?</strong>
                </div>
                <div className="segmented">
                  {["low", "steady", "high"].map((e) => (
                    <button
                      key={e}
                      className={state.settings.energy === e ? "active" : ""}
                      onClick={() => act("settings", { energy: e })}
                    >
                      {e === "low"
                        ? "A little"
                        : e === "steady"
                          ? "Steady"
                          : "Plenty"}
                    </button>
                  ))}
                </div>
              </div>
              <div className="now-grid">
                <section className="focus-card">
                  <div className="focus-top">
                    <span className="pill">
                      <span className="status-light" />
                      {active ? "IN FOCUS" : "YOUR NEXT SMALL STEP"}
                    </span>
                    <span>
                      {next?.minutes || state.settings.focusMinutes} min
                    </span>
                  </div>
                  <h2>{next?.title || "Choose one thing worth finishing."}</h2>
                  <p>
                    {nextTask?.nextStep ||
                      next?.reason ||
                      "Clara can turn your priorities into a gentle plan. Start with “Plan for me”, or capture one thing on your mind."}
                  </p>
                  <div className="finish-line">
                    <Check size={17} />
                    <div>
                      <span>You can stop when</span>
                      <p>
                        {nextTask?.doneWhen ||
                          "you have a clear result and a note about what comes next."}
                      </p>
                    </div>
                  </div>
                  <div className="focus-bottom">
                    <button
                      className="light-button"
                      disabled={!next || busy}
                      onClick={() =>
                        active
                          ? act("block", {
                              id: active.id,
                              status: "done",
                              actualMinutes: Math.ceil(elapsed / 60),
                            })
                          : next &&
                            act("block", { id: next.id, status: "active" })
                      }
                    >
                      {active ? <Check size={17} /> : <Play size={17} />}{" "}
                      {active ? "Finish this session" : "Begin gently"}
                    </button>
                    <span className="timer">
                      {String(Math.floor(remaining / 60)).padStart(2, "0")}:
                      {String(remaining % 60).padStart(2, "0")}
                      <small>
                        {active
                          ? "remaining · no alarm"
                          : "one thing at a time"}
                      </small>
                    </span>
                  </div>
                </section>
                <section className="card intentions">
                  <p className="eyebrow">TODAY’S ANCHORS</p>
                  <h2>Keep it small.</h2>
                  <div className="anchor">
                    <span>01</span>
                    <div>
                      <strong>Prepare before joining</strong>
                      <p>Make space to understand the meeting.</p>
                    </div>
                  </div>
                  <div className="anchor">
                    <span>02</span>
                    <div>
                      <strong>Finish something useful</strong>
                      <p>A reviewed outcome beats another open project.</p>
                    </div>
                  </div>
                  <div className="anchor">
                    <span>03</span>
                    <div>
                      <strong>Leave room for life</strong>
                      <p>Meals, recovery and plans outside work count.</p>
                    </div>
                  </div>
                  <div className="soft-note">
                    <Leaf size={19} />
                    <p>You don’t need to earn a break.</p>
                  </div>
                </section>
              </div>
              <div className="lower-grid">
                <section className="card timeline">
                  <div className="section-heading">
                    <div>
                      <p className="eyebrow">THE SHAPE OF YOUR DAY</p>
                      <h2>A little structure. Some space.</h2>
                    </div>
                    <button
                      className="text-button"
                      onClick={() => setView("Plan")}
                    >
                      Edit your day <ArrowRight size={16} />
                    </button>
                  </div>
                  {blocks.length ? (
                    blocks.slice(0, 7).map(row)
                  ) : (
                    <div className="empty">
                      <CalendarDays />
                      <h3>Your day is still open.</h3>
                      <p>
                        Use the priorities already captured, or add an
                        appointment before planning.
                      </p>
                      <button
                        className="small-button"
                        onClick={() => makePlan()}
                      >
                        Make my first plan
                      </button>
                    </div>
                  )}
                </section>
                <section className="card">
                  <p className="eyebrow">BEFORE YOU NEED IT</p>
                  <h2>Prepare, then participate.</h2>
                  {state.events
                    .filter((e) => e.date >= today())
                    .slice(0, 2)
                    .map((e) => (
                      <div className="meeting-preview" key={e.id}>
                        <span className="tag">
                          {e.date} · {time(e.start)}
                        </span>
                        <h3>{e.title}</h3>
                        <p>
                          {e.confirmed
                            ? "Details reviewed by you."
                            : "Found in a source. Please check the details."}
                        </p>
                        <button
                          className="text-button"
                          onClick={() => setView("Meeting prep")}
                        >
                          Open preparation <ArrowUpRight size={16} />
                        </button>
                      </div>
                    ))}
                  {!state.events.length && (
                    <p className="muted">
                      Your work calendar is not connected yet. Clara won’t
                      invent meetings or assume an empty calendar means you’re
                      free.
                    </p>
                  )}
                  <div className="line" />
                  <p className="eyebrow">PLANNING STATUS</p>
                  <p className="muted">{state.planner.message}</p>
                  <small>
                    {state.planner.mode === "rules"
                      ? "Local scheduling rules · AI ranking not active"
                      : "AI-assisted priority proposal"}
                  </small>
                </section>
              </div>
            </>
          )}
          {view === "Plan" && (
            <>
              <div className="plan-controls">
                <div className="tabs">
                  {["Hour", "Day", "Week", "Month", "Year"].map((h) => (
                    <button
                      key={h}
                      className={horizon === h ? "active" : ""}
                      onClick={() => setHorizon(h)}
                    >
                      {h}
                    </button>
                  ))}
                </div>
                <div className="date-nav">
                  <button
                    aria-label="Previous day"
                    onClick={() => setDate(addDays(date, -1))}
                  >
                    <ChevronLeft size={18} />
                  </button>
                  <input
                    aria-label="Plan date"
                    type="date"
                    value={date}
                    onChange={(e) => setDate(e.target.value)}
                  />
                  <button
                    aria-label="Next day"
                    onClick={() => setDate(addDays(date, 1))}
                  >
                    <ChevronRight size={18} />
                  </button>
                  <button
                    className="text-button"
                    onClick={() => {
                      setDate(today());
                    }}
                  >
                    Today
                  </button>
                </div>
              </div>
              {["Hour", "Day"].includes(horizon) && (
                <div className="card">
                  <div className="section-heading">
                    <h2>{niceDate(date)}</h2>
                    <button
                      className="small-button"
                      onClick={() => setModal("event")}
                    >
                      <Plus size={15} /> Appointment
                    </button>
                  </div>
                  {(horizon === "Hour"
                    ? blocks.filter((b) => {
                        const n = new Date();
                        const m =
                          Number(
                            new Intl.DateTimeFormat("en-GB", {
                              timeZone: "Europe/London",
                              hour: "2-digit",
                              minute: "2-digit",
                              hour12: false,
                            })
                              .format(n)
                              .split(":")[0],
                          ) *
                            60 +
                          n.getMinutes();
                        return b.start < m + 60 && b.start + b.minutes > m;
                      })
                    : blocks
                  ).map(row)}
                  {!blocks.length && (
                    <div className="empty">
                      <p>No plan for this date yet.</p>
                      <button className="primary" onClick={() => makePlan()}>
                        Plan this day
                      </button>
                    </div>
                  )}
                </div>
              )}
              {horizon === "Week" && (
                <div className="week-grid">
                  {Array.from({ length: 7 }, (_, i) => addDays(date, i)).map(
                    (d) => (
                      <section className="card week-day" key={d}>
                        <h3>
                          {new Date(d + "T12:00:00").toLocaleDateString(
                            "en-GB",
                            { weekday: "short", day: "numeric" },
                          )}
                        </h3>
                        {state.plan
                          .filter((b) => b.date === d && b.kind !== "break")
                          .map((b) => (
                            <button
                              className={"week-block " + b.kind}
                              key={b.id}
                              onClick={() => {
                                setDate(d);
                                setHorizon("Day");
                              }}
                            >
                              <small>
                                {time(b.start)} · {b.minutes}m
                              </small>
                              {b.title}
                            </button>
                          ))}
                        <span className="muted">Leave some breathing room</span>
                      </section>
                    ),
                  )}
                </div>
              )}
              {["Month", "Year"].includes(horizon) && (
                <>
                  <div className="section-heading">
                    <h2>
                      {horizon === "Month"
                        ? new Date(date + "T12:00:00").toLocaleDateString(
                            "en-GB",
                            { month: "long", year: "numeric" },
                          )
                        : date.slice(0, 4)}{" "}
                      · outcomes before busywork
                    </h2>
                    <button
                      className="small-button"
                      onClick={() => setModal("goal")}
                    >
                      <Plus size={16} /> Add an outcome
                    </button>
                  </div>
                  {horizon === "Month" && (
                    <MonthGrid
                      date={date}
                      state={state}
                      onSelect={(d) => {
                        setDate(d);
                        setHorizon("Day");
                      }}
                    />
                  )}
                  {horizon === "Year" && (
                    <div className="year-grid">
                      {Array.from(
                        { length: 12 },
                        (_, i) =>
                          date.slice(0, 4) +
                          "-" +
                          String(i + 1).padStart(2, "0") +
                          "-01",
                      ).map((d) => (
                        <button
                          className="card month-tile"
                          key={d}
                          onClick={() => {
                            setDate(d);
                            setHorizon("Month");
                          }}
                        >
                          <strong>
                            {new Date(d + "T12:00:00").toLocaleDateString(
                              "en-GB",
                              { month: "long" },
                            )}
                          </strong>
                          <small>
                            {
                              state.goals.filter((g) =>
                                g.due.startsWith(d.slice(0, 7)),
                              ).length
                            }{" "}
                            outcomes ·{" "}
                            {
                              state.events.filter((e) =>
                                e.date.startsWith(d.slice(0, 7)),
                              ).length
                            }{" "}
                            appointments
                          </small>
                        </button>
                      ))}
                    </div>
                  )}
                  <div className="goals-grid">
                    {state.goals
                      .filter(
                        (g) =>
                          g.horizon === horizon.toLowerCase() &&
                          (!g.due ||
                            g.due.startsWith(
                              date.slice(0, horizon === "Month" ? 7 : 4),
                            )),
                      )
                      .map((g) => (
                        <section className="card" key={g.id}>
                          <span className="tag">
                            {g.due || "Date to decide"}
                          </span>
                          <h2>{g.title}</h2>
                          <p>{g.outcome}</p>
                          <button
                            className="small-button"
                            onClick={() =>
                              act("goalStatus", {
                                id: g.id,
                                done: g.status !== "done",
                              })
                            }
                          >
                            {g.status === "done" ? (
                              <Check size={16} />
                            ) : (
                              <Target size={16} />
                            )}{" "}
                            {g.status === "done"
                              ? "Achieved · reopen"
                              : "Mark achieved"}
                          </button>
                        </section>
                      ))}
                  </div>
                  <div className="card horizon-note">
                    <Target />
                    <div>
                      <h3>Long-term direction, not a year of time slots.</h3>
                      <p>
                        Set the result you want. Break it into a monthly
                        milestone, a weekly commitment, and the next small task.
                      </p>
                      <button
                        className="text-button"
                        onClick={() => showTask()}
                      >
                        Turn an outcome into a next step{" "}
                        <ArrowRight size={16} />
                      </button>
                    </div>
                  </div>
                </>
              )}
            </>
          )}
          {view === "Life" && (
            <LifeView state={state} act={act} onEdit={showTask} />
          )}
          {view === "Projects" && (
            <>
              <div className="section-heading">
                <div className="tabs">
                  {["Active", "Parked", "Finished"].map((h) => (
                    <button
                      key={h}
                      className={
                        message === h ||
                        (!["Parked", "Finished"].includes(message) &&
                          h === "Active")
                          ? "active"
                          : ""
                      }
                      onClick={() => setMessage(h)}
                    >
                      {h}
                    </button>
                  ))}
                </div>
                <button className="small-button" onClick={() => showTask()}>
                  <Plus size={16} /> Capture next step
                </button>
              </div>
              <div className="goals-grid">
                {state.tasks
                  .filter(
                    (t) =>
                      t.status ===
                      (message === "Parked"
                        ? "parked"
                        : message === "Finished"
                          ? "done"
                          : "open"),
                  )
                  .map((t) => (
                    <section className="card project-card" key={t.id}>
                      <div className="section-heading">
                        <span className={"tag " + t.category}>
                          {t.category === "development"
                            ? "Development goal"
                            : t.category}
                        </span>
                        <span className="muted">{t.minutes} min</span>
                      </div>
                      <h2>{t.title}</h2>
                      <p>{t.nextStep}</p>
                      <div className="definition">
                        <strong>Done looks like</strong>
                        <p>{t.doneWhen}</p>
                      </div>
                      <small className="source">Source: {t.source}</small>
                      <div className="card-actions">
                        <button
                          className="text-button"
                          onClick={() => showTask(t)}
                        >
                          Edit <ArrowUpRight size={15} />
                        </button>
                        <button
                          className="text-button"
                          onClick={() =>
                            act("taskStatus", {
                              id: t.id,
                              status: t.status === "open" ? "parked" : "open",
                            })
                          }
                        >
                          {t.status === "open" ? "Park for now" : "Reopen"}
                        </button>
                        {t.status !== "done" && (
                          <button
                            className="small-button"
                            onClick={() =>
                              act("taskStatus", { id: t.id, status: "done" })
                            }
                          >
                            <Check size={15} /> Finished
                          </button>
                        )}
                      </div>
                    </section>
                  ))}
              </div>
              {state.projects.length > 0 && (
                <>
                  <div className="section-heading">
                    <div>
                      <h2>Project inventory</h2>
                      <p className="muted">
                        A current checkout inventory, not yet a full delivery
                        assessment. Choose one to investigate.
                      </p>
                    </div>
                    <span className="tag">
                      {state.projects.length} projects
                    </span>
                  </div>
                  <div className="goals-grid">
                    {state.projects.map((p) => (
                      <section className="card" key={p.id}>
                        <h2>{p.title}</h2>
                        <p>{p.outcome}</p>
                        <p className="muted">{p.nextStep}</p>
                        <small className="source">{p.source}</small>
                        <button
                          className="small-button"
                          onClick={() =>
                            act("addTask", {
                              title: "Define a finish line for " + p.title,
                              category: "project",
                              projectId: p.id,
                              minutes: 25,
                              priority: 2,
                              nextStep: p.nextStep,
                              doneWhen:
                                "A useful result, its intended user and the smallest delivery gap are recorded.",
                              source: p.source,
                            })
                          }
                        >
                          Choose a finishing step <ArrowRight size={16} />
                        </button>
                      </section>
                    ))}
                  </div>
                </>
              )}
            </>
          )}
          {view === "Meeting prep" && (
            <>
              <div className="section-heading">
                <p className="muted">
                  Calendar appointments and preparation stay separate.
                </p>
                <button
                  className="small-button"
                  onClick={() => setModal("event")}
                >
                  <Plus size={16} /> Add appointment
                </button>
              </div>
              {state.events.length === 0 && (
                <div className="card empty">
                  <BookOpen />
                  <h2>No meetings imported yet.</h2>
                  <p>
                    Connect your work calendar on the work MacBook, or add the
                    next meeting.
                  </p>
                </div>
              )}
              <div className="goals-grid">
                {state.events
                  .filter((e) => e.date >= date)
                  .map((e) => (
                    <MeetingCard
                      key={e.id}
                      meeting={e}
                      onSave={(notes) =>
                        act("saveMeeting", { id: e.id, notes })
                      }
                    />
                  ))}
              </div>
            </>
          )}
          {view === "Review" && (
            <>
              <div className="stats">
                <div className="card">
                  <p>Planned today</p>
                  <strong>
                    {totalMinutes}
                    <small> minutes</small>
                  </strong>
                </div>
                <div className="card">
                  <p>Sessions you finished</p>
                  <strong>
                    {done.length}
                    <small>
                      {" "}
                      of {blocks.filter((b) => b.kind !== "break").length}
                    </small>
                  </strong>
                </div>
                <div className="card">
                  <p>Evidence to review</p>
                  <strong>
                    {evidence.length}
                    <small> clues, not verdicts</small>
                  </strong>
                </div>
              </div>
              <div className="card">
                <h2>Planned and observed</h2>
                <p className="muted">
                  Elapsed sessions are self-reported. Files, commits and
                  messages can suggest activity; they cannot prove attention or
                  completion.
                </p>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Task</th>
                        <th>Planned</th>
                        <th>Recorded</th>
                        <th>Outcome</th>
                      </tr>
                    </thead>
                    <tbody>
                      {blocks
                        .filter((b) => b.kind !== "break")
                        .map((b) => (
                          <tr key={b.id}>
                            <td>{b.title}</td>
                            <td>{b.minutes} min</td>
                            <td>
                              {b.actualMinutes === undefined
                                ? "Unknown"
                                : `${b.actualMinutes} min`}
                            </td>
                            <td>
                              {b.status === "done"
                                ? "Session complete"
                                : b.status === "skipped"
                                  ? "Set aside"
                                  : "Not confirmed"}
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
              <div className="section-heading">
                <h2>What the evidence suggests</h2>
                <button
                  className="small-button"
                  onClick={() => setModal("evidence")}
                >
                  <Plus size={16} /> Record what happened
                </button>
              </div>
              {state.evidence
                .slice()
                .reverse()
                .map((e) => (
                  <div className="card evidence-row" key={e.id}>
                    <span className="source-icon">
                      <Monitor size={20} />
                    </span>
                    <div>
                      <span className="tag">
                        {e.source} · {e.confidence} confidence
                      </span>
                      <p>{e.summary}</p>
                      <small>
                        {new Date(e.observedAt).toLocaleString("en-GB")} ·{" "}
                        {e.status}
                      </small>
                    </div>
                    {e.status === "unreviewed" && (
                      <div className="card-actions">
                        <button
                          className="small-button"
                          onClick={() =>
                            act("reviewEvidence", {
                              id: e.id,
                              status: "confirmed",
                            })
                          }
                        >
                          That’s right
                        </button>
                        <button
                          className="text-button"
                          onClick={() =>
                            act("reviewEvidence", {
                              id: e.id,
                              status: "dismissed",
                            })
                          }
                        >
                          Dismiss
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              {!state.evidence.length && (
                <div className="card empty">
                  <p>No observed activity yet. Unknown time stays unknown.</p>
                </div>
              )}
            </>
          )}
          {view === "Connections" && (
            <>
              <div className="connection-banner">
                <ShieldCheck />
                <div>
                  <strong>Public code. Private life.</strong>
                  <p>
                    Your plans, messages and activity are held separately from
                    the open-source repository. Each laptop needs its own
                    revocable connection.
                  </p>
                </div>
              </div>
              <div className="goals-grid">
                {[
                  [
                    "Gmail",
                    "Background OAuth connection not set up. Reviewed snapshots appear in Review.",
                  ],
                  [
                    "WhatsApp",
                    "Capture selected messages from WhatsApp Web for review. Background chat monitoring is not connected.",
                  ],
                  [
                    "NHS",
                    "Reviewed appointment snapshots only. Open NHS for current records; no background clinical-record access.",
                  ],
                  [
                    "Codex projects",
                    "Local metadata collector available. A project inventory has been reviewed.",
                  ],
                  [
                    "Claude Cowork",
                    "Selected export folders only. Configure on each MacBook.",
                  ],
                  [
                    "Work in Chrome",
                    "Jira, Confluence, Outlook and Slack need the work browser and approved capture setup.",
                  ],
                  [
                    "Downloads",
                    "Opt-in filenames and modification times. File contents are excluded.",
                  ],
                  [
                    "smile & Co-operative Bank",
                    "Not connected. Read-only Open Banking provider and bank-side consent required.",
                  ],
                ].map(([title, desc]) => (
                  <section className="card connection" key={title}>
                    <div className="section-heading">
                      <h3>{title}</h3>
                      <span className="tag">
                        {(title === "Downloads" &&
                          state.evidence.some(
                            (e) => e.source === "downloads",
                          )) ||
                        (title === "Codex projects" &&
                          state.evidence.some((e) => e.source === "codex")) ||
                        (title === "WhatsApp" &&
                          state.evidence.some(
                            (e) => e.source === "whatsapp",
                          )) ||
                        (title === "NHS" &&
                          state.evidence.some((e) => e.source === "nhs"))
                          ? "Evidence received"
                          : "Setup needed"}
                      </span>
                    </div>
                    <p>{desc}</p>
                  </section>
                ))}
              </div>
              <div className="section-heading">
                <h2>Your laptops</h2>
                <button
                  className="small-button"
                  onClick={() => setModal("device")}
                >
                  <Plus size={16} /> Pair a laptop
                </button>
              </div>
              {state.devices.map((d) => (
                <div key={d.id} className="card device-row">
                  <Monitor />
                  <div>
                    <strong>{d.name}</strong>
                    <p>
                      {d.os} ·{" "}
                      {d.revoked
                        ? "Access revoked"
                        : d.lastSeen
                          ? `Last seen ${new Date(d.lastSeen).toLocaleString("en-GB")}`
                          : "Waiting for companion"}
                    </p>
                  </div>
                  <button
                    className="text-button"
                    disabled={d.revoked}
                    onClick={() => act("revokeDevice", { id: d.id })}
                  >
                    Revoke access
                  </button>
                </div>
              ))}
              {deviceToken && (
                <div className="notice">
                  <div>
                    <strong>One-time pairing key</strong>
                    <p>
                      Use this only in the companion’s pairing prompt. It grants
                      the permissions you selected. Store it in the laptop’s
                      credential manager.
                    </p>
                    <code className="token">{deviceToken}</code>
                    <button
                      className="small-button"
                      onClick={() => setDeviceToken("")}
                    >
                      Hide key
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
          {view === "Preferences" && (
            <>
              <div className="settings-grid">
                <form
                  className="card"
                  onSubmit={(e) =>
                    save(e, "settings", (d) => ({
                      focusMinutes: Number(d.focus),
                      bufferMinutes: Number(d.buffer),
                      dayStart: mins(String(d.start)),
                      dayEnd: mins(String(d.end)),
                      maxPriorities: Number(d.max),
                    }))
                  }
                >
                  <h2>A sustainable rhythm</h2>
                  <label>
                    Focus session (minutes)
                    <input
                      name="focus"
                      type="number"
                      min="5"
                      max="60"
                      defaultValue={state.settings.focusMinutes}
                    />
                  </label>
                  <label>
                    Breathing room (minutes)
                    <input
                      name="buffer"
                      type="number"
                      min="5"
                      max="60"
                      defaultValue={state.settings.bufferMinutes}
                    />
                  </label>
                  <div className="form-row">
                    <label>
                      Start of day
                      <input
                        name="start"
                        type="time"
                        defaultValue={time(state.settings.dayStart)}
                      />
                    </label>
                    <label>
                      End of day
                      <input
                        name="end"
                        type="time"
                        defaultValue={time(state.settings.dayEnd)}
                      />
                    </label>
                  </div>
                  <label>
                    Maximum priorities per day
                    <input
                      name="max"
                      type="number"
                      min="1"
                      max="5"
                      defaultValue={state.settings.maxPriorities}
                    />
                  </label>
                  <button className="primary" disabled={busy}>
                    Save my rhythm
                  </button>
                </form>
                <section className="card">
                  <h2>You remain in control.</h2>
                  <p>
                    Quiet by default. No notification permission, no streak
                    penalties, no background screenshots, no inferred diagnoses.
                  </p>
                  <p>
                    A little energy means one priority. Tasks start small and
                    have a stopping point. You can park anything.
                  </p>
                  <div className="line" />
                  <h3>Your data</h3>
                  <p>
                    New collection stops when paused. Device evidence is pruned
                    to 30 days on ingestion. Exports contain private
                    information.
                  </p>
                  <button className="small-button" onClick={exportData}>
                    <Download size={16} /> Export my private data
                  </button>
                  <button
                    className="text-button danger"
                    onClick={() => setModal("purge")}
                  >
                    Delete observed activity
                  </button>
                </section>
              </div>
            </>
          )}
          <footer className="page-footer">
            <span>
              <Leaf size={14} /> A plan is an invitation. You can change your
              mind.
            </span>
            <span>
              {config.mode === "aws"
                ? "Your private AWS space"
                : "Saved on this laptop"}{" "}
              · London time
            </span>
          </footer>
        </main>
      </div>
      {modal && (
        <div
          className="modal-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget) setModal("");
          }}
        >
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-label={
              modal === "task" ? "Capture a next step" : "Edit your space"
            }
          >
            <button
              className="modal-close icon-button"
              aria-label="Close dialog"
              onClick={() => setModal("")}
            >
              <X />
            </button>
            {modal === "task" && (
              <form
                onSubmit={(e) =>
                  save(e, editing ? "editTask" : "addTask", (d) => ({
                    ...d,
                    ...(editing ? { id: editing.id } : {}),
                    minutes: Number(d.minutes),
                    priority: Number(d.priority),
                  }))
                }
              >
                <p className="eyebrow">MAKE IT CONCRETE</p>
                <h2>
                  {editing ? "Edit this next step" : "Get it out of your head."}
                </h2>
                <label>
                  What needs doing?
                  <input
                    autoFocus
                    name="title"
                    required
                    maxLength={180}
                    defaultValue={editing?.title}
                  />
                </label>
                <div className="form-row">
                  <label>
                    Area
                    <select
                      name="category"
                      defaultValue={editing?.category || "project"}
                    >
                      <option value="project">Finish a project</option>
                      <option value="prep">Meeting preparation</option>
                      <option value="development">Development goal</option>
                      <option value="personal">Personal life</option>
                    </select>
                  </label>
                  <label>
                    Minutes
                    <input
                      name="minutes"
                      type="number"
                      min="5"
                      max="480"
                      defaultValue={editing?.minutes || 25}
                    />
                  </label>
                </div>
                <label>
                  The first small step
                  <textarea name="nextStep" defaultValue={editing?.nextStep} />
                </label>
                <label>
                  I can stop when…
                  <textarea name="doneWhen" defaultValue={editing?.doneWhen} />
                </label>
                <div className="form-row">
                  <label>
                    Priority
                    <select
                      name="priority"
                      defaultValue={editing?.priority || 2}
                    >
                      <option value="3">Important</option>
                      <option value="2">Normal</option>
                      <option value="1">Whenever there’s room</option>
                    </select>
                  </label>
                  <label>
                    Due (optional)
                    <input type="date" name="due" defaultValue={editing?.due} />
                  </label>
                </div>
                <button className="primary" disabled={busy}>
                  Save next step
                </button>
              </form>
            )}
            {modal === "event" && (
              <form
                onSubmit={(e) =>
                  save(e, "addEvent", (d) => ({
                    ...d,
                    start: mins(String(d.start)),
                    minutes: Number(d.minutes),
                    prepMinutes: Number(d.prepMinutes),
                    confirmed: true,
                  }))
                }
              >
                <h2>Protect an appointment.</h2>
                <label>
                  What’s happening?
                  <input autoFocus name="title" required />
                </label>
                <div className="form-row">
                  <label>
                    Date
                    <input
                      type="date"
                      name="date"
                      defaultValue={date}
                      required
                    />
                  </label>
                  <label>
                    Time
                    <input
                      type="time"
                      name="start"
                      defaultValue="10:00"
                      required
                    />
                  </label>
                </div>
                <div className="form-row">
                  <label>
                    Duration (minutes)
                    <input
                      name="minutes"
                      type="number"
                      defaultValue="60"
                      min="5"
                      max="720"
                    />
                  </label>
                  <label>
                    Preparation (minutes)
                    <input
                      name="prepMinutes"
                      type="number"
                      defaultValue="20"
                      min="0"
                      max="120"
                    />
                  </label>
                </div>
                <button className="primary" disabled={busy}>
                  Save appointment
                </button>
              </form>
            )}
            {modal === "goal" && (
              <form onSubmit={(e) => save(e, "addGoal", (d) => d)}>
                <h2>Choose a meaningful outcome.</h2>
                <label>
                  What would you like to achieve?
                  <input name="title" required autoFocus />
                </label>
                <label>
                  What would success look like?
                  <textarea name="outcome" required />
                </label>
                <label>
                  Horizon
                  <select name="horizon" defaultValue={horizon.toLowerCase()}>
                    <option value="month">Month</option>
                    <option value="year">Year</option>
                  </select>
                </label>
                <label>
                  Target date
                  <input type="date" name="due" />
                </label>
                <button className="primary">Save outcome</button>
              </form>
            )}
            {modal === "block" &&
              (() => {
                const b = state.plan.find((b) => b.id === message);
                return (
                  b && (
                    <form
                      onSubmit={(e) =>
                        save(e, "block", (d) => ({
                          id: b.id,
                          start: mins(String(d.start)),
                          locked: true,
                        }))
                      }
                    >
                      <span className="tag">
                        {b.kind} · {b.minutes} min
                      </span>
                      <h2>{b.title}</h2>
                      <p>{b.reason}</p>
                      <label>
                        Start time
                        <input
                          name="start"
                          type="time"
                          defaultValue={time(b.start)}
                          required
                        />
                      </label>
                      <button className="primary" disabled={busy}>
                        Move & keep this time
                      </button>
                      <div className="card-actions">
                        <button
                          type="button"
                          className="small-button"
                          onClick={() => {
                            act("block", { id: b.id, locked: !b.locked });
                            setModal("");
                          }}
                        >
                          {b.locked ? "Allow replanning" : "Keep this time"}
                        </button>
                        {b.kind !== "event" && (
                          <button
                            type="button"
                            className="text-button"
                            onClick={() => {
                              act("block", { id: b.id, status: "skipped" });
                              setModal("");
                            }}
                          >
                            Set aside
                          </button>
                        )}
                      </div>
                    </form>
                  )
                );
              })()}
            {modal === "evidence" && (
              <form
                onSubmit={(e) =>
                  save(e, "addEvidence", (d) => ({
                    ...d,
                    source: "manual",
                    confidence: "high",
                    observedAt: new Date().toISOString(),
                  }))
                }
              >
                <h2>What happened?</h2>
                <p>
                  Record a useful result or a change of plan, without scoring
                  yourself.
                </p>
                <label>
                  Your note
                  <textarea autoFocus name="summary" required maxLength={800} />
                </label>
                <button className="primary">Save observation</button>
              </form>
            )}
            {modal === "device" && (
              <form
                onSubmit={(e) =>
                  save(e, "pairDevice", (d) => ({
                    ...d,
                    planner: d.planner === "on",
                  }))
                }
              >
                <h2>Pair a laptop.</h2>
                <p>
                  This grants access to upload selected activity summaries.
                  Optionally allow this laptop to read task briefs and propose
                  their order.
                </p>
                <label>
                  Laptop name
                  <input
                    autoFocus
                    name="name"
                    required
                    maxLength={80}
                    placeholder="Personal MacBook"
                  />
                </label>
                <label>
                  Operating system
                  <select name="os">
                    <option>macOS</option>
                    <option>Windows</option>
                  </select>
                </label>
                <label className="checkbox-label">
                  <input type="checkbox" name="planner" /> Allow Codex planning
                  on this laptop (task briefs only)
                </label>
                <button className="primary">Create pairing key</button>
              </form>
            )}
            {modal === "purge" && (
              <>
                <h2>Delete observed activity?</h2>
                <p>
                  This removes the activity held by Clara. Tasks and plans
                  remain. Export first if you want a copy.
                </p>
                <button
                  className="primary"
                  onClick={async () => {
                    await act("purgeEvidence");
                    setModal("");
                  }}
                >
                  Delete activity
                </button>
              </>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
function MeetingCard({
  meeting: e,
  onSave,
}: {
  meeting: Meeting;
  onSave: (notes: string) => unknown;
}) {
  const [notes, setNotes] = useState(e.notes);
  return (
    <form
      className="card meeting-card"
      onSubmit={(ev) => {
        ev.preventDefault();
        onSave(notes);
      }}
    >
      <span className="tag">
        {e.date} · {time(e.start)} · {e.minutes} min
      </span>
      <h2>{e.title}</h2>
      <p className="muted">
        {e.prepMinutes} minutes reserved for preparation when planning.
      </p>
      <ol className="prep-checklist">
        <li>What is this meeting for?</li>
        <li>What do I need to understand beforehand?</li>
        <li>What decision or contribution is needed from me?</li>
        <li>Which questions should I bring?</li>
        <li>What should I capture before leaving?</li>
      </ol>
      <label>
        Your briefing & questions
        <textarea
          rows={5}
          value={notes}
          maxLength={2000}
          onChange={(ev) => setNotes(ev.target.value)}
          placeholder="Purpose, links to read, what is still unclear…"
        />
      </label>
      <small className="source">Source: {e.source}</small>
      <button className="small-button">
        <Check size={15} />
        {e.confirmed ? "Update briefing" : "Save briefing & confirm details"}
      </button>
    </form>
  );
}
function MonthGrid({
  date,
  state,
  onSelect,
}: {
  date: string;
  state: State;
  onSelect: (d: string) => void;
}) {
  const first = date.slice(0, 7) + "-01";
  const dt = new Date(first + "T12:00:00");
  const offset = (dt.getDay() + 6) % 7;
  const count = new Date(dt.getFullYear(), dt.getMonth() + 1, 0).getDate();
  return (
    <div className="month-calendar">
      {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((x) => (
        <div className="calendar-label" key={x}>
          {x}
        </div>
      ))}
      {Array.from({ length: offset }, (_, i) => (
        <div className="calendar-blank" key={"b" + i} />
      ))}
      {Array.from({ length: count }, (_, i) => addDays(first, i)).map((d) => (
        <button
          key={d}
          className={"calendar-day " + (d === today() ? "is-today" : "")}
          onClick={() => onSelect(d)}
        >
          <strong>{Number(d.slice(-2))}</strong>
          {state.events
            .filter((e) => e.date === d)
            .slice(0, 2)
            .map((e) => (
              <span key={e.id}>
                {time(e.start)} {e.title}
              </span>
            ))}
          <small>
            {state.plan.filter((b) => b.date === d && b.taskId).length || ""}
            {state.plan.some((b) => b.date === d && b.taskId)
              ? " focus blocks"
              : ""}
          </small>
        </button>
      ))}
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
