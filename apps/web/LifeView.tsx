import {
  Moon,
  Heart,
  Mail,
  Users,
  Sprout,
  ArrowUpRight,
  Check,
  ShieldCheck,
} from "lucide-react";
import type { State, Task } from "./api";
const areas = [
  {
    id: "sleep",
    title: "More room for sleep",
    icon: Moon,
    description:
      "Protect a wind-down and sleep opportunity. Review the trend and how you feel; a watch score is only one clue.",
    status: "Watch data not connected",
  },
  {
    id: "health",
    title: "Keep up with your health",
    icon: Heart,
    description:
      "Check appointments, messages and agreed follow-up. Keep only the next action here, with clinical details in the health service.",
    status: "NHS login required",
  },
  {
    id: "inbox",
    title: "Fewer distractions",
    icon: Mail,
    description:
      "Reduce obvious promotions while keeping the messages that support your life and work. Choose unsubscribe rules deliberately.",
    status: "Cleanup happens only within your instructions",
  },
  {
    id: "social",
    title: "People, pleasure & time away",
    icon: Users,
    description:
      "Make room for enjoyable contact, a familiar shared activity and something to look forward to. Recovery time belongs alongside social time.",
    status: "No events or travel booked automatically",
  },
  {
    id: "business",
    title: "A more secure future",
    icon: Sprout,
    description:
      "Explore a small business opportunity through real customer needs, a clear role for each person and a modest test before committing money.",
    status: "Ideas to investigate, not income promises",
  },
];
export function LifeView({
  state,
  act,
  onEdit,
}: {
  state: State;
  act: (action: string, data?: unknown) => Promise<unknown>;
  onEdit: (task: Task) => void;
}) {
  return (
    <>
      <div className="connection-banner">
        <ShieldCheck />
        <div>
          <strong>These are part of your life, not five extra jobs.</strong>
          <p>
            Clara keeps the next step for each area visible. Your daily capacity
            still applies; new priorities do not add unlimited tasks to the day.
          </p>
        </div>
      </div>
      <div className="life-grid">
        {areas.map((area) => {
          const tasks = state.tasks.filter((t) => t.lifeArea === area.id);
          return (
            <section className={"card life-card " + area.id} key={area.id}>
              <div className="life-heading">
                <span className="source-icon">
                  <area.icon size={22} />
                </span>
                <div>
                  <h2>{area.title}</h2>
                  <small>
                    {area.id === "health" &&
                    state.evidence.some((e) => e.source === "nhs")
                      ? "Appointment snapshot reviewed · check NHS for changes"
                      : area.status}
                  </small>
                </div>
              </div>
              <p className="muted">{area.description}</p>
              {tasks.length ? (
                tasks.map((t) => (
                  <div className="life-task" key={t.id}>
                    <span className="tag">
                      {t.status === "done"
                        ? "Step complete"
                        : `${t.minutes} minute next step`}
                    </span>
                    <h3>{t.title}</h3>
                    <p>{t.nextStep}</p>
                    <div className="definition">
                      <strong>Enough for this step</strong>
                      <p>{t.doneWhen}</p>
                    </div>
                    <div className="card-actions">
                      <button className="text-button" onClick={() => onEdit(t)}>
                        Adjust this step <ArrowUpRight size={16} />
                      </button>
                      <button
                        className="small-button"
                        onClick={() =>
                          act("taskStatus", {
                            id: t.id,
                            status: t.status === "done" ? "open" : "done",
                          })
                        }
                      >
                        <Check size={16} />
                        {t.status === "done" ? "Reopen" : "Step finished"}
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <p className="muted">No next step chosen yet.</p>
              )}
              {area.id === "health" && (
                <a
                  className="resource-link"
                  href="https://www.nhs.uk/nhs-app/account/"
                  target="_blank"
                  rel="noreferrer"
                >
                  Open NHS App services <ArrowUpRight size={15} />
                </a>
              )}
              {area.id === "sleep" && (
                <a
                  className="resource-link"
                  href="https://www.nhs.uk/every-mind-matters/mental-wellbeing-tips/how-to-fall-asleep-faster-and-sleep-better/"
                  target="_blank"
                  rel="noreferrer"
                >
                  NHS guidance on sleep routines <ArrowUpRight size={15} />
                </a>
              )}
            </section>
          );
        })}
      </div>
    </>
  );
}
